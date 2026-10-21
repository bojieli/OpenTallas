`timescale 1ns/1ps
`default_nettype none
// Optional scalar VM adapter for selected L0 broadcast / indexed gather.
// NOT instantiated by the existing die. Integration must give it a real VM
// calendar owner, route its request/return ports, and arbitrate RF ingress.
// One fixed slot at a time; busy is diagnostic, never backpressure.
// Requests are sampled on the edge with vm_read_v=1; return is sampled exactly
// READ_RETURN later. Missing/early/extra returns latch fault. All addresses
// are VM WORD addresses; placement translation is outside this adapter.
// Indexed mode reads live I, computes base+U32(I)*INDEX_MUL, then reads A.
// Broadcast mode reads A directly; rr_wd broadcasts the live selected word
// into the reserved eight-word RF sector. Gather writes ONE masked VM word.
module ot_hbm_vm_scalar_runtime_1021 #(
 parameter integer READ_RETURN=0,
 parameter [31:0] INDEX_MUL=32'd1
)(
 input wire clk,rst_n,
 input wire cmd_v,cmd_indexed,cmd_to_rf,
 input wire [23:0] cmd_base_word,cmd_index_word,cmd_destination_word,
 input wire [4:0] cmd_rf_sector,
 output wire busy,
 output wire vm_read_v,output wire [20:0] vm_read_sector,
 input wire vm_return_v,input wire [255:0] vm_return_data,
 output reg vm_write_v,output reg [20:0] vm_write_sector,
 output reg [7:0] vm_write_mask,output reg [255:0] vm_write_data,
 output reg rr_wv,output reg [4:0] rr_wa,output reg [255:0] rr_wd,
 output reg done,output reg fault
);
 initial begin if(READ_RETURN<1)$fatal(1,"bind actual VM request-to-return age");end
 localparam IDLE=0,INDEX_REQ=1,INDEX_WAIT=2,ADDRESS_MUL=3,
            ADDRESS_ADD=4,DATA_REQ=5,DATA_WAIT=6;
 reg [2:0] state;
 integer remain;
 reg [23:0] base_word,index_word,destination_word,source_word;
 reg [4:0] rf_sector;
 reg to_rf;
 reg [31:0] index_value;
 reg [63:0] product;
 wire [64:0] runtime_address={1'b0,product}+{41'd0,base_word};
 assign busy=state!=IDLE;
 assign vm_read_v=state==INDEX_REQ||state==DATA_REQ;
 assign vm_read_sector=(state==INDEX_REQ)?index_word[23:3]:source_word[23:3];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;remain<=0;vm_write_v<=0;rr_wv<=0;done<=0;fault<=0;
  end else begin
   vm_write_v<=0;rr_wv<=0;done<=0;
   if(cmd_v&&state!=IDLE)fault<=1;
   if(vm_return_v&&!((state==INDEX_WAIT||state==DATA_WAIT)&&remain==0))fault<=1;
   case(state)
    IDLE:if(cmd_v)begin
     base_word<=cmd_base_word;index_word<=cmd_index_word;
     destination_word<=cmd_destination_word;rf_sector<=cmd_rf_sector;
     source_word<=cmd_base_word;to_rf<=cmd_to_rf;
     state<=cmd_indexed?INDEX_REQ:DATA_REQ;
    end
    INDEX_REQ:begin remain<=READ_RETURN-1;state<=INDEX_WAIT;end
    INDEX_WAIT:if(remain!=0)remain<=remain-1;
     else if(!vm_return_v)begin fault<=1;state<=IDLE;done<=1;end
     else begin index_value<=vm_return_data[index_word[2:0]*32+:32];state<=ADDRESS_MUL;end
    ADDRESS_MUL:begin product<=index_value*INDEX_MUL;state<=ADDRESS_ADD;end
    ADDRESS_ADD:if(|runtime_address[64:24])begin fault<=1;state<=IDLE;done<=1;end
     else begin source_word<=runtime_address[23:0];state<=DATA_REQ;end
    DATA_REQ:begin remain<=READ_RETURN-1;state<=DATA_WAIT;end
    DATA_WAIT:if(remain!=0)remain<=remain-1;
     else begin
      done<=1;state<=IDLE;
      if(!vm_return_v)fault<=1;
      else if(to_rf)begin
       rr_wv<=1;rr_wa<=rf_sector;
       rr_wd<={8{vm_return_data[source_word[2:0]*32+:32]}};
      end else begin
       vm_write_v<=1;vm_write_sector<=destination_word[23:3];
       vm_write_mask<=8'd1<<destination_word[2:0];
       vm_write_data<=256'd0;
       vm_write_data[destination_word[2:0]*32+:32]<=vm_return_data[source_word[2:0]*32+:32];
      end
     end
    default:begin state<=IDLE;fault<=1;end
   endcase
  end
 end
endmodule
// Stream-domain wrapper uses the existing COLL 8-bank VM bus ABI.
// Binding reserves COLL owner3/read and owner2/write for the complete slot.
// cmd addresses MUST already be physical VM words; indexed A must occupy a
// contiguous affine region. Output rr_* joins hb_coll rr_* BEFORE cxrc_s;
// programme must register the tag->RFsector mapping through real red_tag.
module ot_hbm_vm_scalar_coll_1021 #(
 parameter integer READ_RETURN=0,parameter [31:0] INDEX_MUL=32'd1
)(
 input wire clk,rst_n,cmd_v,cmd_indexed,cmd_to_rf,
 input wire [23:0] cmd_base_word,cmd_index_word,cmd_destination_word,
 input wire [2:0] cmd_return_tag,
 output wire [135:0] vm_rq,input wire [2055:0] vm_rr,
 output wire [2247:0] vm_kq,
 output wire rr_v,output wire [2:0] rr_tag,output wire [255:0] rr_d,
 output wire busy,done,output wire fault
);
 wire rqv,wv,rv,core_fault;
 wire [20:0] rqs,ws;
 wire [7:0] wm;wire [255:0] wd;
 wire [4:0] unused_wa;
 reg [2:0] return_bank,tag;
 reg address_fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)address_fault<=0;
  else begin
   if(rqv)begin return_bank<=rqs[2:0];if(|rqs[20:16])address_fault<=1;end
   if(wv&&(|ws[20:16]))address_fault<=1;
   if(cmd_v&&!busy)tag<=cmd_return_tag;
  end
 end
 for(genvar b=0;b<8;b=b+1)begin:g_bus
  assign vm_rq[b*17+:17]={rqv&&(rqs[2:0]==b)&&!(|rqs[20:16]),rqs[15:0]};
  assign vm_kq[b*281+:281]={wv&&(ws[2:0]==b)&&!(|ws[20:16]),ws[15:0],wm,wd};
 end
 assign rv=vm_rr[return_bank*257+256];
 assign rr_tag=tag;
 assign fault=address_fault|core_fault;
 ot_hbm_vm_scalar_runtime_1021 #(.READ_RETURN(READ_RETURN),.INDEX_MUL(INDEX_MUL))u_scalar(
  .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_indexed(cmd_indexed),.cmd_to_rf(cmd_to_rf),
  .cmd_base_word(cmd_base_word),.cmd_index_word(cmd_index_word),.cmd_destination_word(cmd_destination_word),
  .cmd_rf_sector(5'd0),.busy(busy),.vm_read_v(rqv),.vm_read_sector(rqs),
  .vm_return_v(rv),.vm_return_data(vm_rr[return_bank*257+:256]),
  .vm_write_v(wv),.vm_write_sector(ws),.vm_write_mask(wm),.vm_write_data(wd),
  .rr_wv(rr_v),.rr_wa(unused_wa),.rr_wd(rr_d),.done(done),.fault(core_fault));
endmodule
`default_nettype wire
