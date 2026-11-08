`timescale 1ns/1ps
module tb;
reg ck=0;always #0.5 ck=~ck;
reg rst=0;reg[2:0]cfg_p=0;reg i_pv=0,i_dv=0,i_csv=0;reg[63:0]i_pa=0,i_csd=0;reg[31:0]i_den=0;reg[4:0]i_csi=0;
wire g_o_ov;
wire [31:0] g_o_o;
wire g_o_f;
dsfd_su_t_smd  u_g(.ck(ck),.rst(rst),.cfg_p(cfg_p),.i_pv(i_pv),.i_pa(i_pa),.i_dv(i_dv),.i_den(i_den),.i_csv(i_csv),.i_csi(i_csi),.i_csd(i_csd),.o_ov(g_o_ov),.o_o(g_o_o),.o_f(g_o_f));
wire c_o_ov;
wire [31:0] c_o_o;
wire c_o_f;
codex_svc_smd_native  u_c(.ck(ck),.rst(rst),.cfg_p(cfg_p),.i_pv(i_pv),.i_pa(i_pa),.i_dv(i_dv),.i_den(i_den),.i_csv(i_csv),.i_csi(i_csi),.i_csd(i_csd),.o_ov(c_o_ov),.o_o(c_o_o),.o_f(c_o_f));
wire m_o_ov;
wire [31:0] m_o_o;
wire m_o_f;
codex_svc_smd_native #(.MUT(1)) u_m(.ck(ck),.rst(rst),.cfg_p(cfg_p),.i_pv(i_pv),.i_pa(i_pa),.i_dv(i_dv),.i_den(i_den),.i_csv(i_csv),.i_csi(i_csi),.i_csd(i_csd),.o_ov(m_o_ov),.o_o(m_o_o),.o_f(m_o_f));
wire n_o_ov,n_o_f;wire[31:0]n_o_o;
codex_svc_smd_native #(.MUT(2)) u_fault_mut(.ck(ck),.rst(rst),.cfg_p(cfg_p),.i_pv(i_pv),.i_pa(i_pa),.i_dv(i_dv),.i_den(i_den),.i_csv(i_csv),.i_csi(i_csi),.i_csd(i_csd),.o_ov(n_o_ov),.o_o(n_o_o),.o_f(n_o_f));
integer faultcycles=0,faultmutdiff=0;
integer checks=0,words=0,bad=0,mutdiff=0,epoch,row,i,j;
always@(negedge ck)if(rst)begin
 checks=checks+1;if(g_o_f)faultcycles=faultcycles+1;if(g_o_f!==n_o_f)faultmutdiff=faultmutdiff+1;
 if({g_o_ov,g_o_f}!=={c_o_ov,c_o_f})bad=bad+1;
 if(g_o_ov)begin words=words+1;if(g_o_o!==c_o_o)bad=bad+1;if(g_o_o!==m_o_o)mutdiff=mutdiff+1;end
end
initial begin
 for(epoch=0;epoch<8;epoch=epoch+1)begin
  rst=0;i_pv=0;i_dv=0;i_csv=0;repeat(64)@(negedge ck);cfg_p=epoch;rst=1;repeat(16)@(negedge ck);
  // All32 real cos/sin entries, including this physical pair's four tail slots.
  for(j=0;j<(epoch%2?0:32);j=j+1)begin i_csv=1;i_csi=j;i_csd=64'h3f8000003e800000;@(negedge ck);end
  i_csv=0;repeat(4)@(negedge ck);
  for(row=0;row<2;row=row+1)begin
   i_dv=1;i_den=row?32'h40000000:32'h3f800000;@(negedge ck);i_dv=0;repeat(4)@(negedge ck);
   for(i=0;i<32;i=i+1)begin i_pv=1;i_pa={32'h3f900000+(i<<12),32'h3fa00000+(i<<13)};@(negedge ck);end
   i_pv=0;repeat(96)@(negedge ck);
  end
 end
 $display("SMD_FAULT_COVER faultcycles=%0d faultmutdiff=%0d",faultcycles,faultmutdiff);
 $display("SMD_NATIVE_BOUNDARY checks=%0d words=%0d bad=%0d mutantdiff=%0d added_data_cycles=0 added_reset_cycles=0",checks,words,bad,mutdiff);
 if(bad||words!=512||mutdiff==0||faultcycles==0||faultmutdiff==0)$fatal(1,"SMD_NATIVE_BOUNDARY FAIL");$display("SMD_NATIVE_BOUNDARY PASS");$finish;
end
endmodule
