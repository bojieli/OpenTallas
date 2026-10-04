`timescale 1ns/1ps
// HA4 successor: +2 dispatch edges; sector issue loop unchanged.
// Canonical bounded-native lifecycle. One writer, 72 source layer/rank rows.
// Default off. All external ACKs are real held ready/valid authorities. This
// component neither synthesizes W2 completion nor releases on elapsed cycles.
// key = {layer[5:0], rank, position[12:0]}. Byte staging is source-allocated
// shared memory, validated by a physical readback before command completion.
module ot_hbm_accel_kv_lifecycle #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable, quiesce,
 input wire cmd_valid, output wire cmd_ready,
 input wire [2:0] cmd_op, input wire [63:0] cmd_identity,
 input wire [19:0] cmd_key, input wire [63:0] cmd_producer,
 input wire [63:0] cmd_sequence, input wire [10:0] cmd_PC,
 input wire cmd_consumer, input wire [3:0] cmd_stage_beat,
 input wire [9:0] cmd_stage_base, input wire [4:0] cmd_stage_SM,
 input wire [511:0] cmd_stage_data,
 input wire [33:0] cmd_K_base, cmd_V_base,
 output reg rsp_valid, input wire rsp_ready, output reg rsp_fault,
 output reg [2:0] rsp_op, output reg [63:0] rsp_identity,
 output reg [19:0] rsp_key, output reg [63:0] rsp_sequence,
 output reg [10:0] rsp_PC, output reg [511:0] rsp_capture,
 output reg [63:0] rsp_producer, output reg rsp_consumer,
 output reg [3:0] rsp_stage_beat,
 output wire shared_valid, shared_write, input wire shared_ready,
 output wire [9:0] shared_addr, output wire [4:0] shared_SM,
 output wire shared_rank, output wire [511:0] shared_wdata,
 input wire shared_done, output wire shared_done_ready,
 input wire [511:0] shared_rdata,
 // Commit admission binds the actual writer owner before issuing sector requests.
 // Backend mapper must retain K RMW grants across OLD_ACK and NEW_ACK reverse.
 output wire commit_valid, input wire commit_ready,
 output wire [63:0] writer_identity, output wire [19:0] writer_key,
 output wire [9:0] writer_stage_base, output wire [4:0] writer_stage_SM,
 output wire [33:0] writer_K_base, writer_V_base,
 input wire payload_valid, output wire payload_ready,
 input wire [63:0] payload_identity, input wire [19:0] payload_key,
 input wire [8:0] payload_sector, input wire [33:0] payload_source_addr,
 input wire payload_visible, payload_reverse, payload_write,
 input wire [255:0] payload_rdata,
 output wire payload_req_valid, input wire payload_req_ready,
 output wire payload_req_write, output wire [8:0] payload_req_sector,
 output wire [33:0] payload_req_source_addr, output wire [255:0] payload_req_data,
 output wire payload_req_rmw, payload_req_rmw_last,
 // 0 bitmap, 1 producer record. Order is source bitmap BEFORE record under lock.
 input wire metadata_valid, output wire metadata_ready,
 input wire [63:0] metadata_identity, input wire [19:0] metadata_key,
 input wire metadata_record,
 input wire consumer_valid, output wire consumer_ready,
 input wire [63:0] consumer_identity, input wire [19:0] consumer_key,
 input wire consumer_stage, consumer_accepted, consumer_reverse,
 // Actual packed reader-record visibility after each source done callback.
 input wire reader_metadata_valid, output wire reader_metadata_ready,
 input wire [63:0] reader_metadata_identity, input wire [19:0] reader_metadata_key,
 input wire reader_metadata_stage,
 // Hydration only from actual checkpoint state captures, never reset defaults.
 // por_n is cold power-on ONLY: warm reset must first quiesce + drain actual
 // external copies. run_enable merely pauses; it never erases retained debt.
 input wire hydrate_valid, output wire hydrate_ready,
 input wire [19:0] hydrate_key, input wire [63:0] hydrate_producer,
 output wire drain_valid, input wire drain_ready,
 output wire [63:0] drain_identity, output wire [19:0] drain_key,
 input wire drain_done_valid, output wire drain_done_ready,
 input wire [63:0] drain_done_identity, input wire [19:0] drain_done_key,
 // Actual stage, payload-request, payload-return, metadata, RF/common-ACK,
 // consumer, request-CDC and reverse-CDC cohorts; each must be empty/retired.
 input wire [7:0] drain_done_allcopies,
 output reg fault, output wire writer_retained, output wire idle
);
 localparam BEGIN=0, STAGE=1, COMMIT=2, PUBLISH=3, ACQUIRE=4, CONSUMER=5, RELEASE=6;
 localparam IDLE=0, WRITE=1, WRITE_ACK=2, READ=3, READ_ACK=4, WAIT_COMMIT=5,
            WAIT_PUBLISH=6, WAIT_CONSUMER=7, WAIT_DRAIN=8,
            LOAD=10, LOAD_ACK=11, OLD_REQ=12, OLD_ACK=13, NEW_REQ=14, NEW_ACK=15;
 reg [4:0] state; reg [6:0] reader_count;
 reg [8:0] sector_cursor; reg [255:0] old_sector;
 reg receipt_visible, receipt_reverse;
 wire [3:0] wanted_beat=sector_cursor<256 ? sector_cursor>>5 : 8+((sector_cursor-256)>>1);
 reg writer_live, commit_sent, drain_sent;
 reg [63:0] w_identity; reg [19:0] w_key; reg [9:0] stage_base, incoming_base;
 reg [33:0] K_base, V_base, incoming_K, incoming_V;
 reg [4:0] stage_SM, incoming_SM;
 reg [15:0] stage_mask;
 reg [271:0] visible_mask, reverse_mask;
 reg [1:0] metadata_mask;
 reg [2:0] op; reg [63:0] ident, seq; reg [19:0] key;
 reg [63:0] producer; reg [10:0] pc; reg cstage;
 reg [3:0] beat; reg [511:0] stage_data;
 reg pub_valid[0:71], reader_live[0:71];
 reg [12:0] pub_pos[0:71]; reg [63:0] pub_tag[0:71], reader_tag[0:71];
 reg [12:0] reader_pos[0:71];
 reg [1:0] consumer_mask[0:71], consumer_reverse_mask[0:71], responded_mask[0:71], reader_metadata_mask[0:71];

 // Saved selection is derived only from the accepted command, never live ports.
 reg [71:0] row_select;
 reg snap_pub_valid, snap_reader_live;
 reg [12:0] snap_pub_pos, snap_reader_pos;
 reg [63:0] snap_pub_tag, snap_reader_tag;
 reg [1:0] snap_consumer_mask, snap_reverse_mask, snap_responded_mask, snap_metadata_mask;
 reg bad_common, bad_begin, bad_stage, bad_commit, bad_publish, bad_acquire, bad_consumer, bad_release;
 wire [163:0] row_word[0:71];
 reg [163:0] selected_word;
 for(genvar r=0;r<72;r=r+1) begin:saved_row
  assign row_word[r]={pub_valid[r],pub_pos[r],pub_tag[r],reader_live[r],reader_tag[r],reader_pos[r],
       consumer_mask[r],consumer_reverse_mask[r],responded_mask[r],reader_metadata_mask[r]} & {164{row_select[r]}};
 end
 always @* begin
  selected_word=0;
  for(integer r=0;r<72;r=r+1) selected_word=selected_word|row_word[r];
 end

 // (2026-10-04 retime) Every completion event keeps its original ready, is captured on the
 // accepting edge, and is checked and applied one edge later from the registered copy, so no
 // input port and no in-cycle arithmetic sits in the check -> refuse/update cone. Events keep
 // their order; each one's effect lands +1 cycle later. A command is not accepted on the edge
 // after a hydrate capture (the original blocked it while hydrate_valid was high).
 // The expected payload address is a register of the current cursor (cursor moves >=1 edge
 // before the next ACK state).
 reg payload_v_q, payload_wide_bad_q;
 reg metadata_v_q;
 reg [63:0] metadata_identity_q;
 reg [19:0] metadata_key_q;
 reg metadata_record_q;
 reg consumer_v_q;
 reg [63:0] consumer_identity_q;
 reg [19:0] consumer_key_q;
 reg consumer_stage_q;
 reg consumer_accepted_q;
 reg consumer_reverse_q;
 reg reader_metadata_v_q;
 reg [63:0] reader_metadata_identity_q;
 reg [19:0] reader_metadata_key_q;
 reg reader_metadata_stage_q;
 reg drain_done_v_q, drain_bad_q;
 reg [63:0] drain_done_identity_q;
 reg [19:0] drain_done_key_q;
 reg [7:0] drain_done_allcopies_q;
 reg hydrate_v_q;
 reg [19:0] hydrate_key_q;
 reg [63:0] hydrate_producer_q;
 reg [33:0] expected_payload_addr;
 wire [33:0] expected_K_addr=K_base + (((sector_cursor >> 6)*512 +
    (w_key[12:0] >> 4))*128 + ((sector_cursor & 63)*2))*16;
 wire [33:0] expected_V_addr=V_base + ((((sector_cursor-256) >> 2)*8192 +
    w_key[12:0])*128) + ((sector_cursor-256) & 3)*32;
 always @(posedge clk) begin
  expected_payload_addr <= sector_cursor<256 ? expected_K_addr : expected_V_addr;
  metadata_identity_q <= metadata_identity;
  metadata_key_q <= metadata_key;
  metadata_record_q <= metadata_record;
  consumer_identity_q <= consumer_identity;
  consumer_key_q <= consumer_key;
  consumer_stage_q <= consumer_stage;
  consumer_accepted_q <= consumer_accepted;
  consumer_reverse_q <= consumer_reverse;
  reader_metadata_identity_q <= reader_metadata_identity;
  reader_metadata_key_q <= reader_metadata_key;
  reader_metadata_stage_q <= reader_metadata_stage;
  drain_done_identity_q <= drain_done_identity;
  drain_done_key_q <= drain_done_key;
  drain_done_allcopies_q <= drain_done_allcopies;
  hydrate_key_q <= hydrate_key;
  hydrate_producer_q <= hydrate_producer;
 end
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin payload_v_q<=0; payload_wide_bad_q<=0; metadata_v_q<=0; consumer_v_q<=0; reader_metadata_v_q<=0; drain_done_v_q<=0; drain_bad_q<=0; hydrate_v_q<=0; end
  else begin
   payload_v_q <= payload_valid && payload_ready;
   payload_wide_bad_q <= payload_identity!=w_identity || payload_key!=w_key || payload_sector!=sector_cursor
       || payload_source_addr!=expected_payload_addr;
   metadata_v_q <= metadata_valid && metadata_ready;
   consumer_v_q <= consumer_valid && consumer_ready;
   reader_metadata_v_q <= reader_metadata_valid && reader_metadata_ready;
   drain_done_v_q <= drain_done_valid && drain_done_ready;
   drain_bad_q <= drain_done_identity!=ident || drain_done_key!=key || drain_done_allcopies!=8'hff;
   hydrate_v_q <= hydrate_valid && hydrate_ready;
  end
 end

 wire active=ENABLE && por_n && run_enable && !fault;
 wire [6:0] cmd_row={cmd_key[19:14],cmd_key[13]};
 wire [6:0] row={key[19:14],key[13]};
 wire [6:0] event_row={consumer_key_q[19:14],consumer_key_q[13]};
 wire [6:0] reader_metadata_row={reader_metadata_key_q[19:14],reader_metadata_key_q[13]};
 wire [6:0] hydrate_row={hydrate_key_q[19:14],hydrate_key_q[13]};

 // Row-indexed event stage 2 (snapshot); same-row updates of the acting stage are forwarded.
 reg c2_v, c2_bad_row, c2_live, c2_stage, c2_acc, c2_rev; reg [6:0] c2_row;
 reg [63:0] c2_tag, c2_ident; reg [12:0] c2_pos, c2_keypos; reg [1:0] c2_cm, c2_crm;
 reg m2_v, m2_bad_row, m2_live, m2_stage; reg [6:0] m2_row;
 reg [63:0] m2_tag, m2_ident; reg [12:0] m2_pos, m2_keypos; reg [1:0] m2_resp, m2_rmm;
 wire c_fwd = c2_v && c2_row == event_row;
 wire m_fwd = m2_v && m2_row == reader_metadata_row;
 reg h2_v, h2_bad_row, h2_live, h2_pubv; reg [6:0] h2_row; reg [12:0] h2_pos; reg [63:0] h2_producer;
 always @(posedge clk) begin
  c2_row <= event_row; c2_bad_row <= event_row >= 72;
  c2_live <= reader_live[event_row]; c2_tag <= reader_tag[event_row]; c2_pos <= reader_pos[event_row];
  c2_ident <= consumer_identity_q; c2_keypos <= consumer_key_q[12:0]; c2_stage <= consumer_stage_q;
  c2_acc <= consumer_accepted_q; c2_rev <= consumer_reverse_q;
  c2_cm <= consumer_mask[event_row] | ((c_fwd && c2_acc) ? (2'b01 << c2_stage) : 2'b00);
  c2_crm <= consumer_reverse_mask[event_row] | ((c_fwd && c2_rev) ? (2'b01 << c2_stage) : 2'b00);
  m2_row <= reader_metadata_row; m2_bad_row <= reader_metadata_row >= 72;
  m2_live <= reader_live[reader_metadata_row]; m2_tag <= reader_tag[reader_metadata_row];
  m2_pos <= reader_pos[reader_metadata_row];
  m2_ident <= reader_metadata_identity_q; m2_keypos <= reader_metadata_key_q[12:0]; m2_stage <= reader_metadata_stage_q;
  m2_resp <= responded_mask[reader_metadata_row];
  m2_rmm <= reader_metadata_mask[reader_metadata_row] | (m_fwd ? (2'b01 << m2_stage) : 2'b00);
  h2_row <= hydrate_row; h2_bad_row <= hydrate_row >= 72; h2_live <= reader_live[hydrate_row];
  h2_pubv <= pub_valid[hydrate_row] | (h2_v && h2_row == hydrate_row);
  h2_pos <= hydrate_key_q[12:0]; h2_producer <= hydrate_producer_q;
 end
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin c2_v<=0; m2_v<=0; h2_v<=0; end
  else begin c2_v <= consumer_v_q; m2_v <= reader_metadata_v_q; h2_v <= hydrate_v_q; end
 end
 assign cmd_ready=active && (!quiesce || (cmd_op!=BEGIN && cmd_op!=ACQUIRE))
    && state==IDLE && !rsp_valid && !hydrate_valid && !hydrate_v_q && !h2_v;
 assign writer_retained=writer_live;
 assign writer_identity=w_identity; assign writer_key=w_key;
 assign writer_stage_base=stage_base; assign writer_stage_SM=stage_SM;
 assign shared_SM=stage_SM; assign shared_rank=w_key[13];
 assign writer_K_base=K_base; assign writer_V_base=V_base;
 assign idle=state==IDLE && !rsp_valid && !writer_live && reader_count==0;
 assign shared_valid=active && (state==WRITE || state==READ || state==LOAD);
 assign shared_write=state==WRITE;
 assign shared_addr=stage_base + (state==LOAD || state==LOAD_ACK ? wanted_beat : beat); assign shared_wdata=stage_data;
 assign shared_done_ready=active && (state==WRITE_ACK || state==READ_ACK || state==LOAD_ACK);
 assign commit_valid=active && state==WAIT_COMMIT && !commit_sent;
 assign payload_ready=active && writer_live && commit_sent && (state==OLD_ACK || state==NEW_ACK);
 assign payload_req_valid=active && (state==OLD_REQ || state==NEW_REQ);
 assign payload_req_write=state==NEW_REQ;
 assign payload_req_sector=sector_cursor;
 assign payload_req_source_addr=sector_cursor<256 ?
    K_base + (((sector_cursor>>6)*512+(w_key[12:0]>>4))*128+((sector_cursor&63)*2))*16 :
    V_base + (((sector_cursor-256)>>2)*8192+w_key[12:0])*128+((sector_cursor-256)&3)*32;
 assign payload_req_rmw=sector_cursor<256;
 assign payload_req_rmw_last=sector_cursor<256 && state==NEW_REQ;
 wire [255:0] partial_mask=(256'hff << (w_key[3:0]*8)) | (256'hff << ((w_key[3:0]+16)*8));
 wire [255:0] partial_lo={248'b0,stage_data[(sector_cursor&31)*16+:8]} << (w_key[3:0]*8);
 wire [255:0] partial_hi={248'b0,stage_data[(sector_cursor&31)*16+8+:8]} << ((w_key[3:0]+16)*8);
 assign payload_req_data=sector_cursor<256 ?
       (old_sector & ~partial_mask) | partial_lo | partial_hi : stage_data[(sector_cursor&1)*256+:256];
 assign metadata_ready=active && writer_live && commit_sent;
 assign consumer_ready=active; assign reader_metadata_ready=active;
 assign hydrate_ready=active && !quiesce && state==IDLE && !writer_live && !rsp_valid;
 assign drain_valid=active && state==WAIT_DRAIN && !drain_sent;
 assign drain_identity=ident; assign drain_key=key;
 assign drain_done_ready=active && state==WAIT_DRAIN && drain_sent;
 task complete;
 begin rsp_valid<=1; rsp_fault<=0; rsp_op<=op; rsp_identity<=ident;
       rsp_key<=key; rsp_sequence<=seq; rsp_PC<=pc; rsp_producer<=producer;
       rsp_consumer<=cstage; rsp_stage_beat<=beat; state<=IDLE; end
 endtask
 task refuse;
 begin fault<=1; rsp_valid<=1; rsp_fault<=1; rsp_op<=op; rsp_identity<=ident;
       rsp_key<=key; rsp_sequence<=seq; rsp_PC<=pc; end
 endtask
 integer i;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin
   row_select<=0;
   {snap_pub_valid,snap_pub_pos,snap_pub_tag,snap_reader_live,snap_reader_tag,snap_reader_pos,
    snap_consumer_mask,snap_reverse_mask,snap_responded_mask,snap_metadata_mask}<=0;
   {bad_common,bad_begin,bad_stage,bad_commit,bad_publish,bad_acquire,bad_consumer,bad_release}<=0;
   state<=IDLE; reader_count<=0; sector_cursor<=0; old_sector<=0; receipt_visible<=0; receipt_reverse<=0; fault<=0; rsp_valid<=0; rsp_fault<=0; rsp_capture<=0;
   writer_live<=0; commit_sent<=0; drain_sent<=0; stage_mask<=0;
   visible_mask<=0; reverse_mask<=0; metadata_mask<=0;
   w_identity<=0; w_key<=0; stage_base<=0; incoming_base<=0;
   K_base<=0; V_base<=0; incoming_K<=0; incoming_V<=0; stage_SM<=0; incoming_SM<=0; op<=0; ident<=0; key<=0;
   producer<=0; seq<=0; pc<=0; cstage<=0; beat<=0; stage_data<=0;
   rsp_producer<=0; rsp_consumer<=0; rsp_stage_beat<=0;
   rsp_op<=0; rsp_identity<=0; rsp_key<=0; rsp_sequence<=0; rsp_PC<=0;
   for(i=0;i<72;i=i+1) begin pub_valid[i]<=0; pub_pos[i]<=0;
    pub_tag[i]<=0; reader_live[i]<=0; reader_tag[i]<=0; reader_pos[i]<=0;
    consumer_mask[i]<=0; consumer_reverse_mask[i]<=0; responded_mask[i]<=0; reader_metadata_mask[i]<=0; end
  end else if(active) begin
   if(rsp_valid && rsp_ready) rsp_valid<=0;
   if(h2_v) begin
    if(h2_bad_row || h2_live || h2_pubv) refuse();
    else begin pub_valid[h2_row]<=1; pub_pos[h2_row]<=h2_pos;
      pub_tag[h2_row]<=h2_producer; end
   end
   // Payload receipts keep the original edge (the per-sector REQ/ACK interval is unchanged):
   // the narrow receipt/state checks act on the accepting edge, the wide identity/key/sector/
   // address equality is captured on that edge and refused one edge later (sticky fault).
   if(payload_valid && payload_ready) begin
    if(payload_write!=(state==NEW_ACK)
       || (!payload_visible && !payload_reverse)
       || (payload_visible && receipt_visible) || (payload_reverse && receipt_reverse)
       || (payload_reverse && !payload_visible && !receipt_visible)) refuse();
    else begin
     if(payload_visible) begin
      receipt_visible<=1;
      if(state==OLD_ACK) old_sector<=payload_rdata;
      else visible_mask[sector_cursor]<=1;
     end
     if(payload_reverse) begin
      receipt_reverse<=1;
      if(state==NEW_ACK) reverse_mask[sector_cursor]<=1;
     end
    end
   end
   if(payload_v_q && payload_wide_bad_q) refuse();
   if(metadata_v_q) begin
    if(metadata_identity_q!=w_identity || metadata_key_q!=w_key
       || metadata_mask[metadata_record_q] || (metadata_record_q && !metadata_mask[0])
       || !(&visible_mask) || !(&reverse_mask)) refuse();
    else metadata_mask[metadata_record_q]<=1;
   end
   // Row-indexed events: the accepted event's row record is snapshotted on the next edge
   // (72:1 select from registers), then checked and applied (same check as the original).
   if(c2_v) begin
    if(c2_bad_row || !c2_live || c2_tag!=c2_ident || c2_pos!=c2_keypos
       || (!c2_acc && !c2_rev)
       || (c2_acc && c2_cm[c2_stage])
       || (c2_rev && c2_crm[c2_stage])
       || (c2_rev && !c2_acc && !c2_cm[c2_stage])
       || (c2_stage && !(c2_cm[0] && c2_crm[0]))) refuse();
    else begin
     if(c2_acc) consumer_mask[c2_row][c2_stage]<=1;
     if(c2_rev) consumer_reverse_mask[c2_row][c2_stage]<=1; end
   end
   if(m2_v) begin
    if(m2_bad_row || !m2_live || m2_tag!=m2_ident || m2_pos!=m2_keypos
       || !m2_resp[m2_stage]
       || m2_rmm[m2_stage]
       || (m2_stage && !m2_rmm[0])) refuse();
    else reader_metadata_mask[m2_row][m2_stage]<=1;
   end
   if(cmd_valid && cmd_ready) begin
    for(i=0;i<72;i=i+1) row_select[i]<=(cmd_row==7'(i));
    op<=cmd_op; ident<=cmd_identity; key<=cmd_key; seq<=cmd_sequence;
    producer<=cmd_producer; pc<=cmd_PC; cstage<=cmd_consumer;
    beat<=cmd_stage_beat; stage_data<=cmd_stage_data;
    incoming_base<=cmd_stage_base; incoming_SM<=cmd_stage_SM; incoming_K<=cmd_K_base; incoming_V<=cmd_V_base;
    // Dispatch on a separate edge, preserving exact command identity on faults.
    state<=9;
   end else case(state)
    9: begin
     {snap_pub_valid,snap_pub_pos,snap_pub_tag,snap_reader_live,snap_reader_tag,snap_reader_pos,
      snap_consumer_mask,snap_reverse_mask,snap_responded_mask,snap_metadata_mask}<=selected_word;
     state<=16;
    end
    16: begin
     bad_common<=(row>=72 || pc>=1737 || op>RELEASE
       || (op>=STAGE && op<=PUBLISH && (incoming_base!=stage_base
           || incoming_K!=K_base || incoming_V!=V_base || incoming_SM!=stage_SM)));
     bad_begin<=(writer_live || snap_reader_live ||
        (snap_pub_valid ? (snap_pub_pos==8191 || key[12:0]!=snap_pub_pos+1'b1) : key[12:0]!=0)
        || incoming_base>1008 || incoming_K[4:0]!=0 || incoming_V[4:0]!=0
        || {1'b0,incoming_K}+35'd4194304>35'h400000000
        || {1'b0,incoming_V}+35'd4194304>35'h400000000
        || (incoming_K<incoming_V ? incoming_V-incoming_K<4194304 : incoming_K-incoming_V<4194304));
     bad_stage<=(!writer_live || ident!=w_identity || key!=w_key || commit_sent
        || stage_mask[beat] || stage_base>1008);
     bad_commit<=(!writer_live || ident!=w_identity || key!=w_key || !(&stage_mask)
        || commit_sent);
     bad_publish<=(!writer_live || ident!=w_identity || key!=w_key || !commit_sent);
     bad_acquire<=(writer_live || !snap_pub_valid || snap_pub_pos!=key[12:0]
        || snap_pub_tag!=producer || snap_reader_live);
     bad_consumer<=(!snap_reader_live || snap_reader_tag!=ident || snap_reader_pos!=key[12:0]
        || snap_responded_mask[cstage]);
     bad_release<=(!snap_reader_live || snap_reader_tag!=ident || snap_reader_pos!=key[12:0]
        || !(&snap_consumer_mask) || !(&snap_reverse_mask) || !(&snap_responded_mask) || !(&snap_metadata_mask));
     state<=17;
    end
    17: begin
     if(bad_common) refuse();
     else case(op)
      BEGIN: if(bad_begin) refuse();
       else begin writer_live<=1; w_identity<=ident; w_key<=key;
        stage_base<=incoming_base; stage_SM<=incoming_SM; K_base<=incoming_K; V_base<=incoming_V; stage_mask<=0; visible_mask<=0; reverse_mask<=0;
        metadata_mask<=0; commit_sent<=0; complete(); end
      STAGE: if(bad_stage) refuse(); else state<=WRITE;
      COMMIT: if(bad_commit) refuse(); else state<=WAIT_COMMIT;
      PUBLISH: if(bad_publish)
        refuse(); else state<=WAIT_PUBLISH;
      ACQUIRE: if(bad_acquire) refuse();
       else begin reader_count<=reader_count+1'b1; reader_live[row]<=1; reader_tag[row]<=ident; reader_pos[row]<=key[12:0];
        consumer_mask[row]<=0; consumer_reverse_mask[row]<=0; responded_mask[row]<=0; reader_metadata_mask[row]<=0; complete(); end
      CONSUMER: if(bad_consumer)
        refuse(); else state<=WAIT_CONSUMER;
      RELEASE: if(bad_release) refuse();
       else begin drain_sent<=0; state<=WAIT_DRAIN; end
     endcase
    end
    WRITE: if(shared_ready) state<=WRITE_ACK;
    WRITE_ACK: if(shared_done) state<=READ;
    READ: if(shared_ready) state<=READ_ACK;
    READ_ACK: if(shared_done) begin
     if(shared_rdata!=stage_data) refuse();
     else begin stage_mask[beat]<=1; rsp_capture<=shared_rdata; complete(); end
    end
    WAIT_COMMIT: begin
     if(commit_valid && commit_ready) begin
      commit_sent<=1; sector_cursor<=0; beat<=0; state<=LOAD;
     end
    end
    LOAD: if(shared_ready) state<=LOAD_ACK;
    LOAD_ACK: if(shared_done) begin
      stage_data<=shared_rdata; beat<=wanted_beat;
      state<=sector_cursor<256 ? OLD_REQ : NEW_REQ;
    end
    OLD_REQ: if(payload_req_ready) begin receipt_visible<=0; receipt_reverse<=0; state<=OLD_ACK; end
    OLD_ACK: if(receipt_visible && receipt_reverse) state<=NEW_REQ;
    NEW_REQ: if(payload_req_ready) begin receipt_visible<=0; receipt_reverse<=0; state<=NEW_ACK; end
    NEW_ACK: if(receipt_visible && receipt_reverse) begin
      if(sector_cursor==271) complete();
      else begin
       sector_cursor<=sector_cursor+1'b1;
       if((sector_cursor<255 && sector_cursor[4:0]!=31) ||
          (sector_cursor>=256 && sector_cursor[0]==0))
        state<=sector_cursor<255 ? OLD_REQ : NEW_REQ;
       else state<=LOAD;
      end
    end
    WAIT_PUBLISH: if(&metadata_mask) begin
      pub_valid[row]<=1; pub_pos[row]<=key[12:0]; pub_tag[row]<=ident;
      writer_live<=0; complete(); end
    WAIT_CONSUMER: if(consumer_mask[row][cstage] && consumer_reverse_mask[row][cstage]) begin
      responded_mask[row][cstage]<=1; complete(); end
    WAIT_DRAIN: begin
     if(drain_valid && drain_ready) drain_sent<=1;
     if(drain_done_v_q) begin
      if(drain_bad_q) refuse();
      else begin reader_count<=reader_count-1'b1; reader_live[row]<=0; complete(); end
     end
    end
   endcase
  end
 end
endmodule
