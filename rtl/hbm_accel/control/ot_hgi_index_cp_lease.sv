`timescale 1ns/1ps
`default_nettype none
// Opt-in dispatch seat, not an allocator. External grant/ACK producers are OPEN.
// Rows are native99 kind2 address-domain capabilities, not EPS physical HBM
// rows. Extent checks constrain encoding; provider certifies actual capacity.
// No EPS descriptor conversion and no layer->row mapping. All receipts are
// cold-POR scoped. Fault retains this seat and forbids release/new native work.
module ot_hgi_index_cp_lease #(parameter integer ENABLE=0)(
 input wire clk,por_n,
 input wire owner_valid,owner_fault,input wire [72:0] owner_frame,
 input wire cmd_v,output wire cmd_r,input wire [1818:0] cmd_rec,
 input wire grant_v,output wire grant_r,input wire [72:0] grant_frame,
 input wire [5:0] grant_layer,input wire [6:0] grant_rank,input wire [19:0] grant_pos,
 input wire [59:0] grant_key_rows,input wire [63:0] grant_row_ends,input wire [35:0] grant_block_counts,
 input wire key_visible,input wire [72:0] key_visible_frame,
 input wire query_ACK,input wire [72:0] query_ACK_frame,
 output wire prefetch_v,output wire [1:0] prefetch_quarter,
 input wire prefetch_accepted,input wire [72:0] prefetch_frame,input wire [1:0] prefetch_accepted_quarter,
 // native_r is a checked exactly-once acceptance receipt, not delayed ready.
 output wire native_v,input wire native_r,input wire [72:0] native_accepted_frame,output wire [1818:0] native_rec,
 output wire [72:0] held_frame,output wire [5:0] held_layer,
 output wire [6:0] held_rank,output wire [14:0] held_key_row0,output wire [8:0] held_blocks,
 output wire [59:0] held_key_rows,output wire [35:0] held_block_counts,
 input wire reads_drained,consumer_done,VM_ACKs_drained,input wire [72:0] drain_frame,
 input wire source_idle,selector_idle,
 output wire release_v,input wire release_r,output wire retained,output reg fault
);
 localparam IDLE=0,GRANT=1,VISIBLE=2,PREFETCH=3,LAUNCH=4,RUN=5,RELEASE=6,FAULT=7;
 reg [2:0] state,state_bar;
 reg [1818:0] record,record_bar;
 reg [72:0] frame,frame_bar;
 reg [159:0] allocation,allocation_bar; // {exclusive_ends64,row0s60,counts36}
 reg [1:0] quarter,quarter_bar;
 reg [4:0] seen,seen_bar; // {ACK drain,consumer done,read drain,query ACK,key visible}
 wire healthy=state==~state_bar&&record==~record_bar&&frame==~frame_bar&&
               allocation==~allocation_bar&&seen==~seen_bar&&quarter==~quarter_bar;
 wire active=state!=IDLE;
 wire allowed=ENABLE&&healthy&&!fault&&owner_valid&&!owner_fault&&(!active||owner_frame==frame);
 wire [7:0] die_id=record[1818:1811];
 wire [7:0] rank8=die_id>=192 ? die_id-192 : die_id>=96 ? die_id-96 : die_id;
 wire [31:0] n=record[64:33]; // imm_a, header starts at bit1
 // Literal hfd_idx_sel.nq_of: contiguous2736-key quarters, eight keys/block.
 function automatic [8:0] count_of(input[31:0] count,input integer q);
  reg[31:0] lo,left;begin lo=2736*q;left=count<=lo?0:count-lo;
   if(left>2736)left=2736;count_of=(left+7)>>3;end
 endfunction
 wire [35:0] needed_counts={count_of(n,3),count_of(n,2),count_of(n,1),count_of(n,0)};
 wire grant_identity=grant_frame==frame&&grant_layer==record[32:1]&&grant_rank==rank8&&
               grant_pos==record[1810:1791]&&grant_block_counts==needed_counts;
 wire [3:0] range_ok;
 genvar g;generate for(g=0;g<4;g=g+1)begin:range_checks
  assign range_ok[g]=needed_counts[g*9+:9]==0||
   (grant_row_ends[g*16+:16]<=32768&&{1'b0,grant_key_rows[g*15+:15]}<grant_row_ends[g*16+:16]);
 end endgenerate
 wire grant_ok=grant_identity&&(&range_ok);
 assign cmd_r=allowed&&state==IDLE;
 assign grant_r=allowed&&state==GRANT;
 assign retained=ENABLE&&active;
 assign held_frame=frame;assign held_layer=record[6:1];assign held_rank=rank8[6:0];
 assign held_key_rows=allocation[95:36];assign held_block_counts=allocation[35:0];
 assign held_key_row0=held_key_rows[quarter*15+:15];assign held_blocks=held_block_counts[quarter*9+:9];
 assign prefetch_quarter=quarter;
 assign prefetch_v=allowed&&state==PREFETCH&&held_blocks!=0;
 assign native_v=allowed&&state==LAUNCH;
 assign native_rec={record[1818:1],native_v};
 assign release_v=allowed&&state==RELEASE&&source_idle&&selector_idle;
 task automatic st(input[2:0] x);begin state<=x;state_bar<=~x;end endtask
 task automatic flags(input[4:0] x);begin seen<=x;seen_bar<=~x;end endtask
 always @(posedge clk or negedge por_n)
 if(!por_n)begin
  st(IDLE);record<=0;record_bar<=~1819'd0;frame<=0;frame_bar<=~73'd0;
  allocation<=0;allocation_bar<=~160'd0;quarter<=0;quarter_bar<=3;flags(0);fault<=0;
 end else if(ENABLE)begin
  if(!healthy||owner_fault||(active&&(!owner_valid||owner_frame!=frame))||
     (grant_v&&(state!=GRANT||!grant_ok))||
     (key_visible&&(state!=VISIBLE||seen[0]||key_visible_frame!=frame))||
     (query_ACK&&(state!=VISIBLE||seen[1]||query_ACK_frame!=frame))||
     (prefetch_accepted&&(!prefetch_v||prefetch_frame!=frame||prefetch_accepted_quarter!=quarter))||
     (native_r&&(state!=LAUNCH||native_accepted_frame!=frame))||
     ((reads_drained||consumer_done||VM_ACKs_drained)&&
      (state!=RUN||drain_frame!=frame||(reads_drained&&seen[2])||
       (consumer_done&&seen[3])||(VM_ACKs_drained&&seen[4]))))begin fault<=1;st(FAULT);end
  else if(!fault&&healthy)case(state)
   IDLE:if(cmd_v&&cmd_r)begin
    if(!cmd_rec[0]||cmd_rec[124:119]!=0||cmd_rec[32:1]>=40||
       cmd_rec[64:33]>10944||cmd_rec[1810:1791]!=owner_frame[72:53])begin fault<=1;st(FAULT);end
    else begin record<=cmd_rec;record_bar<=~cmd_rec;frame<=owner_frame;frame_bar<=~owner_frame;flags(0);quarter<=0;quarter_bar<=3;st(GRANT);end
   end
   GRANT:if(grant_v&&grant_r)begin allocation<={grant_row_ends,grant_key_rows,grant_block_counts};allocation_bar<=~{grant_row_ends,grant_key_rows,grant_block_counts};st(VISIBLE);end
   VISIBLE:begin
    flags(seen|{3'b0,query_ACK,key_visible});
    if((n==0||seen[0]||key_visible)&&(seen[1]||query_ACK))st(PREFETCH);
   end
   PREFETCH:if(held_blocks==0||(prefetch_accepted&&prefetch_v))begin
    if(quarter==3)st(LAUNCH);
    else begin quarter<=quarter+1'b1;quarter_bar<=~(quarter+2'd1);end
   end
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
