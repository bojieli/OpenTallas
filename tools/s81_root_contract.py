#!/usr/bin/env python3
"""S81 production return ROOT contract: face, protection and the 2-stage pipelined CAM (Claude design, 2026-10-07).

Executable contract for the 128 per-region roots of the PQ full-shape partition (ROOTD = QD = 128), pinned to the
native rtl/v41rom/ot_v41_ret.sv ot_v41_ret_root and the pq_parent adapter rtl/dsrom_sys/s81_pq_parent/
ot_s81_pq_root_adapter.sv (tree word {e, d[32], tag[32], v}).  Codex /root/s81/pq_parent owns the RTL and its exact
proof; this file owns the contract and its reference models:

  GoldenRoot   cycle model of the native single-cycle root (validated against the RTL with --rtl, Icarus)
  PipeRoot     the contracted 2-stage pipelined CAM (stage A: select + match, stage B: fix-up + decide), with the
               insert-forward / remove-mask rules, odd-parity protection, bv shadow and queue-counter check
  variants     negative controls: no insert forwarding, no remove mask, stale free search, truncating rounding,
               parity check disabled, no output suppression after fault

Checks (fail closed, written to the results JSON): pipelined == golden per row (bit-exact fp32/bf16/e, same row set,
no extra rows) on randomised csum-tree cuts with adversarial back-to-back siblings, duplicate-free; golden == csum
reference; each negative control is detected; injected storage / face / counter faults raise the sticky fault before
any corrupted word is published.
"""
import argparse
import hashlib
import json
import random
import re
import shutil
import struct
import subprocess
import tempfile
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RET = ROOT / 'rtl/v41rom/ot_v41_ret.sv'
ADAPTER = ROOT / 'rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_root_adapter.sv'
ADDER = ROOT / 'rtl/proto/ot_fp32_add_rne_pipe.sv'
DELAY = ROOT / 'rtl/hdc/ot_hdc_delay.sv'
OUT = ROOT / 'results/uarch/dsrom_s81_pq_fullshape_design_20261007/current_main/root_contract'
D = QD = 128
ADD_LAT = 6          # decision cycle t -> sum is a candidate in cycle t + 6 (add/tag_in registered, 5-stage adder / delay)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------- native tag functions
def fields(t):
    return (t >> 13) & 0x7FFFF, (t >> 8) & 31, (t >> 5) & 7, t & 31          # {pos,row}, lo, k, nseg


def mk(r19, lo, k, n):
    return (r19 << 13) | (lo << 8) | (k << 5) | n


def norm(t):
    r19, lo, k, n = fields(t)
    for _ in range(5):
        one = (1 << k) & 63
        lok = (lo >> k) & 1 if k < 5 else None            # Verilog lo[k] out of range is X: the if is not taken
        if not (lo == 0 and one >= n) and lok == 0 and ((lo + one) & 63) >= n:
            k = (k + 1) & 7
    return mk(r19, lo, k, n)


def complete(t):
    _, lo, k, n = fields(t)
    return lo == 0 and ((1 << k) & 63) >= n


def sibling(a, b):
    ra, la, ka, na = fields(a)
    rb, lb, kb, nb = fields(b)
    return ra == rb and ka == kb and na == nb and (la ^ lb) == ((1 << ka) & 31)


def parent(a, b):
    r19, la, k, n = fields(a)
    lb = fields(b)[1]
    return norm(mk(r19, min(la, lb), (k + 1) & 7, n))


def f32(u):
    return np.frombuffer(struct.pack('<I', u), dtype=np.float32)[0]


def u32(x):
    return struct.unpack('<I', np.float32(x).tobytes())[0]


def fadd(a, b):
    s = u32(np.float32(f32(a)) + np.float32(f32(b)))
    return 0 if (s & 0x7FFFFFFF) == 0 else s          # RTL canonicalises every zero result to +0


def rne16(d):
    return (((d + 0x7FFF + ((d >> 16) & 1)) & ((1 << 33) - 1)) >> 16) & 0xFFFF


def trunc16(d):
    return d >> 16


def par(*vals):
    """odd parity bit: XOR of all bits of the values, inverted (data ^ p has odd weight)"""
    x = 0
    for v in vals:
        x ^= bin(v).count('1') & 1
    return x ^ 1


# ------------------------------------------------------------------------------------------- golden native root
class GoldenRoot:
    """cycle model of ot_v41_ret_root (one candidate decision a cycle, outputs registered)"""

    def __init__(self, add_lat=ADD_LAT, rounding=rne16):
        self.lat, self.rnd = add_lat, rounding
        self.q = deque()
        self.buf = [None] * D
        self.pend = {}
        self.fault = False
        self.t = 0
        self.occ_max = 0

    def step(self, inp):
        t, out = self.t, None
        sv = self.pend.pop(t, None)
        c = None
        if sv is not None:
            c = sv
        elif self.q:
            tg, d, e = self.q.popleft()
            c = (norm(tg), d, e)
        use_q = sv is None and c is not None
        if inp is not None and not use_q and len(self.q) == QD:
            self.fault = True
        if c is not None:
            ct, cd, ce = c
            if complete(ct):
                out = (ct, cd, self.rnd(cd), ce)
            else:
                hit = next((k for k in range(D) if self.buf[k] is not None and sibling(self.buf[k][0], ct)), -1)
                fr = next((k for k in range(D) if self.buf[k] is None), -1)
                if hit >= 0:
                    bt, bd, be = self.buf[hit]
                    self.buf[hit] = None
                    a, b = (bd, cd) if ((bt >> 8) & 31) < ((ct >> 8) & 31) else (cd, bd)
                    self.pend[t + self.lat] = (parent(bt, ct), fadd(a, b), be | ce)
                elif fr >= 0:
                    self.buf[fr] = c
                else:
                    self.fault = True
        if inp is not None:
            self.q.append(inp)
        self.occ_max = max(self.occ_max, sum(x is not None for x in self.buf))
        self.t += 1
        return out


# ------------------------------------------------------------------------------------------- contracted pipelined root
class PipeRoot:
    """2-stage pipelined CAM root with protection.

    Stage A (cycle t): candidate = adder result (priority) else queue head (registered FWFT head, norm precomputed);
      check the candidate's parity; M_raw[k] = bv[k] & sibling(bt[k], ct) against the buffer state at the start of t;
      fwd = sibling(tag of the candidate now in B, ct); complete(ct); register {cand, P, M_raw, fwd, complete}.
    Stage B (cycle t+1): M = (M_raw & ~RM_prev) | (fwd & INS_prev ? onehot(slot_prev)); RM_prev / INS_prev / slot_prev
      are B's own registered decision of the previous cycle; hit = lowest set bit of M; free = lowest clear bv (current
      state); decide complete / add (remove hit, issue add with bd[hit] one-hot read) / insert / fault; re-check the
      candidate parity; output register {row, pos, fp32, RNE bf16, e, r_par}.
    """

    def __init__(self, fwd_insert=True, mask_remove=True, free_current=True, rounding=rne16, check_parity=True,
                 suppress_after_fault=True, inject=None):
        self.q = deque()
        self.buf = [None] * D           # (tag, data, e, p)
        self.bv_shadow = [False] * D
        self.pend = {}
        self.A = None                   # candidate registered by stage A, decided by stage B next cycle
        self.prev = None                # B's registered decision: (kind, slot, tag)
        self.fault = False
        self.cause = set()
        self.t = 0
        self.occ_max = 0
        self.opt = dict(fwd_insert=fwd_insert, mask_remove=mask_remove, free_current=free_current,
                        check_parity=check_parity, suppress=suppress_after_fault)
        self.rnd = rounding
        self.inject = inject or {}
        self.qr = self.qw = self.qc = 0
        self.stale_bv = [False] * D
        self.ghost = [None] * D             # last contents of each slot (hardware keeps data after bv clears)

    def set_fault(self, why):
        self.fault = True
        self.cause.add(why)

    def stage_b(self, out_ok):
        out = None
        if self.A is None:
            self.prev = None
            return None
        c, p, mraw, fwd, comp = self.A
        ct, cd, ce = c
        if self.opt['check_parity'] and par(ct, cd, ce) != p:
            self.set_fault('parity_AB')
            self.prev = None
            return None
        m = list(mraw)
        if self.prev is not None:
            kind, slot, ptag = self.prev
            if kind == 'rm' and self.opt['mask_remove']:
                m[slot] = False
            if kind == 'ins' and self.opt['fwd_insert'] and fwd:
                m[slot] = True
        self.prev = None
        if comp:
            bf = self.rnd(cd)
            out = (ct, cd, bf, ce)
        else:
            hit = next((k for k in range(D) if m[k]), -1)
            if self.opt['free_current']:
                fr = next((k for k in range(D) if self.buf[k] is None), -1)
            else:
                fr = next((k for k in range(D) if not self.stale_bv[k]), -1)
            if hit >= 0:
                bt, bd, be, bp = self.buf[hit] if self.buf[hit] is not None else self.ghost[hit]
                if self.opt['check_parity'] and par(bt, bd, be) != bp:
                    self.set_fault('parity_buf')
                    return None
                self.buf[hit] = None
                self.bv_shadow[hit] = False
                a, b = (bd, cd) if ((bt >> 8) & 31) < ((ct >> 8) & 31) else (cd, bd)
                s = fadd(a, b)
                pt = parent(bt, ct)
                self.pend[self.t + ADD_LAT] = (pt, s, be | ce)
                self.prev = ('rm', hit, bt)
            elif fr >= 0:
                self.buf[fr] = self.ghost[fr] = (ct, cd, ce, p)
                self.bv_shadow[fr] = True
                self.prev = ('ins', fr, ct)
            else:
                self.set_fault('buffer_full')
        if out is not None and self.fault and self.opt['suppress']:
            out = None
        return out

    def step(self, inp):
        t = self.t
        # fault injection hooks (storage upsets) at the start of the cycle
        for kind, arg in self.inject.pop(t, []):
            if kind == 'buf_bit':
                live = [k for k in range(D) if self.buf[k] is not None]
                if live:
                    k = live[arg % len(live)]
                    bt, bd, be, bp = self.buf[k]
                    self.buf[k] = (bt, bd ^ (1 << (arg % 32)), be, bp)
            elif kind == 'bv_bit':
                self.bv_shadow[arg % D] = not self.bv_shadow[arg % D]
            elif kind == 'qc':
                self.qc ^= 1
            elif kind == 'q_bit' and self.q:
                tg, d, e, p = self.q[0]
                self.q[0] = (tg, d ^ 1, e, p)
        # stage B first (decides on last cycle's A registers; writes land at the end of the cycle)
        start = list(self.buf)                      # buffer state at the start of this cycle (stage A compares)
        b_tag = self.A[0][0] if self.A is not None else None   # candidate in B this cycle (for fwd)
        out = self.stage_b(True)
        # stage A: candidate selection and match against the buffer state at the START of this cycle
        sv = self.pend.pop(t, None)
        c, p = None, None
        if sv is not None:
            c = sv
            p = par(*sv)                       # generated at A for adder results
        elif self.q:
            tg, d, e, qp = self.q.popleft()
            self.qr = (self.qr + 1) % QD
            self.qc -= 1
            c = (norm(tg), d, e)
            p = par(*c)                        # head load: raw parity checked, normed candidate parity generated
            if self.opt['check_parity'] and par(tg, d, e) != qp:
                self.set_fault('parity_q')
                c = None
        if c is not None:
            ct = c[0]
            mraw = [start[k] is not None and sibling(start[k][0], ct) for k in range(D)]
            fwd = b_tag is not None and sibling(b_tag, ct)
            self.A = (c, p, mraw, fwd, complete(ct))
        else:
            self.A = None
        # input station: face parity checked, the word enqueued (dropped on a parity error)
        if inp is not None:
            tg, d, e, ip = inp
            if self.opt['check_parity'] and par(tg, d, e) != ip:
                self.set_fault('parity_in')
            else:
                if self.qc == QD:
                    self.set_fault('queue_overflow')
                self.q.append((tg, d, e, ip))
                self.qw = (self.qw + 1) % QD
                self.qc += 1
        # invariants checked every cycle
        if (self.qw - self.qr) % QD != self.qc % QD:
            self.set_fault('queue_counter')
        if any((self.buf[k] is not None) != self.bv_shadow[k] for k in range(D)):
            self.set_fault('bv_shadow')
        self.stale_bv = [x is not None for x in start]   # A-time view for the candidate decided next cycle
        self.occ_max = max(self.occ_max, sum(x is not None for x in self.buf))
        self.t += 1
        return out



# ------------------------------------------------------------------------------------------- traffic
def row_cut(rng, n, levels=3):
    """a random cut of the padded csum tree of a row with n segments: list of (lo, k) covering [0, n)"""
    out = []

    def rec(lo, k):
        if lo >= n:
            return
        if k == 0 or rng.random() < 0.45:
            out.append((lo, k))
        else:
            rec(lo, k - 1)
            rec(lo + (1 << (k - 1)), k - 1)
    rec(0, levels)
    return out


def ref_value(leaf, lo, k, n):
    if k == 0:
        return leaf[lo]
    left = ref_value(leaf, lo, k - 1, n)
    rlo = lo + (1 << (k - 1))
    return fadd(left, ref_value(leaf, rlo, k - 1, n)) if rlo < n else left


def rand_f32(rng):
    s = rng.getrandbits(1)
    e = rng.randrange(100, 150)
    return (s << 31) | (e << 23) | rng.getrandbits(23)


def traffic(seed, rows=120, density=None, adversarial=True):
    """per cycle input words (tag, d, e) or None; plus the reference {row19: (fp32, bf16, e)}"""
    rng = random.Random(seed)
    density = (0.6, 0.9, 1.0)[seed % 3] if density is None else density
    words, ref = [], {}
    for r in range(rows):
        r19 = (rng.randrange(8) << 16) | rng.randrange(1 << 16)
        while r19 in ref:
            r19 = (rng.randrange(8) << 16) | rng.randrange(1 << 16)
        n = rng.randrange(1, 9)
        leaf = [rand_f32(rng) for _ in range(n)]
        err = [1 if rng.random() < 0.03 else 0 for _ in range(n)]
        cut = row_cut(rng, n)
        K = 0
        while (1 << K) < n:
            K += 1
        ref[r19] = ref_value(leaf, 0, K, n)
        ref[r19] = (ref[r19], rne16(ref[r19]), int(any(err)))
        parts = []
        for lo, k in cut:
            hi = min(n, lo + (1 << k))
            parts.append((mk(r19, lo, k, n), ref_value(leaf, lo, k, n), int(any(err[lo:hi]))))
        if adversarial and len(parts) > 1 and rng.random() < 0.7:
            # siblings back to back (insert-forward hazard) or right sibling first
            parts.sort(key=lambda p: (fields(p[0])[2], -fields(p[0])[1] if rng.random() < 0.5 else fields(p[0])[1]))
        else:
            rng.shuffle(parts)
        words.append(parts)
    # interleave rows; insert idle cycles
    seq = []
    live = [deque(p) for p in words]
    while any(live):
        i = rng.randrange(len(live))
        if not live[i]:
            continue
        burst = rng.randrange(1, 4)
        for _ in range(burst):
            if live[i]:
                seq.append(live[i].popleft())
        if rng.random() > density:
            seq.extend([None] * rng.randrange(1, 4))
    return seq, ref


def run(model, seq, drain=200, with_parity=False, face_flip=None):
    outs = []
    for i, w in enumerate(seq + [None] * drain):
        if w is not None and with_parity:
            p = par(*w)
            if face_flip is not None and i == face_flip:
                p ^= 1
            w = (*w, p)
        o = model.step(w)
        if o is not None:
            outs.append((model.t - 1, o))
    return outs


def by_row(outs):
    rows = {}
    for t, (ct, cd, bf, ce) in outs:
        rows.setdefault(fields(ct)[0], []).append((cd, bf, ce))
    return rows


def compare(outs, ref):
    rows = by_row(outs)
    bad = [r for r in ref if rows.get(r) != [ref[r]]]
    extra = [r for r in rows if r not in ref]
    return dict(rows=len(ref), published=sum(len(v) for v in rows.values()), mismatched=len(bad), extra=len(extra),
                PASS=not bad and not extra)


# ------------------------------------------------------------------------------------------- RTL cross-check
TB = r'''`timescale 1ns/1ps
module tb;
  reg clk = 0; always #1 clk = ~clk;
  reg rst_n = 0, i_v = 0, i_e = 0; reg [31:0] i_t = 0, i_d = 0;
  wire r_v, r_e, fault; wire [15:0] r_row, r_bf16; wire [2:0] r_pos; wire [31:0] r_fp32;
  ot_v41_ret_root #(.D(128), .QD(128)) dut(.clk(clk), .rst_n(rst_n), .i_v(i_v), .i_t(i_t), .i_d(i_d), .i_e(i_e),
    .r_v(r_v), .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .fault(fault));
  reg [65:0] stim [0:NCYC-1]; integer c, f;
  initial begin
    $readmemh("stim.hex", stim); f = $fopen("rtl_out.txt", "w");
    repeat (3) @(negedge clk); rst_n = 1;
    for (c = 0; c < NCYC; c = c + 1) begin
      @(negedge clk); {i_e, i_d, i_t, i_v} = stim[c];
      @(posedge clk); #0.1;
      if (r_v) $fwrite(f, "%0d %h %h %h %h %h\n", c, r_pos, r_row, r_fp32, r_bf16, r_e);
      if (fault) $fwrite(f, "FAULT %0d\n", c);
    end
    $fclose(f); $finish;
  end
endmodule
'''


def rtl_check(seq, drain=200, model=None):
    """GoldenRoot vs the native RTL, cycle-exact on (cycle, pos, row, fp32, bf16, e)"""
    if not shutil.which('iverilog'):
        return dict(PASS=None, skipped='iverilog not found')
    full = seq + [None] * drain
    with tempfile.TemporaryDirectory(dir='/var/tmp') as w:
        w = Path(w)
        lines = []
        for x in full:
            if x is None:
                lines.append('0' * 17)
            else:
                tg, d, e = x
                lines.append('%017x' % ((e << 65) | (d << 33) | (tg << 1) | 1))
        (w / 'stim.hex').write_text('\n'.join(lines) + '\n')
        (w / 'tb.sv').write_text(TB.replace('NCYC', str(len(full))))
        r = subprocess.run(['iverilog', '-g2012', '-o', str(w / 'x.vvp'), '-s', 'tb', str(w / 'tb.sv'), str(RET),
                            str(ADDER), str(DELAY)], capture_output=True, text=True)
        if r.returncode:
            return dict(PASS=False, compile=r.stderr[-2000:])
        subprocess.run(['vvp', '-n', str(w / 'x.vvp')], cwd=w, capture_output=True, text=True, timeout=600)
        rtl = (w / 'rtl_out.txt').read_text().split('\n')
    rtl = [l for l in rtl if l]
    g = model or GoldenRoot()
    gl = []
    for c, x in enumerate(full):
        o = g.step(x)
        if o is not None:
            ct, cd, bf, ce = o
            gl.append('%d %x %04x %08x %04x %x' % (c, (ct >> 29) & 7, (ct >> 13) & 0xFFFF, cd, bf, ce))
    # the RTL's registered output for the decision of input cycle c is sampled at that cycle's posedge + 1:
    # align by matching the cycle offset found on the first line
    norm_rtl = []
    for l in rtl:
        if l.startswith('FAULT'):
            norm_rtl.append(l)
            continue
        c, *rest = l.split()
        norm_rtl.append((int(c), ' '.join(x.lstrip('0') or '0' for x in rest)))
    gl2 = [(int(l.split()[0]), ' '.join(x.lstrip('0') or '0' for x in l.split()[1:])) for l in gl]
    off = 0                                   # stimulus cycle c's decision is registered at the posedge ending c
    same = [(c - off, v) for c, v in norm_rtl if not isinstance(c, str)] == gl2
    return dict(PASS=same and not any(isinstance(x, str) for x in norm_rtl), cycle_offset=off, rtl_rows=len(rtl),
                golden_rows=len(gl2), faults=[x for x in norm_rtl if isinstance(x, str)][:3])


# ------------------------------------------------------------------------------------------- face / parity contract
def face_contract():
    t = RET.read_text()
    hdr = t[t.index('module ot_v41_ret_root'):]
    hdr = hdr[:hdr.index(');')]
    native = {m[3]: (m[1], int(m[2]) + 1 if m[2] else 1) for m in
              re.finditer(r'(input|output)\s+(?:wire|reg)\s+(?:\[(\d+):0\]\s+)?(\w+)', hdr)}
    a = ADAPTER.read_text()
    assert ".i_v(tree_return[66*r])" in a and ".i_t(tree_return[66*r+1 +: 32])" in a and \
        ".i_d(tree_return[66*r+33 +: 32])" in a and ".i_e(tree_return[66*r+65])" in a
    assert native == {'clk': ('input', 1), 'rst_n': ('input', 1), 'i_v': ('input', 1), 'i_t': ('input', 32),
                      'i_d': ('input', 32), 'i_e': ('input', 1), 'r_v': ('output', 1), 'r_row': ('output', 16),
                      'r_pos': ('output', 3), 'r_fp32': ('output', 32), 'r_bf16': ('output', 16), 'r_e': ('output', 1),
                      'fault': ('output', 1)}, native
    pins = [
        ('clk', 'in', 1, 'clock', 'column clock (stream_1p2 region root at the column FIFO); 833.333 ps'),
        ('rst_n', 'in', 1, 'reset', 'async assert, sync deassert from the column reset synchroniser'),
        ('tree_in[0]', 'in', 1, 'native i_v', 'word valid; no ready, at most one word a cycle'),
        ('tree_in[32:1]', 'in', 32, 'native i_t', 'tag {pos[3], row[16], lo[5], k[3], nseg[5]}'),
        ('tree_in[64:33]', 'in', 32, 'native i_d', 'FP32 partial'),
        ('tree_in[65]', 'in', 1, 'native i_e', 'error bit'),
        ('tree_par', 'in', 1, 'NEW', 'odd parity over tree_in[65:1]; meaningful when tree_in[0]'),
        ('upstream_fault', 'in', 1, 'adapter', 'column / tree fault, ORed into fault (as ot_s81_pq_root_adapter)'),
        ('r_v', 'out', 1, 'native', 'row valid; at most one a cycle; no ready'),
        ('r_row', 'out', 16, 'native', 'tag row'),
        ('r_pos', 'out', 3, 'native', 'tag position'),
        ('r_fp32', 'out', 32, 'native', 'row FP32 sum'),
        ('r_bf16', 'out', 16, 'native', 'RNE of r_fp32 (rb = fp32 + 0x7FFF + fp32[16]; bits 31:16)'),
        ('r_e', 'out', 1, 'native', 'row error'),
        ('r_par', 'out', 1, 'NEW', 'odd parity over {r_row, r_pos, r_fp32, r_bf16, r_e} (68 b); meaningful when r_v'),
        ('fault', 'out', 1, 'native + adapter', 'sticky: OR of native faults, protection faults and upstream_fault'),
    ]
    n = sum(p[2] for p in pins)
    assert n == 141 and sum(p[2] for p in pins if p[3].startswith('native')) == 66 + 69 + 1
    timing = dict(
        inputs='tree_in, tree_par: pin -> input station flop (inside the 142.56 um strip, <= 100 um) with at most '
               'buffering; launched by the producer station <= 215 um away; budget: external <= 833.3 - 60 (setup '
               'unc) - 15 (accept) - 120 (station internal) = 638 ps',
        outputs='r_*, r_par, fault: output station flop -> pin, at most buffering (<= 120 ps internal); consumer is '
                'the RWB stage-0 register through the return-trunk stations',
        reset='rst_n is a reset tree input, not timed as data; deassertion synchronised at the column root',
        hold='FF +15 ps with 25 ps hold uncertainty on every registered face')
    protocol = dict(
        tree_in='valid-only, no backpressure (native); the producer guarantees occupancy <= QD = 128; overflow is the '
                'native queue fault',
        r='valid-only, no ready (native); consumer (RWB) FIFO >= max rows per region per phase (14) accepts every '
          'cycle',
        fault='level, sticky until rst_n, registered; the cycle after it is set r_v is held 0 (fail closed)')
    return dict(native_ports=native, adapter_bit_order='tree_return[66r +: 66] = {e, d[32], tag[32], v}',
                pins=[dict(name=a_, dir=b_, bits=c_, source=d_, meaning=e_) for a_, b_, c_, d_, e_ in pins],
                total_pins=n, native_pins=66 + 69 + 1 + 2, new_pins=['tree_par', 'r_par', 'upstream_fault'],
                reconciliation='native 66 in (i_v, i_t, i_d, i_e) + 69 out (r_v, r_row, r_pos, r_fp32, r_bf16, r_e) '
                               '+ fault + clk + rst_n = 138; + tree_par + r_par (protection) + upstream_fault '
                               '(adapter OR, already in ot_s81_pq_root_adapter) = 141. The design draft\'s 67/71 '
                               'counted parity + {fault, busy}; busy is NOT a root port (column busy stays on the '
                               'column FIFO path)',
                timing=timing, protocol=protocol)


def parity_contract():
    return dict(
        sense='odd: data bits XOR parity bit has odd weight (an all-zero word with p = 0 is an error, so stuck-at-0 '
              'words and dead drivers are caught)',
        domains=[
            dict(name='face in', protected='tree_in[65:1] = {e, d, tag} (65 b) with tree_par', granularity='1 bit / word',
                 generated='producer: the last return-stage register of the column tree (dsfd_rstg / node output '
                           'register) - NOT in RTL today: an obligation on the tree-return owner; fallback: '
                           'generate in the root input station (then the die wire is unprotected and documented)',
                 checked='root input station register, every cycle with tree_in[0] = 1',
                 on_error='word dropped (not enqueued), sticky fault cause IN'),
            dict(name='queue', protected='qt/qd/qe entry (65 b) + 1 parity bit (the face parity carried, not '
                                         'regenerated: end-to-end from the producer)', bits=QD,
                 checked='stage A when the entry becomes the candidate (FWFT head register carries it)',
                 on_error='candidate dropped, sticky fault cause Q'),
            dict(name='buffer', protected='bt/bd/be entry (65 b) + 1 parity bit', bits=D,
                 generated='queue-sourced candidate: its carried bit; adder-sourced candidate: generated in stage A '
                           'from {st tag, sum, e} (the adder and tag-delay pipelines are logic, not storage: '
                           'unprotected, disclosed)',
                 checked='stage B on the hit entry (the bd one-hot read also returns bt, be, p); stage B re-checks '
                         'the A->B candidate register',
                 on_error='no add issued, sticky fault cause BUF / AB',
                 note='a tag upset that turns a match into a miss leaves the entry stranded: caught by the spine '
                      'rows-left watchdog (system obligation), not by parity'),
            dict(name='bv', protected='valid bits bv[127:0]', bits=D, scheme='kept shadow copy bv_s (not parity): '
                 'any bv != bv_s -> sticky fault cause BV (checked every cycle)'),
            dict(name='queue counters', protected='qr[6:0], qw[6:0], qc[7:0]', scheme='invariant (qw - qr) mod 128 '
                 '== qc mod 128 every cycle -> sticky fault cause QC'),
            dict(name='face out', protected='{r_row, r_pos, r_fp32, r_bf16, r_e} (68 b) with r_par',
                 generated='stage B from the D-inputs of the output register (after the A->B parity re-check, so '
                           'coverage is contiguous; the RNE incrementer is logic, unprotected)',
                 checked='RWB stage-0 register', on_error='RWB drops the write, RWB sticky fault -> spine f_fault')],
        storage_bits=dict(native=QD * 65 + D * 66, native_layout='queue QD x {t32,d32,e} + buffer D x {bv,t32,d32,e}',
                          parity=D + QD, bv_shadow=D, station_and_pipe_parity=3,
                          total=QD * 65 + D * 66 + D + QD + D + 3),
        design_draft_correction='the d95 draft counted 256 parity bits (2 x 128) and no bv shadow; the contract adds the '
                                '128-bit bv shadow and 3 pipe/station bits: 16,768 + 387 = 17,155 bits per root',
        fail_closed=dict(
            sticky='cause register {IN, Q, BUF, AB, BV, QC, QOVF (native queue), BFULL (native buffer), UP} cleared only '
                   'by rst_n; fault pin = OR, registered',
            blocks=['the faulting word is never published or used (dropped at its check point)',
                    'from the cycle after any cause is set, r_v is forced 0 (no further publication from this root)',
                    'RWB ORs fault into the spine f_fault: the spine fault is sticky, ready stays low (no new go), '
                    'the controller aborts/replays the token',
                    'adder results still in flight are discarded with the suppression'],
            native_difference='native keeps publishing after a fault; post-fault output is outside the golden '
                              'contract, so suppression is allowed and required here'))


def cam_contract():
    return dict(
        clock_ps=833.333, setup_unc_ps=60, accept_ps=15,
        stages=[
            dict(name='I (input station)', regs='tree_in 66 + tree_par', logic='parity check (65-input XOR, 4 levels)',
                 depth_levels=5),
            dict(name='queue (FWFT)', regs='128 x 66 entry array + qr/qw/qc + registered head (norm precomputed on '
                                           'the head load)',
                 logic='write decode; head load mux 128:1 x 66 (7 levels) + norm (3 levels)', depth_levels=11),
            dict(name='A (select + match)', regs='cand 65 + p + M_raw[128] + fwd + complete + valid',
                 logic='sv/head 2:1 mux; candidate tag fan-out to 128 comparators via 8 kept copies (16 each); '
                       '27-bit equality {pos,row,k,nseg} + lo XOR == 1<<k; AND-reduce; parity of adder results',
                 depth_levels=9, fanout='candidate tag bits: 8 kept copies x 16 comparators (owner rule: replicate)'),
            dict(name='B (fix-up + decide)', regs='hit/free one-hot -> bv/bv_s/bt/bd/be/p writes; add_a/add_b/tag_in; '
                                                   'output register {row,pos,fp32,bf16,e,r_par}; prev decision '
                                                   '(rm/ins one-hot, slot)',
                 logic='M = (M_raw & ~RM_prev) | (fwd & INS_prev ? onehot_prev); lowest-set priority (7 levels '
                       'prefix OR + AND); lowest-free on current bv (parallel); bd/bt/be/p one-hot AND-OR read (7 '
                       'levels) -> parity check (4) and operand order by ct.lo[k]; RNE 16-bit prefix increment (5)',
                 depth_levels=16, note='if B misses SS +15 ps: split the bd one-hot read into a stage C (operand '
                                       'fetch) - safe because a slot removed in B cannot be rewritten before C reads '
                                       'it (rewrite needs a later B) - +1 cycle on the add path only'),
            dict(name='O (output station)', regs='r_* 68 + r_par + r_v + fault', logic='none', depth_levels=1)],
        hazard_rules=[
            'H1 insert-forward: the candidate in A at t compared against the buffer at the start of t; the candidate '
            'decided in B at t may insert into slot s at the end of t. fwd = sibling(B.cand.tag, A.cand.tag) is '
            'registered in A; in B at t+1 the match bit of s is set iff fwd and B(t) inserted into s.',
            'H2 remove-mask: if B(t) removed slot s (paired it), the match bit of s is cleared for the candidate '
            'decided in B(t+1) (golden: bv[s] cleared before the next decision).',
            'H3 free search uses the CURRENT bv in B (it includes B(t)\'s write), never the A-time snapshot.',
            'H4 only B(t) can write between the A compare of a candidate and its B decision, so H1-H3 are complete.',
            'H5 operand order: left = the entry with the lower lo (= the hit entry iff ct.lo bit k is set); parent '
            'tag = norm({row, ct.lo & ~(1<<k), k+1, nseg}) computable from the candidate alone in A.'],
        equivalence=dict(
            pairing='identical: every add combines the same two golden siblings in the same operand order, so every '
                    'published word is bit-identical to the native root\'s word for that row',
            order='output ORDER and slot indices may differ (decisions are one cycle later, so adder results and '
                  'queue heads interleave differently); the VM writes by address and the spine counts rows, so order '
                  'is not observable',
            faults='native overflow faults stay overflow faults; occupancy may differ transiently (reported as '
                   'occ_max for both models)'),
        latency=dict(per_pass_cycles=1, row_complete_extra='+1 per root decision on the row\'s critical chain: '
                     '<= 1 + 3 (nseg <= 8 -> <= 3 root-level adds)', stations=2,
                     word_in_to_row_out=dict(native=2, contracted='2 + 1 (CAM) + 2 (stations) = 5 for a word that '
                                             'completes at once; + 1 per root-level add')),
        counters_and_rounding=dict(
            state=['qr[6:0], qw[6:0], qc[7:0] (queue)', 'bv[127:0] + bv_s shadow', 'add pipeline 5 stages + tag delay '
                   '5 x 33 b (registered issue: add, add_a, add_b, tag_in)', 'B prev decision (rm/ins, slot[6:0])',
                   'sticky cause[8:0]'],
            rounding='stateless: r_bf16 = (r_fp32 + 0x7FFF + r_fp32[16])[31:16] computed in B from the registered '
                     'candidate data, registered with r_par; no other rounding site',
            pipelining='queue counters update in A (pop) and at the input station (push); bv/bv_s update in B; the '
                       'add issue registers are written in B'),
        reset=dict(asserted='bv = bv_s = 0, qr = qw = qc = 0, A/B valid = 0, prev = none, add valid = 0, tag delay '
                            'valid = 0, r_v = 0, cause = 0',
                   not_reset='entry arrays (qt/qd/qe/p, bt/bd/be/p): written before they become valid; parity is '
                             'checked only on valid entries',
                   deassert='synchronous release from the column reset synchroniser; first word accepted 2 cycles '
                            'after release'))


# ------------------------------------------------------------------------------------------- checks
def checks(seeds):
    res = dict(positive=[], negatives={}, faults={})
    for s in seeds:
        seq, ref = traffic(s)
        g = GoldenRoot()
        go = run(g, seq)
        p = PipeRoot()
        po = run(p, seq, with_parity=True)
        rg, rp = compare(go, ref), compare(po, ref)
        res['positive'].append(dict(seed=s, words=sum(x is not None for x in seq), golden=rg, pipelined=rp,
                                    golden_fault=g.fault, pipe_fault=p.fault, occ_max=[g.occ_max, p.occ_max]))
        assert rg['PASS'] and rp['PASS'] and not g.fault and not p.fault, (s, rg, rp, p.cause)
    seq, ref = traffic(seeds[0])
    neg = {
        'no_insert_forward': PipeRoot(fwd_insert=False),
        'no_remove_mask': PipeRoot(mask_remove=False),
        'stale_free_search': PipeRoot(free_current=False),
        'truncating_rounding': PipeRoot(rounding=trunc16),
    }
    for name, m in neg.items():
        seq_n, ref_n = seq, ref
        if name == 'no_remove_mask':
            seq_n, ref_n = dup_trace()
        r = compare(run(m, seq_n, with_parity=True), ref_n)
        g = GoldenRoot()
        gr = compare(run(g, [w[:3] if w else None for w in seq_n]), ref_n) if name == 'no_remove_mask' else None
        detected = (not r['PASS']) or m.fault
        res['negatives'][name] = dict(result=r, fault=m.fault, cause=sorted(m.cause), detected=detected,
                                      golden_on_same_trace=gr)
        assert detected, name
    # protection: injected upsets must fault and publish nothing wrong
    for name, inj, opt in (('buffer_data_bit', {150: [('buf_bit', 30)], 160: [('buf_bit', 61)]}, {}),
                           ('bv_bit', {200: [('bv_bit', 5)]}, {}),
                           ('queue_counter', {120: [('qc', 0)]}, {}),
                           ('queue_entry_bit', {90: [('q_bit', 0)]}, {}),
                           ('buffer_data_bit_no_check', {150: [('buf_bit', 30)], 160: [('buf_bit', 61)]},
                            dict(check_parity=False))):
        m = PipeRoot(inject={k: list(v) for k, v in inj.items()}, **opt)
        outs = run(m, seq, with_parity=True)
        wrong = sum(1 for t, (ct, cd, bf, ce) in outs if ref.get(fields(ct)[0]) != (cd, bf, ce))
        res['faults'][name] = dict(fault=m.fault, cause=sorted(m.cause), wrong_published=wrong)
        if opt.get('check_parity') is False:
            assert wrong > 0 or m.fault, 'no-check negative must publish a wrong word or fault'
        else:
            assert m.fault and wrong == 0, (name, m.cause, wrong)
    m = PipeRoot()
    outs = run(m, seq, with_parity=True, face_flip=next(i for i, w in enumerate(seq) if w))
    wrong = sum(1 for t, (ct, cd, bf, ce) in outs if ref.get(fields(ct)[0]) != (cd, bf, ce))
    res['faults']['face_parity'] = dict(fault=m.fault, cause=sorted(m.cause), wrong_published=wrong)
    assert m.fault and wrong == 0 and 'parity_in' in m.cause
    m = PipeRoot(inject={150: [('buf_bit', 30)], 160: [('buf_bit', 61)]}, suppress_after_fault=False)
    outs = run(m, seq, with_parity=True)
    res['faults']['no_suppression_publishes_after_fault'] = dict(fault=m.fault, published=len(outs),
                                                                 suppressed_publish=len(run(PipeRoot(inject={150: [('buf_bit', 30)], 160: [('buf_bit', 61)]}), seq, with_parity=True)))
    assert res['faults']['no_suppression_publishes_after_fault']['published'] > \
        res['faults']['no_suppression_publishes_after_fault']['suppressed_publish']
    return res


def dup_trace():
    """an upstream duplicate partial: X buffered, Y (sibling) then Z (= duplicate of Y) back to back"""
    r19 = 0x12345
    x = (mk(r19, 0, 0, 2), 0x3F800000, 0)
    y = (mk(r19, 1, 0, 2), 0x40000000, 0)
    seq = [x, None, None, y, y] + [None] * 20
    ref = {r19: (fadd(0x3F800000, 0x40000000), rne16(fadd(0x3F800000, 0x40000000)), 0)}
    return seq, ref


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seeds', type=int, default=12)
    ap.add_argument('--rtl', action='store_true', help='cross-check GoldenRoot against the native RTL (Icarus)')
    ap.add_argument('--out', type=Path, default=OUT / 'root_contract.json')
    a = ap.parse_args()
    c = checks(list(range(1, a.seeds + 1)))
    rtl = None
    if a.rtl:
        rtl = [dict(seed=s, **rtl_check(traffic(s)[0])) for s in (1, 2, 3)]
        assert all(r['PASS'] for r in rtl), rtl
        neg = [dict(variant=n, **rtl_check(traffic(1)[0], model=m)) for n, m in
               (('golden_add_latency_7', GoldenRoot(add_lat=7)), ('golden_truncating', GoldenRoot(rounding=trunc16)))]
        assert not any(r['PASS'] for r in neg), neg
        rtl = dict(positives=rtl, negatives=neg)
    assert QD * 65 + D * 66 == 16768
    res = dict(schema='opentallas.s81.root-contract.v1', adopted=False,
               sources={str(p.relative_to(ROOT)): sha(p) for p in (RET, ADAPTER, ADDER, DELAY, Path(__file__))},
               owner='contract: Claude design agent; RTL + exact adapter proof: Codex /root/s81/pq_parent',
               face=face_contract(), parity=parity_contract(), cam=cam_contract(), checks=c, rtl_golden_check=rtl)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, default=str) + '\n')
    print(json.dumps(dict(pins=res['face']['total_pins'], positives=len(c['positive']),
                          negatives={k: v['detected'] for k, v in c['negatives'].items()},
                          faults={k: (v.get('fault'), v.get('wrong_published')) for k, v in c['faults'].items()},
                          rtl=dict(pos=[(r['seed'], r['PASS'], r.get('rtl_rows')) for r in rtl['positives']],
                                   neg=[(r['variant'], r['PASS']) for r in rtl['negatives']]) if rtl else None), indent=1))


if __name__ == '__main__':
    main()
