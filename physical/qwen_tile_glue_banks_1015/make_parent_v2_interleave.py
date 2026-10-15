#!/usr/bin/env python3
"""qfd_tile_nk_banked_v2 = banked_v1 with the four W tree-face registers held in two paired interleaved masters
(qwen_glue_x1028 face_tb = t_out launch + n_b capture, face_ya = n_y launch + n_a capture) for the PM-H-S
bit-interleaved W pin plan (coordinator 2026-10-15, main 48fab3baf).  Same registers, clocks, resets: zero added edges.
OT_FACE_MUT (bench only): face_tb's n_b capture rotated by one bit -> must FAIL the full numeric reference."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[2]; D=root/'rtl/qwen_sys/tile_parent_banked_20261015'
s=(D/'qfd_tile_nk_banked_v1.sv').read_text()
def rep(a,b):
    global s; assert s.count(a)==1,a; s=s.replace(a,b)
rep('module qfd_tile_nk_banked_v1 #(','module qfd_tile_nk_banked_v2 #(')
old=['qwen_glue_v514 face_n_a(.clk(ck_bank[37]),.rst_n(r_reset_branch_w_mid[10]),.d(bank_d[19018 +: 514]),.q(bank_q[19018 +: 514]));\n',
     'qwen_glue_v514 face_n_b(.clk(ck_bank[38]),.rst_n(r_reset_branch_w_mid[9]),.d(bank_d[19532 +: 514]),.q(bank_q[19532 +: 514]));\n',
     'qwen_glue_v514 face_n_y(.clk(ck_bank[39]),.rst_n(r_reset_branch_w_mid[8]),.d(bank_d[20046 +: 514]),.q(bank_q[20046 +: 514]));\n',
     'qwen_glue_v514 face_t_out(.clk(ck_bank[40]),.rst_n(r_reset_branch_w_high0[4]),.d(bank_d[20560 +: 514]),.q(bank_q[20560 +: 514]));\n']
for o in old: rep(o,'')
new=('`ifdef OT_FACE_MUT\nwire [513:0] face_tb_id={bank_d[19532 +: 513],bank_d[20045]};\n`else\nwire [513:0] face_tb_id=bank_d[19532 +: 514];\n`endif\n'
     'qwen_glue_x1028 face_tb(.clk_o(ck_bank[40]),.clk_i(ck_bank[38]),.rst_o_n(r_reset_branch_w_high0[4]),.rst_i_n(r_reset_branch_w_mid[9]),'
     '.od(bank_d[20560 +: 514]),.oq(bank_q[20560 +: 514]),.id(face_tb_id),.iq(bank_q[19532 +: 514]));\n'
     'qwen_glue_x1028 face_ya(.clk_o(ck_bank[39]),.clk_i(ck_bank[37]),.rst_o_n(r_reset_branch_w_mid[8]),.rst_i_n(r_reset_branch_w_mid[10]),'
     '.od(bank_d[20046 +: 514]),.oq(bank_q[20046 +: 514]),.id(bank_d[19018 +: 514]),.iq(bank_q[19018 +: 514]));\n')
rep('qwen_glue_v508 face_tap(', new+'qwen_glue_v508 face_tap(')
(D/'qfd_tile_nk_banked_v2.sv').write_text(s)
T=root/'physical/qwen_tile_glue_banks_1015'
for tb in ['tb_parent_banked.sv','tb_parent_banked_allbanks.sv','tb_parent_banked_boot16.sv']:
    t=(T/tb).read_text(); assert t.count('qfd_tile_nk_banked_v1 #(')==1
    (T/tb.replace('.sv','_v2.sv')).write_text(t.replace('qfd_tile_nk_banked_v1 #(','qfd_tile_nk_banked_v2 #('))
p=(T/'prepare_parent_bench.py').read_text()
for a,b in [("'qfd_tile_nk_banked_v1.sv'","'qfd_tile_nk_banked_v2.sv'"),("'physical/qwen_tile_glue_banks_1015/tb_parent_banked.sv'","'physical/qwen_tile_glue_banks_1015/tb_parent_banked_v2.sv','physical/qwen_tile_glue_banks_1015/tb_parent_banked_allbanks_v2.sv','physical/qwen_tile_glue_banks_1015/tb_parent_banked_boot16_v2.sv','rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_x1028.sv'"),("run_parent_bench.sh',out/'run_parent_bench.sh'","run_parent_bench_v2.sh',out/'run_parent_bench_v2.sh'")]:
    assert p.count(a)==1,a; p=p.replace(a,b)
(T/'prepare_parent_bench_v2.py').write_text(p)
print('v2', hashlib.sha256((D/'qfd_tile_nk_banked_v2.sv').read_bytes()).hexdigest())
