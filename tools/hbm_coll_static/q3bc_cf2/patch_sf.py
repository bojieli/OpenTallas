# HBM-CORES-B q3bc structural form SF1 (COORD 08:0x GO): three cycle-exact edits on the flat body_ctl RTL.
#  T  tk_c chain: register incf (= q_n + 1) instead of qf; the loop decision no longer carries the incrementer.
#  B  programme banks: read one edge early (address = fetch_pc next-state, ce = fch_c[0] = fv_c next-state) and
#     register rd_out once; data reg (AND vm) sees the same word on the same edge. Writes never coincide with an
#     early read (write needs !busy_r && !start_q, early read needs fch_c[0] -> busy).
#  F  programme check: the row_bad term of the final-row decision (fault / configured) is registered (hcb_fin /
#     hcb_bad / hcb_f0) and applied through fault = fault_q | pending, configured = configured_q | pending, so every
#     reader and port sees gold timing.
# usage: patch_sf.py IN OUT [T][B][F]
import re, sys
src, dst, which = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
P = r'\u_body.g_q3.n_u_fj.u_fj.u.u_program.'
I = r'\u_body.g_iss256.u_issuer.'
RST = r'\u_body.g_q3.n_u_fj.u_fj.u.rst_q '
add = []

def rep1(old, new):
    global s
    n = s.count(old)
    assert n == 1, (n, old[:120])
    s = s.replace(old, new)

def bits(base, n):
    return '{ ' + ' , '.join(f'{base}[{i}]' for i in range(n - 1, -1, -1)) + '  }'

if 'T' in which:
    qf = bits(I + 'qf', 32)
    qn = bits(I + 'q_n', 32)
    inc = bits(I + 'incf', 32)
    rep1(f'  assign {inc} = {qf} + 32\'d1;', f'  assign {inc} = _hcb_incf_r;')
    add.append(f'  reg [31:0] _hcb_incf_r;\n  always @(posedge clk_issue)\n    _hcb_incf_r <= {qn} + 32\'d1;\n')

if 'B' in which:
    m = re.search(r'reg \[7:0\] (_\d+_);\n  always @\(posedge clk_issue\)\n    \1 <= (\{ [^;]* \});\n  assign ' + re.escape(bits(I + 'fetch_pc', 8)) + r' = \1;', s)
    assert m, 'fetch_pc reg'
    fpn = m.group(2)
    fp = bits(I + 'fetch_pc', 8)
    for b in range(3):
        for h in ('hi', 'lo'):
            inst = f'ot_sram_1r1w_256x256_m2_r2c2 {I}g_mem[{b}].u_bank.u_sram_{h}  ('
            i0 = s.index(inst); i1 = s.index(');', i0)
            body = s[i0:i1]
            rq = bits(I + f'g_mem[{b}].u_bank.rq_{h}', 256)
            w = f'_hcb_rq{b}{h}'
            nb = body.replace(f'.r_addr_in({fp})', f'.r_addr_in({fpn})')
            nb = nb.replace(f'.r_ce_in({I}fv_c[{b}] )', f'.r_ce_in({I}fch_c[0] )')
            nb = nb.replace(f'.rd_out({rq})', f'.rd_out({w}_m)')
            assert nb.count(fpn) == 1 and nb.count('fch_c[0]') == 1 and nb.count(w) == 1, (b, h)
            s = s[:i0] + nb + s[i1:]
            add.append(f'  wire [255:0] {w}_m;\n  reg [255:0] {w}_r;\n  always @(posedge clk_issue)\n    {w}_r <= {w}_m;\n'
                       f'  assign {rq} = {w}_r;\n')

if 'F' in which:
    for n in ('fault', 'configured'):
        rep1(f'  reg {P}{n} ;', f'  wire {P}{n} ;\n  reg {P}{n}_q ;')
        rep1(f'    if (!{RST}) {P}{n}  <= 1\'h0;', f'    if (!{RST}) {P}{n}_q  <= 1\'h0;')
    rep1(f'    else {P}fault  <= _020095_;', f'    else {P}fault_q  <= _020095_;')
    rep1(f'    else {P}configured  <= _020093_;', f'    else {P}configured_q  <= _020093_;')
    rep1(f'  assign _036465_ = _027232_ ? {P}configured  : _036464_;', f'  assign _036465_ = {P}configured ;')
    rep1('  assign _036494_ = _027232_ ? 1\'h1 : _036493_;', '  assign _036494_ = _036493_;')
    add.append(f'  reg _hcb_fin, _hcb_bad, _hcb_f0;\n'
               f'  always @(posedge clk_program, negedge {RST})\n'
               f'    if (!{RST}) begin _hcb_fin <= 1\'h0; _hcb_bad <= 1\'h0; _hcb_f0 <= 1\'h0; end\n'
               f'    else begin _hcb_fin <= {P}checking  && _027185_; _hcb_bad <= _027232_; _hcb_f0 <= {P}fault ; end\n'
               f'  assign {P}fault  = {P}fault_q  || (_hcb_fin && _hcb_bad);\n'
               f'  assign {P}configured  = {P}configured_q  || (_hcb_fin && !_hcb_bad && !_hcb_f0);\n')
    # check_bad accumulation (rd -> row_bad -> check_bad, TT -61): the row_bad set is a pending register
    # (_hcb_rbd) folded in through check_bad = check_bad_q | _hcb_rbd; the descriptor accept clear (dv && target &&
    # !fault-cond) cannot coincide with checking, and the pending term is gated by it anyway.
    rep1(f'  reg {P}check_bad ;', f'  wire {P}check_bad ;\n  reg {P}check_bad_q ;')
    rep1(f'    if (!{RST}) {P}check_bad  <= 1\'h0;\n    else {P}check_bad  <= _020083_;',
         f'    if (!{RST}) {P}check_bad_q  <= 1\'h0;\n    else {P}check_bad_q  <= _020083_;')
    rep1(f'  assign _036315_ = {P}row_bad  ? 1\'h1 : {P}check_bad ;', f'  assign _036315_ = {P}check_bad ;')
    add.append(f'  reg _hcb_rbd;\n'
               f'  always @(posedge clk_program, negedge {RST})\n'
               f'    if (!{RST}) _hcb_rbd <= 1\'h0;\n'
               f'    else _hcb_rbd <= {P}checking  && {P}row_bad  && !(_027215_ && !_027256_);\n'
               f'  assign {P}check_bad  = {P}check_bad_q  || _hcb_rbd;\n')

k = s.index('\nendmodule', s.index('module ot_hfd_coll_q3_body_ctl_x'))
s = s[:k] + '\n  // HBM-CORES-B SF1 (' + which + ')\n' + ''.join(add) + s[k:]
open(dst, 'w').write(s)
print('patched', which, len(add), 'blocks')
