from pathlib import Path
import hashlib
p=Path(__file__).parent
s=(p/'original_leaf.sv').read_text().strip()
a=(p/'replay_sf137_private.sv').read_text(); a=a[a.index('module '):a.index('endmodule')+len('endmodule')]
a=a.replace('ot_qkvd_llr_replay_sram_leaf_sf137_private','ot_qkvd_llr_replay_sram_leaf_sf').replace('wire [136:0] mr;','wire [511:0] mr;').replace('ot_sram_1r1w_64x137_m1_r2c2_p192','ot_sram_1r1w_64x512_m1_r2c2').replace('.wd_in(dq)',".wd_in({{(512-W){1'b0}},dq})").replace(".w_mask_in({137{1'b1}})",".w_mask_in({{(512-W){1'b0}},{W{1'b1}}})").replace(".cr_sel(16'd0)",".cr_sel(18'd0)")
a=a.replace("    generate if (W != 137 || QD != 64 || QA != 6 || GB != 16) begin : g_bad_shape\n        OT_PRIVATE_REPLAY137_REQUIRES_W137_QD64_QA6_GB16 u_bad_shape ();\n    end endgenerate\n",'')
assert a==s, 'Unexpected equation/control change'
print('PASS exact original leaf after reverse width adaptation; same dq/dqq, wq/aq and nine selects')
