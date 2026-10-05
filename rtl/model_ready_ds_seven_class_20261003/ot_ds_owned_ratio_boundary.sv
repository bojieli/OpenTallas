// Additive diagnostic boundary. No original caller or shared FIFO changed.
// cold_n is INITIALISATION ONLY. Warm transport resets require synchronous
// abort_s/abort_d before reset. Accepted owner survives transport reset.
// Raw control/data are not protected: this module has no parent adoption credit.
module ot_ds_owned_ratio_boundary #(parameter integer W=64, ENABLE=0)(
 input wire sclk,dclk,cold_n, srst_n,drst_n,abort_s,abort_d,
 input wire in_v, output wire in_ready, input wire [W-1:0] in_data,
 input wire [227:0] in_owner,
 output wire out_v,input wire out_ready,output wire [W-1:0] out_data,
 output wire [227:0] out_owner,
 input wire retire_v,output wire retire_ready,input wire [227:0] retire_owner,
 input wire reconcile_v,allcopies_fenced,input wire [227:0] reconcile_owner,
 output reg pending,quarantined,output reg [227:0] pending_owner
);
 wire fw_ready,fw_v,rv,rrdy; wire [W+227:0] fd; wire [227:0] receipt;
 wire accept=in_v&&in_ready;
 assign in_ready=ENABLE&&cold_n&&srst_n&&!abort_s&&!pending&&!quarantined&&fw_ready;
 assign out_v=ENABLE&&cold_n&&drst_n&&!abort_d&&fw_v;
 assign out_data=fd[W-1:0]; assign out_owner=fd[W+227:W];
 assign retire_ready=ENABLE&&cold_n&&drst_n&&!abort_d&&rrdy;
 ot_ratio_cdc_fifo #(.W(W+228)) forward_fifo(
 .wclk(sclk),.wrst_n(srst_n&&cold_n),.w_v(accept),.w_rdy(fw_ready),.w_d({in_owner,in_data}),
 .rclk(dclk),.rrst_n(drst_n&&cold_n),.r_v(fw_v),.r_rdy(out_ready&&out_v),.r_d(fd),.w_live(),.r_live());
 ot_ratio_cdc_fifo #(.W(228)) receipt_fifo(
 .wclk(dclk),.wrst_n(drst_n&&cold_n),.w_v(retire_v&&retire_ready),.w_rdy(rrdy),.w_d(retire_owner),
 .rclk(sclk),.rrst_n(srst_n&&cold_n),.r_v(rv),.r_rdy(ENABLE&&cold_n),.r_d(receipt),.w_live(),.r_live());
 always @(posedge sclk) begin
  if(!cold_n) begin pending<=0; quarantined<=0; pending_owner<=0; end
  else begin
   if(accept) begin pending<=1; pending_owner<=in_owner; end
   if((abort_s||!srst_n)&&pending) quarantined<=1;
   if(rv&&ENABLE) begin
    if(pending&&!quarantined&&!abort_s&&srst_n&&receipt==pending_owner) pending<=0;
    else quarantined<=1;
   end
   if(reconcile_v&&allcopies_fenced&&pending&&quarantined&&reconcile_owner==pending_owner) begin
    pending<=0; quarantined<=0;
   end
  end
 end
endmodule
