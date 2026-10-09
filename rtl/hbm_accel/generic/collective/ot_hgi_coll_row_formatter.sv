`timescale 1ns/1ps
// HGI-1 ROW_GATHER list/owner formatter. Uses the CURRENT row reader; it does
// not instantiate HBM queues or row storage. A read response's written bit is
// supplied by that reader's row-valid knowledge. All errors terminate the call
// with fault completion and suppress output for the offending word.
module ot_hgi_coll_row_formatter #(
 parameter integer ENABLE=0,MUT_OWNER=0,MUT_ORDER=0,MUT_WRITTEN=0
)(
 input wire clk,rst_n,
 input wire start_v,output wire start_r,
 input wire [7:0] group_size,owner_block,destinations,
 input wire [19:0] row_count,input wire [15:0] row_words,
 input wire id_v,output wire id_r,input wire [19:0] id,
 output wire read_v,input wire read_r,
 output reg [7:0] read_owner,output reg [19:0] read_local_row,
 output reg [15:0] read_word,
 input wire response_v,output wire response_r,
 input wire [511:0] response_data,input wire response_written,
 output wire out_v,input wire out_r,output reg [511:0] out_data,
 output reg [19:0] out_index,output reg [15:0] out_word,
 output reg [7:0] out_destinations,
 output wire done_v,input wire done_r,output reg fault
);
 localparam IDLE=0,IDS=1,MAP=2,DIVB=3,DIVG=4,REQUEST=5,RESPONSE=6,OUTPUT=7,DONE=8,CHECK=9;
 reg [3:0] state;
 reg [7:0] G,B;reg [19:0] K,index_,saved_id;
 reg [15:0] words;
 reg [19:0] dividend,quotient,qblock,remainder_b;
 reg [20:0] rem_;reg [4:0] step;
 wire [20:0] shifted={rem_[19:0],dividend[19]};
 wire [7:0] divisor=(state==DIVB)?B:G;
 wire subtract=shifted>={13'd0,divisor};
 wire [20:0] nextrem=subtract?shifted-{13'd0,divisor}:shifted;
 wire [19:0] nextquot={quotient[18:0],subtract};
 wire good_g=(G==1||G==2||G==4||G==8||G==96);
 assign start_r=(ENABLE!=0 && state==IDLE);
 assign id_r=(ENABLE!=0 && state==IDS);
 assign read_v=(ENABLE!=0 && state==REQUEST);
 assign response_r=(ENABLE!=0 && state==RESPONSE);
 assign out_v=(ENABLE!=0 && state==OUTPUT);
 assign done_v=(ENABLE!=0 && state==DONE);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;G<=96;B<=8;K<=0;index_<=0;saved_id<=0;words<=0;
   read_owner<=0;read_local_row<=0;read_word<=0;out_data<=0;
   out_index<=0;out_word<=0;out_destinations<=0;fault<=0;
   dividend<=0;quotient<=0;qblock<=0;remainder_b<=0;rem_<=0;step<=0;
  end else if(ENABLE!=0)begin
   case(state)
    IDLE:if(start_v)begin
     fault<=0;G<=group_size;B<=owner_block;K<=row_count;words<=row_words;
     out_destinations<=destinations;index_<=0;state<=CHECK;
    end
    CHECK:begin
     if(!good_g || B==0 || out_destinations==0 || out_destinations>G || K==0 || words==0)begin fault<=1;state<=DONE;end
     else state<=IDS;
    end
    IDS:if(id_v)begin saved_id<=id;read_word<=0;state<=MAP;end
    MAP:begin
     // DS block8: compile-time constant divides for all admitted groups.
     // Generic non-eight blocks use exact iterative division below.
     if(B==8)begin
      case(G)
       1:begin read_owner<=0;read_local_row<=saved_id;end
       2:begin read_owner<=saved_id[3];read_local_row<={saved_id[19:4],saved_id[2:0]};end
       4:begin read_owner<=saved_id[4:3];read_local_row<={saved_id[19:5],saved_id[2:0]};end
       8:begin read_owner<=saved_id[5:3];read_local_row<={saved_id[19:6],saved_id[2:0]};end
       96:begin
        read_owner<=MUT_OWNER?0:((saved_id>>3)%96);
        read_local_row<=((saved_id>>3)/96)*8+saved_id[2:0];
       end
       default:begin fault<=1;state<=DONE;end
      endcase
      if(G==1 || G==2 || G==4 || G==8 || G==96)state<=REQUEST;
     end else begin dividend<=saved_id;quotient<=0;rem_<=0;step<=19;state<=DIVB;end
    end
    DIVB:begin
     dividend<={dividend[18:0],1'b0};quotient<=nextquot;rem_<=nextrem;
     if(step==0)begin
      qblock<=nextquot;remainder_b<=nextrem[19:0];
      dividend<=nextquot;quotient<=0;rem_<=0;step<=19;state<=DIVG;
     end else step<=step-1;
    end
    DIVG:begin
     dividend<={dividend[18:0],1'b0};quotient<=nextquot;rem_<=nextrem;
     if(step==0)begin
      read_owner<=MUT_OWNER?0:nextrem[7:0];
      read_local_row<=nextquot*B+remainder_b;state<=REQUEST;
     end else step<=step-1;
    end
    REQUEST:if(read_r)state<=RESPONSE;
    RESPONSE:if(response_v)begin
     if(!response_written && !MUT_WRITTEN)begin fault<=1;state<=DONE;end
     else begin out_data<=response_data;out_index<=MUT_ORDER?(index_^20'd1):index_;out_word<=read_word;state<=OUTPUT;end
    end
    OUTPUT:if(out_r)begin
     if(read_word+1==words)begin
      if(index_+1==K)state<=DONE;
      else begin index_<=index_+1;state<=IDS;end
     end else begin read_word<=read_word+1;state<=REQUEST;end
    end
    DONE:if(done_r)state<=IDLE;
    default:begin fault<=1;state<=DONE;end
   endcase
  end
 end
endmodule
