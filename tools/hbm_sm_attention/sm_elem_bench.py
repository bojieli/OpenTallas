#!/usr/bin/env python3
"""SM-ELEMENT attention bench + static calendar compiler (H-SM-ATT r2 2026-10-15).

Replaces the component bench (tb_hbm_sm_attn: converter + issue + 4 lane columns) with the whole static SM
(rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv: 8 columns x 4 leaves of the closed XS / tcl / tct / pass-through / BE
arithmetic, KV converter, probability store, 64-bit run descriptor).  This script is the COMPILER: it builds the exact
per-cycle 192-bit command calendar (plus the KV line packets at the SM staging-buffer boundary, x-loader beats and
KV_DESC words) from a cycle model of the converter (KvLineModel, a transcription of ot_hbm_sm_kv_line) and measured
implemented latencies, then plays it in tb_hbm_smh_attn and checks every result word bit for bit against the golden
(tools/hgi_sim/lib.py att_qk / att_pv chunk sums, via sm_attn_bench).  The testbench never reacts to the DUT; any
beat, packet, score or node that is not where the calendar put it is a sticky schedule_fault (no stall).

  sm_elem_bench.py run --shape ds640 --ops qk_sm0,pv_sm0 [--mut ...] --work DIR --out R.json [--probe]
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
sys.path.insert(0, str(HERE))
import sm_attn_bench as B  # noqa: E402
import numpy as np  # noqa: E402

F = np.float32
MAGIC = 0xA2
XC, BFOFF = 3152, 2128            # fragment bits per column, BF16 field offset in a column
LINE_RATE = (8, 11)               # 8 lines / 11 cycles per SM = 98.9 B/cycle (HBM 99 B/cycle/SM physical BW)

SRC = ["rtl/hdc/ot_hdc_prefix.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/gpu/ot_gpu_tree.sv",
       "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
       "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
       "rtl/gpu/ot_gpu_stack.sv", "rtl/hbm_accel/sm/ot_hbm_accel_stack.sv", "rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv",
       "rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv", "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv", "rtl/hbm_accel/sm/ot_hbm_accel_smh_gu.sv",
       "rtl/hbm_accel/sm/static/ot_smh_static_feed.sv", "rtl/hbm_accel/sm/static/ot_smh_static_front.sv",
       "rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv", "rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv",
       "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_native_col.sv", "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_pstore.sv",
       "rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_desc_static.sv", "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv",
       "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_leafh.sv", "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_tile.sv",
       "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_be.sv", "rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv",
       "rtl/lib/ot_hdly.sv", "rtl/v41rom/ot_v41_bterm.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv",
       "rtl/lib/ot_rst_relay.sv", "rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv"]


# ---------------------------------------------------------------- converter cycle model (= ot_hbm_sm_kv_line) ---------
class KvLineModel:
    """Cycle transcription of ot_hbm_sm_kv_line's write side (qword realigner, two waves), read side (2-deep read
    pipeline, 4-entry FIFO) and its op state, used by the compiler to place packet and consume slots exactly."""

    def __init__(self):
        self.act = False

    def cfg(self, qk, kv4, n8, h128, rows):
        self.act, self.qk, self.h128 = True, qk, h128
        self.kv4 = kv4 and not h128
        self.n8 = rows if h128 else (0 if kv4 else n8)
        self.tq = h128 and qk
        self.wcap = 32 if self.tq else 8
        self.wb, self.wr, self.wleft, self.wri, self.fill = 0, 0, rows, 0, 0
        self.wn = min(rows, self.wcap)
        self.full, self.fn, self.flast = [False, False], [0, 0], [False, False]
        self.rb, self.rs, self.rt, self.inflight, self.op_drain = 0, 0, 0, 0, False
        self.p1, self.p2, self.fifo = None, None, []

    def comb(self):
        rqw = 16 if self.h128 else (36 if self.wri >= self.n8 else 66)
        emit = self.act and self.wleft != 0 and not self.full[self.wb] and self.fill >= rqw
        fill_e = self.fill - (rqw if emit else 0)
        s_ready = self.act and self.wleft != 0 and fill_e + 17 <= 96
        return rqw, emit, fill_e, s_ready

    def s_ready(self):
        return self.comb()[3]

    def m_valid(self):
        return len(self.fifo) > 0

    def head(self):
        return self.fifo[0]

    def step(self, s_valid, m_ready):
        """Advance one clock edge.  Returns the popped beat (or None)."""
        if not self.act:
            assert not s_valid and not m_ready
            return None
        rqw, emit, fill_e, s_ready = self.comb()
        assert not s_valid or s_ready, "line offered while the converter has no room (schedule fault)"
        wacc = s_valid and s_ready
        wwave_end = emit and self.wr == self.wn - 1
        rn = self.fn[self.rb]
        nsl = (rn + 3) >> 2 if self.tq else rn
        bmax = 7 if self.qk else (1 if self.h128 else 7)
        rlast_beat = self.rt == bmax and self.rs == nsl - 1
        can_rd = self.act and self.full[self.rb] and self.inflight + len(self.fifo) < 4
        rwave_end = can_rd and rlast_beat
        op_done_rd = rwave_end and self.flast[self.rb]
        op_done = self.op_drain and self.inflight == 0 and len(self.fifo) == 0
        pop = len(self.fifo) > 0 and m_ready
        assert not m_ready or pop, "consume slot with no beat (schedule fault)"
        popped = self.fifo.pop(0) if pop else None
        # ---- edge ----
        p2_new = self.p1
        self.p1 = dict(slot=self.rs, step=self.rt, last=op_done_rd, wend=rlast_beat) if can_rd else None
        if self.p2 is not None:
            self.fifo.append(self.p2)
        self.p2 = p2_new
        self.inflight = (1 if self.p1 else 0) + (1 if self.p2 else 0)   # = inflight + can_rd - p2_v
        wb0, wleft0, rb0 = self.wb, self.wleft, self.rb
        self.fill = fill_e + (17 if wacc else 0)
        if emit:
            self.wr += 1
            self.wleft -= 1
            self.wri += 1
        if wwave_end:
            self.wr = 0
            self.wb ^= 1
            self.fn[wb0] = self.wn
            self.flast[wb0] = wleft0 == 1
            self.wn = min(wleft0 - 1, self.wcap)
            self.full[wb0] = True
        if rwave_end:
            self.full[rb0] = False
        if can_rd:
            if op_done_rd:
                self.op_drain = True
            if self.qk:
                if self.rs == nsl - 1:
                    self.rs, self.rt = 0, self.rt + 1
                else:
                    self.rs += 1
            else:
                if self.rt == bmax:
                    self.rt, self.rs = 0, self.rs + 1
                else:
                    self.rt += 1
            if rwave_end:
                self.rb ^= 1
                self.rs = self.rt = 0
        elif op_done:
            self.op_drain = False
            self.act = False
        return popped


# ---------------------------------------------------------------- command word ------------------------------------------
def cmd_word(**f):
    w = 0
    if not f:
        return 0

    def put(lo, width, v):
        nonlocal w
        assert 0 <= int(v) < (1 << width), (lo, width, v)
        w |= int(v) << lo
    put(184, 8, MAGIC)
    put(181, 3, f.get("mode", 0))
    put(180, 1, f.get("h128", 0))
    put(179, 1, f.get("configure", 0))
    put(166, 13, f.get("rows", 0))
    put(153, 13, f.get("n8", 0))
    put(152, 1, f.get("consume", 0))
    put(149, 3, f.get("eslot", 0))
    put(146, 3, f.get("estep", 0))
    put(145, 1, f.get("pclear", 0))
    put(144, 1, f.get("pread", 0))
    put(137, 7, f.get("paddr", 0))
    put(136, 1, f.get("run_first", 0))
    put(135, 1, f.get("run_last", 0))
    put(134, 1, f.get("publish", 0))
    put(132, 2, f.get("pubsel", 0))
    put(115, 1, f.get("dload", 0))
    put(109, 2, f.get("be_mode", 0))
    put(108, 1, f.get("be_clear", 0))
    put(107, 1, f.get("be_publish", 0))
    put(103, 4, f.get("be_index", 0))
    put(91, 12, f.get("be_row", 0))
    put(83, 8, f.get("be_expect", 0))
    put(82, 1, f.get("req", 0))
    put(50, 32, f.get("req_addr", 0))
    put(40, 10, f.get("req_tag", 0))
    put(30, 10, f.get("pkt_tag", 0))
    put(29, 1, f.get("pkt", 0))
    put(25, 1, f.get("consume", 0))
    put(24, 1, f.get("first", 0))
    put(23, 1, f.get("last", 0))
    put(11, 12, f.get("tag_row", 0))
    put(10, 1, f.get("tag_last", 0))
    put(7, 3, f.get("tag_slot", 0))
    put(0, 7, f.get("xaddr", 0))
    return w


# ---------------------------------------------------------------- calendar ----------------------------------------------
class Calendar:
    def __init__(self):
        self.cyc = []          # per cycle dict of command fields (merged)
        self.pkt = {}
        self.xw = {}
        self.kvd = {}

    def at(self, c):
        while len(self.cyc) <= c:
            self.cyc.append({})
        return self.cyc[c]

    def set(self, c, **f):
        d = self.at(c)
        for k, v in f.items():
            assert k not in d or d[k] == v, f"calendar conflict at {c}: {k} {d.get(k)} vs {v}"
            d[k] = v

    def write(self, d: Path, n):
        att = dict(mode=None)
        with open(d / "cmd.hex", "w") as fc, open(d / "pkt.hex", "w") as fp, open(d / "xw.hex", "w") as fx, \
                open(d / "kvd.hex", "w") as fk:
            for c in range(n):
                f = self.cyc[c] if c < len(self.cyc) else {}
                fc.write(f"{cmd_word(**f):048x}\n")
                fp.write(f"{self.pkt.get(c, 0):0275x}\n")
                fx.write(f"{self.xw.get(c, 0):0516x}\n")
                fk.write(f"{self.kvd.get(c, 0):016x}\n")


def bf16b(x):
    return int(B.bf16b(np.asarray([x], dtype=F))[0])


def x_beats(fields):
    """fields: {(col, leaf_row): 256-bit BF16 field} -> the 13 x-loader beats of one x address (original fragment)."""
    frag = 0
    for (c, r), v in fields.items():
        frag |= v << (c * XC + BFOFF + r * 256)
    return [(frag >> (2048 * g)) & ((1 << 2048) - 1) for g in range(13)]


def compile_op(rec, op, lat, mode_pv, t0=8):
    """One attention op on one SM -> (calendar, expectation).  lat: implemented latencies (cycles)."""
    name, kind, kv4, rows, nrun = op[:5]
    T8 = len(rec["rows8"])
    qk = kind == "qk"
    n8 = sum(1 for r in rows if r < T8)
    cal = Calendar()
    c = t0
    # ---- x loader: q image (QK) or probabilities (PV, reserved group 127) ----
    if qk:
        qb = B.bf16b(rec["q"])
        for t in range(8):
            fields = {}
            for col in range(8):
                for lr in range(4):
                    fields[(col, lr)] = sum(int(qb[8 * (16 * lr + l) + t]) << (16 * l) for l in range(16))
            for g, beat in enumerate(x_beats(fields)):
                cal.xw[c] = (1 << 2062) | (t << 2055) | (g << 2048) | beat
                c += 1
    else:
        pb = B.bf16b(rec["p"])
        for i, r in enumerate(rows):
            cal.xw[c] = (1 << 2062) | (i << 2055) | (127 << 2048) | sum(int(pb[r]) << (16 * col) for col in range(8))
            c += 1
    # ---- lines, descriptor ----
    blob = b""
    for r in rows:
        codes, sc, _ = rec["rows4"][r - T8] if r >= T8 else rec["rows8"][r]
        blob += B.canon_row(codes, sc, 1 if r >= T8 else 0)
    lines = B.stream_lines(blob)
    base = 0x1000
    c += 2
    mode = 4 | (2 if not qk else 0) | (1 if (kv4 and not qk) else 0)
    cal.kvd[c] = base | (len(lines) << 32)
    cal.set(c, mode=mode, dload=1)
    t_cfg = c
    c += 1
    cal.set(c, mode=mode, configure=1, rows=len(rows), n8=(n8 if qk else (0 if kv4 else len(rows))))
    m = KvLineModel()
    m.cfg(qk, bool(kv4) and not qk, n8 if qk else (0 if kv4 else len(rows)), False, len(rows))
    c += 1
    # requests lead their packets by REQ_LEAD cycles (declared staging-buffer boundary)
    li, acc, consumed, beats = 0, 0, 0, []
    nbeats = 8 * len(rows)
    ring_k = 0
    first_line = None
    while consumed < nbeats:
        assert c < 60000, "calendar runaway"
        # packet slot
        acc += LINE_RATE[0]
        give = False
        if li < len(lines) and acc >= LINE_RATE[1] and m.s_ready() and c > t_cfg + lat["req_lead"]:
            acc -= LINE_RATE[1]
            give = True
        elif acc >= LINE_RATE[1]:
            acc = LINE_RATE[1]
        # consume slot: head beat whose ring residue matches this cycle
        take = False
        if m.m_valid():
            h = m.head()
            ring = h["slot"] if qk else h["step"]
            if (c - ring_k) % 8 == ring:
                take = True
        popped = m.step(give, take)
        if give:
            tag = li & 0x3FF
            cal.pkt[c] = (1 << 1098) | (tag << 1088) | lines[li]
            cal.set(c, mode=mode, pkt=1, pkt_tag=tag)
            cal.set(c - lat["req_lead"], mode=mode, req=1, req_addr=base + li, req_tag=tag)
            if first_line is None:
                first_line = c
            li += 1
        if take:
            b = popped
            if qk:
                wave = consumed // (8 * 8)
                row = 8 * wave + b["slot"]
                cal.set(c, mode=mode, consume=1, eslot=b["slot"], estep=b["step"], first=int(b["step"] == 0),
                        last=int(b["step"] == 7), tag_row=row, tag_last=1, tag_slot=b["slot"], xaddr=b["step"])
            else:
                wave = consumed // 64
                tk = 8 * wave + b["slot"]
                nr = len(rows)
                lastc = (nr - 1) & ~7
                cal.set(c, mode=mode, consume=1, eslot=b["slot"], estep=b["step"], first=int(tk % 8 == 0),
                        last=int(tk % 8 == 7 or tk + 1 == nr), run_first=int(tk < 8), run_last=int(tk >= lastc),
                        tag_row=tk, tag_slot=b["step"])
                cal.set(c - 3, mode=mode, pread=1, paddr=tk)
            beats.append((c, b))
            consumed += 1
        c += 1
    last_consume = beats[-1][0]
    exp = dict(first_line=first_line, last_consume=last_consume, lines=len(lines))
    # ---- results ----
    if qk:
        nw = (len(rows) + 7) // 8
        exp["qk"] = []
        for w in range(nw):
            wbeats = [cc for cc, b in beats if (beats.index((cc, b)) // 64) == w]
            last_w = max(wbeats)
            ncols = min(8, len(rows) - 8 * w)
            pub = last_w + lat["qk_land"] + 1
            clr = last_w + lat["qk_clear"]
            cal.set(clr, mode=mode, be_clear=1)
            cal.set(pub, mode=mode, be_publish=1, be_row=8 * w, be_expect=(1 << ncols) - 1)
            exp["qk"].append(dict(wave=w, rows=[rows[8 * w + k] for k in range(ncols)], publish=pub))
        end = exp["qk"][-1]["publish"] + lat["out"]
    else:
        pub = last_consume + lat["pv_node"]
        cal.set(pub, mode=mode, publish=1)
        exp["pv_publish"] = pub
        end = pub + 64 + lat["out"]
    # hold the attention mode (with the BE mode) on every cycle of the op so the BE treats arriving results as attention
    be_mode = 3 if not qk else 1
    for cc in range(t_cfg, end + 1):
        d = cal.at(cc)
        d.setdefault("mode", mode)
        d.setdefault("be_mode", be_mode)
    exp["end"] = end
    return cal, exp


# ---------------------------------------------------------------- build / run / check -----------------------------------
def build(work, probe, dmut):
    obj = work / f"obj_p{int(probe)}_d{dmut}"
    exe = obj / "Vtb_hbm_smh_attn"
    if exe.exists():
        return exe
    vl = os.environ.get("VERILATOR") or next((c for c in (os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"),) if os.path.exists(c)), "verilator")
    cmd = [vl, "--binary", "-j", "16", "-O1", "-CFLAGS", "-O1", "--x-assign", "fast", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
           "-Wno-MULTIDRIVEN", "--unroll-count", "256", "--top-module", "tb_hbm_smh_attn", "-DOT_SMH_HIER", "-DOT_SMH_FC_HIER",
           f"-GDMUT={dmut}", "--Mdir", str(obj)] + (["-DPROBE"] if probe else []) + [str(ROOT / s) for s in SRC]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_p{int(probe)}_d{dmut}.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_p{int(probe)}_d{dmut}.log)")
    return exe


def check(rec, op, exp, out):
    name, kind, kv4, rows, nrun = op[:5]
    res = [ln.split() for ln in out.splitlines() if ln.startswith("R ")]
    words = [(int(r[1]), int(r[2], 16), int(r[3], 16)) for r in res]
    mism, got = 0, 0
    if kind == "qk":
        want = B.bits32(rec["s"])
        for wv in exp["qk"]:
            hit = [w for w in words if w[1] == 8 * wv["wave"]]
            if len(hit) != 1:
                mism += 1
                continue
            for k, r in enumerate(wv["rows"]):
                got += 1
                if (hit[0][2] >> (32 * k)) & 0xFFFFFFFF != int(want[r]):
                    mism += 1
        expected = len(rows)
    else:
        cs = B.chunk_sums(rec["p"][rows], rec["K"][rows])
        node = B.bits32(B.A.pairwise([cs[i] for i in range(cs.shape[0])] + [np.zeros_like(cs[0])] * (nrun - cs.shape[0])))
        seen = np.full(512, -1, dtype=np.int64)
        for cyc, rrow, data in words:
            lr, wd = rrow >> 4, rrow & 15
            for col in range(8):
                seen[8 * (16 * lr + wd) + col] = (data >> (32 * col)) & 0xFFFFFFFF
        got = int(np.sum(seen >= 0))
        mism = int(np.sum(seen != node.astype(np.int64)))
        expected = 512
    return dict(results=got, expected=expected, mismatches=mism, result_rows=len(words),
                first_result=words[0][0] if words else None, last_result=words[-1][0] if words else None)


DEFAULT_LAT = dict(req_lead=8, qk_land=120, qk_clear=8, pv_node=160, out=40)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--shape", choices=["ds640", "ds128"], default="ds640")
    p.add_argument("--ops", default="qk_sm0,pv_sm0")
    p.add_argument("--seed", type=int, default=1015)
    p.add_argument("--lat", default="", help="JSON of implemented latencies (default: margin calendar)")
    p.add_argument("--probe", action="store_true")
    p.add_argument("--dmut", type=int, default=0)
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    lat = dict(DEFAULT_LAT)
    if a.lat:
        lat.update(json.loads(a.lat))
    T8, T4 = (128, 512) if a.shape == "ds640" else (128, 0)
    rec = B.make_record(T8, T4, a.seed)
    ops, nrun = B.plan(rec, a.shape)
    want = a.ops.split(",")
    ops = [o for o in ops if o[0] in want]
    assert ops, "no ops"
    exe = build(work, a.probe, a.dmut)
    results = []
    t0 = time.time()
    for op in ops:
        cal, exp = compile_op(rec, op, lat, op[1] == "pv")
        d = work / f"{a.shape}_{op[0]}_p{int(a.probe)}_d{a.dmut}"
        d.mkdir(exist_ok=True)
        n = exp["end"] + 4
        cal.write(d, n)
        r = subprocess.run([str(exe), f"+CMD={d}/cmd.hex", f"+PKT={d}/pkt.hex", f"+XW={d}/xw.hex", f"+KVD={d}/kvd.hex", f"+N={n}"],
                           capture_output=True, text=True, timeout=7200)
        out = r.stdout + r.stderr
        (d / "run.log").write_text(out)
        res = dict(name=op[0], kind=op[1], rows=len(op[3]), rc=r.returncode, fault=("FAULT" in out), calendar=exp)
        res.update(check(rec, op, exp, out))
        res["pass"] = r.returncode == 0 and not res["fault"] and res["mismatches"] == 0 and res["results"] == res["expected"]
        if res["first_result"] is not None:
            res["span_first_line_to_last_result"] = res["last_result"] - exp["first_line"]
        results.append(res)
        print(("PASS " if res["pass"] else "FAIL ") + json.dumps({k: v for k, v in res.items() if k != "calendar"}), flush=True)
    summ = dict(shape=a.shape, ops=len(results), passed=sum(r["pass"] for r in results), probe=a.probe, dmut=a.dmut,
                lat=lat, wall_s=round(time.time() - t0, 1),
                verdict="PASS" if all(r["pass"] for r in results) else "FAIL")
    Path(a.out).write_text(json.dumps(dict(summary=summ, ops=results), indent=1))
    print(("PASS" if summ["verdict"] == "PASS" else "FAIL") + " HBM_SM_ELEMENT_ATTENTION " + json.dumps(summ))
    return 0 if summ["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
