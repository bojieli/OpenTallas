#!/usr/bin/env python3
"""VEH-FMT-SM2 (10-19): SM.MATVEC on the d4g die SM master, from the REAL layer fixture (no random records).

The d4g GEN2/GEN2b SM is ot_hbm_accel_smh_attn (sm_SW0..7 / sm_NW0..7): normal modes run the static S1 feed
(rtl/hbm_accel/sm/static/ot_smh_static_feed.sv, command[82:0] of the 192-bit word) whose every issue slot is
compiler-supplied.  Until this tool NO compiler of that 83-bit normal-op calendar existed
(tools/hbm_svc_static_sm_packed136_model.py: full_native_SM83_programme_bound=False, compiler_calendar_bound=False) and no
bench had run a DS weight matrix through the static SM.  This is that compiler + the unit pre-check.

Calendar (one SM, one or more ops; every cycle fixed, no ready / wait):
  * operand packing = tools/dshbm_matched_sm_seq.gen_op (the layout the dynamic smh element was qualified with bit for bit
    against the golden csum): FP8 / FP4 block-dot lines (LA = 4 / 8 lanes of 32 codes + UE8M0 scale bytes at 1024 + 8 j),
    BF16 lines (64 lanes of 16 b); x-store words per address (13 beats of 2048 b; column n = MTP slot n, AR uses
    column 0 only, columns 1..7 hold x = 0);
  * line order = rtl_gpu_sm_exact.issue_order(R, Gn, 8, gs=True) (group-slot waves of IL = 8 (row, group) items): item s
    of a wave issues on slot cycle s of each of the 8 t steps; a partial last wave keeps its empty slots idle (positional
    IL-deep column interleave; smoke 10-19 without the padding: wrong accumulation, R=1 wq_a row 0 bd0785f9 vs bd971bbd); command[25:0] = {valid, first (t = 0), last (t = 7), row12 = r, group_last (g = Gn - 1), slot3 = r mod 8
    (ot_hbm_accel_issue_pq iss_slot = row_now[2:0]), xaddr7 = g * 8 + t}; command[29] / [39:30] = packet valid / tag
    (the feed faults a valid without its packet or a tag mismatch); packet = {1, tag10, scale64, weights1024} in the
    SAME cycle;
  * format_launch (command[28], [27:26] = fmt = mode[1:0]) FMT_LEAD cycles before an op's first line (fc_fmt state:
    +5 to the unpack, as the line);  magic 0xA2 [191:184] on every non-zero word; BE control [111:83] = 0 (normal);
  * x store written before the first op (one beat a cycle, X_GAP idle cycles after the last beat).
Checks (per op): every row retires exactly once (rv / rrow), column 0 FP32 == golden FP32 accumulator bit for bit
(V.linear_q csum of the block terms / V.mv csum, HDC_V41_ARITH=chunk8), column 0 rounded to O.fmt == the fixture O
(the ds_native layer run), columns 1..7 == +0 (x = 0), no fault / schedule_fault (the TB stops on either).
Golden self-test: the recomputed O must equal the fixture O (else status golden_mismatch, no RTL claim).
Measured: first line -> last result cycles per op vs the d4g price of the record (fixture 'priced' base_cost, W1 class).

d4g placement (tools/hgi_sim/d4g_quadrant_1017.py W1): the TP-96 rank-0 record's rows split in halves over dies 2r / 2r+1
(fixture d4g_placement row_split_halves_on_dies_2r_2r+1), then dealt in blocks of R = ceil(m_die / 16) to SM 0..15.
Ops per record: 'sm0' = die 0 SM 0's block (the timing of record of the busiest SM), 'all' = every row of the rank
(coverage of every weight row on the RTL).

  sm_mv_unit.py run --fixtures FIX/L00 --weights SMW/L00 --bundle B --work W --out J [--recs 4,7] [--mut wbit|nopkt]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import rtl_gpu_sm_exact as S  # noqa: E402

F = np.float32
MAGIC = 0xA2
SUB, LBS, LSB, NC, IL, XD, NBEAT = 4, 2, 16, 8, 8, 128, 13
LB, LF = SUB * LBS, SUB * LSB
XC = LB * 266 + LF * 16                      # 3,152 x bits per column
C8 = 8                                       # t steps per chunk (column accumulation, csum leaf)
FMT_LEAD, X_GAP, OP_GAP, DRAIN = 8, 16, 256, 512
MAXC = 262144                                # TB array depth of this lane's build (-GMAXC)
DIE_DEFINES = ["OT_SMH_FC_HIER", "OT_SMH_HIER", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY"]
FMT_NAME = {0: "BF16", 1: "FP8", 2: "FP4"}


# ------------------------------------------------------------------------------------------------ operands
def x_terms(fmt, x):
    """per-format x image: BF16 bits, or (E4M3 codes, block exponents) of quant_fp8 (the golden's own act quant)."""
    if fmt == 0:
        return S.bf16_bits(np.asarray(x, F))
    import rtl_hdc_v41_blockdot_campaign as BC
    xq, xe = V.quant_fp8(np.asarray(x, F))
    return BC.e4m3_codes(xq), np.asarray(xe, np.int64)


def golden_acc(fmt, w, x):
    """FP32 accumulator the SM column must hold (before the O-format rounding of the writer)."""
    x = np.asarray(x, F)
    if fmt == 0:
        return V.csum(G.mul(np.asarray(w, F), G.to_bf16(x)[None, :]))
    xq, xe = V.quant_fp8(x)
    nb = w.q.shape[1] // 32
    terms = np.stack([np.ldexp((w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F),
                               w.e[:, b] + xe[b]).astype(F) for b in range(nb)], axis=-1)
    return V.csum(terms)


def pack(fmt, w, x):
    """weight lines per (row, g, t) and x-store words per address (gen_op layout, NC = 8, column 0 = x)."""
    import rtl_hdc_v41_blockdot_campaign as BC
    if fmt == 0:
        wb = S.bf16_bits(np.asarray(w, F)).astype(np.int64)
        R, K = wb.shape
        C = -(-K // C8)
        LA = LF
        xb = x_terms(0, x)
    else:
        R, K = w.q.shape
        nb = K // 32
        assert K % 32 == 0
        C = -(-nb // C8)
        fp4 = fmt == 2
        LA = LB if fp4 else LB // 2
        wcode = (BC.e2m1_codes if fp4 else BC.e4m3_codes)(w.q.reshape(-1)).reshape(R, K)
        we = np.asarray(w.e, np.int64)
        xc, xe = x_terms(fmt, x)
    Gn = -(-C // LA)
    assert Gn * C8 <= XD, ("x store too small", Gn, C8, XD)

    def line(r, g, t):
        word = 0
        for j in range(LA):
            ch = g * LA + j
            if ch >= C:
                continue
            if fmt == 0:
                k = ch * C8 + t
                if k < K:
                    word |= int(wb[r, k]) << (16 * j)
            else:
                b = ch * C8 + t
                if b < nb:
                    codes = wcode[r, b * 32:(b + 1) * 32]
                    if fmt == 2:
                        for i, cd in enumerate(codes):
                            word |= (int(cd) & 0xF) << (128 * j + 4 * i)
                    else:
                        for i, cd in enumerate(codes):
                            word |= (int(cd) & 0xFF) << (256 * j + 8 * i)
                    se = int(we[r, b]) + 127
                    assert 0 <= se < 256, ("UE8M0 scale out of range", r, b, se)
                    word |= se << (1024 + 8 * j)
        return word

    xw = []
    for a in range(Gn * C8):
        g, t = divmod(a, C8)
        word = 0
        for j in range(LA):
            ch = g * LA + j
            if ch >= C:
                continue
            if fmt == 0:
                k = ch * C8 + t
                if k < K:
                    word |= int(xb[k]) << (LB * 266 + 16 * j)          # column 0
            else:
                b = ch * C8 + t
                if b < nb:
                    f = 0
                    for i, cd in enumerate(xc[b * 32:(b + 1) * 32]):
                        f |= (int(cd) & 0xFF) << (8 * i)
                    f |= (int(xe[b]) & 0x3FF) << 256
                    word |= f << (266 * j)
        xw.append(word)
    return line, Gn, xw


# ------------------------------------------------------------------------------------------------ calendar
def cmd_word(**f):
    if not f:
        return 0
    w = 0

    def put(lo, width, v):
        nonlocal w
        assert 0 <= int(v) < (1 << width), (lo, width, v)
        w |= int(v) << lo
    put(184, 8, MAGIC)
    put(181, 3, f.get("mode", 0))
    put(30, 10, f.get("pkt_tag", 0))
    put(29, 1, f.get("pkt", 0))
    put(28, 1, f.get("flaunch", 0))
    put(26, 2, f.get("ffmt", 0))
    put(25, 1, f.get("valid", 0))
    put(24, 1, f.get("first", 0))
    put(23, 1, f.get("last", 0))
    put(11, 12, f.get("row", 0))
    put(10, 1, f.get("glast", 0))
    put(7, 3, f.get("slot", 0))
    put(0, 7, f.get("xaddr", 0))
    return w


class Cal:
    def __init__(self):
        self.cmd, self.pkt, self.xw = {}, {}, {}

    def set(self, c, **f):
        assert c not in self.cmd, ("calendar conflict", c)
        self.cmd[c] = f

    def write(self, d: Path, n):
        assert n <= MAXC, (n, MAXC)
        with open(d / "cmd.hex", "w") as fc, open(d / "pkt.hex", "w") as fp, open(d / "xw.hex", "w") as fx, \
                open(d / "kvd.hex", "w") as fk:
            for c in range(n):
                fc.write(f"{cmd_word(**self.cmd.get(c, {})):048x}\n")
                fp.write(f"{self.pkt.get(c, 0):0275x}\n")
                fx.write(f"{self.xw.get(c, 0):0516x}\n")
                fk.write("0" * 16 + "\n")


def compile_record(fmt, w, x, ops, mut=""):
    """ops = [(name, row indices)] -> (calendar, n, per-op expectations).  mut (negative controls, must FAIL):
    'wbit' flips weight bit 0 of op 0's first line (arithmetic: the row's result changes); 'nopkt' withholds op 0's
    third packet (schedule: the feed's packet-valid check must raise schedule_fault)."""
    line, Gn, xw = pack(fmt, w, x)
    cal = Cal()
    c = 4
    for a, word in enumerate(xw):
        for g in range(NBEAT):
            cal.xw[c] = (1 << 2062) | (a << 2055) | (g << 2048) | ((word >> (2048 * g)) & ((1 << 2048) - 1))
            c += 1
    c += X_GAP
    exp, tag = [], 0
    for oi, (name, rows) in enumerate(ops):
        cal.set(c, mode=fmt, flaunch=1, ffmt=fmt)
        c += FMT_LEAD
        first = c
        # group-slot waves of IL issue slots: item s of a wave owns slot cycle s of every t step (the column macros'
        # IL-deep accumulation interleave is positional); a partial last wave keeps its empty slots as idle cycles
        # (issue_pq issues padding slots with row_ok = 0: no line, no command)
        items = [(r, g) for r in range(len(rows)) for g in range(Gn)]
        order = []
        for wb in range(0, len(items), IL):
            for t in range(C8):
                for s_ in range(IL):
                    order.append((items[wb + s_][0], items[wb + s_][1], t) if wb + s_ < len(items) else None)
        li = -1
        for slot_c, it in enumerate(order):
            if it is None:
                c += 1
                continue
            li += 1
            r, g, t = it
            word = line(rows[r], g, t)
            if mut == "wbit" and oi == 0 and li == 0:
                word ^= 1
            cal.set(c, mode=fmt, valid=1, first=int(t == 0), last=int(t == C8 - 1), row=r, glast=int(g == Gn - 1),
                    slot=r & 7, xaddr=g * C8 + t, pkt=1, pkt_tag=tag)
            if not (mut == "nopkt" and oi == 0 and li == 2):
                cal.pkt[c] = (1 << 1098) | (tag << 1088) | word
            tag = (tag + 1) & 1023
            c += 1
        exp.append(dict(name=name, rows=list(map(int, rows)), first_line=first, last_line=c - 1, lines=li + 1,
                        issue_cycles=len(order)))
        c += OP_GAP
    n = c + DRAIN
    for i, e in enumerate(exp):
        e["window_end"] = exp[i + 1]["first_line"] if i + 1 < len(exp) else n + 64
    return cal, n, exp, Gn


# ------------------------------------------------------------------------------------------------ fixture
def load_record(fix: Path, smw: Path, k: int):
    # k = the layer-local dispatch index (weights.json k = fixture k_layer; the fixture's own k is the operand key)
    rec = [q for q in json.loads((fix / "records.json").read_text())["records"]["0"] if q.get("k_layer", q["k"]) == k]
    assert len(rec) == 1, k
    rec = rec[0]
    assert rec["op"] == "SM.MATVEC", rec["op"]
    z = np.load(fix / "operands.npz")
    x = z[f"r0.k{rec['k']}.A"].view(F)
    o = z[f"r0.k{rec['k']}.O"]
    wj = json.loads((smw / "weights.json").read_text())
    ent = [e for e in wj["records"] if e["rank"] == 0 and e["k"] == k]
    assert len(ent) == 1 and ent[0]["tag"] == rec["tag"] and ent[0]["occ"] == rec["occ"], (k, ent)
    ent = ent[0]
    wz = np.load(smw / "weights.npz")
    if ent["kind"] == "Q8":
        w = V.Q8(wz[f"r0.k{k}.Wq"].astype(np.float64), wz[f"r0.k{k}.We"].astype(np.int64))
        fmt = ent["fmt"]
        assert fmt in (1, 2)
    else:
        w = (wz[f"r0.k{k}.W"].astype(np.uint32) << 16).view(F)
        fmt = 0
    return rec, ent, fmt, w, x, o


def check_golden(rec, fmt, w, x, o):
    acc = np.asarray(golden_acc(fmt, w, x), F)
    ofmt = rec["desc"]["O"][6]
    out = G.to_bf16(acc) if ofmt == "BF16" else acc
    ok = np.array_equal(np.asarray(out, F).view(np.uint32), o)
    return acc, ofmt, ok


# ------------------------------------------------------------------------------------------------ build / run
def die_sources(bundle: Path):
    mf = json.loads((bundle / "master_files.json").read_text())
    return [bundle / p for p in mf["ot_hbm_accel_smh_attn"]]


def build(work: Path, bundle: Path):
    obj = work / "obj_mv"
    exe = obj / "Vtb_hbm_smh_attn"
    if exe.exists():
        return exe
    tb = ROOT / "rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv"
    vl = os.environ.get("VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    cmd = [vl, "--binary", "-j", os.environ.get("VL_JOBS", "16"), "-O1", "-CFLAGS", "-O1", "--x-assign", "fast",
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "256",
           "--top-module", "tb_hbm_smh_attn", f"-GMAXC={MAXC}", "--Mdir", str(obj)] + \
          [f"-D{d}" for d in DIE_DEFINES] + \
          [f"-I{bundle / p}" for p in sorted({str(Path(s).parent.relative_to(bundle)) for s in die_sources(bundle)})] + \
          [str(s) for s in die_sources(bundle)] + [str(tb)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / "build_mv.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr +
                                       f"\nBUILD_RC {r.returncode} wall {time.time() - t0:.0f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_mv.log)")
    return exe


def parse(log):
    res, fault, done = [], None, False
    for ln in log.splitlines():
        p = ln.split()
        if ln.startswith("R ") and len(p) == 4:
            res.append((int(p[1]), int(p[2], 16), int(p[3], 16)))
        elif ln.startswith("FAULT"):
            fault = ln.strip()
        elif ln.startswith("DONE"):
            done = True
    return res, fault, done


def check_run(exp, res, acc, o, ofmt):
    out, ok_all = [], True
    for e in exp:
        rr = [x for x in res if e["first_line"] <= x[0] < e["window_end"]]
        rows = e["rows"]
        seen = {}
        bad = []
        for cyc, rrow, data in rr:
            if rrow >= len(rows) or rrow in seen:
                bad.append(("unexpected_or_duplicate_row", rrow, cyc))
                continue
            seen[rrow] = cyc
            got = data & 0xFFFFFFFF
            gr = rows[rrow]
            want = int(np.asarray(acc[gr], F).view(np.uint32))
            if got != want:
                bad.append(("acc", gr, f"{got:08x}", f"{want:08x}"))
            gv = np.array([got], np.uint32).view(F)
            ov = int((G.to_bf16(gv) if ofmt == "BF16" else gv).view(np.uint32)[0])
            if ov != int(o[gr]):
                bad.append(("O", gr, f"{ov:08x}", f"{int(o[gr]):08x}"))
            if data >> 32:
                bad.append(("cols1-7_nonzero", gr, f"{data >> 32:x}"))
        missing = [rows[i] for i in range(len(rows)) if i not in seen]
        ok = not bad and not missing
        ok_all &= ok
        last = max(seen.values()) if seen else None
        out.append(dict(e, results=len(seen), missing=missing[:16], n_missing=len(missing), bad=bad[:16],
                        n_bad=len(bad), first_result=min(seen.values()) if seen else None, last_result=last,
                        cycles_first_line_to_last_result=(last - e["first_line"] + 1) if last is not None else None,
                        verdict="PASS" if ok else "FAIL"))
    return out, ok_all


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cmd_run(a):
    fix, smw = Path(a.fixtures), Path(a.weights)
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    recs = [int(k) for k in a.recs.split(",")] if a.recs else \
        [e["k"] for e in json.loads((smw / "weights.json").read_text())["records"] if e["rank"] == 0]
    exe = None if a.dry else build(work, Path(a.bundle).resolve())
    report, ok_all = [], True
    for k in recs:
        rec, ent, fmt, w, x, o = load_record(fix, smw, k)
        acc, ofmt, gok = check_golden(rec, fmt, w, x, o)
        m = len(o)
        m_die = -(-m // 2)
        R = -(-m_die // 16)
        ops = [("sm0", list(range(R))), ("all", list(range(m)))]
        if a.sm0_only:
            ops = ops[:1]
        row = dict(k=k, tag=rec["tag"], occ=rec["occ"], fmt=FMT_NAME[fmt], O_fmt=ofmt, m=m,
                   K=int(len(x)), d4g_rows_die=m_die, d4g_rows_sm=R, golden_selftest="PASS" if gok else "golden_mismatch",
                   priced=rec.get("priced"))
        if not gok:
            row["verdict"] = "golden_mismatch"
            report.append(row)
            ok_all = False
            print(f"SM_MV k{k} {rec['tag'][:24]} golden_mismatch", flush=True)
            continue
        cal, n, exp, Gn = compile_record(fmt, w, x, ops, a.mut)
        d = work / f"k{k}{'_' + a.mut if a.mut else ''}"
        d.mkdir(exist_ok=True)
        cal.write(d, n)
        row.update(Gn=Gn, lines_per_row=Gn * C8, calendar_cycles=n, x_beats=len(cal.xw),
                   cmd_sha256=sha(d / "cmd.hex"), pkt_sha256=sha(d / "pkt.hex"), xw_sha256=sha(d / "xw.hex"))
        if a.dry:
            row["ops"] = exp
            report.append(row)
            print(f"SM_MV k{k} {rec['tag'][:24]} {FMT_NAME[fmt]} m={m} K={len(x)} Gn={Gn} n={n} (dry)", flush=True)
            continue
        t0 = time.time()
        r = subprocess.run([str(exe), f"+CMD={d}/cmd.hex", f"+PKT={d}/pkt.hex", f"+XW={d}/xw.hex",
                            f"+KVD={d}/kvd.hex", f"+N={n}"], capture_output=True, text=True, cwd=d)
        log = r.stdout + r.stderr
        (d / "run.log").write_text(log)
        res, fault, done = parse(log)
        ops_out, ok = check_run(exp, res, acc, o, ofmt)
        ok = ok and done and fault is None and r.returncode == 0
        row.update(ops=ops_out, run_rc=r.returncode, fault=fault, done=done, sim_s=round(time.time() - t0, 1),
                   run_log_sha256=sha(d / "run.log"), verdict="PASS" if ok else "FAIL")
        ok_all &= ok
        report.append(row)
        s0 = ops_out[0]
        print(f"SM_MV k{k} {rec['tag'][:24]} {FMT_NAME[fmt]} m={m} K={len(x)} {row['verdict']} "
              f"sm0 R={R} lines={s0['lines']} cyc={s0['cycles_first_line_to_last_result']} "
              f"priced={(rec.get('priced') or [{}])[0].get('base_cost')} fault={fault}", flush=True)
    doc = dict(schema="opentallas.hbm_sm_mv_unit.v1", fixtures=str(fix), weights=str(smw), bundle=a.bundle,
               mut=a.mut or None, rtl="ot_hbm_accel_smh_attn die master (bundle master_files.json, DIE_DEFINES) in "
               "rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv, Verilator 5.050", records=report,
               verdict="PASS" if ok_all else "FAIL")
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"SM_MV_UNIT {'PASS' if ok_all else 'FAIL'} records={len(report)} mut={a.mut or '-'}")
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("run")
    p.add_argument("--fixtures", required=True)
    p.add_argument("--weights", required=True)
    p.add_argument("--bundle", default="")
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--recs", default="")
    p.add_argument("--mut", default="", choices=["", "wbit", "nopkt"])
    p.add_argument("--sm0-only", action="store_true")
    p.add_argument("--dry", action="store_true", help="compile calendars + golden self-test only (no build / sim)")
    a = ap.parse_args(argv)
    return cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
