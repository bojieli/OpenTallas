`timescale 1ns/1ps
// HGI-1 ROW_GATHER list/owner formatter. Uses the CURRENT row reader; it does
// not instantiate HBM queues or row storage. A read response's written bit is
// supplied by that reader's row-valid knowledge. All errors terminate the call
// with fault completion and suppress output for the offending word.
module ot_hgi_coll_row_formatter #(
 parameter integer ENABLE=0,MUT_OWNER=0,MUT_ORDER=0,MUT_WRITTEN=0,MUT_ID_BOUND=0,MUT_PROGRESS=0
)(
 input wire clk,rst_n,
 input wire start_v,output wire start_r,
 input wire [7:0] group_size,owner_block,destinations,
 input wire [20:0] row_count,input wire [15:0] row_words,input wire [31:0] context_rows,
 input wire id_v,output wire id_r,input wire [31:0] id,
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
 localparam IDLE=0,IDS=1,MAP=2,DIVB=3,DIVG=4,REQUEST=5,RESPONSE=6,OUTPUT=7,DONE=8,CHECK=9,PRE=10,MUL=11;
 // drive-0849 (c130 / c180 TT -83 / -115): the id bound compare and the /3, %3 of the G = 96 map are registered in
 // PRE (one edge after IDS) and the generic local-row multiply q*B + r gets its own MUL edge: +1 cycle per id
 // (+2 on the generic iterative path); same owner / local row / output order.
 reg oob_q;reg [11:0] r96q_q;reg [1:0] r96r_q;reg [19:0] qg_q;
 reg [3:0] state;
 reg [7:0] G,B;reg [20:0] K;reg [19:0] index_;reg [31:0] saved_raw,context_q;
 wire [19:0] saved_id=saved_raw[19:0];
 reg [15:0] words,word_limit,word_next;
 reg [20:0] index_limit;reg [19:0] index_next;
 reg word_last,index_last;
 // Independent nibble carry terms avoid an increment carry chain feeding
 // terminal comparison and the wide output/state enables in the same edge.
 function automatic [15:0] inc_word(input [15:0] v);
  begin
   inc_word[3:0]=v[3:0]+4'd1;
   inc_word[7:4]=v[7:4]+(&v[3:0]);
   inc_word[11:8]=v[11:8]+(&v[7:0]);
   inc_word[15:12]=v[15:12]+(&v[11:0]);
  end
 endfunction
 function automatic [19:0] inc_index(input [19:0] v);
  begin
   inc_index[3:0]=v[3:0]+4'd1;
   inc_index[7:4]=v[7:4]+(&v[3:0]);
   inc_index[11:8]=v[11:8]+(&v[7:0]);
   inc_index[15:12]=v[15:12]+(&v[11:0]);
   inc_index[19:16]=v[19:16]+(&v[15:0]);
  end
 endfunction
 // floor(i/768) and floor(i/8)%96, with exact native widths:
 // i[19:8] /3 and %3 rather than unsized 32-bit /96 arithmetic.
 wire [11:0] row96_quot=saved_id[19:8]/12'd3;
 wire [1:0] row96_rem=saved_id[19:8]%12'd3;
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
   state<=IDLE;G<=96;B<=8;K<=0;index_<=0;saved_raw<=0;context_q<=0;words<=0;
   read_owner<=0;read_local_row<=0;read_word<=0;out_data<=0;
   out_index<=0;out_word<=0;out_destinations<=0;fault<=0;
   dividend<=0;quotient<=0;qblock<=0;remainder_b<=0;rem_<=0;step<=0;
   word_limit<=0;index_limit<=0;word_next<=0;index_next<=0;word_last<=0;index_last<=0;
  end else if(ENABLE!=0)begin
   case(state)
    IDLE:if(start_v)begin
     fault<=0;G<=group_size;B<=owner_block;K<=row_count;words<=row_words;
     out_destinations<=destinations;context_q<=context_rows;index_<=0;state<=CHECK;
    end
    CHECK:begin
     word_limit<=words-16'd1;index_limit<=K-21'd1;
     if(!good_g || B==0 || out_destinations==0 || out_destinations>G || K==0 || K>21'd1048576 || context_q==0 || context_q>32'd1048576 || words==0)begin fault<=1;state<=DONE;end
     else state<=IDS;
    end
    IDS:if(id_v)begin saved_raw<=id;read_word<=0;state<=PRE;end
    PRE:begin
     oob_q<=(saved_raw>=context_q || |saved_raw[31:20]);r96q_q<=row96_quot;r96r_q<=row96_rem;state<=MAP;
    end
    MAP:begin
     index_next<=inc_index(index_);index_last<=({1'b0,index_}==index_limit);
     if(!MUT_ID_BOUND && oob_q)begin fault<=1;state<=DONE;end
     else begin
     // DS block8: compile-time constant divides for all admitted groups.
     // Generic non-eight blocks use exact iterative division below.
     if(B==8)begin
      case(G)
       1:begin read_owner<=0;read_local_row<=saved_id;end
       2:begin read_owner<=saved_id[3];read_local_row<={saved_id[19:4],saved_id[2:0]};end
       4:begin read_owner<=saved_id[4:3];read_local_row<={saved_id[19:5],saved_id[2:0]};end
       8:begin read_owner<=saved_id[5:3];read_local_row<={saved_id[19:6],saved_id[2:0]};end
       96:begin
        read_owner<=MUT_OWNER?0:{1'b0,r96r_q,saved_id[7:3]};
        read_local_row<={5'b0,r96q_q,saved_id[2:0]};
       end
       default:begin fault<=1;state<=DONE;end
      endcase
      if(G==1 || G==2 || G==4 || G==8 || G==96)state<=REQUEST;
     end else begin dividend<=saved_id;quotient<=0;rem_<=0;step<=19;state<=DIVB;end
    end
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
      qg_q<=nextquot;state<=MUL;
     end else step<=step-1;
    end
    MUL:begin read_local_row<=qg_q*B+remainder_b;state<=REQUEST;end
    REQUEST:begin
     word_next<=inc_word(read_word);word_last<=MUT_PROGRESS?1'b1:(read_word==word_limit);
     if(read_r)state<=RESPONSE;
    end
    RESPONSE:if(response_v)begin
     if(!response_written && !MUT_WRITTEN)begin fault<=1;state<=DONE;end
     else begin out_data<=response_data;out_index<=MUT_ORDER?(index_^20'd1):index_;out_word<=read_word;state<=OUTPUT;end
    end
    OUTPUT:if(out_r)begin
     if(word_last)begin
      if(index_last)state<=DONE;
      else begin index_<=index_next;state<=IDS;end
     end else begin read_word<=word_next;state<=REQUEST;end
    end
    DONE:if(done_r)state<=IDLE;
    default:begin fault<=1;state<=DONE;end
   endcase
  end
 end
endmodule
