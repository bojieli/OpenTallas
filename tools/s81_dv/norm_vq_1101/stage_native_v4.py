from pathlib import Path
import shutil
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');a=r/'native_leaf_ece_v3';b=r/'native_leaf_ece_v4';b.mkdir(exist_ok=False)
for n in ['source','source.f','defines.f','entry.memh','stage.json','closure_retry.json','run_current_native_leaf.sh']:
 if (a/n).is_dir():shutil.copytree(a/n,b/n)
 else:shutil.copyfile(a/n,b/n)
s=(a/'tb_current_native_leaf.sv').read_text();s=s.replace('tick(160);if(nseen','tick(160);$display("NATIVE_FAULT mode%0d vp%0d vna%0d vnb%0d vs%0d vq%0d cland%0d ready%0d",which,dut.w_u_lf0_u_vp_driver_fault_Q,dut.w_u_lf0_u_vn_u_a_fault,dut.w_u_lf0_u_vn_u_b_fault,dut.w_u_lf0_u_vs_fault,dut.w_u_lf0_u_vq_fault,dut.cland_up_fault,dut.cland_up_ready);if(dut.w_u_lf0_u_vp_driver_fault_Q||dut.w_u_lf0_u_vn_u_a_fault||dut.w_u_lf0_u_vn_u_b_fault||dut.w_u_lf0_u_vs_fault||dut.w_u_lf0_u_vq_fault||dut.cland_up_fault||!dut.cland_up_ready)errors++;if(nseen')
(b/'tb_current_native_leaf.sv').write_text(s);(b/'.keep').write_text('critical native source fault qualification\n')
