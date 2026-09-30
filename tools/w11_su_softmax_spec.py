#!/usr/bin/env python3
"""W11: the V4.1 stream unit's attention softmax chain at the model's spec width (N = 1,024 light lanes,
M = 256 SFU lanes), exact against the golden, cycles measured.

The four ops are the fixture of tools/rtl_v41x_su_softmax_campaign.py (H16, D512, T128/T640):
  0  scale + row max        (RED_MAX)
  1  exp(s - max) + row sum (SFU_EXP, RED_SUM)
  2  sink denominator       (exp(sink - max) + sum)
  3  acc / den, then BF16   (M1_DIVB)
Every case compares the WHOLE vector memory bit for bit against the direct golden arithmetic
(hdc_golden / hdc_golden_v41: G.mul, max, G.exp, V.csum, V.div, G.to_bf16).

Variants per (N, M, T):
  serial_adapt  the SU adapter bench rtl/test/tb_hdc_v41x_su_softmax.sv (ot_hdc_v41x_su_adapt over
                ot_hdc_v41x_vec), every op w_idle = 1: the committed N16/M8 method (3,280 cycles at T640).
  serial_vec    the vector-unit bench rtl/test/tb_hdc_v41x_vec.sv, every op w_idle = 1.
  chained       the vector-unit bench, w_idle = 0, the chaining fields and waits from
                rtl_hdc_v41x_vec_campaign.schedule(chain=True): an op issues as soon as the results it reads
                have arrived (w_rseq) and element reads chase the producer's writes (CH_SELF lead / mul).

Per op: accept, emit / write / result cycles, the vector count and depths against the model's issue
(layout(): max 16 vectors, exp + sum 48, sink 1, divide 32 at N1024/M256, H16/T640; linear depth 21,
exp 49 in S, reducer 26 + 3 log2(S/8) + 3 L when spanning).

Wire stages (--stages B:R ...): ot_hdc_v41x_vec's BCAST_STAGES (controller -> lanes broadcast tree) and
RET_STAGES (lanes / reducer -> vector memory).  0:0 is the unit as it was (config key N{N}_M{M}); any other
pair is keyed N{N}_M{M}_B{B}R{R}.  `wire_stage_derivation` sets the spec pair from the W1 hub placement
(results/floorplan/v41_pack_expanded_woa.json) with the model's wire rule (tools/uarch_model.wire_cycles at
0.92 ns, 0.76 ps/um).

Writes results/rtl/w11_su_spec.json (new record; does not touch results/rtl/v41x_su_softmax.json).
    python3 tools/w11_su_softmax_spec.py --scratch /tmp/.../su [--configs 16x8 1024x256] [--stages 0:0 4:4]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402
import rtl_v41x_su_softmax_campaign as S   # noqa: E402

OUT = ROOT / "results/rtl/w11_su_spec.json"
ADAPT = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv"
TB_ADAPT = ROOT / "rtl/test/tb_hdc_v41x_su_softmax.sv"
TB_VEC = ROOT / "rtl/test/tb_hdc_v41x_vec.sv"
# the bench memories: the fixture's VM is 2^15 words; KV / CR / WR / XB are not read beyond 16 words
MEMP = dict(VMA=15, KVA=4, CRA=4, WRA=4, XBA=4, PMAX=8)
OP_NAMES = ["scale+row max", "exp(s-max)+row sum", "sink denominator", "acc/den divide + BF16"]
# the microarchitecture model's issue at N1024/M256 (tools/uarch_model.py adopts layout()), H16/T640
MODEL_VECTORS_T640_N1024 = [16, 48, 1, 32]
MODEL_DEPTHS = dict(linear_emit_to_write=21, exp_in_S=49,
                    reducer="26 + 3*log2(S/8) + 3*L (L = time levels when the row spans vectors)")
SOURCES = [*C.LIB, *C.RTL, ADAPT, TB_ADAPT, TB_VEC, C.FIELDS_SVH, C.HARNESS, Path(__file__).resolve(),
           ROOT / "tools/rtl_v41x_su_softmax_campaign.py", *C.TOOLS]


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


FLOORPLAN = ROOT / "results/floorplan/v41_pack_expanded_woa.json"
SPEC_CLOCK_PS = 920.0
WIRE_PS_PER_UM = 0.76


def wire_stage_derivation(N=1024, M=256):
    """BCAST_STAGES / RET_STAGES at the spec width from the W1 hub placement.

    The lane array: (N - M) light lanes and M SFU lanes at the model's per-lane area estimates
    (uarch_model.UNIT su_light_lane_um2 / su_lane_um2), laid out as a square of side s.  The controller sits at
    the array's centre; the farthest lane is a corner: s / sqrt(2) straight, s Manhattan (routes are
    Manhattan).  The return path goes from the farthest lane to the vector memory (HUB_VM, the strip on the
    region's west edge): with the array abutting HUB_VM it is s + max(0, s/2 - VM height / 2); with the
    array centred in HUB_SU_VECTOR it is longer (listed, not adopted)."""
    import uarch_model as U
    fp = json.loads(FLOORPLAN.read_text())
    reg = {r[0]: dict(x=r[2], y=r[3], w=r[4], h=r[5]) for r in fp["soft_regions"]}
    su, vm = reg["HUB_SU_VECTOR"], reg["HUB_VM"]
    light, sfu = U.UNIT["su_light_lane_um2"], U.UNIT["su_lane_um2"]
    area = (N - M) * light + M * sfu
    side = math.sqrt(area)
    vm_x1, vm_yc, vm_h = vm["x"] + vm["w"], vm["y"] + vm["h"] / 2, vm["h"]
    cyc = lambda um: U.wire_cycles(um, 1e12 / SPEC_CLOCK_PS, WIRE_PS_PER_UM)
    bcast_um = side                                            # centre -> corner, Manhattan
    ret_abut_um = side + max(0.0, side / 2 - vm_h / 2)         # far corner -> HUB_VM's east edge
    cx, cy = su["x"] + su["w"] / 2, su["y"] + su["h"] / 2
    ret_centred_um = (cx + side / 2 - vm_x1) + max(0.0, abs(cy - vm_yc) + side / 2 - vm_h / 2)
    return dict(
        region=dict(HUB_SU_VECTOR_um=[round(su["w"], 1), round(su["h"], 1)],
                    HUB_SU_VECTOR_centre_um=[round(cx, 1), round(cy, 1)],
                    HUB_VM_um=[round(vm["w"], 1), round(vm["h"], 1)], HUB_VM_east_edge_x_um=round(vm_x1, 1),
                    floorplan=str(FLOORPLAN.relative_to(ROOT))),
        lane_array=dict(light_lanes=N - M, sfu_lanes=M, light_um2=light, sfu_um2=sfu, area_mm2=round(area / 1e6, 3),
                        square_side_um=round(side, 1), area_basis="uarch_model.UNIT estimates (not hardened)"),
        wire_rule=dict(fn="tools/uarch_model.wire_cycles", clock_ps=SPEC_CLOCK_PS, ps_per_um=WIRE_PS_PER_UM,
                       check={"3000um": cyc(3000), "6000um": cyc(6000)}),
        controller="at the lane array's centre, which is HUB_SU_VECTOR's centre height; the array abuts HUB_VM",
        broadcast=dict(farthest_lane_manhattan_um=round(bcast_um, 1),
                       farthest_lane_straight_um=round(side / math.sqrt(2), 1),
                       stages=cyc(bcast_um), stages_if_straight=cyc(side / math.sqrt(2))),
        ret=dict(farthest_lane_to_vm_um=round(ret_abut_um, 1), stages=cyc(ret_abut_um),
                 alternative_array_centred_in_region=dict(um=round(ret_centred_um, 1), stages=cyc(ret_centred_um))),
        adopted=dict(BCAST_STAGES=cyc(bcast_um), RET_STAGES=cyc(ret_abut_um)),
        not_modelled="the operand reads (rd_addr -> rd_q, 4 streams) and the gather index read cross the same "
                     "array to the vector memory; the unit's fetch depth (3) assumes a one-cycle memory beside "
                     "every lane")


def build(kind, N, M, LV, obj: Path, jobs, vflags=(), stages=(0, 0), mlat=3):
    obj.mkdir(parents=True, exist_ok=True)
    top = "tb_hdc_v41x_su_softmax" if kind == "adapt" else "tb_hdc_v41x_vec"
    srcs = [*map(str, C.LIB), *map(str, C.RTL)]
    srcs += [str(ADAPT), str(TB_ADAPT)] if kind == "adapt" else [str(TB_VEC)]
    cmd = ["/usr/bin/time", "-v", C.VERILATOR, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
           "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-UNOPTFLAT", *vflags, "--top-module", top, "--prefix", "Vtb", "-Mdir", str(obj),
           f"-GN={N}", f"-GM={M}", f"-GLV={LV}", f"-GBCAST_STAGES={stages[0]}", f"-GRET_STAGES={stages[1]}",
           f"-GMLAT={mlat}", *[f"-G{k}={v}" for k, v in MEMP.items()],
           f"-I{ROOT / 'rtl/test'}", *srcs, str(C.HARNESS), "-CFLAGS", "-O1", "-j", str(jobs)]
    t0 = time.time()
    with (obj / "build.log").open("w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    wall = time.time() - t0
    text = (obj / "build.log").read_text(errors="replace")
    if r.returncode:
        raise RuntimeError(f"build {kind} N{N} failed:\n" + text[-4000:])
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    return obj / "Vtb", dict(wall_s=round(wall, 1), verilator_flags=list(vflags), stages=list(stages), mlat=mlat, max_rss_gib=round(int(m.group(1)) / 2**20, 2) if m else None,
                             note="max RSS of the largest single process (verilator or one g++)")


def cases(N, M, tokens):
    """(variant, bench kind, ops, schedule reference or None) for one token count."""
    mem, ops, expected, regions = S.fixture(tokens)
    out = []
    out.append(("serial_adapt", "adapt", [dict(f) for f in ops], None))
    out.append(("serial_vec", "vec", [dict(f) for f in ops], None))
    free = [dict(f, w_idle=0) for f in ops]
    # schedule()'s ok also folds layout()'s "span and L > 6" refusal (the campaign bench's LV = 6); this bench is
    # built with LV = 7, so a 7-level span (N16/M8 T640 exp: 80 vectors) is legal here.  The whole-VM compare
    # against the golden is the check.
    mref, sops, lays, _ = C.schedule(free, mem, N, M, chain=True)
    out.append(("chained", "vec", sops, mref))
    return mem, expected, regions, out


def stats(v):
    return dict(first=min(v), last=max(v), count=len(v)) if v else None


def per_op(tr, ops, N, M):
    rows = []
    for k, f in enumerate(ops):
        lay = C.layout(f, N, M)
        em, rt, rs = C.op_trace(tr, k)
        r = dict(op=OP_NAMES[k], accept=tr["acc"].get(k), emit=stats(em), write=stats(rt), result=stats(rs),
                 vectors=len(em), layout_vectors=lay["nv"], vector_width=lay["vw"], S=lay["S"], span=lay["span"],
                 time_levels=lay["L"] if lay["span"] else 0, tap_level=lay["lt"],
                 chain=dict(w_idle=f["w_idle"], ch_src=f["ch_src"], ch_seq=f["ch_seq"], ch_lead=f["ch_lead"],
                            ch_mul=f["ch_mul"], w_rseq_en=f["w_rseq_en"], w_rseq=f["w_rseq"]),
                 model_depth_emit_to_write=lay["dP"], model_depth_emit_to_result=lay["dR"])
        if em:
            r["emit_span_cycles"] = em[-1] - em[0] + 1
            r["accept_to_first_emit"] = em[0] - r["accept"] if r["accept"] is not None else None
        if em and rt:
            r["emit_to_write"] = rt[0] - em[0]
        if rs and em:
            r["last_emit_to_last_result"] = rs[-1] - em[-1]
            r["first_emit_to_first_result"] = rs[0] - em[0]
        if rs and rt:
            r["last_write_to_last_result"] = rs[-1] - rt[-1]
        rows.append(r)
    for k in range(1, len(rows)):
        prev = rows[k - 1]
        done = max(x["last"] for x in (prev["write"], prev["result"]) if x)
        rows[k]["accept_after_prev_done"] = rows[k]["accept"] - done
        rows[k]["first_emit_after_prev_done"] = rows[k]["emit"]["first"] - done
    return rows


def run_one(exe, d: Path, mem, ops, expected, regions, mref, N, M):
    C.write_case(d, mem, ops)
    tr = C.run_case(exe, d, len(ops))
    vm = tr["vm"]
    mism = {name: int(np.count_nonzero(vm[b:b + n] != expected.vm[b:b + n])) for name, (b, n) in regions.items()}
    ops_rows = per_op(tr, ops, N, M)
    first = ops_rows[0]["accept"]
    last = max(max(x["last"] for x in (r["write"], r["result"]) if x) for r in ops_rows)
    rec = dict(end_cycle=tr["end"][0] if tr["end"] else None, completed=bool(tr["end"] and tr["end"][1] == "ok"),
               first_accept_to_last_write_cycles=last - first + 1,
               whole_vm_mismatches=int(np.count_nonzero(vm != expected.vm)), region_mismatches=mism,
               faults=tr["faults"], order_faults=tr["orders"], sim_wall_s=round(tr["wall_s"], 2), ops=ops_rows)
    if mref is not None:
        rec["schedule_reference_vm_mismatches"] = int(np.count_nonzero(vm != mref.vm))
    kvo = tr["kv"]
    rec["kv_written_words"] = int(np.count_nonzero(kvo)) if kvo is not None else None
    rec["pass_"] = bool(rec["completed"] and rec["whole_vm_mismatches"] == 0 and rec["faults"] == 0
                        and rec["order_faults"] == 0 and rec.get("schedule_reference_vm_mismatches", 0) == 0)
    return rec


def ports(N, M, AW=24):
    """The unit's memory-port widths (ot_hdc_v41x_vec ports) and the 256-bit VM banks they imply."""
    NR = N // 8
    p = dict(
        operand_read_streams=dict(streams=4, words_per_stream=N, bits=4 * N * 32, addr_bits=4 * N * AW,
                                  note="rd_addr / rd_q: A, B, C, D per lane, each 32 bits (VM, CROM lo/hi or WROM)"),
        index_read=dict(words=N, bits=N * 32, note="vi_q: the gather index read (IND_I / IND_O)"),
        element_write=dict(words=N, bits=N * 32, note="vm_we / vm_wdata"),
        kv_write=dict(words=N, bits=N * 32, note="kv_we / kv_wdata (a separate KV SRAM port)"),
        result_write=dict(words=NR, bits=NR * 32, note="res_we / res_data: one per 8-lane chunk (N/8)"),
    )
    bank = 256
    vm_read_bits = p["operand_read_streams"]["bits"] + p["index_read"]["bits"]
    vm_write_bits = p["element_write"]["bits"] + p["result_write"]["bits"]
    p["vm_banks_256b"] = dict(
        per_operand_stream=N * 32 // bank, all_four_operand_streams=4 * N * 32 // bank,
        index_stream=N * 32 // bank, element_write=N * 32 // bank, result_write=-(-NR * 32 // bank),
        read_bits_per_cycle=vm_read_bits, write_bits_per_cycle=vm_write_bits,
        note="the bench gives every lane and stream an independent one-cycle port; a banked VM needs every "
             "read stream's N words in distinct 256-bit banks each cycle (unit-stride rows), i.e. N*32/256 "
             "banks per stream.  The softmax chain uses A and B (VM) on op 0-3 and C (VM) on op 2; B is a "
             "broadcast per row (bso=1, bsi=0), so its N words hit one address.")
    p["kv_banks_256b"] = N * 32 // bank
    p["result_bits_per_cycle"] = NR * 32
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--configs", nargs="+", default=["16x8", "1024x256"])
    ap.add_argument("--lv", type=int, default=7, help="reducer time levels (l_in is 3 bits: LV <= 7 is exact)")
    ap.add_argument("--tokens", type=int, nargs="+", default=[128, 640])
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--builds-from", type=Path,
                    help="with --reuse: a record whose 'builds' made the reused benches (copied, marked reused)")
    ap.add_argument("--vflags", default="", help="extra Verilator flags, e.g. '-fno-inline' (recorded)")
    ap.add_argument("--build-parallel", type=int, default=2, help="benches built at once (memory: ~31 GiB at N1024)")
    ap.add_argument("--stages", nargs="+", default=["0:0"], help="BCAST_STAGES:RET_STAGES pairs")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--mlat", type=int, default=3,
                    help="ot_hdc_v41x_vec MLAT: multiplier latency (3, or 4: the W11 serial domain); keys get _L<mlat>")
    args = ap.parse_args()
    C.set_mlat(args.mlat)
    C.write_fields_svh()
    args.scratch.mkdir(parents=True, exist_ok=True)
    rec = dict(schema="opentallas.rtl.w11_su_spec/1", generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               contract=S.__doc__.strip().splitlines()[0], fixture="tools/rtl_v41x_su_softmax_campaign.fixture",
               heads=16, head_dim=512, reducer_levels=args.lv, clock_ghz=C.CLOCK_GHZ,
               model_issue=dict(vectors_H16_T640_N1024_M256=dict(zip(OP_NAMES, MODEL_VECTORS_T640_N1024)),
                                depths=MODEL_DEPTHS),
               mlat=args.mlat,
               depths_at_mlat=dict(linear_emit_to_write=C.D_FETCH + C.D_PRE + C.D_M1 + C.D_STAGE + C.D_AD
                                   + 2 * C.D_STAGE + C.D_OUT, exp_in_S=C.SFU_DEPTH[C.I.SFU_EXP],
                                   reducer=f"{C.D_RED} + 3*log2(S/8) + 3*L"),
               wire_stage_derivation=wire_stage_derivation(), builds={}, configs={})
    if args.reuse and args.builds_from:
        prev = json.loads(args.builds_from.read_text())
        rec["builds"] = {k: dict(v, reused_from=dict(record=str(args.builds_from), git_head=prev.get("git_head")))
                         for k, v in prev["builds"].items()}
    runs = [(cfg, tuple(map(int, st.split(":")))) for cfg in args.configs for st in args.stages]
    sfx_of = lambda B, R: ("" if (B, R) == (0, 0) else f"_B{B}R{R}") + ("" if args.mlat == 3 else f"_L{args.mlat}")
    # every bench first (build_parallel at once: an N1024 build peaks near 31 GiB), then the cases
    exes, futs = {}, {}
    with ThreadPoolExecutor(args.build_parallel) as pool:
        for cfg, (B, R) in sorted(runs, key=lambda r: int(r[0].split("x")[0])):
            N, M = map(int, cfg.split("x"))
            for kind in ("adapt", "vec"):
                key = f"{kind}_N{N}_M{M}{sfx_of(B, R)}"
                obj = args.scratch / f"obj_{kind}_N{N}_M{M}_LV{args.lv}{sfx_of(B, R)}"
                if args.reuse and (obj / "Vtb").exists():
                    exes[key] = obj / "Vtb"
                    continue
                futs[key] = pool.submit(build, kind, N, M, args.lv, obj, args.jobs, args.vflags.split(), (B, R), args.mlat)
        for key, fu in futs.items():
            exes[key], info = fu.result()
            rec["builds"][key] = info
            print("built", key, info, flush=True)
    for cfg, (B, R) in runs:
        N, M = map(int, cfg.split("x"))
        C.BCAST, C.RET = B, R           # the layout model's depths for this bench
        sfx = sfx_of(B, R)
        crec = dict(N=N, M=M, LV=args.lv, BCAST_STAGES=B, RET_STAGES=R, ports=ports(N, M), cases={})
        jobs = []
        for T in args.tokens:
            mem, expected, regions, cl = cases(N, M, T)
            for variant, kind, ops, mref in cl:
                d = args.scratch / f"case_N{N}{sfx}_T{T}_{variant}"
                jobs.append((T, variant, exes[f"{kind}_N{N}_M{M}{sfx}"], d, mem, ops, expected, regions, mref))
        with ThreadPoolExecutor(len(jobs)) as pool:
            res = list(pool.map(lambda j: (j[0], j[1], run_one(j[2], j[3], j[4], j[5], j[6], j[7], j[8], N, M)),
                                jobs))
        for T, variant, r in res:
            crec["cases"].setdefault(f"T{T}", {})[variant] = r
            print(N, M, T, variant, r["pass_"], r["end_cycle"], r["first_accept_to_last_write_cycles"], flush=True)
        rec["configs"][f"N{N}_M{M}{sfx}"] = crec
    # what the wire stages cost: end-to-end cycles against the same case with none
    for key, cf in rec["configs"].items():
        base = rec["configs"].get(f"N{cf['N']}_M{cf['M']}" + ("" if args.mlat == 3 else f"_L{args.mlat}"))
        if base is None or base is cf:
            continue
        cf["delta_vs_no_wire_stages"] = {
            T: {v: dict(first_accept_to_last_write=r["first_accept_to_last_write_cycles"]
                        - base["cases"][T][v]["first_accept_to_last_write_cycles"],
                        end_cycle=r["end_cycle"] - base["cases"][T][v]["end_cycle"],
                        per_op_last_done=[max(x["last"] for x in (o["write"], o["result"]) if x)
                                          - max(x["last"] for x in (b["write"], b["result"]) if x)
                                          for o, b in zip(r["ops"], base["cases"][T][v]["ops"])])
                for v, r in cs.items()} for T, cs in cf["cases"].items() if T in base["cases"]}
    # the model's vector counts against the measured ones (T640 at N1024/M256)
    c = rec["configs"].get("N1024_M256" + ("" if args.mlat == 3 else f"_L{args.mlat}"), {}).get("cases", {}).get("T640")
    if c:
        rec["model_vector_check"] = {v: [dict(op=o["op"], model=m, measured=o["vectors"], equal=o["vectors"] == m)
                                         for o, m in zip(c[v]["ops"], MODEL_VECTORS_T640_N1024)] for v in c}
    rec["pass_"] = all(r["pass_"] for cf in rec["configs"].values() for t in cf["cases"].values() for r in t.values())
    h = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    d = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                       capture_output=True, text=True)
    # a remote run (rsync of the tree without .git) passes the commit it copied in OT_GIT_HEAD
    rec["git_head"] = h.stdout.strip() if h.returncode == 0 else os.environ.get("OT_GIT_HEAD", "")
    rec["git_dirty_tracked_files"] = [x[3:] for x in d.stdout.splitlines()] if d.returncode == 0 else \
        "unknown: run outside a git checkout (sources are pinned by sha256)"
    rec["host"] = os.uname().nodename
    rec["verilator"] = C.VERILATOR
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print("wrote", args.out, "pass", rec["pass_"])


if __name__ == "__main__":
    main()
