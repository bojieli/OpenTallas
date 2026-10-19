#!/usr/bin/env python3
"""Q-CTLM calendar bench (rtl/qwen_dv/qfd_dv_cmd_cal.sv inside rtl/qwen_dv/qfd_tt_ctlm_dv.sv), Verilator.

Builds a calendar image (PW0..1023 + DW0..7, the qfd_dv_cmd_cal format), replays it as qfd_sys_face does (tt_pw and
seq_dh on the same edge, one word an edge), starts the four segments (BOOT on the seal, stage 0, stages 1 and 2 = decode
layers, stage 37 = LM head) and compares every issued command / local event with a Python model of the documented
timing (cmd register loaded at S + T_k, T_k = sum of deltas; S = start edge = run event + 1, BOOT S = DW7 + 2; EMB and SEG
one register later).  Also checks dc: the merged next token (ss5 tok_v / tok_idx) -> s_done / ntok two edges later.
--nsl 12 adds the twelve-slice qfd_dv_slice2 row on the cmd / hr chain: every slice must latch id k from the BOOT SETID.

    python3 rtl/test/qwen_dv/tt_ctlm_cal_bench.py [--mut N] [--nsl 12] [--work DIR]
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 512                       # entry 0 at PW 512 (8-aligned, below the ME control rows 976..)


def cmdw(go=1, kind=0, f=0, dst=15):
    """slice command word: [0] go, [3:1] kind, [111:4] fields (f << 4), [115:112] dst"""
    return (go & 1) | ((kind & 7) << 1) | ((f & ((1 << 108) - 1)) << 4) | ((dst & 15) << 112)


def setid(i=0):
    return cmdw(1, 7, i & 15, 15)


def build_segments(rng):
    """four segments of (delta, cmd); returns {seg: [(delta, cmd)]}"""
    seg = {}
    seg[3] = [(4, setid(0)), (3, cmdw(1, 4, rng.getrandbits(75), 15)), (2, cmdw(0, 0, 0, 0))]          # BOOT
    s0 = [(5, cmdw(1, 1, 0, 14)),                                   # LOCAL EMB
          (1, cmdw(1, 5, rng.getrandbits(30), 0)),                  # STREAM to W5
          (1, cmdw(1, 1, 7, 15)),                                   # SU pidx 7, all
          (2, cmdw(1, 0, (1 << 2) | (64 << 3) | (0xBEEF << 19), 0)),  # XC: COLL mode 1 words 64 tag
          (4095, cmdw(0, 0, 0, 0)),                                 # NOP spacer
          (9, cmdw(1, 2, rng.getrandbits(46), 3)),                  # STN slice 3
          (1, cmdw(1, 3, rng.getrandbits(99), 0)),                  # ROOT
          (1, cmdw(1, 6, 1, 15))]                                   # AMAX clear
    seg[0] = s0
    s1 = [(4, cmdw(1, 2, rng.getrandbits(46), k % 12)) for k in range(12)]
    s1[0] = (6, s1[0][1])
    s1 += [(1, cmdw(1, 1, 3 + k, 15)) for k in range(9)]                                                   # back-to-back
    s1 += [(3, cmdw(1, 2, 0x155, 14)), (2, cmdw(1, 0, (0 << 2) | (16 << 3) | (77 << 19), 0)), (40, cmdw(1, 1, 300, 15))]
    seg[1] = s1                                                     # [.., LOCAL SEG base 0x155, XC, SU]
    seg[2] = [(4, cmdw(1, 6, 0b10, 15)), (1, cmdw(1, 6, 0b11, 15)), (30, cmdw(1, 0, (1 << 2) | (1 << 3), 0))]
    return seg


def image(seg, mut_meta=False):
    order = [3, 0, 1, 2]
    ents, desc = [], {}
    for s in order:
        while len(ents) % 4:
            ents.append((1, 0))                                     # padding (never fetched: outside the segment)
        desc[s] = (len(ents), len(seg[s]))
        ents += seg[s]
    pw = [0] * 1024
    for i in range(BASE):
        pw[i] = (i * 0x9E3779B97F4A7C15) & ((1 << 64) - 1)          # program words (the ME copy and this copy)
    for e, (d, c) in enumerate(ents):
        w = (d << 116) | c
        pw[BASE + 2 * e] = w & ((1 << 64) - 1)
        pw[BASE + 2 * e + 1] = w >> 64
    dw = [0] * 8
    dw[0] = (0x43414C44 << 32) | (BASE << 16) | len(ents)
    for s in range(4):
        f, n = desc[s]
        dw[1 + s] = (f << 16) | n
    return pw, dw, desc


def digest(pw, dw):
    """qkd_program_commit digest over PW0..1023 then DW0..7"""
    m = (1 << 64) - 1
    d = 0x51484F5354505247
    for i, w in enumerate(pw + dw):
        desc, addr = (1, i - 1024) if i >= 1024 else (0, i)
        d = (((d << 7) | (d >> 57)) & m) ^ w ^ ((desc << 10) | addr)
    return d


def model(seg, starts):
    """starts: [(S, seg)] -> expected log lines {(cycle, kind, value)}"""
    exp = []
    for S, s in starts:
        t = 0
        for d, c in seg[s]:
            t += d
            go, kind, dst = c & 1, (c >> 1) & 7, c >> 112
            if not go:
                continue
            if dst == 14:
                if kind == 1:
                    exp.append((S + t + 1, "EMB", None))
                elif kind == 2:
                    exp.append((S + t + 1, "SEG", (c >> 4) & 0xFFF))
            else:
                exp.append((S + t, "CMD", c))
    return exp


def run(work: Path, mut: int, nsl: int):
    rng = random.Random(17)
    seg = build_segments(rng)
    pw, dw, desc = image(seg)
    ev = [(5, 4, 0), (7, 5, digest(pw, dw))]
    c = 10
    for a in range(1024):
        ev.append((c, 0, (a << 64) | pw[a])); c += 1
    for a in range(8):
        ev.append((c, 1, (a << 64) | dw[a])); c += 1
    c_dw7 = c - 1
    boot_s = c_dw7 + 2
    tok, pos = 0x2468A, 77
    run_ev = [(boot_s + 40, 0), (boot_s + 4400, 1), (boot_s + 4600, 2), (boot_s + 4800, 37)]
    starts = [(boot_s, 3)]
    for rc, stg in run_ev:
        ev.append((rc, 2, (1 << 42) | (stg << 36) | (tok << 18) | pos))
        starts.append((rc + 1, {0: 0, 37: 2}.get(stg, 1)))
    tok_c = boot_s + 4900
    ntok = 0x1F00D
    nval = 0x3F8CAFE5                        # Q-DIEPLAN6: the merged value (ss5 tok_val [105:74]) -> dc nval [31:0]
    ev.append((tok_c, 3, (nval << 74) | (1 << 24) | ntok))
    ncyc = tok_c + 20
    exp = model(seg, starts)
    # EMB carries the stage-0 token; SEG the base; the dc s_done / ntok two edges after the ss5 pulse
    exp = [(cy, k, tok if k == "EMB" else v) for cy, k, v in exp]
    work.mkdir(parents=True, exist_ok=True)
    evf, lgf = work / "ev.txt", work / f"log_m{mut}_n{nsl}.txt"
    with open(evf, "w") as f:
        for cy, k, v in sorted(ev, key=lambda e: (e[0], e[1])):
            f.write(f"{cy} {k} {v:x}\n")
    obj = work / f"obj_m{mut}_n{nsl}"
    srcs = [str(ROOT / l.strip()) for l in open(HERE / "tt_ctlm_dv_sources.f") if l.strip()]
    if nsl:
        srcs += [str(ROOT / s) for s in SLICE_SRCS]
    srcs.append(str(HERE / "tb_qfd_tt_ctlm_cal.sv"))
    if not (obj / "Vtb").exists():
        cmd = ["verilator", "--cc", "--exe", "--build", "-O1" if nsl else "-O2", "-j", "8", "-Wno-fatal", "-Wno-lint",
               "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-WIDTHCONCAT", "--x-assign", "0", "--x-initial", "0",
               "--top-module", "tb_qfd_tt_ctlm_cal", "--prefix", "Vtb", f"-GMUT={mut}", f"-GNSL={nsl}", "-Mdir", str(obj),
               str(HERE / "main2.cpp")] + srcs
        if nsl:
            cmd[cmd.index("--build"):cmd.index("--build")] = ["--output-split", "20000"]
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if p.returncode:
            print(p.stdout[-3000:], p.stderr[-3000:])
            raise SystemExit("verilator build failed")
    subprocess.run([str(obj / "Vtb"), f"+EV={evf}", f"+LOG={lgf}", f"+NCYC={ncyc}"], cwd=work, check=True,
                   capture_output=True)
    got = []
    sids, cf = {}, None
    ready = fault = commit = None
    errs = []
    dcs = []
    for line in open(lgf):
        p = line.split()
        cy, k = int(p[0]), p[1]
        if k == "CMD":
            got.append((cy, k, int(p[2], 16)))
        elif k == "EMB":
            got.append((cy, k, int(p[2], 16)))
        elif k == "SEG":
            got.append((cy, k, int(p[2], 16)))
        elif k == "DC":
            dcs.append((cy, int(p[2], 16)))
        elif k == "COMMIT":
            commit = cy
        elif k == "SINKF":
            errs.append(f"record-port sink fault at {cy}")
        elif k == "READY":
            ready = cy
        elif k == "FAULT":
            fault = cy
        elif k == "SID":
            sids[int(p[2])] = int(p[3])
        elif k == "CF":
            cf = (int(p[2]), int(p[3]))
    n_extra = 1
    if commit is None:
        errs.append("record-port sink 1 never committed the calendar copy")
    se, sg = set(exp), set(got)
    for e in sorted(se - sg)[:6]:
        errs.append(f"missing {e[1]} at {e[0]} {e[2]:x}" if e[2] is not None else f"missing {e}")
    for g in sorted(sg - se)[:6]:
        errs.append(f"unexpected {g[1]} at {g[0]} {g[2]:x}")
    ok = len(se & sg) + (commit is not None)
    n = len(se) + n_extra
    if ready is None:
        errs.append("calendar image never ready")
    if fault is not None:
        errs.append(f"calendar fault at {fault}")
    # dc: s_done (bit 50), ntok ([49:32]) and nval ([31:0]) two edges after the ss5 tok_v edge
    want = [cy for cy, v in dcs if (v >> 50) & 1 and ((v >> 32) & 0x3FFFF) == ntok and (v & 0xFFFFFFFF) == nval]
    n += 1
    if want and want[0] == tok_c + 2:
        ok += 1
    else:
        errs.append(f"dc s_done/ntok at {want[:1]} want {tok_c + 2}")
    if nsl:
        n += nsl
        for k in range(nsl):
            if sids.get(k) == k:
                ok += 1
            else:
                errs.append(f"slice {k}: id {sids.get(k)}")
    return ok, n, errs


SLICE_SRCS = """rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/qfd_dv_redstn2.sv rtl/qwen_dv/qfd_dv_vm.sv rtl/qwen_dv/qfd_dv_scalar2.sv
rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv
rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_sfu.sv
rtl/hdc/ot_hdc_sfu_q.sv rtl/physical/ot_hdc_vred_pending_guard.sv rtl/test/full_sm_service/sram_models.sv
rtl/test/hbm_rf_visibility/scale_sram_model.sv rtl/qwen_dv/qfd_dv_heads.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv
rtl/lib/ot_rst_pipe.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv""".split()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mut", type=int, default=0)
    ap.add_argument("--nsl", type=int, default=0)
    ap.add_argument("--work", default="/tmp/qctlm_cal")
    a = ap.parse_args()
    ok, n, errs = run(Path(a.work), a.mut, a.nsl)
    v = "PASS" if ok == n and not errs else "FAIL"
    print(f"CTLM_CAL MUT={a.mut} NSL={a.nsl}: {v} {ok}/{n}")
    for e in errs[:8]:
        print("   ", e)
    sys.exit(0 if v == "PASS" else 1)


if __name__ == "__main__":
    main()
