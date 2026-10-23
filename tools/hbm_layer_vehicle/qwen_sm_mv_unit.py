#!/usr/bin/env python3
"""SMB-INT8 (10-19): Qwen3-8B D4G8 SM.MATVEC (fmt 3 INT8) on the d4g die SM master with the opt-in INT8 packet path.

RTL: ot_hbm_accel_smh_attn #(.ENABLE_INT8(1)) (bench define OT_SMH_ATTN_INT8): command[116] marks the cycle's packet as
ONE packed line of 128 INT8 codes; ot_smh_static_int8 (the real ot_hbm_accel_int8_line converter, PIPE 1) delivers two
BF16 lines (low 64 codes first, both with the packet's tag) to the static front I8_LAT = 2 and 3 cycles later, where
they are ordinary fmt-0 (BF16) issue slots.  Exactness: INT8 codes are exact in BF16, BF16 x BF16 products exact in FP32,
so the SM's fmt-0 chunk8 csum of the widened image == hgi_sim.lib.sm_int8 (the fmt-3 golden, raw FP32 sums); the row
scale is applied after the reduction by the SU consumer (qwen_compiler row_scale_* records), not by the SM.

Compiler (this file, on top of sm_mv_unit.py's fmt-0 calendar): the BF16 line order (group-slot waves of IL = 8, IL-deep
positional interleave, padding slots idle) is unchanged; issue slots are PAIRED (2p, 2p + 1): one packed INT8 line
{codes of slot 2p+1, codes of slot 2p} (the INT8 HBM image: 128 B a line, half the BF16 image) enters the SM I8_LAT
cycles before slot 2p with command[116] set, and both slots expect that packet's tag (a padding slot of a pair expects
the packet with valid = 0).  One packed line per two edges = the converter's fixed rate = 64 codes / cycle / SM, the
rate the d4g Qwen price charges (lines / SM + overhead).
Self-check (no RTL claim without it): every packed line, widened by a Python model of the converter, equals the two
fmt-0 lines sm_mv_unit.pack would issue; the captured O == lib.sm_int8(W, A) == V.csum(G.mul(W, bf16(A))).

Placement (d4g8, one die a TP-8 rank, 16 SM): rows dealt in blocks of R = ceil(m / 16) to SM 0..15; op 'sm0' = SM 0's
block (all blocks equal: the busiest SM), op 'all' = every row of the die (coverage).

  qwen_sm_mv_unit.py run --kv DIR/<stage> --L 0 --bundle B --work W --out J [--tags qkv,o,gu,down] [--all]
                         [--mut wbit|nopkt|late]
  qwen_sm_mv_unit.py regress ...  (sm_mv_unit.py run on the DS fixtures with this tree's ot_hbm_accel_smh_attn at its
                                   DEFAULT parameters: the default-off path must still PASS)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402
import sm_mv_unit as SM  # noqa: E402
from hgi_sim import lib as A  # noqa: E402

F = np.float32
I8_LAT = 2
SMH_ATTN = "rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv"
I8_FILES = ["rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv", "rtl/hbm_accel/sm/static/ot_smh_static_int8.sv",
            "rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv"]   # LH-SMATT/INT8 10-19: ENABLE_INT8 1 = the hard SAFE tile
NSM = 16


# HBM-QINT8B (10-20): the wide INT8 front's files, always taken from THIS tree (the bundle's front_static is the
# pre-INT8W revision, byte-identical to this tree's default-off build)
I8W_TREE = ["rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv"]
I8W_FILES = ["rtl/hbm_accel/sm/attn/ot_hbm_sm_i8w_front.sv"]


def die_sources_tree(bundle: Path, int8: bool, i8w: bool = False):
    """bundle master files with THIS tree's ot_hbm_accel_smh_attn (+ the INT8 adapter files when int8; + the wide INT8
    front and this tree's front_static when i8w)."""
    tree = [SMH_ATTN] + I8W_TREE        # this tree's front_static always (its INT8W = 0 build is the bundle's netlist)
    src = []
    for p in SM.die_sources(bundle):
        t = next((f for f in tree if str(p).endswith(f)), None)
        src.append(ROOT / t if t else p)
    assert any(str(p) == str(ROOT / SMH_ATTN) for p in src), "bundle has no ot_hbm_accel_smh_attn"
    return src + ([ROOT / f for f in I8_FILES] if int8 or i8w else []) + [ROOT / f for f in I8W_FILES]


def build(work: Path, bundle: Path, mut_sign=False, int8=True, i8w=False, rtl_mut=""):
    name = ("obj_i8w" + ("_" + rtl_mut if rtl_mut else "")) if i8w else \
        (("obj_i8_sign" if mut_sign else "obj_i8") if int8 else "obj_default")
    # HBM-P4-SM (10-23): QSM_DEFINES=OT_SM_QSPLIT[,OT_SM_QSPLIT_MUT=n] = extra build defines (opt-in RTL variants)
    xdef = [d for d in os.environ.get("QSM_DEFINES", "").split(",") if d]
    obj = work / (name + "".join("_" + d.replace("=", "") for d in xdef))
    exe = obj / "Vtb_hbm_smh_attn"
    if exe.exists():
        return exe
    srcs = die_sources_tree(bundle, int8, i8w)
    tb = ROOT / "rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv"
    vl = os.environ.get("VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    defs = SM.DIE_DEFINES + (["OT_SMH_ATTN_I8W"] if i8w else ["OT_SMH_ATTN_INT8"] if int8 else []) + \
        (["OT_INT8_MUT_SIGN"] if mut_sign else []) + \
        ({"sign": ["OT_I8W_MUT_SIGN"], "noswap": ["OT_I8W_MUT_NOSWAP"], "half": ["OT_I8W_MUT_HALF"]}.get(rtl_mut, [])
         if i8w else []) + xdef
    inc = sorted({str(Path(s).parent) for s in srcs})
    cmd = [vl, "--binary", "-j", os.environ.get("VL_JOBS", "16"), "-O1", "-CFLAGS", "-O1", "--x-assign", "fast",
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "256",
           "--top-module", "tb_hbm_smh_attn", f"-GMAXC={SM.MAXC}", "--Mdir", str(obj)] + \
          [f"-D{d}" for d in defs] + [f"-I{p}" for p in inc] + [str(s) for s in srcs] + [str(tb)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_{obj.name}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr +
                                               f"\nBUILD_RC {r.returncode} wall {time.time() - t0:.0f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_{obj.name}.log)")
    return exe


def widen(code):
    """Python model of ot_hbm_accel_int8_line: signed INT8 -> BF16 bits (exact), 0 -> +0."""
    return int(SM.S.bf16_bits(np.asarray([float(code)], F))[0])


WIDEN = [widen(c - 256 if c >= 128 else c) for c in range(256)]


def cmd_word(**f):
    i8 = f.pop("i8", 0)
    w = SM.cmd_word(**f) if f else (SM.cmd_word(mode=0) if i8 else 0)
    return w | (int(i8) << 116)


class Cal(SM.Cal):
    def merge(self, c, **f):
        cur = self.cmd.setdefault(c, {})
        for k, v in f.items():
            assert k not in cur or cur[k] == v, ("calendar conflict", c, k)
            cur[k] = v

    def write(self, d: Path, n):
        assert n <= SM.MAXC, (n, SM.MAXC)
        with open(d / "cmd.hex", "w") as fc, open(d / "pkt.hex", "w") as fp, open(d / "xw.hex", "w") as fx, \
                open(d / "kvd.hex", "w") as fk:
            for c in range(n):
                fc.write(f"{cmd_word(**dict(self.cmd.get(c, {}))):048x}\n")
                fp.write(f"{self.pkt.get(c, 0):0275x}\n")
                fx.write(f"{self.xw.get(c, 0):0516x}\n")
                fk.write("0" * 16 + "\n")


def codes_line(W, r, g, t):
    """64 INT8 codes of BF16-line slot (r, g, t) in sm_mv_unit.pack's fmt-0 lane order (k = (64 g + j) * 8 + t)."""
    K = W.shape[1]
    word = 0
    for j in range(SM.LF):
        k = (g * SM.LF + j) * SM.C8 + t
        if k < K:
            word |= (int(W[r, k]) & 0xFF) << (8 * j)
    return word


def compile_int8(W, x, ops, mut="", check_lines=256):
    wf = W.astype(F)
    line_bf, Gn, xw = SM.pack(0, wf, x)
    cal = Cal()
    c = 4
    for a, word in enumerate(xw):
        for g in range(SM.NBEAT):
            cal.xw[c] = (1 << 2062) | (a << 2055) | (g << 2048) | ((word >> (2048 * g)) & ((1 << 2048) - 1))
            c += 1
    c += SM.X_GAP
    exp, tag, nchk, packed_total = [], 0, 0, 0
    for oi, (name, rows) in enumerate(ops):
        cal.set(c, mode=0, flaunch=1, ffmt=0)
        c += SM.FMT_LEAD
        first = c
        items = [(r, g) for r in range(len(rows)) for g in range(Gn)]
        order = []
        for wb in range(0, len(items), SM.IL):
            for t in range(SM.C8):
                for s_ in range(SM.IL):
                    order.append((items[wb + s_][0], items[wb + s_][1], t) if wb + s_ < len(items) else None)
        assert len(order) % 2 == 0
        li, pi = 0, 0
        for p in range(0, len(order), 2):
            pair = order[p:p + 2]
            if pair[0] is None and pair[1] is None:
                continue
            halves = [codes_line(W, rows[it[0]], it[1], it[2]) if it is not None else 0 for it in pair]
            word = halves[0] | (halves[1] << 512)
            if nchk < check_lines:                       # converter model == the fmt-0 lines (exactness of the image)
                for h, it in enumerate(pair):
                    want = line_bf(rows[it[0]], it[1], it[2]) if it is not None else 0
                    got = 0
                    for j in range(SM.LF):
                        got |= WIDEN[(halves[h] >> (8 * j)) & 0xFF] << (16 * j)
                    assert got == want, ("widened INT8 line != fmt-0 line", name, p + h)
                nchk += 1
            if mut == "wbit" and oi == 0 and pi == 0:
                word ^= 1
            for h, it in enumerate(pair):
                f = dict(mode=0, pkt=1, pkt_tag=tag)
                if it is not None:
                    r, g, t = it
                    f.update(valid=1, first=int(t == 0), last=int(t == SM.C8 - 1), row=r, glast=int(g == Gn - 1),
                             slot=r & 7, xaddr=g * SM.C8 + t)
                    li += 1
                cal.merge(first + p + h, **f)
            withhold = mut == "nopkt" and oi == 0 and pi == 1
            pc = first + p - I8_LAT + (1 if (mut == "late" and oi == 0 and pi == 1) else 0)
            if not withhold:
                cal.merge(pc, i8=1)
                assert pc not in cal.pkt, ("packet slot conflict", pc)
                cal.pkt[pc] = (1 << 1098) | (tag << 1088) | word
            tag = (tag + 1) & 1023
            pi += 1
        c = first + len(order)
        packed_total += pi
        exp.append(dict(name=name, rows=list(map(int, rows)), first_line=first, first_packet=first - I8_LAT,
                        last_line=c - 1, lines=li, packed_lines=pi, issue_cycles=len(order)))
        c += SM.OP_GAP
    n = c + SM.DRAIN
    for i, e in enumerate(exp):
        e["window_end"] = exp[i + 1]["first_line"] if i + 1 < len(exp) else n + 64
    return cal, n, exp, Gn, nchk


I8W_RTL_MUTS = ("sign", "noswap", "half")


def compile_int8w(W, x, ops, mut="", check_lines=256):
    """HBM-QINT8B: the WIDE INT8 front (ot_hbm_sm_i8w_front, command mode 3).  An op's R rows are PAIRED: A = r and
    B = r + Rh (Rh = ceil(R / 2)); one packed line an edge carries chunk (g, t) of A (low 64 codes, left side, x in
    column 0) and of B (high 64 codes, right side, x in column 4), issued with A's row / slot / xaddr / first / last on the
    SAME edge as its packet (no converter offset).  Slot order = compile_int8's per wave (t-major, IL items) over the A
    items, so each side's columns see exactly the fmt-0 line sequence of their rows (exact: the BF16 csum per row).
    Result row = A's tag: column 0 = A, rdata column 1 = B (the front's result mode).  x is written to columns 0 and 4.
    Compiler mutants: wbit (a code bit of the first line), halfswap (first line's halves swapped), nopkt (one packet
    withheld), late (one packet a cycle late), tag (one word expects the wrong packet tag)."""
    wf = W.astype(F)
    line_bf, Gn, xw = SM.pack(0, wf, x)
    cal = Cal()
    c = 4
    for a, word in enumerate(xw):
        word = word | (word << (4 * SM.XC))                       # x in column 0 (rows A) and column 4 (rows B)
        for g in range(SM.NBEAT):
            cal.xw[c] = (1 << 2062) | (a << 2055) | (g << 2048) | ((word >> (2048 * g)) & ((1 << 2048) - 1))
            c += 1
    c += SM.X_GAP
    exp, tag, nchk, packed_total = [], 0, 0, 0
    for oi, (name, rows) in enumerate(ops):
        R = len(rows)
        Rh = -(-R // 2)
        first = c
        items = [(r, g) for r in range(Rh) for g in range(Gn)]
        order = []
        for wb in range(0, len(items), SM.IL):
            for t in range(SM.C8):
                for s_ in range(SM.IL):
                    order.append((items[wb + s_][0], items[wb + s_][1], t) if wb + s_ < len(items) else None)
        li, pi = 0, 0
        for p, it in enumerate(order):
            if it is None:
                cal.merge(first + p, mode=3)
                continue
            r, g, t = it
            halves = [codes_line(W, rows[r], g, t), codes_line(W, rows[r + Rh], g, t) if r + Rh < R else 0]
            if nchk < check_lines:
                for h, rr in enumerate((r, r + Rh)):
                    want = line_bf(rows[rr], g, t) if rr < R else 0
                    got = 0
                    for j in range(SM.LF):
                        got |= WIDEN[(halves[h] >> (8 * j)) & 0xFF] << (16 * j)
                    assert got == want, ("widened INT8 half != fmt-0 line", name, p, h)
                nchk += 1
            if mut == "halfswap" and oi == 0 and pi == 0:
                halves = halves[::-1]
            word = halves[0] | (halves[1] << 512)
            if mut == "wbit" and oi == 0 and pi == 0:
                word ^= 1
            ptag = (tag + 1) & 1023 if (mut == "tag" and oi == 0 and pi == 2) else tag
            cal.merge(first + p, mode=3, pkt=1, pkt_tag=ptag, valid=1, first=int(t == 0), last=int(t == SM.C8 - 1),
                      row=r, glast=int(g == Gn - 1), slot=r & 7, xaddr=g * SM.C8 + t)
            li += 2 if r + Rh < R else 1
            withhold = mut == "nopkt" and oi == 0 and pi == 1
            pc = first + p + (1 if (mut == "late" and oi == 0 and pi >= 1) else 0)   # op 0's stream one edge late from line 1
            if not withhold:
                assert pc not in cal.pkt, ("packet slot conflict", pc)
                cal.pkt[pc] = (1 << 1098) | (tag << 1088) | word
            tag = (tag + 1) & 1023
            pi += 1
        c = first + len(order)
        packed_total += pi
        exp.append(dict(name=name, rows=list(map(int, rows)), Rh=Rh, first_line=first, first_packet=first,
                        last_line=c - 1, lines=li, packed_lines=pi, issue_cycles=len(order)))
        c += SM.OP_GAP
    n = c + SM.DRAIN
    for i, e in enumerate(exp):
        e["window_end"] = exp[i + 1]["first_line"] if i + 1 < len(exp) else n + 64
    return cal, n, exp, Gn, nchk


def check_run_i8w(exp, res, acc):
    """results of the wide front: row tag r -> column 0 = acc[A = rows[r]], column 1 = acc[B = rows[r + Rh]]."""
    out, ok_all = [], True
    for e in exp:
        rows, Rh = e["rows"], e["Rh"]
        rr = [x for x in res if e["first_line"] <= x[0] < e["window_end"]]
        seen, bad = {}, []
        for cyc, rrow, data in rr:
            if rrow >= Rh or rrow in seen:
                bad.append(("unexpected_or_duplicate_row", rrow, cyc))
                continue
            seen[rrow] = cyc
            for col, ri in ((0, rrow), (1, rrow + Rh)):
                if ri >= len(rows):
                    continue
                got = (data >> (32 * col)) & 0xFFFFFFFF
                want = int(np.asarray(acc[rows[ri]], F).view(np.uint32))
                if got != want:
                    bad.append(("acc", rows[ri], col, f"{got:08x}", f"{want:08x}"))
        missing = [i for i in range(Rh) if i not in seen]
        ok = not bad and not missing
        ok_all &= ok
        last = max(seen.values()) if seen else None
        out.append(dict(e, results=len(seen), missing=missing[:16], n_missing=len(missing), bad=bad[:16],
                        n_bad=len(bad), first_result=min(seen.values()) if seen else None, last_result=last,
                        cycles_first_line_to_last_result=(last - e["first_line"] + 1) if last is not None else None,
                        verdict="PASS" if ok else "FAIL"))
    return out, ok_all


def load_kv(kv: Path, L: int, rank=0):
    meta = json.loads((kv / "sm_mv.json").read_text())
    z = np.load(kv / "sm_mv.npz")
    out = {}
    for r in meta["records"]:
        if r["rank"] != rank or r["L"] != L:
            continue
        g = lambda n: z[r["arrays"][n]["key"]]  # noqa: E731
        out[r["tag"]] = dict(meta=r, A=g("A").astype(F), W=g("W").astype(np.int8), O=g("O").astype(F))
    return meta, out


def cmd_run(a):
    kv = Path(a.kv)
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    meta, recs = load_kv(kv, a.L)
    tags = a.tags.split(",") if a.tags else list(recs)
    i8w = getattr(a, "i8w", False)
    if i8w:
        exe = None if a.dry else build(work, Path(a.bundle).resolve(), i8w=True,
                                       rtl_mut=a.mut if a.mut in I8W_RTL_MUTS else "")
    else:
        exe = None if a.dry else build(work, Path(a.bundle).resolve(), mut_sign=a.mut == "sign")
    report, ok_all = [], True
    for tag in tags:
        e = recs[tag]
        W, x, O = e["W"], e["A"], e["O"]
        m, K = W.shape
        acc = np.asarray(SM.V.csum(SM.G.mul(W.astype(F), SM.G.to_bf16(x)[None, :])), F)
        lib = np.asarray(A.sm_int8(W, x), F)
        gok = np.array_equal(acc.view(np.uint32), O.view(np.uint32)) and np.array_equal(lib.view(np.uint32),
                                                                                         O.view(np.uint32))
        R = -(-m // NSM)
        ops = [("sm0", list(range(R)))] + ([("all", list(range(m)))] if a.all else [])
        pr = (e["meta"].get("priced_d4g8") or [{}])[0]
        row = dict(tag=tag, L=a.L, fmt="INT8 (fmt 3) via the opt-in packet path", m=m, K=K, rows_sm=R,
                   golden_selftest="PASS" if gok else "golden_mismatch", priced_d4g8=pr)
        if not gok:
            row["verdict"] = "golden_mismatch"
            report.append(row)
            ok_all = False
            print(f"QSM_MV {tag} golden_mismatch", flush=True)
            continue
        if i8w:
            row["fmt"] = "INT8 (fmt 3) via the WIDE INT8 front (command mode 3, 128 codes/edge)"
            mut = "" if a.mut in I8W_RTL_MUTS else a.mut
            cal, n, exp, Gn, nchk = compile_int8w(W, x, ops, mut)
        else:
            mut = "" if a.mut == "sign" else a.mut
            cal, n, exp, Gn, nchk = compile_int8(W, x, ops, mut)
        d = work / f"L{a.L}_{tag}{'_all' if a.all else ''}{'_' + a.mut if a.mut else ''}"
        d.mkdir(exist_ok=True)
        cal.write(d, n)
        row.update(Gn=Gn, bf16_lines_per_row=Gn * SM.C8, calendar_cycles=n, x_beats=len(cal.xw),
                   widened_lines_checked=nchk, cmd_sha256=SM.sha(d / "cmd.hex"), pkt_sha256=SM.sha(d / "pkt.hex"),
                   xw_sha256=SM.sha(d / "xw.hex"))
        if a.dry:
            row["ops"] = exp
            report.append(row)
            print(f"QSM_MV {tag} m={m} K={K} R={R} Gn={Gn} n={n} packed={exp[0]['packed_lines']} (dry)", flush=True)
            continue
        t0 = time.time()
        r = subprocess.run([str(exe), f"+CMD={d}/cmd.hex", f"+PKT={d}/pkt.hex", f"+XW={d}/xw.hex",
                            f"+KVD={d}/kvd.hex", f"+N={n}"], capture_output=True, text=True, cwd=d)
        log = r.stdout + r.stderr
        (d / "run.log").write_text(log)
        res, fault, done = SM.parse(log)
        ops_out, ok = check_run_i8w(exp, res, acc) if i8w else SM.check_run(exp, res, acc, O.view(np.uint32), "FP32")
        for o in ops_out:
            if o["last_result"] is not None:
                o["cycles_first_packet_to_last_result"] = o["last_result"] - o["first_packet"] + 1
        ok = ok and done and fault is None and r.returncode == 0
        row.update(ops=ops_out, run_rc=r.returncode, fault=fault, done=done, sim_s=round(time.time() - t0, 1),
                   run_log_sha256=SM.sha(d / "run.log"), verdict="PASS" if ok else "FAIL")
        ok_all &= ok
        report.append(row)
        s0 = ops_out[0]
        print(f"QSM_MV L{a.L} {tag} INT8 m={m} K={K} {row['verdict']} sm0 R={R} lines={s0['lines']} "
              f"packed={s0['packed_lines']} cyc={s0.get('cycles_first_packet_to_last_result')} "
              f"priced={pr.get('base_cost')} fault={fault}", flush=True)
    doc = dict(schema="opentallas.hbm_qwen_sm_mv_unit.v1", lane="SMB-INT8", kv=str(kv), kv_npz_sha256=meta["npz_sha256"],
               L=a.L, bundle=a.bundle, mut=a.mut or None,
               rtl=("ot_hbm_accel_smh_attn #(.ENABLE_INT8(1), .INT8W(1)) + ot_hbm_sm_attn_front_static + ot_hbm_sm_i8w_front "
                    "(this tree) + bundle master files (DIE_DEFINES), tb_hbm_smh_attn -DOT_SMH_ATTN_I8W, Verilator 5.050"
                    if getattr(a, "i8w", False) else
                    "ot_hbm_accel_smh_attn #(.ENABLE_INT8(1)) (this tree) + bundle master files (DIE_DEFINES) + "
                    "ot_smh_int8_tile (hard SAFE tile, ENABLE_INT8 1) / ot_smh_static_int8 / ot_hbm_accel_int8_line, tb_hbm_smh_attn -DOT_SMH_ATTN_INT8, Verilator 5.050"),
               records=report, verdict="PASS" if ok_all else "FAIL")
    Path(a.out).write_text(json.dumps(doc, indent=1, default=int) + "\n")
    print(f"QWEN_SM_MV_UNIT {'PASS' if ok_all else 'FAIL'} records={len(report)} mut={a.mut or '-'}")
    return 0 if ok_all else 1


def cmd_regress(rest):
    """sm_mv_unit.py run with this tree's ot_hbm_accel_smh_attn at its default parameters (ENABLE_INT8 = 0)."""
    SM.build = lambda work, bundle: build(work, bundle, int8=False)
    return SM.main(["run"] + rest)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "regress":
        return cmd_regress(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("run")
    p.add_argument("--kv", required=True, help="qwen_sm_mv_kv.py output dir of one stage (sm_mv.json / sm_mv.npz)")
    p.add_argument("--L", type=int, default=0)
    p.add_argument("--bundle", default="")
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--tags", default="")
    p.add_argument("--all", action="store_true", help="also run every row of the die as one op (coverage)")
    p.add_argument("--mut", default="", choices=["", "wbit", "nopkt", "late", "sign", "halfswap", "tag", "noswap", "half"])
    p.add_argument("--i8w", action="store_true", help="HBM-QINT8B wide INT8 front (INT8W 1, command mode 3)")
    p.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    return cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
