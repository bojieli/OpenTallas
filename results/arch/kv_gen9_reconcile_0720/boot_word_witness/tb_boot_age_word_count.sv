`timescale 1ns/1ps
module tb;
reg ck=0; always #5 ck=~ck; reg rst_n=0,por_n=0; reg[142:0] pr_age=0,pr_old=0;reg ready_age=0,ready_old=0; integer i; integer fault_at_plain=-1,fault_at_mu=-1;
wire we_plain,sealed_plain,cf_plain,df_plain;wire[7:0] addr_plain,fc_plain;wire[63:0] data_plain;
qkd_static_kv_boot_dispatch #(.DIECFG(1),.NRST(43),.DIECAP(1)) d_plain(.ck(ck),.rst_n(rst_n),.boot_pr(pr_age),.boot_image_target(4'd10),.boot_image_ready(ready_age),.boot_image_fault(1'b0),.boot_image_epoch(16'd1),.boot_image_digest(64'd1),.execution_active(1'b0),.sink_applied(160'd0),.local_configured(3'd0),.sink_fault(1'b0),.diecfg_sealed(sealed_plain),.diecfg_fault(cf_plain),.diecfg_we(we_plain),.diecfg_addr(addr_plain),.diecfg_data(data_plain),.fault(df_plain),.fault_code(fc_plain));
qkd_kv_die_cfg_a #(.NRST(43),.CAP(1)) c_plain(.ck(ck),.por_n(por_n),.cfg_we(we_plain),.cfg_addr(addr_plain),.cfg_data(data_plain),.sealed(sealed_plain),.fault(cf_plain));
wire we_mu,sealed_mu,cf_mu,df_mu;wire[7:0] addr_mu,fc_mu;wire[63:0] data_mu;
qkd_static_kv_boot_dispatch_mu #(.DIECFG(1),.NRST(43),.DIECAP(1)) d_mu(.ck(ck),.rst_n(rst_n),.boot_pr(pr_age),.boot_image_target(4'd10),.boot_image_ready(ready_age),.boot_image_fault(1'b0),.boot_image_epoch(16'd1),.boot_image_digest(64'd1),.execution_active(1'b0),.sink_applied(160'd0),.local_configured(3'd0),.sink_fault(1'b0),.diecfg_sealed(sealed_mu),.diecfg_fault(cf_mu),.diecfg_we(we_mu),.diecfg_addr(addr_mu),.diecfg_data(data_mu),.fault(df_mu),.fault_code(fc_mu));
qkd_kv_die_cfg_a #(.NRST(43),.CAP(1)) c_mu(.ck(ck),.por_n(por_n),.cfg_we(we_mu),.cfg_addr(addr_mu),.cfg_data(data_mu),.sealed(sealed_mu),.fault(cf_mu));
wire we_legacy_control,sealed_legacy_control,cf_legacy_control,df_legacy_control;wire[7:0] addr_legacy_control,fc_legacy_control;wire[63:0] data_legacy_control;
qkd_static_kv_boot_dispatch #(.DIECFG(1),.NRST(43),.DIECAP(1)) d_legacy_control(.ck(ck),.rst_n(rst_n),.boot_pr(pr_old),.boot_image_target(4'd10),.boot_image_ready(ready_old),.boot_image_fault(1'b0),.boot_image_epoch(16'd1),.boot_image_digest(64'd1),.execution_active(1'b0),.sink_applied(160'd0),.local_configured(3'd0),.sink_fault(1'b0),.diecfg_sealed(sealed_legacy_control),.diecfg_fault(cf_legacy_control),.diecfg_we(we_legacy_control),.diecfg_addr(addr_legacy_control),.diecfg_data(data_legacy_control),.fault(df_legacy_control),.fault_code(fc_legacy_control));
qkd_kv_die_cfg #(.NRST(43),.CAP(1)) c_legacy_control(.ck(ck),.por_n(por_n),.cfg_we(we_legacy_control),.cfg_addr(addr_legacy_control),.cfg_data(data_legacy_control),.sealed(sealed_legacy_control),.fault(cf_legacy_control));
task tick; begin @(posedge ck); #1; end endtask
function automatic[63:0] age_word(input integer a); begin if(a==95)age_word=64'h514b564443464731;else if(a==76)age_word=64'h01010101;else if(a==77||a==78)age_word=1;else if(a>=79)age_word=64'h0101;else age_word=0;end endfunction
initial begin
repeat(4)tick(); @(negedge ck);por_n=1;rst_n=1;repeat(5)tick();
for(i=0;i<96;i=i+1)begin @(negedge ck);pr_age=0;pr_age[74]=1;pr_age[73:64]=10'(i);pr_age[63:0]=age_word(i);pr_old=0;if(i<77)begin pr_old[74]=1;pr_old[73:64]=10'(i);pr_old[63:0]=(i==76)?64'h514b564443464731:0;end tick();if(df_plain&&fault_at_plain<0)fault_at_plain=i;if(df_mu&&fault_at_mu<0)fault_at_mu=i;end
@(negedge ck);pr_age=0;pr_old=0;repeat(6)tick();
if(fault_at_plain!=77||fault_at_mu!=77||!fc_plain[3]||!fc_mu[3]||sealed_plain||sealed_mu||!sealed_legacy_control||cf_legacy_control||df_legacy_control)$fatal(1,"BOOT_WORD_WITNESS_FAIL plain=%0d mu=%0d codes=%h/%h sealed=%b%b old=%b/%b/%b",fault_at_plain,fault_at_mu,fc_plain,fc_mu,sealed_plain,sealed_mu,sealed_legacy_control,cf_legacy_control,df_legacy_control);
$display("EXPECTED_SCHEMA_REFUSAL actual_plain=word77 actual_fresh_MU=word77 AGE_SEAL95_UNREACHED LEGACY77_CONTROL_PASS");$finish;end
endmodule
