`timescale 1ps/1fs
`default_nettype none
// VERIFICATION FIXTURE ONLY. Uses the actual bound root's index-read port.
// Start while the real caller withholds publication acceptance; the fixture
// never creates publication ACKs, writes SRAM, or releases a lease.
module ot_hbm_norm_samebank_readback_checker #(
 parameter integer D=4096, parameter GOLDEN_FILE="ey.mem"
)(
 input wire clk,por_n,start,publication_checked,lease_retained,
 input wire [72:0] held_frame,input wire [6:0] rank,
 input wire [31:0] output_base_word,
 input wire native_ACK_v,native_ACK_r,
 input wire [72:0] native_ACK_frame,input wire [31:0] native_ACK_addr,
 output wire read_v,input wire read_r,
 output wire [31:0] read_addr,output wire [5:0] read_words,
 output wire [7:0] read_tag,output wire [72:0] read_frame,
 output wire [6:0] read_rank,
 input wire rsp_v,output wire rsp_r,input wire [1023:0] rsp_data,
 input wire [7:0] rsp_tag,input wire [72:0] rsp_frame,input wire [6:0] rsp_rank,
 output reg passed
);
 localparam integer ROWS=D/32;
 localparam [2:0] IDLE=0,REQUEST=1,RESPONSE=2,HOLD=3,DONE=4;
 reg [2:0] state=IDLE;
 reg [31:0] golden[0:D-1];
 reg [72:0] frame_q;reg [6:0] rank_q;
 reg [31:0] base_q;integer row=0,acks=0,hold_edges=0;
 reg [1023:0] held_data;reg [7:0] held_tag;
 reg [72:0] held_rsp_frame;reg [6:0] held_rsp_rank;
 initial begin
  if(D<32||D%32!=0)$fatal(1,"readback fixture requires complete32word rows");
  // No fallback values: missing/short golden leaves X and fails comparison.
  $readmemh(GOLDEN_FILE,golden);
 end
 assign read_v=state==REQUEST;
 assign read_addr=base_q+32'(row*32);assign read_words=6'd32;
 assign read_tag=8'(row);assign read_frame=frame_q;assign read_rank=rank_q;
 assign rsp_r=state==HOLD&&hold_edges>=3;
 always @(posedge clk)begin
  if(!por_n)begin
   state<=IDLE;passed<=0;row<=0;acks<=0;hold_edges<=0;
   frame_q<=0;rank_q<=0;base_q<=0;
   held_data<=0;held_tag<=0;held_rsp_frame<=0;held_rsp_rank<=0;
  end else begin
   if(native_ACK_v&&native_ACK_r)begin
    if(native_ACK_frame!==held_frame||native_ACK_addr!==output_base_word+32'(acks*32))
     $fatal(1,"norm actual publication ACK frame/address/order differs");
    if(acks>=ROWS)$fatal(1,"norm duplicate/excess publication ACK");
    acks<=acks+1;
   end
   if(state!=IDLE&&state!=DONE)begin
    if(!lease_retained||held_frame!==frame_q)
     $fatal(1,"norm lease dropped/changed before samebank golden readback");
    if(!publication_checked)$fatal(1,"norm checked publication lost while caller held");
   end
   case(state)
    IDLE:if(start)begin
     if(!publication_checked||!lease_retained||acks!=ROWS||(|output_base_word[4:0]))
      $fatal(1,"norm final readback started before actual complete checked publication");
     frame_q<=held_frame;rank_q<=rank;base_q<=output_base_word;row<=0;state<=REQUEST;
    end
    REQUEST:if(read_v&&read_r)state<=RESPONSE;
    RESPONSE:if(rsp_v)begin
     if(rsp_frame!==frame_q||rsp_tag!==8'(row)||rsp_rank!==rank_q)
      $fatal(1,"norm samebank response identity mismatch");
     for(integer k=0;k<32;k=k+1)
      if((^golden[row*32+k])===1'bx||rsp_data[k*32+:32]!==golden[row*32+k])
       $fatal(1,"norm samebank golden mismatch word=%0d got=%h expected=%h",row*32+k,rsp_data[k*32+:32],golden[row*32+k]);
     held_data<=rsp_data;held_tag<=rsp_tag;held_rsp_frame<=rsp_frame;held_rsp_rank<=rsp_rank;
     hold_edges<=0;state<=HOLD;
    end
    HOLD:begin
     if(!rsp_v||rsp_data!==held_data||rsp_tag!==held_tag||rsp_frame!==held_rsp_frame||rsp_rank!==held_rsp_rank)
      $fatal(1,"norm actual samebank response changed under held ready");
     hold_edges<=hold_edges+1;
     if(rsp_v&&rsp_r)begin
      if(row+1==ROWS)begin
       passed<=1;state<=DONE;
       $display("PASS_NORM_SAMEBANK_GOLDEN_READBACK words=%0d actual_ACKs=%0d full73 held_response",D,acks);
      end else begin row<=row+1;state<=REQUEST;end
     end
    end
    DONE:state<=DONE;
    default:$fatal(1,"norm readback fixture invalid state");
   endcase
  end
 end
endmodule
`default_nettype wire
