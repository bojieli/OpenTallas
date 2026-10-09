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
 localparam IDLE=0,FEED=1,WAIT_HASH=2,EMIT=3;
 reg [1:0] state;
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
 assign cmd_ready=state==IDLE&&!token_begin&&!accept_valid&&!fault;
 assign row_valid=state==EMIT;
 assign row_column=column_q;
 assign row_id={{(32-ENG_ROW_W){1'b0}},rows[ENG_ROW_W*column_q+:ENG_ROW_W]};
 integer i;
 reg constants_match;
 always @* begin
  constants_match=cmd_layer<ENG_LAYERS;
  for(integer p=0;p<ENG_N;p=p+1)
   if(b_mult[64*p+:64]!=ENG_NIB[64*((cmd_layer*ENG_N+p)*64+1)+:64]) constants_match=0;
  for(integer c=0;c<ENG_COLS;c=c+1) begin
   if(b_prime[32*c+:32]!={{(32-ENG_RES_W){1'b0}},ENG_PRIME[ENG_RES_W*(cmd_layer*ENG_COLS+c)+:ENG_RES_W]}) constants_match=0;
   if(b_offset[32*c+:32]!={{(32-ENG_ROW_W){1'b0}},ENG_OFFSET[ENG_ROW_W*(cmd_layer*ENG_COLS+c)+:ENG_ROW_W]}) constants_match=0;
  end
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
   if(cmd_valid&&cmd_ready) begin
    if(cmd_op!=4||cmd_layer>=ENG_LAYERS||cmd_slot>=NSLOT||
       (ENABLE_GENERIC&&!constants_match&&MUTANT!=4)||
       (!seen[cmd_slot]&&cmd_slot!=next_slot)||
       (seen[cmd_slot]&&cmd_cid!=windows[cmd_slot][ENG_ID_W-1:0]))fault<=1;
    else begin
     layer_q<=(MUTANT==3)?0:cmd_layer;
     if(!seen[cmd_slot]||MUTANT==1) begin
      window_q<={cmd_first?{3{ENG_PAD}}:history,cmd_cid};
      windows[cmd_slot]<={cmd_first?{3{ENG_PAD}}:history,cmd_cid};
      snapshots[cmd_slot]<={cmd_first?{2{ENG_PAD}}:history[2*ENG_ID_W-1:0],cmd_cid};
      history<={cmd_first?{2{ENG_PAD}}:history[2*ENG_ID_W-1:0],cmd_cid};
      seen[cmd_slot]<=1;next_slot<=next_slot+1;
     end else window_q<=windows[cmd_slot];
     feed_count<=0;state<=FEED;
    end
   end
   case(state)
    FEED:if(feed_count==3)state<=WAIT_HASH;else feed_count<=feed_count+1;
    WAIT_HASH:if(hash_valid&&last_pipe[11])begin
     rows<=hash_rows[ENG_ROW_W*ENG_COLS*layer_q+:ENG_ROW_W*ENG_COLS];column_q<=0;state<=EMIT;
    end
    EMIT:if(row_ready)begin
     if(column_q==ENG_COLS-1)begin state<=IDLE;done<=1;end
     else column_q<=column_q+1;
    end
   endcase
  end
 end
endmodule
