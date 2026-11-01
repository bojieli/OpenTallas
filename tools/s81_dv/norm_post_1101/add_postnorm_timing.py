from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/native_final_postnorm_v1/tb_current_native_leaf.sv');s=p.read_text().replace('integer nlo=0,postpin=-1','integer vspin=-1,vslast=-1,vswrites=0,npublic=0;integer nlo=0,postpin=-1')
s=s.replace('if(op_==2)postpin=cyc;','if(op_==13)vspin=cyc;if(op_==2)postpin=cyc;')
s=s.replace('if(arst_n&&postpin>=0&&dut.w_u_lf0_u_vp_driver_hw_v_Q)', 'if(arst_n&&vspin>=0&&dut.w_u_lf0_u_vs_x_wv)begin vslast=cyc;vswrites++;$display("POST_VS_WRITE age%0d row%0d",cyc-vspin,dut.w_u_lf0_u_vs_x_wa);end\nif(arst_n&&returned[290])begin if(npublic>=25||returned[34+:256]!==gold_[npublic])errors++;npublic++;end\nif(arst_n&&postpin>=0&&dut.w_u_lf0_u_vp_driver_hw_v_Q)')
s=s.replace('if(nlo!=25||hwcount!=16)errors++;', 'if(nlo!=25||npublic!=25||hwcount!=16)errors++;$display("POST_TIMING VS13writes%0d last%0d public_pairs%0d",vswrites,vslast-vspin,npublic);')
p.write_text(s)
