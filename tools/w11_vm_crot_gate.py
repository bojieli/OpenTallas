#!/usr/bin/env python3
"""W11: exactness, per-op latency and die-decode gate of the C_ROTATE vector memory (root ruling 2026-10-01).

C_rotate (rtl/chip/ot_v41_vm_crot.sv): one central banked VM strip (SU_W | VM strip | SU_E) with a rotate network
between the bank array and the stream unit's lanes.  Every SU op pays the strip round trip; no per-op class
decision, no layout rule.  Opt-in (VM_DIST = 1, VM_CROT = 1); the default build is the flat memory, unchanged.

The stream unit is built with its lanes reading CR_RD cycles after the strip's read (ot_hdc_v41x_vec
BCAST_STAGES = CR_LEAD + CR_RD, RD_LEAD = CR_LEAD: its own consumers' credits lead the landing by CR_LEAD), writing
elements CR_WR and results CR_RES later, a gathered A held CR_GX more; the strip counts LEAD HAZARDS (an SU
operand read whose word landed in the CR_RD cycles before it), which must be 0: then every value the bench reads
is the value the pipelined strip read.

Parts:
  su     tools/rtl_hdc_v41x_vec_campaign.py random (N16/M8 x 24 seeds, N64/M16 x 16 seeds), vehicle (N64/M16, every
         stream op of the reduced vehicle, builder alignment as today: C_rotate has no layout rule), perf64, and the
         attention softmax chain of tools/w11_su_softmax_spec.py (serial_vec and chained, T128 / T640) at N16/M8,
         each with the flat memory (VM_DIST = 0) and C_rotate on the same programs (tools/w11_vm_dist_gate.su_part).
  lat    measured per-op latency: chains of K dependent ops of one class at N64/M16 (and N1024/M256 with --n1024),
         flat vs C_rotate: cycles per dependent op, and the C_rotate extra per op.
  die    the reduced V4.1 decode step through the die top (tools/w11_vm_dist_die_gate.py's bench and build):
         token 3118 against the golden, every logit, the whole VM and KV against the ISA model, 0 lead hazards;
         cycles against the flat memory on the same image.

Stage set: results/floorplan/v41_vm_crot_stages.json (tools/w11_vm_crot_stages.py, from W18b's measured hub
distances and W15's SS wire reach), or --stages KEY=V,....

Writes results/rtl/w11_vm_crot_gate_<parts>.json (new records; never overwrites).
    python3 tools/w11_vm_crot_gate.py --scratch DIR --parts su,lat [--die-image DIR] [--jobs 16]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402
import hdc_isa_v41 as I                    # noqa: E402
import w11_vm_dist_gate as G               # noqa: E402
import w11_su_softmax_spec as SM           # noqa: E402

STAGES_REC = ROOT / "results/floorplan/v41_vm_crot_stages.json"
CROT = [ROOT / "rtl/chip/ot_v41_vm_crot.sv", ROOT / "rtl/v41rom/ot_v41_ret.sv",
        # the stream unit's serial-build primitives (MLAT / ALAT > 3), absent from the die's source list
        ROOT / "rtl/hdc/ot_hdc_fp32_add_lat.sv", ROOT / "rtl/hdc/ot_hdc_fp32_mul_lat.sv", ROOT / "rtl/hdc/ot_hdc_prefix.sv"]
VMCROT = re.compile(r"VMCROT roots=(\d+) rows=(\d+) nonlocal=(\d+) e=(\d+) wr_nonlocal=(\d+) cr_rd=(\d+) "
                    r"lead_hazards=(\d+)")
SU_KEYS = ("CR_LEAD", "CR_RD", "CR_GX", "CR_WR", "CR_RES")
SOURCES = ["rtl/chip/ot_v41_vm_crot.sv", "rtl/v41rom/ot_v41_ret.sv", "rtl/chip/ot_v41_vm_dist.sv",
           "rtl/chip/ot_v41_vm_dist_group.sv", "rtl/chip/ot_v41_vm_dist_bank.sv", "rtl/chip/ot_v41_vm_dist_pipe.sv",
           "rtl/hdc/v41x/ot_hdc_v41x_vec.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv",
           "rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv", "rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv",
           "rtl/hdc/v41x/ot_hdc_core_v41x.sv", "rtl/chip/ot_chip_v41x_tile.sv", "rtl/chip/ot_chip_v41x_die.sv",
           "rtl/test/tb_hdc_v41x_vec.sv", "rtl/test/tb_chip_v41x_die_vmdist.sv", "tools/rtl_hdc_v41x_vec_campaign.py",
           "tools/w11_vm_dist_gate.py", "tools/w11_vm_dist_die_gate.py", "tools/w11_su_softmax_spec.py",
           "tools/w11_vm_crot_gate.py", "results/floorplan/v41_vm_crot_stages.json"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def crot_set(over: str = "", stage_set: str = "") -> dict:
    st = {}
    if STAGES_REC.exists():
        rec = json.loads(STAGES_REC.read_text())
        st.update(rec["rtl_parameters"])
        if stage_set:
            st.update({k: v for k, v in rec["variants"][stage_set].items() if isinstance(v, int)})
    for kv in filter(None, over.split(",")):
        k, v = kv.split("=")
        st[k] = int(v)
    st["VM_CROT"] = 1
    # su_part's flat runs use these too (RET_SCATTER_STAGES on the bench's producer, SU_RES_STAGES unused)
    st.setdefault("SU_RES_STAGES", st.get("CR_RES", 8))
    st.setdefault("RET_SCATTER_STAGES", 8)
    return st


# ---- the vector unit's bench with the strip --------------------------------------------------------------
_flags0 = G.su_flags
LAST = {}                                  # case dir -> the strip's report


SERIAL = dict(mlat=3, alat=3)              # ot_hdc_v41x_vec MLAT / ALAT of the benches (--mlat / --alat)


def su_flags(vd, st):
    f = _flags0(vd, {k: v for k, v in st.items() if k != "VM_DIST_H"})
    if (SERIAL["mlat"], SERIAL["alat"]) != (3, 3):
        f += f" -GMLAT={SERIAL['mlat']} -GALAT={SERIAL['alat']}"
    if vd and st.get("VM_CROT"):
        f += " -GVM_CROT=1 " + " ".join(f"-G{k}={st[k]}" for k in SU_KEYS)
    return f


def crot_fields(text):
    m = VMCROT.search(text or "")
    if not m:
        return None
    g = list(map(int, m.groups()))
    return dict(roots=g[0], rows=g[1], nonlocal_rows=g[2], e=g[3], wr_nonlocal=g[4], cr_rd=g[5], lead_hazards=g[6])


def install():
    G.su_flags = su_flags
    for p in CROT:
        if p not in G.DIST:
            G.DIST.append(p)
    G.su_setup()
    parse0, compare0, run0 = C.parse_trace, C.compare, C.run_case

    def parse(text):
        tr = parse0(text)
        tr["crot"] = crot_fields(text)
        return tr

    def run(exe, d, *a, **k):
        tr = run0(exe, d, *a, **k)
        LAST[str(d)] = tr.get("crot")
        return tr

    def compare(tr, mref):
        c = compare0(tr, mref)
        c["crot"] = tr.get("crot")
        if c["crot"] is not None and c["crot"]["lead_hazards"]:
            c["pass_"] = False
        return c
    C.parse_trace, C.compare, C.run_case = parse, compare, run
    run_one0 = SM.run_one
    build0 = SM.build
    SM.build = lambda *a, **k: build0(*a, **dict(k, mlat=SERIAL["mlat"], alat=SERIAL["alat"]))

    def run_one(exe, d, *a, **k):
        r = run_one0(exe, d, *a, **k)
        r["crot"] = LAST.get(str(d))
        if r["crot"] is not None and r["crot"]["lead_hazards"]:
            r["pass_"] = False
        return r
    SM.run_one = run_one


# ---- measured per-op latency: chains of dependent ops ------------------------------------------------------
def chain_ops(N, cls, K, rng, al, init):
    """K dependent ops of one class: op k reads op k-1's output (op 0 reads a fresh region)."""
    b = C.op_defaults()
    n = N
    if cls == "linear_1vec":                       # y = a * 1.5 (one N-element vector)
        x = al.get(n); init.append((x, C.rand_vals(rng, n, "small")))
        ops, src = [], x
        for _ in range(K):
            o = al.get(n)
            ops.append(dict(b, nout=1, nin=n, abase=src, asi=1, m1=I.M1_AIMM, imm1=C.f32u(0.75), dst=I.DST_VM,
                            obase=o, osi=1))
            src = o
        return ops
    if cls == "linear_4vec":                       # the same over 4 N elements (streaming)
        n = 4 * N
        x = al.get(n); init.append((x, C.rand_vals(rng, n, "small")))
        ops, src = [], x
        for _ in range(K):
            o = al.get(n)
            ops.append(dict(b, nout=1, nin=n, abase=src, asi=1, m1=I.M1_AIMM, imm1=C.f32u(0.75), dst=I.DST_VM,
                            obase=o, osi=1))
            src = o
        return ops
    if cls == "exp_1vec":                          # y = exp(a) chained on 'small' values (bounded by 0.75 scale)
        x = al.get(n); init.append((x, C.rand_vals(rng, n, "small")))
        ops, src = [], x
        for k in range(K):
            o = al.get(n)
            ops.append(dict(b, nout=1, nin=n, abase=src, asi=1, sfu=I.SFU_EXP if k % 2 == 0 else 0,
                            m1=I.M1_AIMM if k % 2 else 0, imm1=C.f32u(-0.5), dst=I.DST_VM, obase=o, osi=1))
            src = o
        return ops
    if cls == "reduce_scale":                      # RMS-norm-like: s = sum(x^2); y = x * s (broadcast B); ...
        x = al.get(n); init.append((x, C.rand_vals(rng, n, "small")))
        ops, src = [], x
        for _ in range(K // 2):
            r = al.get(2)
            ops.append(dict(b, nout=1, nin=n, abase=src, asi=1, red=I.RED_SUM, redsq=1, rbase=r))
            o = al.get(n)
            ops.append(dict(b, nout=1, nin=n, abase=src, asi=1, bbase=r, bsi=0, m1=I.M1_AB, dst=I.DST_VM,
                            obase=o, osi=1))
            src = o
        return ops
    if cls == "gather_1vec":                       # y = a[idx] (IND_I): a is the previous output
        idx = al.get(n); init.append((idx, C.ffrom(rng.permutation(n).astype(np.uint32))))
        x = al.get(n); init.append((x, C.rand_vals(rng, n, "small")))
        ops, src = [], x
        for _ in range(K):
            o = al.get(n)
            ops.append(dict(b, nout=1, nin=n, abase=src, asi=1, aind=I.IND_I, aibase=idx, m1=I.M1_AIMM,
                            imm1=C.f32u(0.75), dst=I.DST_VM, obase=o, osi=1))
            src = o
        return ops
    raise ValueError(cls)


LAT_CLASSES = ("linear_1vec", "linear_4vec", "exp_1vec", "reduce_scale", "gather_1vec")


def lat_part(exes, N, M, scratch: Path, K=16):
    out = {}
    for cls in LAT_CLASSES:
        row = {}
        for tag, exe in exes.items():
            rng = np.random.default_rng(20261001)
            al = C.Alloc(64, (1 << C.VMA) - 64)
            init = []
            ops = chain_ops(N, cls, K, rng, al, init)
            mem0 = C.fresh_mem(rng, init)
            c, tr, sops, lays = C.run_program(exe, scratch / f"lat_{tag}_N{N}_{cls}", mem0, ops, N, M)
            ev = []
            for k in range(len(sops)):
                em, rt, rs = C.op_trace(tr, k)
                ev.append(dict(first_emit=em[0] if em else None, last_write=(rt[-1] if rt else None),
                               last_result=(rs[-1] if rs else None)))
            t0 = ev[0]["first_emit"]
            done = [max(x for x in (e["last_write"], e["last_result"]) if x is not None) for e in ev]
            # steady state: op k+1's completion - op k's completion, over the second half of the chain
            gaps = [done[k + 1] - done[k] for k in range(len(done) - 1)]
            half = gaps[len(gaps) // 2:]
            row[tag] = dict(ops=len(sops), first_emit=t0, last_done=done[-1], total_cycles=done[-1] - t0,
                            cycles_per_op=(done[-1] - t0) / len(sops),
                            steady_cycles_per_op=float(np.mean(half)), steady_gaps=sorted(set(half)),
                            chained_by_credit=sum(1 for f in sops if f["ch_src"] == C.CH_SELF and f["ch_lead"] > 0),
                            check=c, pass_=c["pass_"])
        if "flat" in row and "crot" in row:
            per = 2 if cls == "reduce_scale" else 1
            row["crot_extra_cycles_per_op"] = round((row["crot"]["steady_cycles_per_op"] -
                                                     row["flat"]["steady_cycles_per_op"]), 3)
            row["crot_extra_cycles_per_dependent_op"] = round((row["crot"]["total_cycles"] -
                                                               row["flat"]["total_cycles"]) / row["crot"]["ops"], 3)
            row["ops_per_step"] = per
        out[cls] = row
        print("lat", N, cls, {k: (v["steady_cycles_per_op"], v["pass_"]) for k, v in row.items() if isinstance(v, dict)},
              row.get("crot_extra_cycles_per_op"), flush=True)
    return out


# ---- the die --------------------------------------------------------------------------------------------
def serial_parts(scratch: Path) -> Path:
    """The die bench runs the FP units on DPI stand-ins (sim_hdc_v41x_fastfp_wrap: ot_hdc_qadd / ot_hdc_qmul); the
    stream unit's serial build (MLAT / ALAT > 3) instantiates the real pipelined primitives, which need the helper
    modules of rtl/hdc/ot_hdc_fastfp.sv.  This copies every module of that file except the two the stand-ins
    provide (a scratch source, regenerated from the pinned file on every run)."""
    import re as _re
    text = (ROOT / "rtl/hdc/ot_hdc_fastfp.sv").read_text()
    mods = _re.findall(r"(^module\s+(\w+).*?^endmodule\b)", text, flags=_re.S | _re.M)
    keep = [m for m, name in mods if name not in ("ot_hdc_qadd", "ot_hdc_qmul")]
    out = scratch / "ot_hdc_fastfp_serial_parts.sv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("`timescale 1ns/1ps\n// generated by tools/w11_vm_crot_gate.serial_parts from rtl/hdc/ot_hdc_fastfp.sv\n" +
                   "\n".join(keep) + "\n")
    return out


def die_part(scratch: Path, image: Path | None, st: dict, jobs: int, variants=("flat", "crot")):
    """The reduced decode step (token 3582 at position 7 -> 3118) through the die bench, flat vs C_rotate."""
    import w11_vm_dist_die_gate as D
    G.ds.setup("dpi")
    for p in CROT + ([serial_parts(scratch)] if (SERIAL["mlat"], SERIAL["alat"]) != (3, 3) else []):
        if p not in G.DIST:
            G.DIST.append(p)
    die_st = dict(VM_DIST_H=0, VM_CROT=1, X_GATHER_STAGES=st["X_GATHER_STAGES"],
                  RET_SCATTER_STAGES=st["RET_SCATTER_STAGES"], COLL_WRITE_STAGES=st["COLL_WRITE_STAGES"],
                  SU_RES_STAGES=st["CR_RES"], **{k: st[k] for k in SU_KEYS})
    img = image or scratch / "img_pos7"
    with cf.ThreadPoolExecutor(3) as ex:
        fi = None if (img / "run.args").exists() else ex.submit(G.core.images, img, "--hbm")
        extra = [f"-GSU_MLAT={SERIAL['mlat']}", f"-GSU_ALAT={SERIAL['alat']}"]
        tag = f"m{SERIAL['mlat']}a{SERIAL['alat']}"
        futs = {v: ex.submit(D.build, scratch / f"die_{v}_{tag}", 0 if v == "flat" else 1, {} if v == "flat" else die_st,
                             jobs, extra) for v in variants}
        if fi is not None:
            fi.result()
        built = {v: f.result() for v, f in futs.items()}
    with cf.ThreadPoolExecutor(len(built)) as ex:
        res = dict(zip(built, ex.map(lambda v: G.die_run(built[v][0], img), built)))
    for v, r in res.items():
        log = r.pop("_log", "")
        r["build"] = built[v][1]
        r["crot"] = crot_fields(log)
        if v != "flat":
            if r["crot"] is None or r["crot"]["lead_hazards"]:
                r["status"] = "fail"
    f, c = res.get("flat"), res.get("crot")
    if f and c and f.get("status") == "pass" and c.get("status") == "pass":
        c["token_identical_to_flat"] = c["step"]["next_token"] == f["step"]["next_token"]
        c["cycle_delta_vs_flat"] = c["step"]["cycles"] - f["step"]["cycles"]
        iss = c["issues"]
        xg = iss["me"] + iss["qe"] + iss["xu"] + iss["he"]
        c["x_gather_issue_cycles"] = xg * die_st["X_GATHER_STAGES"]
        c["cycle_delta_beyond_x_gather"] = c["cycle_delta_vs_flat"] - c["x_gather_issue_cycles"]
        c["su_ops"] = iss["su"]
        c["cycle_delta_beyond_x_gather_per_su_op"] = round(c["cycle_delta_beyond_x_gather"] / max(1, iss["su"]), 3)
    return dict(stages=die_st, su_mlat=SERIAL["mlat"], su_alat=SERIAL["alat"], image=str(img), image_sha256={n: G.sha(img / n) for n in sorted(os.listdir(img))
                                                             if n.endswith((".hex", ".json", ".args"))},
                runs=res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--parts", default="su,lat")
    ap.add_argument("--stages", default="", help="override KEY=V,... (CR_LEAD, CR_RD, CR_GX, CR_WR, CR_RES, ...)")
    ap.add_argument("--n1024", action="store_true", help="lat also at N1024/M256")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--die-image", type=Path)
    ap.add_argument("--stage-set", default="", help="a variants key of results/floorplan/v41_vm_crot_stages.json "
                                                     "(e.g. square_hub) in place of rtl_parameters")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--mlat", type=int, default=3, help="ot_hdc_v41x_vec MLAT (the serial build: 5)")
    ap.add_argument("--alat", type=int, default=3, help="ot_hdc_v41x_vec ALAT (the serial build: 4)")
    a = ap.parse_args()
    SERIAL.update(mlat=a.mlat, alat=a.alat)
    C.set_mlat(a.mlat, a.alat)
    a.scratch.mkdir(parents=True, exist_ok=True)
    st = crot_set(a.stages, a.stage_set)
    parts = a.parts.split(",")
    install()
    t0 = time.time()
    rec = dict(schema="opentallas.rtl.w11_vm_crot_gate.v1", parts=parts, stages=st, stage_set=a.stage_set or "rtl_parameters",
               mlat=a.mlat, alat=a.alat,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               host=socket.gethostname(), git_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                                   capture_output=True, text=True).stdout.strip(),
               git_dirty_tracked_files=subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=ROOT,
                                                      capture_output=True, text=True).stdout.split())
    ok = True
    if "su" in parts:
        su = G.su_part(a.scratch / "su", st, False, a.jobs, small=True)
        rec["su"] = su
        cases = [x for c in su["campaigns"].values() for v in c.values() if isinstance(v, list) for x in v]
        sm = [x for c in su["softmax"].values() for x in c.values()]
        rec["su_summary"] = dict(cases=len(cases), passed=sum(x["pass_"] for x in cases),
                                 softmax=len(sm), softmax_passed=sum(bool(x["pass_"]) for x in sm),
                                 lead_hazards=sum((x.get("crot") or {}).get("lead_hazards", 0) for x in cases + sm))
        ok &= rec["su_summary"]["passed"] == len(cases) and rec["su_summary"]["softmax_passed"] == len(sm)
        print("su", rec["su_summary"], flush=True)
    if "lat" in parts:
        rec["lat"] = {}
        cfgs = [(64, 16)] + ([(1024, 256)] if a.n1024 else [])
        for N, M in cfgs:
            with cf.ThreadPoolExecutor(2) as ex:
                fl = ex.submit(G.su_build, N, M, a.scratch / f"lat_vd0_N{N}", 0, st)
                cr = ex.submit(G.su_build, N, M, a.scratch / f"lat_vd1_N{N}", 1, st)
                exes = dict(flat=fl.result()[0], crot=cr.result()[0])
            rec["lat"][f"N{N}_M{M}"] = lat_part(exes, N, M, a.scratch)
            ok &= all(v["pass_"] for r in rec["lat"][f"N{N}_M{M}"].values() for v in r.values() if isinstance(v, dict))
    if "die" in parts:
        rec["die"] = die_part(a.scratch, a.die_image, st, a.jobs)
        ok &= all(v.get("status") == "pass" for v in rec["die"]["runs"].values()) and \
            rec["die"]["runs"].get("crot", {}).get("token_identical_to_flat", False)
    rec["status"] = "pass" if ok else "fail"
    rec["wall_seconds"] = round(time.time() - t0)
    rec["source_sha256"] = {s: sha(ROOT / s) for s in SOURCES if (ROOT / s).exists()}
    tag = ("" if (a.mlat, a.alat) == (3, 3) else f"_m{a.mlat}a{a.alat}") + (f"_{a.stage_set}" if a.stage_set else "")
    out = a.out or ROOT / f"results/rtl/w11_vm_crot_gate_{'_'.join(parts)}{tag}.json"
    if out.exists():
        out = out.with_name(out.stem + "_" + datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + ".json")
    out.write_text(json.dumps(rec, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print("wrote", out, rec["status"], flush=True)


if __name__ == "__main__":
    main()
