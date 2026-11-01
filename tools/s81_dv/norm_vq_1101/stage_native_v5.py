from pathlib import Path
import shutil
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');a=r/'native_leaf_ece_v4';b=r/'native_leaf_ece_v5';b.mkdir(exist_ok=False)
for n in ['source','source.f','defines.f','entry.memh','stage.json','closure_retry.json','run_current_native_leaf.sh']:
 if (a/n).is_dir():shutil.copytree(a/n,b/n)
 else:shutil.copyfile(a/n,b/n)
s=(a/'tb_current_native_leaf.sv').read_text().replace('errors=0,mut=0','errors=0,mut=0,rpin=-1,xcount=0,xheads=0')
s=s.replace('if(arst_n&&pin>=0&&dut.u_u_lf0_u_vq.m_v)', 'if(arst_n&&dut.leafdn_i0_q[67])begin rpin=cyc;$display("NATIVE_RSTD mode%0d cycle%0d",which,cyc);end\nif(arst_n&&rpin>=0&&dut.u_u_lf0_u_vq.xf_v)begin xcount++;if(dut.u_u_lf0_u_vq.xf_s)begin xheads++;$display("NATIVE_XF mode%0d RSTDage%0d kind%0d index%0d",which,cyc-rpin,dut.u_u_lf0_u_vq.xf[3:1],dut.u_u_lf0_u_vq.xf[20:13]);end end\nif(arst_n&&pin>=0&&dut.u_u_lf0_u_vq.m_v)')
s=s.replace('pubseen=0;tick(64)','pubseen=0;rpin=-1;xcount=0;xheads=0;tick(64)')
s=s.replace('tick(160);$display("NATIVE_FAULT','tick(140);packet=pack(0,0,0,0,0,0);packet[67]=1;packet[66:35]=32\'h40ca3c85;tick(1);packet=pack(0,0,0,0,0,0);tick(160);if(xcount!=(which==2?8:4)||xheads!=(which==2?2:1))errors++;$display("NATIVE_PUBLICATION mode%0d fragments%0d headers%0d",which,xcount,xheads);$display("NATIVE_FAULT')
(b/'tb_current_native_leaf.sv').write_text(s);(b/'.keep').write_text('critical native source RSTD to VQ timing probe; fixture state not productionPOST\n')
