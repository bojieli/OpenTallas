#!/usr/bin/env python3
"""LH-PGVM 10-19: tb_hbm_su_pg_stream_safe2.sv from the regional bench (reference gets the 2 reset stages SAFE2 owns)."""
from pathlib import Path
import sys
# MODE safe2: SAFE2 top, kit face landing 1 stage.  MODE kitland: the CURRENT regional/legacy top (SAFE_COPY) behind the
# CURRENT kit's 3 serial landing stages -- checks whether the shipped kit landing keeps the seam windows.
MODE = sys.argv[1] if len(sys.argv) > 1 else 'safe2'
assert MODE in ('safe2', 'kitland')
HDR = '' if MODE == 'safe2' else '// KITLAND: regional/legacy DUT behind the kit 3-stage landing (DLAND 3); reference as in safe2.\n'
src = Path('rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_regional.sv').read_text()
t = src
def rep(a, b):
    global t
    assert t.count(a) == 1, (a, t.count(a))
    t = t.replace(a, b)
rep('module tb_hbm_su_pg_stream_regional;', HDR+'''// LH-PGVM 2026-10-19 SAFE2: generated from tb_hbm_su_pg_stream_regional.sv by tools/hbm_static/pgstream_safe/gen_safe2_tb.py.
// The SAFE2 kit lands rst_n / bridge_rst_n in ONE face stage and the source adds the other two (reset tree); the bench
// models the kit face landing: the DUT gets 1 face stage, the REFERENCE the old kit's 3 (plain clk_ctl flops),
// so both see the same epoch-aligned 3-stage release.  Everything else (stimulus, compare, windows) is the regional bench.
module tb_hbm_su_pg_stream_'''+MODE+';')
rep('parameter integer SAFE_COPY=1,QID=1,', 'parameter integer DLAND=1,QID=1,' if MODE=='safe2' else 'parameter integer SAFE_COPY=1,DLAND=3,QID=1,')
rep('.clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(rst_n),.bridge_rst_n(brst_n),.pos(pos),',
    '.clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(N``_rst),.bridge_rst_n(N``_brst),.pos(pos),')
rep(' `PGS_PORTS(r)\n', ''' `PGS_PORTS(r)
 // DUT: the kit face landing (DLAND plain clk_ctl flops: 1 for SAFE2).  REFERENCE: the designed release (100 ps before
 // a coincident edge) delayed by one epoch (12q, transport) -> both leave reset on the same coincident edge in both
 // clock domains if the DUT's reset tree is epoch-exact.
 reg [2:0] rl_r=0, rl_b=0;
 always @(posedge clk_ctl) begin rl_r <= {rl_r[1:0], rst_n}; rl_b <= {rl_b[1:0], brst_n}; end
 reg r_rst=0, r_brst=0;
 always @(rst_n) r_rst <= #(12*Q*1.0e-3) rst_n;
 always @(brst_n) r_brst <= #(12*Q*1.0e-3) brst_n;
 wire d_rst = rl_r[DLAND-1], d_brst = rl_b[DLAND-1];
''')
if MODE=='safe2': rep('ot_hbm_su_static_pg_stream_split_regional #(.SAFE_COPY(SAFE_COPY),', 'ot_hbm_su_static_pg_stream_split_safe2 #(')
rep(' always @(posedge clk_ctl or negedge rst_n)\n  if(!rst_n) pgf_sync_ref<=0;',
    ' always @(posedge clk_ctl or negedge r_rst)\n  if(!r_rst) pgf_sync_ref<=0;')
Path('rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_'+MODE+'.sv').write_text(t)
