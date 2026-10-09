`timescale 1ns/1ps
// HGI EHASH DS binding. Unchanged shipped hash arithmetic. B is a typed
// validation tuple, NOT a serialized generic-B implementation. Generic B
// mismatches fail closed until the compiler operand ABI is supplied.
import ot_hdc_engram_tables_shipped_pkg::*;
module ot_hbm_idx_ehash_ds #(
 parameter integer ENABLE_GENERIC=0, NSLOT=8, SW=$clog2(NSLOT), MUTANT=0
)(
 input wire clk,rst_n,
 input wire token_begin,
 input wire accept_valid, input wire [SW-1:0] accept_slot,
 input wire cmd_valid, output wire cmd_ready,
 input wire [2:0] cmd_op,cmd_layer,
 input wire [SW-1:0] cmd_slot,
 input wire [16:0] cmd_cid,
 input wire cmd_first,
 input wire [255:0] b_mult,
 input wire [767:0] b_prime,b_offset,
 output wire row_valid,input wire row_ready,
 output wire [31:0] row_id, output wire [4:0] row_column,
 output reg done,fault
);
 localparam IDLE=0,FEED=1,WAIT_HASH=2,EMIT=3,CHECK=4,MATCH=5;
 // MATCH (drive-0849 -633 ps): the 1,792-bit constants compare is registered (cm_q) one edge before CHECK
 // gates the snapshot / window writes: +1 cycle per EHASH command, same result.
 reg cm_q;
 reg [2:0] state;
 reg [2:0] q_op,q_layer;reg [SW-1:0] q_slot;
 reg [16:0] q_cid;reg q_first;
 reg [255:0] q_mult;reg [767:0] q_prime,q_offset;
 reg [31:0] row_head;
 reg [NSLOT-1:0] seen;
 reg [4*ENG_ID_W-1:0] windows[0:NSLOT-1];
 reg [3*ENG_ID_W-1:0] snapshots[0:NSLOT-1];
 reg [3*ENG_ID_W-1:0] history;
 reg [SW:0] next_slot;
 reg [4*ENG_ID_W-1:0] window_q;
 reg [2:0] layer_q;
 reg [1:0] feed_count;
 reg [4:0] column_q;
 reg [ENG_ROW_W*ENG_COLS-1:0] rows;
 reg [11:0] last_pipe;
 wire hash_valid;
 wire [ENG_ROW_W*ENG_LAYERS*ENG_COLS-1:0] hash_rows;
 wire feeding=state==FEED;
 ot_hdc_engram_hash_shipped u_ds_hash(.clk(clk),.rst_n(rst_n),
  .in_valid(feeding),.in_first(feed_count==0),
  .in_cid(window_q[ENG_ID_W*(3-feed_count)+:ENG_ID_W]),
  .out_valid(hash_valid),.out_row(hash_rows));
 assign cmd_ready=state==IDLE&&!fault;
 assign row_valid=state==EMIT;
 assign row_column=column_q;
 assign row_id=row_head;
 integer i;
 reg constants_match;
 always @* begin
  constants_match=0;
  case(q_layer)
   3'd0:begin
    constants_match=1;
    for(integer p=0;p<ENG_N;p=p+1)
     if(q_mult[64*p+:64]!=ENG_NIB[64*((0*ENG_N+p)*64+1)+:64]) constants_match=0;
    for(integer c=0;c<ENG_COLS;c=c+1)begin
     if(q_prime[32*c+:32]!={{(32-ENG_RES_W){1'b0}},ENG_PRIME[ENG_RES_W*(0*ENG_COLS+c)+:ENG_RES_W]})constants_match=0;
     if(q_offset[32*c+:32]!={{(32-ENG_ROW_W){1'b0}},ENG_OFFSET[ENG_ROW_W*(0*ENG_COLS+c)+:ENG_ROW_W]})constants_match=0;
    end
   end
   3'd1:begin
    constants_match=1;
    for(integer p=0;p<ENG_N;p=p+1)
     if(q_mult[64*p+:64]!=ENG_NIB[64*((1*ENG_N+p)*64+1)+:64]) constants_match=0;
    for(integer c=0;c<ENG_COLS;c=c+1)begin
     if(q_prime[32*c+:32]!={{(32-ENG_RES_W){1'b0}},ENG_PRIME[ENG_RES_W*(1*ENG_COLS+c)+:ENG_RES_W]})constants_match=0;
     if(q_offset[32*c+:32]!={{(32-ENG_ROW_W){1'b0}},ENG_OFFSET[ENG_ROW_W*(1*ENG_COLS+c)+:ENG_ROW_W]})constants_match=0;
    end
   end
   default:constants_match=0;
  endcase
 end
 always @(posedge clk)if(cmd_valid&&cmd_ready&&!token_begin&&!accept_valid)begin
  q_op<=cmd_op;q_layer<=cmd_layer;q_slot<=cmd_slot;q_cid<=cmd_cid;q_first<=cmd_first;
  q_mult<=b_mult;q_prime<=b_prime;q_offset<=b_offset;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE; seen<=0;next_slot<=0;history<={3{ENG_PAD}};
   last_pipe<=0;done<=0;fault<=0;feed_count<=0;column_q<=0;layer_q<=0;
  end else begin
   done<=0;last_pipe<={last_pipe[10:0],feeding&&feed_count==3};
   if(token_begin) begin
    if(state!=IDLE||accept_valid) fault<=1;
    else begin seen<=0;next_slot<=0;end
   end
   if(accept_valid) begin
    if(state!=IDLE||!seen[accept_slot]||token_begin)fault<=1;
    else begin
     if(MUTANT!=2)history<=snapshots[accept_slot];
     seen<=0;next_slot<=0;
    end
   end
   if(cmd_valid&&cmd_ready)begin
    if(token_begin||accept_valid)fault<=1;else state<=MATCH;
   end
   if(state==MATCH) begin
    cm_q<=constants_match;state<=CHECK;
   end
   if(state==CHECK) begin
    if(q_op!=4||q_layer>=ENG_LAYERS||q_slot>=NSLOT||
       (ENABLE_GENERIC&&!cm_q&&MUTANT!=4)||
       (!seen[q_slot]&&q_slot!=next_slot)||
       (seen[q_slot]&&q_cid!=windows[q_slot][ENG_ID_W-1:0]))fault<=1;
    else begin
     layer_q<=(MUTANT==3)?0:q_layer;
     if(!seen[q_slot]||MUTANT==1) begin
      window_q<={q_first?{3{ENG_PAD}}:history,q_cid};
      windows[q_slot]<={q_first?{3{ENG_PAD}}:history,q_cid};
      snapshots[q_slot]<={q_first?{2{ENG_PAD}}:history[2*ENG_ID_W-1:0],q_cid};
      history<={q_first?{2{ENG_PAD}}:history[2*ENG_ID_W-1:0],q_cid};
      seen[q_slot]<=1;next_slot<=next_slot+1;
     end else window_q<=windows[q_slot];
     feed_count<=0;state<=FEED;
    end
   end
   case(state)
    FEED:if(feed_count==3)state<=WAIT_HASH;else feed_count<=feed_count+1;
    WAIT_HASH:if(hash_valid&&last_pipe[11])begin
     case(layer_q)
      0:begin rows<=hash_rows[0+:ENG_ROW_W*ENG_COLS];row_head<={{(32-ENG_ROW_W){1'b0}},hash_rows[0+:ENG_ROW_W]};end
      1:begin rows<=hash_rows[ENG_ROW_W*ENG_COLS+:ENG_ROW_W*ENG_COLS];row_head<={{(32-ENG_ROW_W){1'b0}},hash_rows[ENG_ROW_W*ENG_COLS+:ENG_ROW_W]};end
     endcase
     column_q<=0;state<=EMIT;
    end
    EMIT:if(row_ready)begin
     if(column_q==ENG_COLS-1)begin state<=IDLE;done<=1;end
     else begin
      case(column_q)
       5'd0:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*1+:ENG_ROW_W]};
       5'd1:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*2+:ENG_ROW_W]};
       5'd2:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*3+:ENG_ROW_W]};
       5'd3:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*4+:ENG_ROW_W]};
       5'd4:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*5+:ENG_ROW_W]};
       5'd5:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*6+:ENG_ROW_W]};
       5'd6:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*7+:ENG_ROW_W]};
       5'd7:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*8+:ENG_ROW_W]};
       5'd8:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*9+:ENG_ROW_W]};
       5'd9:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*10+:ENG_ROW_W]};
       5'd10:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*11+:ENG_ROW_W]};
       5'd11:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*12+:ENG_ROW_W]};
       5'd12:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*13+:ENG_ROW_W]};
       5'd13:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*14+:ENG_ROW_W]};
       5'd14:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*15+:ENG_ROW_W]};
       5'd15:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*16+:ENG_ROW_W]};
       5'd16:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*17+:ENG_ROW_W]};
       5'd17:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*18+:ENG_ROW_W]};
       5'd18:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*19+:ENG_ROW_W]};
       5'd19:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*20+:ENG_ROW_W]};
       5'd20:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*21+:ENG_ROW_W]};
       5'd21:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*22+:ENG_ROW_W]};
       5'd22:row_head<={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*23+:ENG_ROW_W]};
       default:row_head<=0;
      endcase
      column_q<=column_q+1;
     end
    end
   endcase
  end
 end
endmodule
