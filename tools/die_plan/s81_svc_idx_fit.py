#!/usr/bin/env python3
"""S81 svc_lo idx fit (DIE-S81-51/MEM, 2026-11-03): right-sized memories of the paired index reader dsdv_idx_rg3.

Closure child dsdv_idx_rg3_fit is generated from the kit's own (unchanged, shared) dsdv_idx_rg3.sv: the 13
dsdv_idx_rg2_m1k (1024x256) landing / queue memories become dsdv_idx_fit_mem sized to what they address:
  lf  x2  u_mem  ra = lfr_a, wa = lf_wn[LFW-1:0], LFW = 8 (LFD 256)                 -> 256 x 256
  h0  x4  u_h0   lw_a in {00xxxxxxxx, 01000xxxxx, 10xxxxxxxx}; ra = s_row / c_row  -> 768 x 256 (rows < 768)
  h1  x4  u_h1   written only when lw_h1 (lw_a = {2'b00, ..}); ra = c_row = {2'b00, ..} -> 256 x 256
  iq / sq        full 1024 depth, data width only (IW 35 / SW 39; wd above is constant 0)
  mq             ring: written every edge at mw, read at mw - (EL + KR - 1) = mw - 123; any 128-deep ring returns
                 the same word (written 123 < 128 edges earlier); reads within 123 edges of reset are masked by warm
                 in both forms                                                      -> 128 x 23
                 S81-SVCRS-3 11-11: only while EL + KR - 1 < 128.  With the IRG pin stages (PR 1, EL 140) the read
                 is 139 edges behind and a 128-deep ring would return a newer word, so u_mq keeps the full 1024-deep
                 form there (WORDS is an elaboration expression of EL / KR; MACROS_EL140 is that macro set).
The bound is renamed dsdv_idx_rg3 -> dsdv_idx_rg3_fit (count-checked). Proof + bench: results/rtl/s81_svc_idx_fit_1103.

NQ (DIE-S81-66 11-05, svc_lo_dsdv_svc_rs__t7): the chain-end reader u_u_irg_07 is dsdv_idx_rg3_nq, a wrapper whose one
child u_rg3 = dsdv_idx_rg3_nq_native (portfix178, sha 038ef90e3733 / c462c830782c with the PRIME hunk).  That source
differs from dsdv_idx_rg3 only in the module name, a private infk2_left successor and the named gk_scan_word sum (no memory, address or write line); every
proof precondition above is re-checked on it.  The same 13 memory swaps give dsdv_idx_rg3_nq_native_fit; the wrapper
becomes dsdv_idx_rg3_nq_fit (same ports, keeps u_rg3), and the bound dsdv_idx_rg3_nq instance is renamed to it.
Bench: results/rtl/s81_svc_idx_fit_1103/run_lock_nq.sh (same lockstep gate with the nq reader as reference).
"""
import hashlib, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC_SHA = ('dd5695c1e6c0', '54e3d3ebf8a9', 'cbbd5eb1b07c', 'feff982713b0')  # portfix178/dsdv_idx_rg3.sv (main / kit-wave-14d..15; lint cast
# only / + DIE-S81-85 11-09 opt-in OT_IDX_RG3_PRIME hunk: off = verilator -E identical to dd5695; on adds pk / pr_f ->
# fc_set[5] only, no memory, address or write line, so the fit proof below holds either way; S81-SVCRS-3 11-11 feff982713b0
# = cbbd5eb1b07c + parameter PR passed to dsdv_idx_rg2_chunk and an EL/PR elaboration guard: no memory, address or write
# line either)
# the older source's 16'(wc) cast (KIT_PREFLIGHT YC1) is emitted in main's form: wc is reg [3:0], both zero-extend
CAST = ("gk_wb + 16'(wc)", "gk_wb + {12'd0, wc}")
NQ_SHA = ('038ef90e3733', 'c462c830782c', 'a610f6f5d338')  # portfix178/dsdv_idx_rg3_nq_native.sv (main / + the same
# PRIME hunk / + the same PR parameter and guard as feff982713b0)
NQ_WRAP_SHA = ('ec1013d7f3d6', '80ed6e06b7e3')    # portfix178/dsdv_idx_rg3_nq.sv (main / + PR passed to u_rg3)
FIT_MEM = 'results/rtl/s81_svc_idx_fit_1103/dsdv_idx_fit_mem.sv'
MACROS = {'ot_sram_1r1w_256x256_m1_r0c0': 6, 'ot_sram_1r1w_768x256_m2_r0c0': 4, 'ot_sram_1r1w_1024x35_m4_r0c0': 1,
          'ot_sram_1r1w_1024x39_m4_r0c0': 1, 'ot_sram_1r1w_128x23_m1_r0c0': 1}
# EL 140 (PR 1): u_mq stays 1024 deep, i.e. the original 1024x256 master (dsdv_idx_fit_mem's other-size branch)
MACROS_EL140 = {**{k: v for k, v in MACROS.items() if k != 'ot_sram_1r1w_128x23_m1_r0c0'},
                'ot_sram_1r1w_1024x256_m2_r2c2': 1}
MEMS = [  # (instance, new parameter text); old = '#(.SRAM_MACRO(SRAM_MACRO)) <inst> ('
    ('u_mem', '.WORDS(LFD <= 256 ? 256 : 1024), .BITS(256)'), ('u_h0', '.WORDS(768), .BITS(256)'),
    ('u_h1', '.WORDS(256), .BITS(256)'), ('u_iq', '.WORDS(1024), .BITS(IW)'),
    ('u_mq', '.WORDS(EL + KR - 1 < 128 ? 128 : 1024), .BITS(MW + 1)'), ('u_sq', '.WORDS(1024), .BITS(SW)')]
# structural preconditions of the proof, checked on the source text (any edit there -> refuse, re-prove)
PRE = [r"wire \[9:0\]  s_row = gatk\[1\] \? \{2'b10, s_it\[32:29\], s_it\[28:25\]\} : \{5'b01000, s_it\[32:29\], s_it\[28\]\};",
       r"wire \[9:0\]  c_row = \{2'b00, c_it\[32:29\], c_it\[28:25\]\};",
       r"\.ra\(mw - 10'\(EL \+ KR - 1\)\), \.rd\(mq_q\), \.we\(1'b1\), \.wa\(mw\),",
       r"localparam integer LFW = \$clog2\(LFD\);",
       r"lw_h1\[u\] <= !sc && bt\[0\];\n\s+if \(!sc\) lw_a\[u\] <= \{2'b00, s_, g \? cl : cl \+ \{3'd0, bt\[1\]\}\};\n"
       r"\s+else if \(!g\) lw_a\[u\] <= \{5'b01000, s_, bt\[0\]\};\n\s+else lw_a\[u\] <= \{2'b10, s_, cl\};",
       r"reg \[3:0\] s_; reg \[3:0\] cl;", r"\.we\(lw_v\[gu\] && lw_h1\[gu\]\), \.wa\(lw_a\[gu\]\)"]
BOUND_RE = re.compile(r'^(\s*)dsdv_idx_rg3( #\(.*\.EL\(1(?:24|40)\).*\.KR\(0\).*\.LFD\(256\).*\) \w+ \()$', re.M)
BOUND_NQ_RE = re.compile(r'^(\s*)dsdv_idx_rg3_nq( #\(.*\.EL\(1(?:24|40)\).*\.KR\(0\).*\.LFD\(256\).*\) \w+ \()$', re.M)
FIT_LINE_RE = re.compile(r'^\s*dsdv_idx_rg3(?:_nq)?_fit #\((.*)\) \w+ \($', re.M)


def sha12(b): return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()[:12]


def fit_source(s, nq=False):
    """dsdv_idx_rg3.sv -> dsdv_idx_rg3_fit; nq: dsdv_idx_rg3_nq_native.sv -> dsdv_idx_rg3_nq_native_fit."""
    h = sha12(s)
    mod = 'dsdv_idx_rg3_nq_native' if nq else 'dsdv_idx_rg3'
    if h not in (NQ_SHA if nq else SRC_SHA): raise ValueError('idx fit: %s.sv %s not a proven source' % (mod, h))
    for p in PRE:
        if len(re.findall(p, s)) != 1: raise ValueError('idx fit: precondition missing ' + p[:50])
    assert s.count('module %s #(' % mod) == 1 and s.count('dsdv_idx_rg2_m1k #(') == 6
    s = s.replace('module %s #(' % mod, 'module %s_fit #(' % mod)
    if h == SRC_SHA[1]:
        assert s.count(CAST[0]) == 1 and len(re.findall(r'^\s*reg  \[3:0\]  wc;$', s, re.M)) == 1
        s = s.replace(*CAST)
    for inst, par in MEMS:
        old = 'dsdv_idx_rg2_m1k #(.SRAM_MACRO(SRAM_MACRO)) %s (' % inst
        if s.count(old) != 1: raise ValueError('idx fit: instance ' + inst)
        s = s.replace(old, 'dsdv_idx_fit_mem #(.SRAM_MACRO(SRAM_MACRO), %s) %s (' % (par, inst))
    return ('// GENERATED by tools/die_plan/s81_svc_idx_fit.py from %s.sv (sha256 %s...): closure child.\n'
            '// Only change: the 13 dsdv_idx_rg2_m1k memories -> dsdv_idx_fit_mem sized to what they address.\n') % (mod, h) + s


def fit_nq_wrapper(s):
    """dsdv_idx_rg3_nq.sv -> dsdv_idx_rg3_nq_fit: same ports, u_rg3 binds dsdv_idx_rg3_nq_native_fit."""
    h = sha12(s)
    if h not in NQ_WRAP_SHA: raise ValueError('idx fit: dsdv_idx_rg3_nq.sv %s not a proven source' % h)
    for a, b in (('module dsdv_idx_rg3_nq #(', 'module dsdv_idx_rg3_nq_fit #('),
                 ('dsdv_idx_rg3_nq_native #(', 'dsdv_idx_rg3_nq_native_fit #(')):
        if s.count(a) != 1: raise ValueError('idx fit: nq wrapper form ' + a)
        s = s.replace(a, b)
    if len(re.findall(r'^\s*dsdv_idx_rg3_nq_native_fit #\(.*\) u_rg3 \($', s, re.M)) != 1:
        raise ValueError('idx fit: nq wrapper child u_rg3')
    return ('// GENERATED by tools/die_plan/s81_svc_idx_fit.py from dsdv_idx_rg3_nq.sv (sha256 %s...): closure child.\n'
            '// Only change: module name and its u_rg3 child -> dsdv_idx_rg3_nq_native_fit.\n') % h + s


def fit_bound(b):
    """bound text -> (text, n): the one svc_lo dsdv_idx_rg3 (or chain-end dsdv_idx_rg3_nq) instance renamed;
    idempotent (n = 0 if already fit)."""
    if re.search(r'^\s*dsdv_idx_rg3(_nq)?_fit #\(', b, re.M): return b, 0
    b, n = BOUND_RE.subn(r'\1dsdv_idx_rg3_fit\2', b)
    b, k = BOUND_NQ_RE.subn(r'\1dsdv_idx_rg3_nq_fit\2', b)
    if n + k not in (0, 1): raise ValueError('idx fit: %d dsdv_idx_rg3 / %d dsdv_idx_rg3_nq instances' % (n, k))
    if re.search(r'^\s*dsdv_idx_rg3(_nq)? #\(', b, re.M):
        raise ValueError('idx fit: dsdv_idx_rg3 / _nq with other parameters')
    return b, n + k


def bound_macros(b):
    """S81-SVCRS-3 11-11: the macro set of the one fit reader in a fit bound: MACROS at EL 124 (PR 0), MACROS_EL140
    at EL 140 with PR 1 (the RTL guard refuses any other EL / PR pair; here anything else is refused too)."""
    m = FIT_LINE_RE.findall(b)
    if len(m) != 1: raise ValueError('idx fit: %d fit reader instances' % len(m))
    el = re.findall(r'\.EL\((\d+)\)', m[0]); pr = re.findall(r'\.PR\((\d+)\)', m[0])
    el, pr = int(el[0]) if len(el) == 1 else None, int(pr[0]) if len(pr) == 1 else 0
    if (el, pr) == (124, 0): return dict(MACROS)
    if (el, pr) == (140, 1): return dict(MACROS_EL140)
    raise ValueError('idx fit: EL %s with PR %s' % (el, pr))


def bound_kind(b):
    """'rg3' / 'nq' for a fit bound, else None."""
    if re.search(r'^\s*dsdv_idx_rg3_nq_fit #\(', b, re.M): return 'nq'
    if re.search(r'^\s*dsdv_idx_rg3_fit #\(', b, re.M): return 'rg3'
    return None


if __name__ == '__main__':
    src = Path(sys.argv[1]); out = Path(sys.argv[2])
    out.write_text(fit_source(src.read_text(), nq=src.name == 'dsdv_idx_rg3_nq_native.sv'))
    print('ok', out, sha12(out.read_text()))
