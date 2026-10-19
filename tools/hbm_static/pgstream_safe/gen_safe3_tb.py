#!/usr/bin/env python3
"""L2H-PGVM 10-19: tb_hbm_su_pg_stream_safe3.sv from tb_hbm_su_pg_stream_safe2.sv.
SAFE3 adds (a) su_wq / vmr_cmd pin capture on clk_ctl -> the REFERENCE gets those inputs through one clk_ctl register,
(b) the lg_fault output flop -> DUT lg_fault at stream edge k+1 == REF at k.  Everything else is the SAFE2 bench."""
from pathlib import Path
t = Path('rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_safe2.sv').read_text()
def rep(a, b):
    global t
    assert t.count(a) == 1, (a, t.count(a))
    t = t.replace(a, b)
rep('module tb_hbm_su_pg_stream_safe2;', '''// L2H-PGVM 2026-10-19 SAFE3: generated from tb_hbm_su_pg_stream_safe2.sv by tools/hbm_static/pgstream_safe/gen_safe3_tb.py:
// the DUT registers su_wq / vmr_cmd at the face (+1 serial edge) -> the reference gets them through one clk_ctl register;
// the DUT publishes lg_fault through an output flop (+1 stream edge) -> lg_fault compared against the reference one
// stream edge earlier.
module tb_hbm_su_pg_stream_safe3;''')
rep('.vmr_cmd(vmr),.su_wq(suwq),', '.vmr_cmd(N``_vmr),.su_wq(N``_suwq),')
rep(' `PGS_PORTS(r)\n', ''' `PGS_PORTS(r)
 // SAFE3 su_wq / vmr_cmd pin capture: reference inputs one clk_ctl edge late (DUT registers them itself).
 reg [59:0] r_vmr_q=0; reg [561:0] r_suwq_q=0;
 always @(posedge clk_ctl) begin r_vmr_q <= vmr; r_suwq_q <= suwq; end
 wire [59:0] r_vmr = r_vmr_q, d_vmr = vmr;
 wire [561:0] r_suwq = r_suwq_q, d_suwq = suwq;
 reg r_lgf_h=0;
''')
rep('ot_hbm_su_static_pg_stream_split_safe2 #(', 'ot_hbm_su_static_pg_stream_split_safe3 #(')
rep('  if(d_lgf!==r_lgf) err("lg_fault");\n', '  if(d_lgf!==r_lgf_h) err("lg_fault (+1 stream)");\n')
# history of the reference lg_fault on EVERY stream edge (also while chk = 0, e.g. across the second reset epoch)
rep(' reg r_lgf_h=0;\n', ' reg r_lgf_h=0;\n always @(posedge pg_clk) r_lgf_h <= r_lgf;\n')
Path('rtl/test/hbm_accel/generic/tb_hbm_su_pg_stream_safe3.sv').write_text(t)
