from pathlib import Path
import shutil,re,json
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');a=r/'native_leaf_ece_v5';b=r/'native_final_post_v1';b.mkdir(exist_ok=False)
for n in ['source','source.f','defines.f','stage.json','closure_retry.json']:
 if(a/n).is_dir():shutil.copytree(a/n,b/n)
 else:shutil.copyfile(a/n,b/n)
f=r/'native_final_post_fixture_v1'
for n in ['img.mem','imgv.mem','exp.mem','manifest.json']:shutil.copyfile(f/n,b/n)
prog=[int(x,16)for x in (f/'prog.mem').read_text().split()];combine=prog[1]&((1<<160)-1)
s=(a/'tb_current_native_leaf.sv').read_text();s=s[:s.index('always @(posedge ck)begin cyc=cyc+1;#2;')]
s += '''reg[127:0]rows_[0:1023];reg valid_[0:1023];reg[255:0]gold_[0:255];integer nlo=0,postpin=-1,hwlast=-1,hwcount=0,mismatch=0;reg[255:0]data_;reg[159:0]combine_;reg[3:0]op_;
always @(posedge ck)begin cyc++;#2;
if(arst_n&&dut.leafdn_i0_q[593])begin op_={dut.leafdn_i0_q[436],dut.leafdn_i0_q[435],dut.leafdn_i0_q[434],dut.leafdn_i0_q[433]};$display("POST_COMMAND op%0d cycle%0d",op_,cyc);if(op_==2)postpin=cyc;end
if(arst_n&&postpin>=0&&dut.w_u_lf0_u_vp_driver_hw_v_Q)begin hwlast=cyc;hwcount++;end
if(arst_n&&dut.w_u_lf0_u_vp_driver_lo_v_Q)begin
 if(nlo>=25||dut.w_u_lf0_u_vp_driver_lo_d_Q!==gold_[nlo])begin errors++;mismatch++;if(mismatch<8)$display("POST_MISMATCH rowpair%0d got%064h want%064h",nlo,dut.w_u_lf0_u_vp_driver_lo_d_Q,gold_[nlo]);end
 nlo++;
end
end
initial begin $readmemh("img.mem",rows_);$readmemh("imgv.mem",valid_);$readmemh("exp.mem",gold_);arst_n=0;packet=0;tick(64);arst_n=1;packet=pack(0,0,0,0,0,0);tick(64);
for(integer j=0;j<1024;j++)if(valid_[j])begin data_={128'd0,rows_[j]};if($test$plusargs("mut_payload")&&j==320)data_[30]=~data_[30];packet=pack(0,0,1,10'(j),8'h0f,data_);tick(1);packet=pack(0,0,0,0,0,0);tick(1);end
 tick(16);command(3,0,0,0);tick(120);
'''+f"combine_=160'h{combine:040x};packet=pack(1,combine_,0,0,0,0);tick(1);packet=pack(0,0,0,0,0,0);tick(240);\n"+'''
command(6,448,0,8);tick(120);command(2,1009,$test$plusargs("mut_posta1")?450:448,0);tick(240);command(4,32,0,0);tick(120);command(6,32,0,16);tick(160);command(6,1008,0,1);tick(80);
$display("POST_FAULT vp%0d vna%0d vnb%0d vs%0d vq%0d cland%0d ready%0d",dut.w_u_lf0_u_vp_driver_fault_Q,dut.w_u_lf0_u_vn_u_a_fault,dut.w_u_lf0_u_vn_u_b_fault,dut.w_u_lf0_u_vs_fault,dut.w_u_lf0_u_vq_fault,dut.cland_up_fault,dut.cland_up_ready);
if(dut.w_u_lf0_u_vp_driver_fault_Q||dut.w_u_lf0_u_vn_u_a_fault||dut.w_u_lf0_u_vn_u_b_fault||dut.w_u_lf0_u_vs_fault||dut.w_u_lf0_u_vq_fault||dut.cland_up_fault||!dut.cland_up_ready)errors++;
if(nlo!=25||hwcount!=16)errors++;
$display("NATIVE_POST_RESULT checked_pairs%0d hwcount%0d post_to_last_hw%0d errors%0d clock833",nlo,hwcount,hwlast-postpin,errors);if(errors==0)$display("NATIVE_POST_PASS");else $fatal(1,"NATIVE_POST_FAIL");$finish;end
endmodule
'''
(b/'tb_current_native_leaf.sv').write_text(s);(b/'.keep').write_text('critical native finalPOST fixture component, no upstreamresidency authority\n')
