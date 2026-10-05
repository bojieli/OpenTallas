#!/usr/bin/env python3
"""DS-ROM S81: bind the full-bandwidth WINDOW load (ot_dsrom_window_stream_la) and the re-index candidate read
(ot_hdc_v41x_idx_kgather) into the S81 layer die's HBM service, and measure them on the minimum vehicle at the
1M target position (1,048,575) on the golden data.  Branch claude/dsrom-s81-window-bind-20261004.

As built, the S81 die refills the 128 packed WINDOW rows one 544-B row per prefetch command through the stack's
single K channel: 149,502 cycles (124.5 us) at REFILL_CREDITS 1 and 24,157 (20.1 us) at the S81 selection's
credits 8 for ONE layer (results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_window_load.json), against a
measured layer time of 8-18 us.  The bound successor (default-off parameters):

  rtl/dsrom_sys/s81_window_la/ot_dsrom_window_attn_source_la.sv   STREAM_LA: the window source; the job's ring is
        read by ot_dsrom_window_stream_la over a per-pseudo-channel wide port, landed by
  rtl/dsrom_sys/s81_window_la/ot_dsrom_window_la_stage.sv         (68 single-write columns, stage4 read path),
  rtl/dsrom_sys/s81_window_la/ot_dsrom_hbm_wmux.sv                per-stack wide port between the karb and the
        stack: client 0 the window, client 1 the candidate gather (K owner code 11 as its tag namespace).
  install_die()  text-patches the S81 die (rtl/dsrom_sys/s81_capture_parent/ot_chip_v41x_die_owner_safe_c8.sv,
        unchanged on disk) with WINDOW_STREAM_LA / IDX_KGATHER_PORT parameters (default 0 = the as-built die,
        the wmux is wires); `bind` lints the patched die at both settings.

Subcommands:
  vectors   golden window rows of L0 (window-only), L20 (scan) and L24 (re-index) at P1048575: 127 synthetic
            state rows (tools/rtl_v41_fullshape_layer_campaign.synthetic_state's window stream, seed 20260930) plus
            the token's own row (the golden shard's win<L>), packed FP8 + UE8M0 (round trip asserted bit-exact),
            as the stack-0 sector image and the expected packed rows; the real 1M candidate lists for KG.
  run       build the vehicle (Verilator) per configuration and run the cases (refresh phases) -> runs.json
  emit      emit the patched die, full source list and opt-in parameters without building or running
  bind      patch + lint the S81 die at WINDOW_STREAM_LA = 0 / 1 (and IDX_KGATHER_PORT) -> bind.json
  record    runs.json (+ screen.json, bind.json) -> results/rtl/dsrom_s81_window_bind_20261004/window_load.json
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/rtl/dsrom_s81_window_bind_20261004"
GOLD_DEFAULT = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
CTX, POS, SEED = 1048576, 1048575, 20260930
FIRST = POS - 127
W_BASE = 0x300000
PITCH = 17
CLK_PS = 833
LAYERS = {0: "window-only (swa, L0)", 20: "L20 global scan (csa1_full)", 24: "re-index (csa1_reindex, L24)"}
PLACEMENTS = {"p1": dict(BASE=0, BSTEP=1000, OSTEP=136), "p2": dict(BASE=123, BSTEP=777, OSTEP=8)}

NEW_RTL = ["rtl/dsrom_sys/s81_window_la/ot_dsrom_hbm_wmux.sv",
           "rtl/dsrom_sys/s81_window_la/ot_dsrom_window_stream_la_s81.sv",
           "rtl/dsrom_sys/s81_window_la/ot_dsrom_window_la_stage.sv",
           "rtl/dsrom_sys/s81_window_la/ot_dsrom_window_attn_source_la.sv"]
BENCH = "rtl/test/dsrom_sys/s81_window_la/tb_dsrom_s81_window_la.sv"
TRACE_MODEL = "rtl/test/ot_hdc_v41x_idx_hbm_trace.sv"   # the controller + JESD238 checker (DRAMCHK builds)
SOURCES = ["rtl/chip/ot_dsrom_window_stream_la.sv",
           "rtl/chip/window_owner_safe/ot_chip_v41x_window_attn_source_owner_safe.sv",
           "rtl/chip/window_owner_safe/ot_chip_v41x_window_kv_prefetch_owner_safe.sv",
           "rtl/chip/ot_chip_v41x_window_refill_schedule.sv", "rtl/chip/ot_chip_v41x_window_retention.sv",
           "rtl/chip/ot_chip_v41x_window_row_codec.sv", "rtl/chip/ot_chip_v41x_window_stage4.sv",
           "rtl/chip/ot_chip_v41x_window_stream.sv", "rtl/chip/ot_chip_v41x_attn_row_merge.sv",
           "rtl/dsrom_sys/c8/ot_chip_v41x_kv_rope_reqmux_c8.sv", "rtl/dsrom_sys/c8/ot_chip_v41x_kv_reqmux_c8.sv",
           "rtl/chip/ot_chip_v41x_hbm_karb.sv", "rtl/chip/ot_chip_v41x_hbm_rsp_pipe.sv",
           "rtl/dsrom_sys/c8/ot_hdc_v41x_idx_hbm_c8.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_kgather.sv",
           *NEW_RTL, BENCH]


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ vectors
def window_rows(m, L, gold: Path):
    """The 128 window rows the golden's layer-L attention reads at P1048575, oldest first: the synthetic state's
    127 (synthetic_state's kind-0 stream, unchanged) and the token's own row from the golden shard."""
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    from hdc_golden import F
    rng = np.random.default_rng([SEED, CTX, 0, L])
    g = m.lw(L, "attn.kv_norm.weight")
    rows = np.concatenate(list(LC._gained(rng, m.window - 1, m.hd, g)))
    rows = V.qdq_fp8(rows.reshape(-1)).reshape(m.window - 1, m.hd)
    cur = np.load(gold / f"ctx1048576_L{L:02d}.npz")[f"win{L}"].reshape(1, -1).astype(F)
    return np.concatenate([np.asarray(rows, F), cur]), hashlib.sha256(np.asarray(rows, F).tobytes()).hexdigest()


def pack_rows(rows):
    """FP8 E4M3 codes + UE8M0 bytes (rtl_v41_fullshape_layer_campaign.pack_fp8_ue8m0, which asserts the bit-exact
    round trip) -> per slot the 17 sectors and the 4,224-bit stage row (byte 0 = bits 7:0; scales at 4096 + 8 g)."""
    import rtl_v41_fullshape_layer_campaign as LC
    codes, scales = LC.pack_fp8_ue8m0(rows)
    sectors, stage = {}, {}
    for t in range(128):
        slot = (FIRST + t) % 128
        cb = codes[t].tobytes()
        sc = scales[t].tobytes()
        for k in range(16):
            sectors[W_BASE + slot * PITCH + k] = int.from_bytes(cb[32 * k:32 * k + 32], "little")
        sectors[W_BASE + slot * PITCH + 16] = int.from_bytes(sc, "little")
        stage[slot] = int.from_bytes(cb, "little") | (int.from_bytes(sc, "little") << 4096)
    return codes, scales, sectors, stage


def decode_stage(word: int):
    import hdc_golden_v41 as V
    vals = []
    for g in range(16):
        e = ((word >> (4096 + 8 * g)) & 255) - 127
        vals += [V.E4M3[(word >> (8 * (32 * g + x))) & 255] * 2.0 ** e for x in range(32)]
    return np.array(vals, dtype=np.float32)


def cmd_vectors(a):
    import rtl_v41_fullshape_layer_campaign as LC
    import dsrom_reindex_candidates as RC
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    meta = dict(position=POS, first=FIRST, w_base=W_BASE, seed=SEED, layers={})
    for L in LAYERS:
        rows, synth_sha = window_rows(m, L, a.gold)
        codes, scales, sectors, stage = pack_rows(rows)
        for t in range(128):                           # the stage row decodes to the golden row, bit for bit
            got = decode_stage(stage[(FIRST + t) % 128])
            assert np.array_equal(got.view(np.uint32), rows[t].astype(np.float32).view(np.uint32)), (L, t)
        own = POS % 128                                 # the token's own row is written by the bench through
        with open(out / f"L{L}.wmem", "w") as f:       # the as-built packed-row writer: zero in the host image
            f.write(f"@{W_BASE:x}\n")
            for s in range(W_BASE, W_BASE + 128 * PITCH):
                f.write(f"{0 if (s - W_BASE) // PITCH == own else sectors[s]:064x}\n")
        with open(out / f"L{L}.cold.wmem", "w") as f:  # OWN_WRITE = 0 (cold-row reference): every row in the image
            f.write(f"@{W_BASE:x}\n")
            for s in range(W_BASE, W_BASE + 128 * PITCH):
                f.write(f"{sectors[s]:064x}\n")
        with open(out / f"L{L}.rows", "w") as f:
            for slot in range(128):
                f.write(f"{stage[slot]:01056x}\n")
        meta["layers"][str(L)] = dict(
            kind=LAYERS[L], rows=128, synthetic_rows_sha256=synth_sha,
            golden_rows_sha256=hashlib.sha256(rows.astype(np.float32).tobytes()).hexdigest(),
            packed_sha256=hashlib.sha256(codes.tobytes() + scales.tobytes()).hexdigest(),
            own_row_from=f"{a.gold.name}/ctx1048576_L{L:02d}.npz:win{L}",
            negative_zeros=int(np.sum((rows == 0) & np.signbit(rows))),
            check="pack_fp8_ue8m0 round trip + stage-row decode == golden rows (uint32 bits, every element)")
        print(f"L{L}", meta["layers"][str(L)]["golden_rows_sha256"][:16], flush=True)
    _, blk = RC.cand_blocks(a.gold)
    for r in range(4):
        for q, l in enumerate(RC.rank_lists(blk, r)):
            (out / f"cand_r{r}.s{q}").write_text(f"{len(l)}\n" + "".join(f"{x:x}\n" for x in l))
    meta["candidates"] = dict(npz_sha256=sha(a.gold / "ctx1048576_cand.npz"), blocks=int(len(blk)))
    (out / "vectors.json").write_text(json.dumps(meta, indent=1) + "\n")


# ------------------------------------------------------------------------------------------------ run
# name: bench parameters.  S81 order: the own row is written while the layer's index traffic runs (the scan
# BG / the candidate gather KG), and the window job starts at the attention issue, after that traffic.
CONFIGS = {
    "asbuilt_c8": dict(LA=0, CREDITS=8), "asbuilt_c1": dict(LA=0, CREDITS=1),
    "asbuilt_c8_scan": dict(LA=0, CREDITS=8, BG=1, BG_STOP=1),
    "la": dict(LA=1), "la_scan": dict(LA=1, BG=1, BG_STOP=1),
    "la_bg": dict(LA=1, BG=1),                                   # stress: scan pressure during the load too
    "la_kg_p1": dict(LA=1, KG=1, KG_FIRST=1, PL="p1"), "la_kg_p2": dict(LA=1, KG=1, KG_FIRST=1, PL="p2"),
    "la_kgcon_p2": dict(LA=1, KG=1, PL="p2"),                    # stress: gather concurrent with the load
    "la_pi16": dict(LA=1, PULLIN=16), "la_pi16lru": dict(LA=1, PULLIN=16, PULLIN_LRU=1),
    "la_pi8lru": dict(LA=1, PULLIN=8, PULLIN_LRU=1),
    "la_pb16": dict(LA=1, PULLIN=16, PULLIN_BATCH=16), "la_pb8": dict(LA=1, PULLIN=8, PULLIN_BATCH=8),
    "la_pb32": dict(LA=1, PULLIN=32, PULLIN_BATCH=32),
    "diag_legacy": dict(LA=1, REF_LEGACY=1),                     # diagnostic: pre-fix REFpb placement, never a result
    "la_pi16_iw16": dict(LA=1, PULLIN=16, LA_IW=16),
    "la_pc": dict(LA=1, LA_ISSUE_PC=1), "la_pc_pi16": dict(LA=1, LA_ISSUE_PC=1, PULLIN=16),
    "cold_la": dict(LA=1, OWN_WRITE=0), "cold_la_pc_pi16": dict(LA=1, LA_ISSUE_PC=1, PULLIN=16, OWN_WRITE=0),
    "cold_la_pi16": dict(LA=1, PULLIN=16, OWN_WRITE=0),
    "cold_la_pc_pb16": dict(LA=1, LA_ISSUE_PC=1, PULLIN=16, PULLIN_BATCH=16, OWN_WRITE=0),
    "cold_la_pc_pb32": dict(LA=1, LA_ISSUE_PC=1, PULLIN=32, PULLIN_BATCH=32, OWN_WRITE=0),
    "la_pc_pb16": dict(LA=1, LA_ISSUE_PC=1, PULLIN=16, PULLIN_BATCH=16),
    "la_pc_pb32": dict(LA=1, LA_ISSUE_PC=1, PULLIN=32, PULLIN_BATCH=32),
    "diag_noref": dict(LA=1, REFI_PS=1000000000000),                # diagnostic floor, never a result
}
# The adopted S81 window configuration (claude/dsrom-s81-window-bind-20261004): the bound full-bandwidth load with
# per-pseudo-channel issue (LA_ISSUE_PC) and the stack controller's batched idle REFpb pull-in (PULLIN 16, BATCH 16).
FINAL = dict(LA=1, LA_ISSUE_PC=1, PULLIN=16, PULLIN_BATCH=16)
CONFIGS.update({
    "lf": dict(FINAL), "lf_scan": dict(FINAL, BG=1, BG_STOP=1), "lf_bg": dict(FINAL, BG=1),
    "lf_kg_p1": dict(FINAL, KG=1, KG_FIRST=1, PL="p1"), "lf_kg_p2": dict(FINAL, KG=1, KG_FIRST=1, PL="p2"),
    "lf_kgcon_p2": dict(FINAL, KG=1, PL="p2"), "lf_cold": dict(FINAL, OWN_WRITE=0), "la_cold": dict(LA=1, OWN_WRITE=0),
})
PLAN = {0: ["asbuilt_c8", "asbuilt_c1", "lf", "lf_cold", "la_cold"], 20: ["asbuilt_c8_scan", "lf_scan", "lf_bg"],
        24: ["lf_kg_p1", "lf_kg_p2", "lf_kgcon_p2", "lf"]}
# job start phases: window cases sample one refresh interval (tREFI 3.9 us = 4,682 cycles) uniformly, 64 points
PHASES = {"asbuilt_c1": [3000, 5077], "asbuilt_c8": [3000, 5077, 7154, 9231], "asbuilt_c8_scan": [3000, 5077],
          **{c: [3000 + 585 * i for i in range(8)] for c in ("lf_kg_p1", "lf_kg_p2", "lf_kgcon_p2")},
          "la": [3000 + 73 * i for i in range(64)]}
CPP = """#include "Vtb_dsrom_s81_window_la.h"
#include "verilated.h"
static double t = 0.0; double sc_time_stamp() { return t; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_dsrom_s81_window_la top; top.clk = 0; top.eval();
    for (long c = 0; c < 2000000 && !Verilated::gotFinish(); ++c) {
        top.clk = 1; top.eval(); t += 5.0; top.clk = 0; top.eval(); t += 5.0; }
    bool f = Verilated::gotFinish(); top.final(); return f ? 0 : 2; }
"""
WL = re.compile(r"WLOAD (.*)")
WS = re.compile(r"WSTREAM cycles=(\d+) ns=([\d.]+) rows=(\d+) beats=(\d+)")
KS = re.compile(r"KGSTACK s=(\d+) blocks=(\d+) sectors=(\d+) hbm_beats=(\d+) keys=(\d+) first=(-?\d+) last=(-?\d+)")
KL = re.compile(r"KGATHER last=(-?\d+) bad=(\d+) first_cycle_rel_window_start=(-?\d+)")
WW = re.compile(r"WWRITE cycles=(-?\d+) ns=(-?[\d.]+) blocks=16 sectors_written=(\d+)")
DC = re.compile(r"DRAMCHK s=(\d+) pre=(\d+) ref=(\d+) act=(\d+) rd=(\d+) wr=(\d+) viol=(\d+) rrefd=(\d+) "
                r"ref_round_bad=(\d+) ref_gap_max_ps=(\d+)")
WD = re.compile(r"WDIAG rsp_stall_pc_cycles=(\d+) req_notrdy_pc_cycles=(\d+) issue_idle_cycles=(\d+)")
VD = re.compile(r"VERDICT (\w+) bad=(\d+) kg_bad=(\d+) rows=(\d+) fault=(\d+)")


def build(cfg: str, obj: Path, verilator: str):
    c = dict(CONFIGS[cfg])
    obj.mkdir(parents=True, exist_ok=True)
    (obj / "main.cpp").write_text(CPP)
    params = dict(CREDITS=8, BG=0, KG=0, KG_FIRST=0, BG_STOP=0, PULLIN=0, CLK_PS=CLK_PS, **PLACEMENTS[c.pop("PL", "p1")])
    chk = c.pop("DRAMCHK", 1)
    params.update(c)
    cmd = [verilator, "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
           "--top-module", "tb_dsrom_s81_window_la", *[f"-G{k}={v}" for k, v in params.items()],
           *(["+define+DRAMCHK", str(ROOT / TRACE_MODEL)] if chk else []),
           "--Mdir", str(obj), str(obj / "main.cpp"), *[str(ROOT / s) for s in SOURCES]]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"build {cfg} failed:\n{(r.stdout + r.stderr)[-4000:]}")
    return obj / "Vtb_dsrom_s81_window_la"


def run_one(binary: Path, vec: Path, L: int, cfg: str, t0: int):
    kg = CONFIGS[cfg].get("KG", 0)
    cold = CONFIGS[cfg].get("OWN_WRITE", 1) == 0
    args = [str(binary), f"+WMEM={vec}/L{L}{'.cold' if cold else ''}.wmem", f"+ROWS={vec}/L{L}.rows", f"+t0={t0}"]
    if kg:
        args.append(f"+PFX={vec}/cand_r1")                 # rank 1: the worst rank of the re-index record
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True)
    out = r.stdout
    row = dict(layer=L, config=cfg, t0=t0, wall_s=round(time.time() - t, 1), returncode=r.returncode)
    m = WL.search(out)
    if m:
        row.update({k: (float(v) if "." in v else int(v)) for k, v in (kv.split("=") for kv in m.group(1).split())})
    m = WS.search(out)
    if m:
        row.update(stream_cycles=int(m.group(1)), stream_ns=float(m.group(2)), streamed_rows=int(m.group(3)))
    m = WW.search(out)
    if m:
        row.update(own_row_write_cycles=int(m.group(1)), own_row_write_ns=float(m.group(2)),
                   own_row_sectors_written=int(m.group(3)))
    if kg:
        row["kg_stacks"] = [dict(zip(("stack", "blocks", "sectors", "hbm_beats", "keys", "first", "last"),
                                     map(int, s.groups()))) for s in KS.finditer(out)]
        m = KL.search(out)
        if m:
            row.update(kg_last_cycles=int(m.group(1)), kg_bad=int(m.group(2)), kg_start_rel_window=int(m.group(3)))
    ck = [list(map(int, m.groups())) for m in DC.finditer(out)]
    if ck:
        row["dram_check"] = dict(stacks=len(ck), violations=sum(c[6] for c in ck), trrefd=sum(c[7] for c in ck),
                                 ref_round_bad=sum(c[8] for c in ck), refpb=sum(c[2] for c in ck),
                                 ref_gap_max_ns=max(c[9] for c in ck) / 1000)
    m = WD.search(out)
    if m:
        row.update(rsp_stall_pc_cycles=int(m.group(1)), req_notrdy_pc_cycles=int(m.group(2)),
                   issue_idle_cycles=int(m.group(3)))
    if row.get("first_rsp_cycles") is not None and row.get("last_rsp_cycles", 0) > row["first_rsp_cycles"]:
        row["sustained_frac"] = round(2176 / ((row["last_rsp_cycles"] - row["first_rsp_cycles"]) * 32 * CLK_PS / 1024), 4)
    m = VD.search(out)
    row["verdict"] = m.group(1) if m else "NONE"
    if row.get("dram_check", {}).get("violations", 0) or (ck and len(ck) != 4):
        row["verdict"] = "FAIL_DRAM"
    if row["verdict"] != "PASS":
        row["log_tail"] = (out + r.stderr)[-2500:]
    return row


def cmd_run(a):
    out = a.out.resolve()
    vec = a.vectors.resolve()
    plan = {int(k): v for k, v in json.loads(a.plan).items()} if a.plan else PLAN
    cfgs = sorted({c for L in plan for c in plan[L]})
    if a.only:
        cfgs = [c for c in cfgs if c in a.only.split(",")]
    with cf.ThreadPoolExecutor(min(len(cfgs), a.jobs)) as ex:
        bins = dict(zip(cfgs, ex.map(lambda c: build(c, out / f"obj_{c}", a.verilator), cfgs)))
    tasks = [(L, c, t0) for L in plan for c in plan[L] if c in bins for t0 in PHASES.get(c, PHASES["la"])]
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda x: run_one(bins[x[1]], vec, *x), tasks))
    for r in rows:
        print(r["layer"], r["config"], r["t0"], r["verdict"], r.get("cycles"), r.get("frac"), r.get("kg_last_cycles"),
              flush=True)
    ver = subprocess.run([a.verilator, "--version"], capture_output=True, text=True).stdout.strip()
    rec = dict(schema="opentallas.dsrom-s81-window-bind.runs.v1", simulator=ver, clk_ps=CLK_PS,
               source_sha256={s: sha(ROOT / s) for s in SOURCES + ["tools/dsrom_s81_window_la.py"]},
               vectors=json.loads((vec / "vectors.json").read_text()), runs=rows,
               status="pass" if all(r["verdict"] == "PASS" for r in rows) else "fail")
    (out / "runs.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("runs", rec["status"], len(rows))


# ------------------------------------------------------------------------------------------------ die binding
DIE = "rtl/dsrom_sys/s81_capture_parent/ot_chip_v41x_die_owner_safe_c8.sv"


def _one(text, old, new):
    if text.count(old) != 1:
        raise ValueError("S81 die anchor changed: " + old[:80])
    return text.replace(old, new, 1)


DIE_PARAMS = """    parameter integer WINDOW_LA_ISSUE_PC = 1, // with WINDOW_STREAM_LA: per-pseudo-channel issue (the adopted, timing-closed)
    parameter integer WINDOW_STREAM_LA = 0, // opt-in (claude/dsrom-s81-window-bind-20261004): the WINDOW refill
                                            // reads the job's ring at full stack bandwidth (ot_dsrom_window_attn_source_la)
    parameter integer IDX_KGATHER_PORT = 0, // opt-in: per-stack wide read client 1 for ot_hdc_v41x_idx_kgather
                                            // (the re-index candidate read); exposed as kgw_* die ports
"""
KGW_PORTS = """    // re-index candidate gather wide clients (IDX_KGATHER_PORT; client 1 of each stack's ot_dsrom_hbm_wmux)
    input  wire [4*32-1:0]       kgw_req_v,
    output wire [4*32-1:0]       kgw_req_rdy,
    input  wire [4*32*K_HAW-1:0] kgw_req_addr,
    input  wire [4*32*4-1:0]     kgw_req_len,
    input  wire [4*32*13-1:0]    kgw_req_tag,
    output wire [4*32-1:0]       kgw_rsp_v,
    input  wire [4*32-1:0]       kgw_rsp_rdy,
    output wire [4*32*13-1:0]    kgw_rsp_tag,
    output wire [4*32*4-1:0]     kgw_rsp_beat,
    output wire [4*32*256-1:0]   kgw_rsp_data,
"""
WL_WIRES = """    // WINDOW_STREAM_LA: the window source's wide port (client 0 of the WIN_STACK stack's wmux)
    wire [31:0] wl_req_v, wl_req_rdy, wl_rsp_v, wl_rsp_rdy;
    wire [32*K_HAW-1:0] wl_req_addr; wire [32*4-1:0] wl_req_len, wl_rsp_beat;
    wire [32*13-1:0] wl_req_tag, wl_rsp_tag; wire [32*256-1:0] wl_rsp_data;
"""


def install_die(text: str) -> str:
    """The S81 die with the bound window load and the wide candidate-gather port.  Default parameters give the
    as-built die (the successor source instantiates the original module; the wmux is wires)."""
    t = _one(text, "    parameter integer C8_PUBLICATION=0,\n",
             DIE_PARAMS + "    parameter integer C8_PUBLICATION=0,\n")
    t = _one(t, "    input  wire              clk,\n    input  wire              rst_n,",
             KGW_PORTS + "    input  wire              clk,\n    input  wire              rst_n,")
    # the window source -> the successor (same parameters and ports, plus the wide port)
    t = _one(t, "        ot_chip_v41x_window_attn_source_owner_safe #(.REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE),",
             "        ot_dsrom_window_attn_source_la #(.STREAM_LA(WINDOW_STREAM_LA != 0), .LA_ISSUE_PC(WINDOW_LA_ISSUE_PC), "
             ".REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE),")
    t = _one(t, "            .s_beat(w_s_beat), .s_data(w_s_data));\n        assign win_fault = win_service_fault;",
             "            .s_beat(w_s_beat), .s_data(w_s_data),\n"
             "            .wl_req_v(wl_req_v), .wl_req_rdy(wl_req_rdy), .wl_req_addr(wl_req_addr), .wl_req_len(wl_req_len),\n"
             "            .wl_req_tag(wl_req_tag), .wl_rsp_v(wl_rsp_v), .wl_rsp_rdy(wl_rsp_rdy), .wl_rsp_tag(wl_rsp_tag),\n"
             "            .wl_rsp_beat(wl_rsp_beat), .wl_rsp_data(wl_rsp_data), .la_load_cycles());\n"
             "        assign win_fault = win_service_fault;")
    # the external-attention branch has no window source: tie the wide port
    t = _one(t, "        end else begin : g_window_external_attention\n",
             "        end else begin : g_window_external_attention\n"
             "        assign wl_req_v = '0; assign wl_req_addr = '0; assign wl_req_len = '0; assign wl_req_tag = '0;\n"
             "        assign wl_rsp_rdy = '0;\n")
    anchor = "        wire [32*K_HAW-1:0] h_addr; wire [32*4-1:0] h_len, r_beat; wire [32*17-1:0] h_tag, r_tag;\n" \
             "        wire [32*256-1:0] h_wdata, r_data; wire [32*32-1:0] h_wstrb;\n"
    t = _one(t, anchor,
             "        wire [32*K_HAW-1:0] h_addr; wire [32*4-1:0] h_len, r_beat; wire [32*17-1:0] h_tag, r_tag;\n"
             "        wire [32*256-1:0] h_wdata, r_data; wire [32*32-1:0] h_wstrb;\n"
             "        // karb stack side -> ot_dsrom_hbm_wmux -> the stack (wires unless WINDOW_STREAM_LA / IDX_KGATHER_PORT)\n"
             "        wire [31:0] ka_v, ka_rdy, ka_we, ka_wd, ka_rv, ka_rrdy;\n"
             "        wire [32*K_HAW-1:0] ka_addr; wire [32*4-1:0] ka_len, ka_rbeat; wire [32*17-1:0] ka_tag, ka_rtag;\n"
             "        wire [32*256-1:0] ka_wdata, ka_rdata; wire [32*32-1:0] ka_wstrb;\n"
             "        wire [63:0] wx_v, wx_rdy, wx_rv, wx_rrdy; wire [64*K_HAW-1:0] wx_addr; wire [64*4-1:0] wx_len, wx_rbeat;\n"
             "        wire [64*13-1:0] wx_tag, wx_rtag; wire [64*256-1:0] wx_rdata;\n"
             "        if (s == WIN_STACK) begin : g_wl\n"
             "            assign wx_v[31:0] = wl_req_v; assign wx_addr[0 +: 32*K_HAW] = wl_req_addr;\n"
             "            assign wx_len[0 +: 128] = wl_req_len; assign wx_tag[0 +: 32*13] = wl_req_tag;\n"
             "            assign wl_req_rdy = wx_rdy[31:0]; assign wl_rsp_v = wx_rv[31:0]; assign wl_rsp_tag = wx_rtag[0 +: 32*13];\n"
             "            assign wl_rsp_beat = wx_rbeat[0 +: 128]; assign wl_rsp_data = wx_rdata[0 +: 32*256];\n"
             "            assign wx_rrdy[31:0] = wl_rsp_rdy;\n"
             "        end else begin : g_nwl\n"
             "            assign wx_v[31:0] = '0; assign wx_addr[0 +: 32*K_HAW] = '0; assign wx_len[0 +: 128] = '0;\n"
             "            assign wx_tag[0 +: 32*13] = '0; assign wx_rrdy[31:0] = '1;\n"
             "        end\n"
             "        assign wx_v[63:32] = IDX_KGATHER_PORT ? kgw_req_v[s*32 +: 32] : '0;\n"
             "        assign wx_addr[32*K_HAW +: 32*K_HAW] = kgw_req_addr[s*32*K_HAW +: 32*K_HAW];\n"
             "        assign wx_len[128 +: 128] = kgw_req_len[s*128 +: 128];\n"
             "        assign wx_tag[32*13 +: 32*13] = kgw_req_tag[s*32*13 +: 32*13];\n"
             "        assign kgw_req_rdy[s*32 +: 32] = IDX_KGATHER_PORT ? wx_rdy[63:32] : '0;\n"
             "        assign kgw_rsp_v[s*32 +: 32] = IDX_KGATHER_PORT ? wx_rv[63:32] : '0;\n"
             "        assign kgw_rsp_tag[s*32*13 +: 32*13] = wx_rtag[32*13 +: 32*13];\n"
             "        assign kgw_rsp_beat[s*128 +: 128] = wx_rbeat[128 +: 128];\n"
             "        assign kgw_rsp_data[s*32*256 +: 32*256] = wx_rdata[32*256 +: 32*256];\n"
             "        assign wx_rrdy[63:32] = IDX_KGATHER_PORT ? kgw_rsp_rdy[s*32 +: 32] : '1;\n"
             "        ot_dsrom_hbm_wmux #(.ENABLE(WINDOW_STREAM_LA != 0 || IDX_KGATHER_PORT != 0), .NPC(32), .AW(K_HAW),\n"
             "            .TAGW(17), .LENW(4), .BEATW(4), .DW(256), .NW(2), .CW(1), .WTAGW(13)) u_wmux (\n"
             "            .clk(clk), .rst_n(rn),\n"
             "            .a_v(ka_v), .a_rdy(ka_rdy), .a_addr(ka_addr), .a_len(ka_len), .a_tag(ka_tag), .a_we(ka_we),\n"
             "            .a_wdata(ka_wdata), .a_wstrb(ka_wstrb), .a_wr_done(ka_wd), .a_rsp_v(ka_rv), .a_rsp_rdy(ka_rrdy),\n"
             "            .a_rsp_tag(ka_rtag), .a_rsp_beat(ka_rbeat), .a_rsp_data(ka_rdata),\n"
             "            .w_v(wx_v), .w_rdy(wx_rdy), .w_addr(wx_addr), .w_len(wx_len), .w_tag(wx_tag),\n"
             "            .w_rsp_v(wx_rv), .w_rsp_rdy(wx_rrdy), .w_rsp_tag(wx_rtag), .w_rsp_beat(wx_rbeat), .w_rsp_data(wx_rdata),\n"
             "            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),\n"
             "            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done),\n"
             "            .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data),\n"
             "            .fault(), .w_grants(), .a_held());\n")
    # both karb flavours drive the wmux's a_* side instead of the stack
    old_h = ("            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),\n"
             "            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done),\n"
             "            .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data),\n"
             "            .k_grants(")
    new_h = ("            .h_v(ka_v), .h_rdy(ka_rdy), .h_addr(ka_addr), .h_len(ka_len), .h_tag(ka_tag), .h_we(ka_we),\n"
             "            .h_wdata(ka_wdata), .h_wstrb(ka_wstrb), .h_wr_done(ka_wd),\n"
             "            .r_v(ka_rv), .r_rdy(ka_rrdy), .r_tag(ka_rtag), .r_beat(ka_rbeat), .r_data(ka_rdata),\n"
             "            .k_grants(")
    if t.count(old_h) != 2:
        raise ValueError("S81 die anchor changed: karb stack side (expected the local and the plain karb)")
    t = t.replace(old_h, new_h)
    # the wide-port wires (module scope, declared before the window source and the stacks use them)
    t = _one(t, "    wire win_service_v, win_service_staged, win_service_done, win_service_fault;\n",
             WL_WIRES + "    wire win_service_v, win_service_staged, win_service_done, win_service_fault;\n")
    return t


def cmd_emit(a):
    """Materialize the existing source hookup for the caller's sole build.

    Selects no operands, model workers or expected output. Full-die source
    emission is not a simulation, timing or physical qualification.
    """
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    patched = out / "ot_chip_v41x_die_owner_safe_c8.sv"
    patched.write_text(install_die((ROOT / DIE).read_text()))
    base = json.loads((ROOT / "rtl/dsrom_sys/s81_capture_parent/selection.json").read_text())
    wrapper_path = "rtl/dsrom_sys/s81_capture_parent/ot_v41_rt_die_l20_c8.sv"
    wrapper = (ROOT / wrapper_path).read_text()
    wrapper = _one(wrapper, "    parameter integer WINDOW_REFILL_CREDITS = 1,\n",
                   DIE_PARAMS + "    parameter integer WINDOW_REFILL_CREDITS = 1,\n")
    # Real wide-client ports pass through the real runtime wrapper. No dummy
    # client or second backend: the caller owns these requests/responses.
    wrapper = _one(wrapper, "    input wire [ROM_R*19-1:0] capture_root_rows,\n",
                   KGW_PORTS.replace("K_HAW", "30") +
                   "    input wire [ROM_R*19-1:0] capture_root_rows,\n")
    wrapper = _one(wrapper, ".WINDOW_REFILL_CREDITS(WINDOW_REFILL_CREDITS)",
                   ".WINDOW_STREAM_LA(WINDOW_STREAM_LA),.IDX_KGATHER_PORT(IDX_KGATHER_PORT)," +
                   ".WINDOW_REFILL_CREDITS(WINDOW_REFILL_CREDITS)")
    names = ("req_v", "req_rdy", "req_addr", "req_len", "req_tag",
             "rsp_v", "rsp_rdy", "rsp_tag", "rsp_beat", "rsp_data")
    wrapper = _one(wrapper, "        .capture_root_rows(capture_root_rows),",
                   "        " + ",".join(f".kgw_{n}(kgw_{n})" for n in names) + ",\n" +
                   "        .capture_root_rows(capture_root_rows),")
    wrapper_out = out / "ot_v41_rt_die_l20_c8.sv"
    wrapper_out.write_text(wrapper)
    original = [s.strip() for s in (ROOT / base["sources_file"]).read_text().splitlines() if s.strip()]
    sources = [str(patched) if s == DIE else (str(wrapper_out) if s == wrapper_path else str(ROOT / s))
               for s in original]
    sources = list(dict.fromkeys(sources + [str(ROOT / s) for s in NEW_RTL +
                                           ["rtl/chip/ot_dsrom_window_stream_la.sv"]]))
    for source in sources:
        if not Path(source).is_file():
            raise ValueError("missing actual source: " + source)
    (out / "sources.f").write_text("\n".join(sources) + "\n")
    params = dict(base["parameters"], WINDOW_STREAM_LA=1, IDX_KGATHER_PORT=a.kgather)
    includes = [str(ROOT / "rtl/hdc/v41"), str(ROOT / "rtl/hdc/v41x"),
                str(ROOT / "rtl/dsrom_sys/s81_capture_parent")]
    selection = dict(top=base["top"], parameters=params, sources_file=str(out / "sources.f"),
                     include_dirs=includes, source_sha256={s: sha(Path(s)) for s in sources},
                     installer_sha256=sha(Path(__file__)),
                     scope="source hookup only; existing caller owns operands, shared clocks and run",
                     native_I55_selected=False, physical_qualified=False)
    (out / "selection.json").write_text(json.dumps(selection, indent=1) + "\n")
    print(str(out / "selection.json"))



# WINDOW-only native model; backend/source lifecycle remains owned by caller.
NATIVE_TOP = "DsromS81WindowLa"
NATIVE_WRAPPER = "rtl/test/v41_runtime/s81_selected/" + NATIVE_TOP + ".sv"
NATIVE_SOURCES = SOURCES[:9] + NEW_RTL[1:] + [NATIVE_WRAPPER]


def cmd_native_emit(a):
    """Emit complete selected source/pins, never compile, tick or generate history."""
    out = a.out.resolve()
    paths = [ROOT / s for s in dict.fromkeys(NATIVE_SOURCES)]
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError("Missing actual WINDOW source: " + str(p))
    # Same original packed writer/merge parameters. STREAM_LA is the sole
    # functional successor selection; module defaults remain off.
    params = dict(STREAM_LA=1, REFILL_OWNER_SAFE=1, POS_W=21, USER_W=10,
                  SEC_W=30, HAW=30, TAGW=16, RETAIN_L0=0, WIN_STACK=0,
                  STREAM_II1=0, REFILL_CREDITS=1, NPC=32, WTAGW=13,
                  WLENW=4, BEATW=4, LA_IW=8, MAX_CONTEXT=1048576)
    out.mkdir(parents=True, exist_ok=False)
    source_file = out / "sources.f"
    source_file.write_text("\n".join(map(str, paths)) + "\n")
    record = dict(top=NATIVE_TOP, prefix="V" + NATIVE_TOP, parameters=params,
                  sources_file=str(source_file), sources=list(map(str, paths)),
                  source_sha256={str(p):sha(p) for p in paths},
                  installer_sha256=sha(Path(__file__)),
                  typed_forwarding_header=str(ROOT / "tools/runtime/dsrom/s81_minimum_window_la.hpp"),
                  typed_forwarding_sha256=sha(ROOT / "tools/runtime/dsrom/s81_minimum_window_la.hpp"),
                  backend_contract=dict(shared_existing_four_stack_memory=True,
                      wide_client=0, inactive_client=1, NPC=32, AW=30,
                      LEN=4, TAG=13, BEAT=4, DW=256,
                      stack_tag_bits=17, namespace="111", client_bits=1,
                      aggregate_C8_tag_bits=16, actual_write_done_required=True,
                      backend_owned_by="Noether", enclosing_caller_owned_by="Arch"),
                  wrapper_model_delta=dict(additional_state_bits=0,
                      additional_MACs_per_cycle=0, additional_pipeline_cycles=0,
                      new_memory_bytes=0, added_clock_sinks=0, port_forward_fanout=1,
                      incremental_logic_area_um2=0,
                      request_boundary_bits_per_cycle=32*(1+1+30+4+13),
                      response_boundary_bits_per_cycle=32*(1+1+13+4+256),
                      maximum_response_bytes_per_cycle=32*256//8,
                      request_bytes_offered_per_cycle=8*4*32,
                      rate_is_interface_ceiling_not_observed=True,
                      new_routing_tracks=0,
                      tracks_basis="Direct hierarchical forwarding of existing 251a wide service wires; no new duplicated route or sink. Context route remains unqualified.",
                      retained_cost_source="results/rtl/dsrom_s81_window_bind_20261004/historical_window_load.json",
                      stage_and_wmux_cost_paid_once=True,
                      model_clock_ps=833, actual_loaded_clock_qualified=False,
                      scope="Wrapper-only delta, not stage/backend area, rate, slot fit or SS/FF qualification"),
                  runtime_context="Borrow actual Runtime.context; one enclosing edge owner; no private clock or memory",
                  first_I55_changed=False, built=False, native_I55_selected=False,
                  physical_qualified=False)
    (out / "selection.json").write_text(json.dumps(record, indent=2) + "\n")
    print(str(out / "selection.json"))


def cmd_bind(a):
    """Patch the S81 die and lint the S81 source set with it at WINDOW_STREAM_LA / IDX_KGATHER_PORT = 0/0, 1/0, 1/1."""
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    die = ROOT / DIE
    patched = out / "ot_chip_v41x_die_owner_safe_c8.sv"
    patched.write_text(install_die(die.read_text()))
    sel = json.loads((ROOT / "rtl/dsrom_sys/s81_capture_parent/selection.json").read_text())
    srcs = [l.strip() for l in (ROOT / sel["sources_file"]).read_text().splitlines() if l.strip()]
    srcs = [str(patched) if s == DIE else str(ROOT / s) for s in srcs]
    extra = [str(ROOT / s) for s in NEW_RTL + ["rtl/chip/ot_dsrom_window_stream_la.sv"]]
    cases = {}
    for la, kg in ((0, 0), (1, 0), (1, 1)):
        params = dict(sel["parameters"])
        cmd = [a.verilator, "--lint-only", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT", "-Wno-PINMISSING",
               "-Wno-UNUSED", "-Wno-CASEINCOMPLETE", "-Wno-IMPLICIT", "--top-module", "ot_chip_v41x_die_owner_safe_c8",
               "-I" + str(ROOT / "rtl/hdc/v41"), "-I" + str(ROOT / "rtl/hdc/v41x"), "-I" + str(ROOT / "rtl/dsrom_sys/s81_capture_parent"), f"-GFULL_SHAPE={a.full_shape}", "-GWINDOW_HBM_ATTENTION=1", f"-GCKV_SELECTED={a.full_shape}",
               f"-GWINDOW_REFILL_OWNER_SAFE={params.get('WINDOW_REFILL_OWNER_SAFE', 1)}",
               f"-GWINDOW_REFILL_CREDITS={params.get('WINDOW_REFILL_CREDITS', 8)}",
               f"-GWINDOW_STREAM_LA={la}", f"-GIDX_KGATHER_PORT={kg}", "-GX_IDX=2", "-GIDX_RING=1",
               *srcs, *extra]
        t = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        errs = [l for l in r.stderr.splitlines() if "%Error" in l]
        cases[f"la{la}_kg{kg}"] = dict(returncode=r.returncode, errors=errs[:20], wall_s=round(time.time() - t, 1))
        print(f"lint la={la} kg={kg}: rc={r.returncode} errors={len(errs)}", flush=True)
    rec = dict(schema="opentallas.dsrom-s81-window-bind.bind.v1", die=DIE, die_sha256=sha(die),
               patched_sha256=sha(patched), new_rtl={s: sha(ROOT / s) for s in NEW_RTL},
               installer="tools/dsrom_s81_window_la.py install_die()", full_shape=a.full_shape, lint=cases,
               status="pass" if all(c["returncode"] == 0 for c in cases.values()) else "fail")
    (out / "bind.json").write_text(json.dumps(rec, indent=1) + "\n")


# ------------------------------------------------------------------------------------------------ record
def _stats(xs):
    xs = sorted(xs)
    return dict(n=len(xs), mean=round(statistics.mean(xs), 1), median=statistics.median(xs),
                p90=xs[min(len(xs) - 1, int(0.9 * len(xs)))], max=xs[-1], min=xs[0]) if xs else None


def cmd_record(a):
    runs = json.loads(Path(a.runs).read_text())
    rows = runs["runs"]
    by = {}
    for r in rows:
        by.setdefault((r["layer"], r["config"]), []).append(r)
    cyc_us = CLK_PS * 1e-6
    peak = 32 * 32 / 1.024e-9 / 1e12                     # one stack: 32 PCs x 32 B / 1,024 ps = 1.0 TB/s
    summary = {}
    for (L, c), rs in sorted(by.items()):
        ok = [r for r in rs if r["verdict"] == "PASS"]
        load = _stats([r["cycles"] for r in ok])
        e = dict(layer=L, config=c, bench_parameters=CONFIGS[c], cases=len(rs), pass_=len(ok),
                 load_cycles=load, write_cycles=_stats([r["own_row_write_cycles"] for r in ok]),
                 stream_cycles=_stats([r["stream_cycles"] for r in ok]))
        if load:
            e["load_us_mean"] = round(load["mean"] * cyc_us, 4)
            e["load_us_max"] = round(load["max"] * cyc_us, 4)
            e["TBps_mean_time"] = round(69632 / (load["mean"] * CLK_PS * 1e-12) / 1e12, 4)
            e["fraction_of_stack_peak_mean_time"] = round(e["TBps_mean_time"] / peak, 4)
            e["TBps_best"] = round(69632 / (load["min"] * CLK_PS * 1e-12) / 1e12, 4)
        su = [r["sustained_frac"] for r in ok if "sustained_frac" in r]
        if su:
            e["sustained_after_first_access"] = dict(median=round(statistics.median(su), 4), mean=round(statistics.mean(su), 4),
                                                     min=round(min(su), 4))
        dc = [r["dram_check"] for r in rs if "dram_check" in r]
        if dc:
            e["dram_check"] = dict(cases=len(dc), violations=sum(d["violations"] for d in dc),
                                   refpb=sum(d["refpb"] for d in dc), ref_gap_max_ns=max(d["ref_gap_max_ns"] for d in dc))
        if any("kg_last_cycles" in r for r in ok):
            kl = [r["kg_last_cycles"] for r in ok]
            e["kgather_cycles"] = _stats(kl)
            e["kgather_sectors_rank"] = sum(17 * s["blocks"] for s in ok[0]["kg_stacks"])
        summary[f"L{L}.{c}"] = e
    S = lambda k, f="mean", what="load_cycles": summary[k][what][f]
    terms = {
        "la": {
            "window_only": dict(own_row_write_cycles=S("L0.lf", what="write_cycles"),
                                window_cycles=S("L0.lf", what="stream_cycles"), source="L0.lf: start -> rows delivered"),
            "scan": dict(own_row_write_cycles=S("L20.lf_scan", what="write_cycles"),
                         window_cycles=S("L20.lf_scan"), source="L20.lf_scan: write under scan, load after it"),
            "reindex": dict(own_row_write_cycles=max(S("L24.lf_kg_p1", what="write_cycles"), S("L24.lf_kg_p2", what="write_cycles")),
                            window_cycles=max(S("L24.lf_kg_p1"), S("L24.lf_kg_p2")),
                            source="L24.lf_kg_p1/p2 (worse): write with the gather, load after it"),
            "reuse": dict(own_row_write_cycles=S("L24.lf", what="write_cycles"), window_cycles=S("L24.lf"),
                          source="L24.lf: no concurrent index traffic"),
        },
        "asbuilt_c8": {
            "window_only": dict(own_row_write_cycles=S("L0.asbuilt_c8", what="write_cycles"),
                                window_cycles=S("L0.asbuilt_c8", what="stream_cycles"), source="L0.asbuilt_c8"),
            "scan": dict(own_row_write_cycles=S("L20.asbuilt_c8_scan", what="write_cycles"),
                         window_cycles=S("L20.asbuilt_c8_scan"), source="L20.asbuilt_c8_scan"),
            "reindex": dict(own_row_write_cycles=S("L0.asbuilt_c8", what="write_cycles"),
                            window_cycles=S("L0.asbuilt_c8"), source="L0.asbuilt_c8 (no index traffic)"),
            "reuse": dict(own_row_write_cycles=S("L0.asbuilt_c8", what="write_cycles"),
                          window_cycles=S("L0.asbuilt_c8"), source="L0.asbuilt_c8"),
        }}
    kg = [r for k in ("lf_kg_p1", "lf_kg_p2") for r in by[(24, k)] if r["verdict"] == "PASS"]
    worst = max(kg, key=lambda r: r["kg_last_cycles"])
    sec = sum(17 * s["blocks"] for s in worst["kg_stacks"])
    secs = worst["kg_last_cycles"] * CLK_PS * 1e-12
    kgs = dict(status="pass", worst_rank=dict(
        name=f"s81_wmux_rank1_{worst['config'].split('_')[-1]}_t0{worst['t0']}", cycles=worst["kg_last_cycles"],
        sectors=sec, bytes=32 * sec, achieved_TBps=round(32 * sec / secs / 1e12, 4),
        fraction_of_peak=round(32 * sec / secs / 1e12 / (4 * peak), 4)),
        basis="ot_hdc_v41x_idx_kgather on each stack's ot_dsrom_hbm_wmux client 1 (S81 HBM service), real 1M "
              "candidate lists of rank 1 (the re-index record's worst rank), with the own-row write concurrent, "
              "two placements x 8 refresh phases; the worst run")
    rec = dict(schema="opentallas.dsrom-s81-window-bind.window-load.v1", position=POS, clk_ps=CLK_PS,
               scope="ONE S81 layer die's WINDOW HBM service (window source -> K mux -> karb -> wmux -> four S81 stack "
                     "models at 1.2 GHz), the 1M token's golden rows of L0 / L20 / L24; every streamed row compared "
                     "with the golden packed rows (bytes), the packed rows decode bit-exactly to the golden FP32 rows",
               simulator=runs["simulator"], source_sha256=runs["source_sha256"], vectors=runs["vectors"],
               summary=summary, composition_terms=terms, kgather_s81=kgs,
               exact=all(r["verdict"] == "PASS" for r in rows), cases=len(rows))
    for f in ("bind", "screen"):
        v = getattr(a, f)
        if v:
            rec[f] = json.loads(Path(v).read_text())
    rec["status"] = "pass" if rec["exact"] and all(rec.get(f, {}).get("status", "pass") == "pass"
                                                   for f in ("bind", "screen")) else "fail"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["status"], json.dumps({k: (v["load_cycles"] or {}).get("mean") for k, v in summary.items()}))


def cmd_inputs(a):
    """Composition inputs under the corrected REFpb controller (results/rtl/hbm_refpb_fix_20261004): the 1M reader
    runs with their fixed-model cycles (dsrom_reader.json variants.fixed) and the adopted gather's fixed-model worst
    rank (dsrom_idxkey_gather_after.json asbuilt_worst_rank, 737 cycles), in the formats tools/dsrom_1m_measure.py
    compose reads.  Derived, never re-simulated here."""
    fix = ROOT / "results/rtl/hbm_refpb_fix_20261004"
    reader = json.loads((ROOT / "results/rtl/dsrom_1m_measured_20261004/reader.json").read_text())
    fixed = json.loads((fix / "dsrom_reader.json").read_text())["variants"]["fixed"]
    for r in reader["runs"]:
        f = fixed.get(r["name"])
        if f is None:
            continue
        clk = r["parameters"]["CLK_PS"]
        r.update(cycles=f["cycles"], sectors=f["sectors"], refpb_fix_before_cycles=f["before_cycles"],
                 refpb_fix_dram_violations=f["dram_check"]["violations"])
        r["bytes"] = r["sectors"] * 32
        r["seconds"] = r["cycles"] * clk * 1e-12
        r["achieved_TBps"] = r["bytes"] / r["seconds"] / 1e12
        r["fraction_of_peak"] = r["achieved_TBps"] / r["peak_TBps"]
    reader["derived_from"] = ["results/rtl/dsrom_1m_measured_20261004/reader.json",
                              "results/rtl/hbm_refpb_fix_20261004/dsrom_reader.json (variants.fixed)"]
    gather = json.loads((ROOT / "results/rtl/dsrom_reindex_candidates_20261004/gather.json").read_text())
    w = json.loads((fix / "dsrom_idxkey_gather_after.json").read_text())["asbuilt_worst_rank"]
    gather["worst_rank"] = dict(gather["worst_rank"], name=w["name"] + "_refpb_fixed", cycles=w["cycles"],
                                achieved_TBps=w["achieved_TBps"], fraction_of_peak=w["fraction_of_peak"])
    gather["derived_from"] = ["results/rtl/dsrom_reindex_candidates_20261004/gather.json",
                              "results/rtl/hbm_refpb_fix_20261004/dsrom_idxkey_gather_after.json (asbuilt_worst_rank)"]
    REC.mkdir(parents=True, exist_ok=True)
    (REC / "reader_refpb_fixed.json").write_text(json.dumps(reader, indent=1) + "\n")
    (REC / "gather_refpb_fixed.json").write_text(json.dumps(gather, indent=1) + "\n")
    print("inputs written", gather["worst_rank"]["cycles"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("vectors")
    v.add_argument("--out", type=Path, required=True)
    v.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    r = sub.add_parser("run")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--vectors", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=16)
    r.add_argument("--only", default="")
    r.add_argument("--plan", default="", help='JSON {layer: [config, ...]} instead of PLAN (diagnostics)')
    r.add_argument("--verilator", default="verilator")
    e = sub.add_parser("emit")
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--kgather", type=int, choices=(0, 1), default=0)
    n = sub.add_parser("native-emit", help="WINDOW-only borrowed wide-service model; source emission only")
    n.add_argument("--out", type=Path, required=True)
    b = sub.add_parser("bind")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--verilator", default="verilator")
    b.add_argument("--full-shape", type=int, default=1, help="0: reduced die (CKV_SELECTED off), a light lint")
    c = sub.add_parser("record")
    c.add_argument("--runs", required=True)
    c.add_argument("--bind", default="")
    c.add_argument("--screen", default="")
    c.add_argument("--out", default=str(REC / "window_load.json"))
    sub.add_parser("inputs")
    a = ap.parse_args()
    dict(inputs=cmd_inputs, vectors=cmd_vectors, run=cmd_run, emit=cmd_emit, **{"native-emit": cmd_native_emit},
         bind=cmd_bind, record=cmd_record)[a.cmd](a)


if __name__ == "__main__":
    main()
