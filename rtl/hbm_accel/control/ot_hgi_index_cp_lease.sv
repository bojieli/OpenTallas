`timescale 1ns/1ps
`default_nettype none
// Opt-in dispatch seat, not an allocator. External grant/ACK producers are OPEN.
// No EPS descriptor conversion and no layer->row mapping. All receipts are
// cold-POR scoped. Fault retains this seat and forbids release/new native work.
module ot_hgi_index_cp_lease #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire owner_valid,owner_fault,input wire [72:0] owner_frame,
 input wire cmd_v,output wire cmd_r,input wire [1818:0] cmd_rec,
 input wire grant_v,output wire grant_r,input wire [72:0] grant_frame,
 input wire [5:0] grant_layer,input wire [6:0] grant_rank,input wire [19:0] grant_pos,
 input wire [14:0] grant_key_row0,input wire [15:0] grant_row_end,input wire [8:0] grant_blocks,
 input wire key_visible,input wire [72:0] key_visible_frame,
 input wire query_ACK,input wire [72:0] query_ACK_frame,
 output wire prefetch_v,input wire prefetch_accepted,input wire [72:0] prefetch_frame,
 output wire native_v,input wire native_r,output wire [1818:0] native_rec,
 output wire [72:0] held_frame,output wire [5:0] held_layer,
 output wire [6:0] held_rank,output wire [14:0] held_key_row0,output wire [8:0] held_blocks,
 input wire reads_drained,consumer_done,VM_ACKs_drained,input wire [72:0] drain_frame,
 input wire source_idle,selector_idle,
 output wire release_v,input wire release_r,output wire retained,output reg fault
);
 localparam IDLE=0,GRANT=1,VISIBLE=2,PREFETCH=3,LAUNCH=4,RUN=5,RELEASE=6,FAULT=7;
 reg [2:0] state,state_bar;
 reg [1818:0] record,record_bar;
 reg [72:0] frame,frame_bar;
 reg [39:0] allocation,allocation_bar; // {exclusive_end16,row0_15,blocks9}
 reg [4:0] seen,seen_bar; // {ACK drain,consumer done,read drain,query ACK,key visible}
 wire healthy=state==~state_bar&&record==~record_bar&&frame==~frame_bar&&
               allocation==~allocation_bar&&seen==~seen_bar;
 wire active=state!=IDLE;
 wire allowed=ENABLE&&healthy&&!fault&&owner_valid&&!owner_fault&&(!active||owner_frame==frame);
 wire [7:0] die_id=record[1818:1811];
 wire [7:0] rank8=die_id>=192 ? die_id-192 : die_id>=96 ? die_id-96 : die_id;
 wire [31:0] n=record[64:33]; // imm_a, header starts at bit1
 wire [31:0] blocks=(n+31)>>5;
 wire grant_ok=grant_frame==frame&&grant_layer==record[32:1]&&grant_rank==rank8&&
               grant_pos==record[1810:1791]&&grant_blocks==blocks&&
               grant_row_end<=32768&&{1'b0,grant_key_row0}<grant_row_end;
 assign cmd_r=allowed&&state==IDLE;
 assign grant_r=allowed&&state==GRANT;
 assign retained=ENABLE&&active;
 assign held_frame=frame;assign held_layer=record[6:1];assign held_rank=rank8[6:0];
 assign held_key_row0=allocation[23:9];assign held_blocks=allocation[8:0];
 assign prefetch_v=allowed&&state==PREFETCH;
 assign native_v=allowed&&state==LAUNCH;
 assign native_rec={record[1818:1],native_v};
 assign release_v=allowed&&state==RELEASE&&source_idle&&selector_idle;
 task automatic st(input[2:0] x);begin state<=x;state_bar<=~x;end endtask
 task automatic flags(input[4:0] x);begin seen<=x;seen_bar<=~x;end endtask
 always @(posedge clk or negedge por_n)
 if(!por_n)begin
  st(IDLE);record<=0;record_bar<=~1819'd0;frame<=0;frame_bar<=~73'd0;
  allocation<=0;allocation_bar<=~40'd0;flags(0);fault<=0;
 end else if(ENABLE)begin
  if(!healthy||owner_fault||(active&&(!owner_valid||owner_frame!=frame))||
     (grant_v&&(state!=GRANT||!grant_ok))||
     (key_visible&&(state!=VISIBLE||seen[0]||key_visible_frame!=frame))||
     (query_ACK&&(state!=VISIBLE||seen[1]||query_ACK_frame!=frame))||
     (prefetch_accepted&&(state!=PREFETCH||prefetch_frame!=frame))||
     ((reads_drained||consumer_done||VM_ACKs_drained)&&
      (state!=RUN||drain_frame!=frame||(reads_drained&&seen[2])||
       (consumer_done&&seen[3])||(VM_ACKs_drained&&seen[4]))))begin fault<=1;st(FAULT);end
  else if(!fault&&healthy)case(state)
   IDLE:if(cmd_v&&cmd_r)begin
    if(!cmd_rec[0]||cmd_rec[124:119]!=0||cmd_rec[32:1]>=40||
       cmd_rec[64:33]>10944||cmd_rec[64:33]==0||cmd_rec[1810:1791]!=owner_frame[72:53])begin fault<=1;st(FAULT);end
    else begin record<=cmd_rec;record_bar<=~cmd_rec;frame<=owner_frame;frame_bar<=~owner_frame;flags(0);st(GRANT);end
   end
   GRANT:if(grant_v&&grant_r)begin allocation<={grant_row_end,grant_key_row0,grant_blocks};allocation_bar<=~{grant_row_end,grant_key_row0,grant_blocks};st(VISIBLE);end
   VISIBLE:begin
    flags(seen|{3'b0,query_ACK,key_visible});
    if((seen[0]||key_visible)&&(seen[1]||query_ACK))st(PREFETCH);
   end
   PREFETCH:if(prefetch_accepted&&prefetch_v)st(LAUNCH);
   LAUNCH:if(native_v&&native_r)st(RUN);
   RUN:begin
    flags(seen|{VM_ACKs_drained,consumer_done,reads_drained,2'b0});
    if((seen[2]||reads_drained)&&(seen[3]||consumer_done)&&(seen[4]||VM_ACKs_drained)&&source_idle&&selector_idle)st(RELEASE);
   end
   RELEASE:if(release_v&&release_r)begin flags(0);st(IDLE);end
   FAULT:begin end
   default:begin fault<=1;st(FAULT);end
  endcase
 end
endmodule
`default_nettype wire
