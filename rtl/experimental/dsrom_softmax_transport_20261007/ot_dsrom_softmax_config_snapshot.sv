// Stream-local exact atomic command snapshot. Loss of protection after lock
// aborts the row; the no-ready numerical core cannot pause for repair.
module ot_dsrom_softmax_config_snapshot(
 input wire clk,rst_n,
 input wire in_valid,output wire in_ready,input wire [1:0] in_beat,
 input wire [31:0] in_epoch,input wire [15:0] in_tag,input wire [1023:0] in_data,
 output wire config_valid,input wire lock_valid,
 output wire [31:0] config_epoch,output wire [15:0] config_tag,
 output wire [2601:0] config_data,
 input wire release_valid,input wire [31:0] release_epoch,input wire [15:0] release_tag,
 output wire locked,fault
);
 import ot_gpu_w6_secded_pkg::*;
 localparam [2:0] IDLE=0,COLLECT=1,COMMIT=2,CHECK=3,READY=4,LOCKED=5,FAILED=6;
 (* keep="true",dont_touch="true" *) reg [2:0] phase,phase_n;
 (* keep="true",dont_touch="true" *) reg [1:0] count,count_n;
 (* keep="true",dont_touch="true" *) reg [31:0] epoch,epoch_n;
 (* keep="true",dont_touch="true" *) reg [15:0] tag,tag_n;
 reg [2951:0] staging;
 wire integrity=(phase_n==~phase)&&(count_n==~count)&&(epoch_n==~epoch)&&(tag_n==~tag)&&(phase<=FAILED)&&(count<=2);
 wire banknormal,bankfault,repairing;wire [2623:0] decoded;
 assign fault=!integrity||phase==FAILED||bankfault||(phase==LOCKED&&!banknormal);
 assign in_ready=rst_n&&!fault&&banknormal&&(phase==IDLE||phase==COLLECT);
 assign config_valid=rst_n&&!fault&&banknormal&&(phase==READY||phase==LOCKED);
 assign locked=phase==LOCKED;
 assign config_data=decoded[2601:0];assign config_epoch=epoch;assign config_tag=tag;
 wire take=in_valid&&in_ready;
 wire badtake=take&&(in_beat!=count||(phase==COLLECT&&(in_epoch!=epoch||in_tag!=tag))||(in_beat==2&&|in_data[1023:554]));
 wire badrelease=release_valid&&(phase!=LOCKED||release_epoch!=epoch||release_tag!=tag);
 wire badlock=lock_valid&&(phase!=READY||!config_valid);
 wire semantic_valid=(decoded[6:0]==8&&decoded[9:7]==3)||(decoded[6:0]==40&&decoded[9:7]==6);
 wire [1151:0] codes;
 for(genvar i=0;i<16;i=i+1)begin:g_encode
  assign codes[72*i+:72]=encode64(in_data[64*i+:64]);
 end
 for(genvar i=0;i<41;i=i+1)begin:g_stage
  always @(posedge clk)if(take&&!badtake&&in_beat==i/16)staging[72*i+:72]<=codes[72*(i%16)+:72];
 end
 ot_hbm_w2_protected_bank #(.WORDS(41)) storage(.clk(clk),.por_n(rst_n),.load(phase==COMMIT&&banknormal&&!fault),
  .load_encoded(1'b1),.fatal(1'b0),.d(2624'd0),.encoded_d(staging),.q(decoded),.encoded_q(),
  .normal(banknormal),.fault(bankfault),.repairing(repairing));
 always @(posedge clk)begin
  if(!rst_n)begin phase<=IDLE;phase_n<=~IDLE;count<=0;count_n<=~2'd0;epoch<=0;epoch_n<=~32'd0;tag<=0;tag_n<=~16'd0;end
  else if(fault||badtake||badrelease||badlock)begin phase<=FAILED;phase_n<=~FAILED;end
  else begin
   if(take)begin
    if(phase==IDLE)begin epoch<=in_epoch;epoch_n<=~in_epoch;tag<=in_tag;tag_n<=~in_tag;end
    if(in_beat==2)begin phase<=COMMIT;phase_n<=~COMMIT;end
    else begin phase<=COLLECT;phase_n<=~COLLECT;count<=count+2'd1;count_n<=~(count+2'd1);end
   end
   if(phase==COMMIT&&banknormal)begin phase<=CHECK;phase_n<=~CHECK;end
   if(phase==CHECK&&banknormal)begin
`ifdef SOFTMAX_CONFIG_IGNORE_SHAPE
    phase<=READY;phase_n<=~READY;
`else
    if(semantic_valid)begin phase<=READY;phase_n<=~READY;end
    else begin phase<=FAILED;phase_n<=~FAILED;end
`endif
   end
   if(lock_valid)begin phase<=LOCKED;phase_n<=~LOCKED;end
   if(release_valid)begin phase<=IDLE;phase_n<=~IDLE;count<=0;count_n<=~2'd0;end
  end
 end
endmodule
