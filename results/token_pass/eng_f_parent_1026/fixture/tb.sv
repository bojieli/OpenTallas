`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg arst_n=0;reg[264:0]pci=0;reg[53:0]fks=0;reg[276:0]vis=0,vin=0;
wire[1:0]b_flt,d_flt,m_flt;wire[39:0]b_rco,d_rco,m_rco;
eng_base b (.clk(clk),.arst_n(arst_n),.unit_i0(pci),.unit_i1(fks),.xtier_i0(vis),.xtier_i1(vin),
.flt_o0(b_flt),.unit_o0(b_rco),.xtier_o0(),.xtier_o1(),.ft0_i(1369'd0),.ft0_o(),.ft1_i(1121'd0),.ft1_o());
eng_trial d (.clk(clk),.arst_n(arst_n),.unit_i0(pci),.unit_i1(fks),.xtier_i0(vis),.xtier_i1(vin),
.flt_o0(d_flt),.unit_o0(d_rco),.xtier_o0(),.xtier_o1(),.ft0_i(1369'd0),.ft0_o(),.ft1_i(1121'd0),.ft1_o());
eng_mut m (.clk(clk),.arst_n(arst_n),.unit_i0(pci),.unit_i1(fks),.xtier_i0(vis),.xtier_i1(vin),
.flt_o0(m_flt),.unit_o0(m_rco),.xtier_o0(),.xtier_o1(),.ft0_i(1369'd0),.ft0_o(),.ft1_i(1121'd0),.ft1_o());
integer cyc=0,checks=0,stage_errors=0,coherence_errors=0,output_epoch_errors=0,mutant_epoch_errors=0,cfgfault_seen=0;
reg[263:0]hpci[0:2];reg[52:0]hfks[0:1];reg[275:0]hvis[0:1];
reg he_pci[0:2];reg he_fks[0:1];reg he_vis[0:1];reg[37:0]hrco[0:3];reg hv[0:3];reg hcf[0:2];
always @(negedge clk)begin
cyc=cyc+1;if(cyc==8)arst_n=1;
pci[263:0]={8'(cyc^8'h5a),{8{32'hac1d1234^cyc}}};pci[38:1]={6'(cyc^6'h2d),32'(32'ha51d6937^(cyc*32'h37a38df1))};pci[0]=(cyc%5)==1;pci[264]=(cyc%7)<3;
fks[51:0]={20'(cyc^20'hab739),32'(32'h91a53647^(cyc*32'h85632bad))};fks[52]=cyc>140 && (cyc%13)==2;fks[53]=(cyc%11)<5;
vis[275:0]={20'(cyc^20'ha5331),{8{32'h31ba7351^cyc}}};vis[3:1]=3;vis[0]=(cyc%4)<2;vis[276]=(cyc%9)<4;
vin[275:0]={20'(cyc^20'h57621),{8{32'hca6291b5^cyc}}};vin[3:1]=3;vin[0]=(cyc%6)<3;vin[276]=(cyc%3)==1;
end
always @(posedge clk)begin
#0.001;
for(integer i=2;i>0;i=i-1)begin hpci[i]=hpci[i-1];he_pci[i]=he_pci[i-1];hcf[i]=hcf[i-1];end
hpci[0]=b.u_u_e.pci;he_pci[0]=b.unit_i0_eq;hcf[0]=d.w_u_cfg_fault;
hfks[1]=hfks[0];hfks[0]=b.u_u_e.f_ks;he_fks[1]=he_fks[0];he_fks[0]=b.unit_i1_eq;
hvis[1]=hvis[0];hvis[0]=b.u_u_e.vi_s;he_vis[1]=he_vis[0];he_vis[0]=b.xtier_i0_eq;
for(integer i=3;i>0;i=i-1)begin hrco[i]=hrco[i-1];hv[i]=hv[i-1];end
hrco[0]=b_rco[37:0];hv[0]=b_flt[0];
if(d_flt[1]!==d_rco[39])output_epoch_errors=output_epoch_errors+1;
if(cyc>80)begin
 checks=checks+1;
 if(d.u_u_e.pci!==hpci[2] || d.unit_i0_eq!==he_pci[2] || d.u_u_e.f_ks!==hfks[1] || d.unit_i1_eq!==he_fks[1] || d.u_u_e.vi_s!==hvis[1] || d.xtier_i0_eq!==he_vis[1] || d.u_u_e.vi_n!==b.u_u_e.vi_n || d_rco[37:0]!==hrco[3] || d_rco[38]!==hcf[2])stage_errors=stage_errors+1;
 if(d_flt[0]!==hv[3])coherence_errors=coherence_errors+1;
 if(m.unit_i1_eq!==he_fks[1])mutant_epoch_errors=mutant_epoch_errors+1;
 if(d_rco[38])cfgfault_seen=cfgfault_seen+1;
end
if(cyc==400)begin
$display("ENGF_TRANSPORT checks=%0d errors=%0d cfgfault_seen=%0d verdict=%s",checks,stage_errors,cfgfault_seen,stage_errors==0?"PASS":"FAIL");
$display("ENGF_RCO_COHERENCE valid_data_mismatches=%0d output_epoch_mismatches=%0d verdict=%s",coherence_errors,output_epoch_errors,(coherence_errors==0 && output_epoch_errors==0)?"PASS":"FAIL");
$display("ENGF_EPOCH_MUTANT mismatches=%0d verdict=%s",mutant_epoch_errors,mutant_epoch_errors>0?"CAUGHT":"MISSED");
if(stage_errors!=0 || mutant_epoch_errors==0 || cfgfault_seen==0)$fatal(1,"transport probe failed");
$finish;
end
end
endmodule
