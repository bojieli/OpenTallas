#!/usr/bin/env python3
"""LH-PGVM 10-19: tb_hbm_su_pg_stream_safe2.sv from the regional bench (reference gets the 2 reset stages SAFE2 owns)."""
from pathlib import Path
src = Path('rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_regional.sv').read_text()
t = src
def rep(a, b):
    global t
    assert t.count(a) == 1, (a, t.count(a))
    t = t.replace(a, b)
rep('module tb_hbm_su_pg_stream_regional;', '''// LH-PGVM 2026-10-19 SAFE2: generated from tb_hbm_su_pg_stream_regional.sv by tools/hbm_static/pgstream_safe/gen_safe2_tb.py.
// The SAFE2 kit lands rst_n / bridge_rst_n in ONE face stage and the source adds the other two (reset tree); the bench
// therefore feeds the REFERENCE through the two stages the source now owns (plain clk_ctl flops, as the kit landing),
// so both see the same 3-stage release.  Everything else (stimulus, compare, windows) is the regional bench.
module tb_hbm_su_pg_stream_safe2;''')
rep('parameter integer SAFE_COPY=1,QID=1,', 'parameter integer QID=1,')
rep('.clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(rst_n),.bridge_rst_n(brst_n),.pos(pos),',
    '.clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(N``_rst),.bridge_rst_n(N``_brst),.pos(pos),')
rep(' `PGS_PORTS(r)\n', ''' `PGS_PORTS(r)
 reg [1:0] rl_r=0, rl_b=0;
 always @(posedge clk_ctl) begin rl_r <= {rl_r[0], rst_n}; rl_b <= {rl_b[0], brst_n}; end
 wire r_rst = rl_r[1], r_brst = rl_b[1], d_rst = rst_n, d_brst = brst_n;
''')
rep('ot_hbm_su_static_pg_stream_split_regional #(.SAFE_COPY(SAFE_COPY),', 'ot_hbm_su_static_pg_stream_split_safe2 #(')
rep(' always @(posedge clk_ctl or negedge rst_n)\n  if(!rst_n) pgf_sync_ref<=0;',
    ' always @(posedge clk_ctl or negedge r_rst)\n  if(!r_rst) pgf_sync_ref<=0;')
Path('rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_safe2.sv').write_text(t)
