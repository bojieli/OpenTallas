#!/usr/bin/env python3
"""CF-SM on hbm-sim's Qwen vectors: the full hierarchical SM element (ot_hbm_accel_smh, ENABLE_INT8 = 1) running
SM.MATVEC format 3 (INT8 rows, raw FP32 sums) on the operands the HGI simulator itself fed its SM.MATVEC records while
proving a Qwen3-8B layer / the LM head bit-exact against the qwen_r25 golden (tools/hgi_sim/qwen_proof.py).

  export  (host with the released snapshot + the deployed INT8 image cache + an hbm-sim source tree):
          runs qwen_proof's layer stage (layer L at position P) and head stage with a spy on ("SM", "MATVEC"), keeps the
          proof verdict, and writes for every SM.MATVEC record and every die the activation x, and for chosen SM row
          shares (rows split over the die's 32 SMs in equal contiguous ranges, HGI-1 2.3 / 10.3) the INT8 codes and
          the simulator's raw FP32 outputs.

          python3 tools/qwen_r25_smh_fmt3_bench.py export --sim-root SIMSRC --snapshot SNAP --cache QIMG --out V.npz

  run     replays them on the RTL (rtl/test/tb_hbm_accel_sm_pq_seq.sv, the --smh hierarchical element):
          * every fmt3 op's result row equals the simulator's output bit for bit (and the simulator equals an
            independent recompute with hdc_golden / hdc_golden_v41.csum: the golden's chunk-8 order);
          * CF-SM: every op is also run as fmt 0 on the BF16-widened image and must equal the fmt3 result;
          * edge rows (all -128, all +127, all 0, alternating -128/+127) on the real activation;
          * interleaved fmt3 / fmt0 independent ops (the adapter bypass and drain ordering, CF-1), or --serial;
          * --mut-sign builds the adapter's sign-drop mutant (OT_INT8_MUT_SIGN) and must FAIL (--expect-fail).

          python3 tools/qwen_r25_smh_fmt3_bench.py run --vectors V.npz --pipe 1 --out R.json --workdir W
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402

F = np.float32
NSM = 32                       # SMs per die (HGI-1 2.3)
NW = 10
SM_PICK = {0: (0,), 1: (13,), 2: (22,), 3: (31,)}      # die -> SM indices whose row share is exported


# ------------------------------------------------------------------------------------------------------------------
# export
# ------------------------------------------------------------------------------------------------------------------
def cmd_export(a):
    sys.path.insert(0, str(Path(a.sim_root) / "tools"))
    import hgi_sim.machine as MM
    from hgi_sim import qwen_proof as QP
    import qwen_r25_golden as R

    cap = {}
    orig = MM.UNITS[("SM", "MATVEC")]

    def spy(M, r, L):
        orig(M, r, L)
        fmt = r.param & 3
        for d, die in enumerate(M.dies):
            x = np.asarray(M.read(r.desc["A"], die, L), dtype=F).copy()
            raw = np.asarray(M.hbm_rows_raw(r.desc["B"], die, L))
            out = np.asarray(M.read(r.desc["O"], die, L), dtype=F).copy()
            nrows = raw.shape[0]
            assert fmt == 3 and out.size == nrows, (r.tag, fmt, out.size, nrows)
            key = f"{a.stage_tag}{r.tag}.L{L}.d{d}"
            share = nrows / NSM
            for s in SM_PICK[d]:
                r0, r1 = int(round(s * share)), int(round((s + 1) * share))
                cap[f"{key}.sm{s}"] = dict(x=x, codes=np.ascontiguousarray(raw[r0:r1]).view(np.int8).copy(),
                                           out=out[r0:r1].copy(), rows=(r0, r1), total_rows=nrows, tag=r.tag)
    MM.UNITS[("SM", "MATVEC")] = spy
    model = R.QwenR25(Path(a.snapshot), Path(a.cache))
    cfg = model.ck.cfg
    proofs = []
    for stage in a.stages.split(","):
        a.stage_tag = f"{stage}:"
        res = QP.run_stage(model, cfg, stage, a.layer, a.position)
        proofs.append({k: v for k, v in res.items() if k != "failures"} | dict(failures=res.get("failures", [])[:5]))
        print(stage, "proof", "PASS" if res["pass_"] else "FAIL", flush=True)
    keys = sorted(cap)
    arrays = {}
    meta = []
    for i, k in enumerate(keys):
        c = cap[k]
        arrays[f"x{i}"], arrays[f"c{i}"], arrays[f"o{i}"] = c["x"], c["codes"], c["out"]
        meta.append(dict(key=k, tag=c["tag"], rows=list(c["rows"]), total_rows=c["total_rows"], K=int(c["x"].size)))
    simsrc = Path(a.sim_root) / "tools"
    manifest = dict(schema="opentallas.qwen_r25_smh_fmt3_vectors.v1",
                    generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    host=os.uname().nodename, snapshot=Path(a.snapshot).name, layer=a.layer, position=a.position,
                    proofs=proofs, proofs_pass=all(p["pass_"] for p in proofs), ops=meta,
                    sm_split="rows split over 32 SMs in equal contiguous ranges (row share = round(s*R/32)..)",
                    sim_source_sha256={p: hashlib.sha256((simsrc / p).read_bytes()).hexdigest() for p in (
                        "hgi_sim/lib.py", "hgi_sim/machine.py", "hgi_sim/qwen_compiler.py", "hgi_sim/qwen_proof.py",
                        "hgi_sim/records.py", "qwen_r25_golden.py")})
    arrays["manifest"] = np.frombuffer(json.dumps(manifest, default=int).encode(), dtype=np.uint8)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.out, **arrays)
    Path(a.out).with_suffix(".json").write_text(json.dumps(manifest, indent=1, default=int) + "\n")
    print("exported", len(meta), "SM row shares;", "proofs PASS" if manifest["proofs_pass"] else "proofs FAIL", a.out)
    return 0 if manifest["proofs_pass"] else 1


# ------------------------------------------------------------------------------------------------------------------
# run
# ------------------------------------------------------------------------------------------------------------------
def load_vectors(path):
    z = np.load(path)
    man = json.loads(bytes(z["manifest"]).decode())
    ops = []
    for i, m in enumerate(man["ops"]):
        ops.append(dict(m, x=z[f"x{i}"].astype(F), codes=z[f"c{i}"].astype(np.int8), out=z[f"o{i}"].astype(F)))
    return man, ops


def golden(codes, x):
    """The golden's SM.MATVEC fmt 3: csum8_k(bf16(x)[k] * code[n, k]) -- hdc_golden mul, hdc_golden_v41 csum."""
    import hdc_golden as G
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    return V.csum(G.mul(np.asarray(codes, dtype=F), G.to_bf16(np.asarray(x, dtype=F))[None, :]))


def build_op(MS, codes, x, fmt):
    """Weight lines (issue order, group-slot), x-store words and geometry for one SM op of R rows x K, one active
    column.  fmt 3: two consecutive 64-lane issue beats of INT8 codes per 1,088-bit line, low beat first, sidecar 0
    (rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv, tools/qwen_r25_int8_image.py).  fmt 0: one beat a line of the
    BF16-widened codes (exact)."""
    S = MS.S
    R, K = codes.shape
    c, LA = 8, MS.SUB * MS.LSB
    C = -(-K // c)
    Gn = -(-C // LA)
    assert Gn * c <= MS.XDEPTH and Gn <= 16, (R, K, Gn)
    beats = []
    u8 = np.ascontiguousarray(codes).view(np.uint8)
    wb = S.bf16_bits(codes.astype(F)).astype(np.uint16) if fmt == 0 else None
    lanes = np.arange(LA)
    for r, g, t in S.issue_order(R, Gn, c, True):
        ks = (g * LA + lanes) * c + t
        ok = ks < K
        if fmt == 3:
            b = np.zeros(LA, dtype=np.uint8)
            b[ok] = u8[r, ks[ok]]
        else:
            b = np.zeros(LA, dtype=np.uint16)
            b[ok] = wb[r, ks[ok]]
        beats.append(int.from_bytes(b.astype("<u%d" % b.itemsize).tobytes(), "little"))
    if fmt == 3:
        assert len(beats) % 2 == 0, "fmt3 needs an even count of issue beats"
        lines = [beats[i] | (beats[i + 1] << 512) for i in range(0, len(beats), 2)]
    else:
        lines = beats
    xb = S.bf16_bits(x).astype(np.uint16)
    xw = []
    for adr in range(Gn * c):
        g, t = divmod(adr, c)
        ks = (g * LA + lanes) * c + t
        ok = ks < K
        b = np.zeros(LA, dtype=np.uint16)
        b[ok] = xb[ks[ok]]
        xw.append(int.from_bytes(b.astype("<u2").tobytes(), "little") << (MS.SUB * MS.LBS * 266))
    return dict(R=R, c=c, Gn=Gn, fmt=fmt, lines=lines, xw=xw)


def edge_rows(K):
    rows = [np.full(K, -128), np.full(K, 127), np.zeros(K), np.where(np.arange(K) % 2 == 0, -128, 127),
            np.where(np.arange(K) % 3 == 0, 127, -128), np.where(np.arange(K) % 64 < 32, -1, 1)]
    return np.stack(rows).astype(np.int8)


def cmd_run(a):
    import dshbm_matched_sm_seq as MS
    import dshbm_sm_pq_seq as PQ
    import hdc_golden as G
    man, vops = load_vectors(a.vectors)
    if not man.get("proofs_pass"):
        raise SystemExit("the vectors' simulator proof did not pass")
    sel = [o for o in vops if (not a.families or o["tag"] in a.families.split(","))
           and (not a.match or any(m in o["key"] for m in a.match.split(",")))]
    if a.max_ops:
        sel = sel[:a.max_ops]
    # the op list: each simulator share as fmt3 then fmt0 (CF-SM pair); edge rows on the first share's activation
    plan = []
    for o in sel:
        gold = golden(o["codes"], o["x"])
        sim_vs_golden = bool(np.array_equal(G.bits(gold), G.bits(o["out"])))
        plan.append(dict(name=f"{o['key']} fmt3", codes=o["codes"], x=o["x"], want=o["out"], fmt=3,
                         sim_vs_golden=sim_vs_golden, pair=None if a.no_pair else len(plan) + 1))
        if not a.no_pair:
            plan.append(dict(name=f"{o['key']} fmt0 widened", codes=o["codes"], x=o["x"], want=o["out"], fmt=0,
                             sim_vs_golden=sim_vs_golden, pair=len(plan) - 1))
    if not a.no_edge and sel:
        x0 = sel[0]["x"]
        e = edge_rows(x0.size)
        plan.append(dict(name="edge rows -128/127/0/alt fmt3", codes=e, x=x0, want=golden(e, x0), fmt=3,
                         sim_vs_golden=True, pair=None))
    d = Path(a.workdir) / ("serial" if a.serial else "piped")
    d.mkdir(parents=True, exist_ok=True)
    nc, active = 8, 1
    xb = -(-active * MS.XC // 2048)
    fw = (nc * MS.XC + 2048 + 3) // 4
    seq, lines, xw = [], [], []
    ptr = 0
    for i, p in enumerate(plan):
        g = build_op(MS, p["codes"], p["x"], p["fmt"])
        p["geom"] = g
        foot = g["Gn"] * g["c"]
        rbase, ptr = ptr, (ptr + foot) % MS.XDEPTH
        dep = 1 if (a.serial or i == 0) else 0
        seq += [g["R"], g["c"], g["Gn"], g["fmt"], len(g["lines"]), 1, 1, foot, dep, rbase]
        lines += [f"{w:0272x}" for w in g["lines"]]
        xw += [f"{w:0{fw}x}" for w in g["xw"]]
    (d / "seq.hex").write_text("\n".join(f"{v:08x}" for v in seq) + "\n")
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    params = dict(SUB=MS.SUB, LBS=MS.LBS, LSB=MS.LSB, NC=nc, XDEPTH=MS.XDEPTH, RMAX=a.rmax, LEV=MS.LEV, XB=xb, HAZ=1,
                  G1ASB=0, REQCR=1, ENABLE_INT8=1, PIPE_INT8=a.pipe)
    defs = ["-DOT_INT8_MUT_SIGN"] if a.mut_sign else []
    bdir = Path(a.workdir) / (f"build_{a.sim}_rmax{a.rmax}_p{a.pipe}" + ("_mutsign" if a.mut_sign else ""))
    run, cmd = PQ.compile_bench(a.sim, params, bdir, a.build_jobs, smh=True, extra_defs=defs)
    with (d / "runtime.log").open("w") as log:
        subprocess.run(run + [f"+DIR={d}", f"+NOPS={len(plan)}"] + (["+REQ_STALLS"] if a.req_stalls else []),
                       check=True, cwd=d, stdout=log, stderr=subprocess.STDOUT)
    res, meta, total, timeout = {}, {}, None, None
    for line in (d / "out.txt").read_text().splitlines():
        if line.startswith("# op"):
            t = line[2:].split()
            meta[int(t[1])] = {t[k]: int(t[k + 1]) for k in range(2, len(t) - 1, 2)}
        elif line.startswith("# total_cycles"):
            total = int(line.split()[-1])
        elif line.startswith("#"):
            if "TIMEOUT" in line:
                timeout = line[2:]
        else:
            o, r, h = line.split()
            res.setdefault(int(o), {})[int(r)] = int(h, 16) & 0xFFFFFFFF
    rows, bad = [], 0
    got_all = {}
    for i, p in enumerate(plan):
        R = p["geom"]["R"]
        got = res.get(i, {})
        want = G.bits(p["want"]).astype(np.uint32)
        mism = sum(1 for r in range(R) if got.get(r) != int(want[r]))
        got_all[i] = got
        m = meta.get(i, {})
        exact = (mism == 0 and len(got) == R and m.get("fault", 1) == 0 and m.get("consumed") == m.get("lines")
                 and m.get("results") == R and p["sim_vs_golden"])
        bad += 0 if exact else 1
        rows.append(dict(op=i, name=p["name"], fmt=p["fmt"], rows=R, K=int(p["x"].size), groups=p["geom"]["Gn"],
                         lines=len(p["geom"]["lines"]), dep=bool(a.serial or i == 0), mismatches=mism,
                         results=len(got), sim_vs_golden=p["sim_vs_golden"], exact=exact, rtl=m))
    # CF-SM pairing: fmt3 result == fmt0 (BF16-widened) result, row for row
    pairs_ok = all(got_all[i] == got_all[p["pair"]] for i, p in enumerate(plan) if p["fmt"] == 3 and p["pair"] is not None)
    npairs = sum(1 for p in plan if p["fmt"] == 3 and p["pair"] is not None)
    status = "pass" if bad == 0 and timeout is None and pairs_ok else "fail"
    srcs = PQ.SRC + PQ.SMH_SRC
    out = dict(schema="opentallas.qwen_r25_smh_fmt3_bench.v1", conformance="HGI-1 CF-SM (smh_front_c format 3)",
               vectors=dict(path=str(a.vectors), sha256=hashlib.sha256(Path(a.vectors).read_bytes()).hexdigest(),
                            snapshot=man["snapshot"], layer=man["layer"], position=man["position"],
                            proofs=[dict(stage=pp["stage"], pass_=pp["pass_"]) for pp in man["proofs"]],
                            sim_source_sha256=man["sim_source_sha256"]),
               element="ot_hbm_accel_smh ENABLE_INT8 = 1 PIPE_INT8 = %d (RMAX %d, NC 8, one active column)" % (a.pipe, a.rmax),
               serial=a.serial, req_stalls=a.req_stalls, mutant=("OT_INT8_MUT_SIGN" if a.mut_sign else None),
               simulator=a.sim, status=status, mismatching_ops=bad, cf_sm_pairs_equal=pairs_ok, cf_sm_pairs=npairs, total_cycles=total,
               timeout=timeout, ops=rows,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               host=os.uname().nodename, build_command=cmd,
               source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in srcs + [
                   "tools/qwen_r25_smh_fmt3_bench.py", "tools/dshbm_sm_pq_seq.py", "tools/dshbm_matched_sm_seq.py",
                   "tools/rtl_gpu_sm_exact.py", "tools/hdc_golden.py", "tools/hdc_golden_v41.py"]})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(f"{r['op']:2d} {r['name'][:44]:44s} fmt{r['fmt']} R{r['rows']:5d} K{r['K']:5d} lines {r['lines']:6d} "
              f"mism {r['mismatches']:5d} sim=gold {int(r['sim_vs_golden'])} exact {r['exact']}")
    print(status.upper(), "pairs_equal", pairs_ok, "total_cycles", total, a.out)
    ok = status == "pass"
    if a.expect_fail:
        print("EXPECTED FAIL:", "yes" if not ok else "NO (negative test did not fail)")
        return 0 if not ok else 1
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="step", required=True)
    e = sp.add_parser("export")
    e.add_argument("--sim-root", required=True)
    e.add_argument("--snapshot", required=True)
    e.add_argument("--cache", required=True)
    e.add_argument("--layer", type=int, default=0)
    e.add_argument("--position", type=int, default=8191)
    e.add_argument("--stages", default="layer,head")
    e.add_argument("--out", required=True)
    r = sp.add_parser("run")
    r.add_argument("--vectors", required=True)
    r.add_argument("--families", default="", help="comma list of SM record tags (default: all)")
    r.add_argument("--match", default="", help="comma list of substrings; keep ops whose key contains any")
    r.add_argument("--max-ops", type=int, default=0)
    r.add_argument("--no-pair", action="store_true")
    r.add_argument("--no-edge", action="store_true")
    r.add_argument("--serial", action="store_true")
    r.add_argument("--req-stalls", action="store_true")
    r.add_argument("--pipe", type=int, default=1)
    r.add_argument("--rmax", type=int, default=4096)
    r.add_argument("--mut-sign", action="store_true")
    r.add_argument("--expect-fail", action="store_true")
    r.add_argument("--sim", choices=("verilator", "iverilog"), default="verilator")
    r.add_argument("--build-jobs", type=int, default=8)
    r.add_argument("--workdir", default=None)
    r.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.step == "export":
        return cmd_export(a)
    a.workdir = a.workdir or tempfile.mkdtemp(prefix="qfmt3_")
    return cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
