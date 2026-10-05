`timescale 1ps/1fs
// Clocked RF byte-store/RMW finiteGPUclient. Test patterns only, no transformer
// arithmetic admission. Every RF_result/retire is a real registered hardware
// edge; no caller timestamp drives completion.27SERedge residence is explicit.
module ot_hbm_r14_finite_client #(parameter integer ENABLE=0)(
 input wire clk,rst_n,start_v,output wire start_r,
 input ot_hbm_r14_pkg::identity_t start_id,input wire [255:0] start_data,
 input wire [31:0] byte_mask,input wire is_reader,
 output wire reserve_v,input wire reserve_r,output ot_hbm_r14_pkg::identity_t reserve_id,
 output wire req_v,input wire req_r,output ot_hbm_r14_pkg::request_t req,
 input wire result_v,output wire result_r,input wire result_we,result_credit,
 input ot_hbm_r14_pkg::owned_t result,
 output wire store_v,input wire store_r,output ot_hbm_r14_pkg::owned_t store,
 output wire reader_result_v,input wire reader_result_r,
 output wire reader_retire_v,output ot_hbm_r14_pkg::identity_t reader_retire_id,
 output wire reader_reverse_v,output ot_hbm_r14_pkg::identity_t reader_reverse_id,
 output wire retire_reverse_v,input wire retire_reverse_r,output ot_hbm_r14_pkg::owned_t retire_reverse,
 output reg RF_commit,output reg RMW_retire,output reg done,output reg fault,
 output wire [1:0] selected_stack,output reg [31:0] result_checksum);
 import ot_hbm_r14_pkg::*;
 generate if(!ENABLE)begin:off
   assign start_r=0;assign reserve_v=0;assign reserve_id='0;assign req_v=0;assign req='0;
   assign result_r=0;assign store_v=0;assign store='0;assign reader_result_v=0;
   assign reader_retire_v=0;assign reader_retire_id='0;assign reader_reverse_v=0;assign reader_reverse_id='0;
   assign retire_reverse_v=0;assign retire_reverse='0;assign selected_stack=0;
   always @*begin RF_commit=0;RMW_retire=0;done=0;fault=0;result_checksum=0;end
 end else begin:on
   localparam integer IDLE=0,RESERVE=1,READREQ=2,READWAIT=3,MERGE=4,MERGED=5,
     WRREQ=6,WRWAIT=7,STORE=8,CREDITWAIT=9,READERRESULT=10,READERRETIRE=11,REVERSE=12;
   reg [3:0] phase;identity_t owner;reg [255:0] supplied,RF;
   reg [31:0] mask;reg reader;reg [4:0] merge_cycles;owned_t held;
   assign start_r=phase==IDLE;assign selected_stack=owner.stack;
   assign reserve_v=phase==RESERVE;assign reserve_id=owner;
   assign req_v=phase==READREQ||phase==WRREQ;
   assign req='{id:owner,len:6'd1,we:(phase==WRREQ),data:RF};
   assign result_r=phase==READWAIT||phase==WRWAIT||phase==CREDITWAIT;
   assign store_v=phase==STORE;assign store=held;
   assign reader_result_v=phase==READERRESULT;assign reader_retire_v=phase==READERRETIRE;
   assign reader_retire_id=owner;assign reader_reverse_v=(phase==CREDITWAIT)&&result_v&&result_credit&&result.id==owner;
   assign reader_reverse_id=owner;assign retire_reverse_v=phase==REVERSE;assign retire_reverse=held;
   integer b;
   always @(posedge clk or negedge rst_n)begin
     if(!rst_n)begin phase<=IDLE;owner<='0;supplied<=0;RF<=0;mask<=0;reader<=0;merge_cycles<=0;held<='0;
       RF_commit<=0;RMW_retire<=0;done<=0;fault<=0;result_checksum<=0;end
     else begin
       RF_commit<=0;RMW_retire<=0;done<=0;
       if(start_v&&start_r)begin owner<=start_id;supplied<=start_data;mask<=byte_mask;reader<=is_reader;RF<=start_data;
         phase<=RESERVE;end
       if(reserve_v&&reserve_r)begin
         if(reader||mask!=32'hffffffff)phase<=READREQ;else phase<=WRREQ;
       end
       if(req_v&&req_r)phase<=(phase==READREQ)?READWAIT:WRWAIT;
       if(result_v&&result_r)begin
         if(result.id!=owner)fault<=1;
         else case(phase)
           READWAIT:if(result_we||result_credit)fault<=1;else begin
             held<=result;RF<=result.data;
             if(reader)begin result_checksum<=result_checksum^result.data[31:0];RF_commit<=1;phase<=READERRESULT;end
             else begin merge_cycles<=0;phase<=MERGE;end
           end
           WRWAIT:if(!result_we||result_credit)fault<=1;else begin held<=result;phase<=STORE;end
           CREDITWAIT:if(!result_credit)fault<=1;else begin phase<=IDLE;done<=1;end
           default:fault<=1;
         endcase
       end
       if(phase==MERGE)begin
         if(merge_cycles==0)for(b=0;b<32;b=b+1)if(mask[b])RF[b*8+:8]<=supplied[b*8+:8];
         if(merge_cycles==26)begin RF_commit<=1;phase<=MERGED;end
         else merge_cycles<=merge_cycles+1'b1;
       end
       if(phase==MERGED)begin RMW_retire<=1;phase<=WRREQ;end
       if(store_v&&store_r)phase<=CREDITWAIT;
       if(reader_result_v&&reader_result_r)phase<=READERRETIRE;
       if(phase==READERRETIRE)phase<=REVERSE;
       if(retire_reverse_v&&retire_reverse_r)phase<=CREDITWAIT;
     end
   end
 end endgenerate
endmodule
