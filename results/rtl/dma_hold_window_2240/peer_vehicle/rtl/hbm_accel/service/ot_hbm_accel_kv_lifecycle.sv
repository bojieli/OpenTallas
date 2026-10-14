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
 // 2026-10-04 1.2 GHz restructure (hbm-clock-loops), closes 0.833 ns SS 60 ps / FF 25 ps routed.
 // Exactness rules kept from the original: the same checks, the same write order inside an edge,
 // the same response/sector order, sector data/addresses and sector issue intervals. Timing structure:
 //  * one-hot state; the small control registers are computed by one next-state block;
 //  * every large register group (the 72-row table, staging/capture bytes, payload receipts,
 //    sector bitmaps, writer record) is enabled by an AND of a few current-state flops; wide
 //    fan-outs read keep-attributed copies (row-table enables per 9 rows, write data per 18 rows);
 //  * command ports are sampled unconditionally (cin_*, plus four row-group copies) and moved by
 //    one flop (acc_q copies);
 //  * the command snapshot is per row: the sampling edge registers each row's tag/position
 //    compares, SNAP2 combines them with the row record into one refusal bit per row and CHECK
 //    selects one bit (+1 edge per command), instead of muxing a 164-bit row word to the centre;
 //  * completion events compare identity/position per row the same way and register the whole
 //    event check on the stage-2 -> 3 edge;
  //  * the STAGE readback compare is registered per 32-bit chunk (+1 edge per STAGE);
 //  * sector request data/address come from registers (a beat shift register and a precomputed
 //    address), so the payload request outputs are flop-driven through one lane mux.
 localparam BEGIN=0, STAGE=1, COMMIT=2, PUBLISH=3, ACQUIRE=4, CONSUMER=5, RELEASE=6;
 localparam IDLE=0, WRITE=1, WRITE_ACK=2, READ=3, READ_ACK=4, WAIT_COMMIT=5,
            WAIT_PUBLISH=6, WAIT_CONSUMER=7, WAIT_DRAIN=8, SNAP=9,
            LOAD=10, LOAD_ACK=11, OLD_REQ=12, OLD_ACK=13, NEW_REQ=14, NEW_ACK=15,
            CHECK=16, ACT=17, READ_CHK=18, SNAP2=19;
 localparam NS=20;
 localparam [NS-1:0] ONE=1;
 reg [NS-1:0] st;
 reg [6:0] reader_count;
 reg [8:0] sector_cursor; reg [271:0] cur_oh; reg [255:0] old_sector;
 reg [8:0] sc_d;     // datapath copy of sector_cursor (addresses, byte select), own incrementer
 reg c_lt256, c_lt255, c_last, c_cont; // flags of the current sector_cursor
 reg receipt_visible, receipt_reverse;
 // == sector_cursor<256 ? sector_cursor>>5 : 8+((sector_cursor-256)>>1) for every cursor value 0..271
 wire [3:0] wanted_beat=sector_cursor[8] ? {1'b1,sector_cursor[3:1]} : {1'b0,sector_cursor[7:5]};
 reg writer_live, commit_sent, drain_sent;
 reg [63:0] w_identity; reg [19:0] w_key; reg [9:0] stage_base, incoming_base;
 reg [33:0] K_base, V_base, incoming_K, incoming_V;
 reg [4:0] stage_SM, incoming_SM;
 reg [15:0] stage_mask;
 reg [271:0] visible_mask, reverse_mask;
 reg vis_all, rev_all; // == &visible_mask, &reverse_mask (updated with the masks)
 reg [1:0] metadata_mask;
 reg [2:0] op; reg [63:0] ident, seq; reg [19:0] key;
 reg [64*4-1:0] ident_tg; reg [13*4-1:0] pos_tg; // row-table write-data copies of ident / key[12:0], per 18 rows
 reg [63:0] producer; reg [10:0] pc; reg cstage;
 reg [3:0] beat; reg [511:0] stage_data;
 // Row table, packed by row.
 reg [71:0] pub_valid, reader_live;
 reg [13*72-1:0] pub_pos, reader_pos;
 reg [64*72-1:0] pub_tag, reader_tag;
 reg [2*72-1:0] consumer_mask, consumer_reverse_mask, responded_mask, reader_metadata_mask;

 function [71:0] row_onehot(input [19:0] k);
  integer r;
  begin for(r=0;r<72;r=r+1) row_onehot[r]=({k[19:14],k[13]}==7'(r)); end
 endfunction
 function [1:0] sel2(input [2*72-1:0] v, input [71:0] oh);
  integer r;
  begin sel2=0; for(r=0;r<72;r=r+1) sel2=sel2|(v[r*2+:2]&{2{oh[r]}}); end
 endfunction
 function [3:0] cursor_flags(input [8:0] c); // {lt256, lt255, last, cont}
  cursor_flags={c<256, c<255, c==271, (c<255 && c[4:0]!=31) || (c>=256 && c[0]==0)};
 endfunction

 reg [71:0] row_select;
 reg [71:0] bad_row;   // per-row snapshot refusal for the sampled op (BEGIN/ACQUIRE/CONSUMER/RELEASE)
 reg s_any;            // port/writer-record refusal of the sampled command
 reg go_ref; wire rd_bad_q; // STAGE readback refusal (OR of rd_part, below)

 // ---------------- active (exact copies of ENABLE && run_en_q && !fault) ----------------
 reg run_en_q, wc_ok_q;
 reg act_c, act_t, act_e, act_w; // control / row table / events / wide groups
 wire active=act_c;

 // Command ports are sampled every edge (cin_*); acc_q moves the accepted copy one edge later.
 // Every SNAP stint begins with acc_q=1 (SNAP is entered only by acceptance); the snapshot is
 // taken on that edge from cin_* and nothing it reads changes while SNAP is held (paused).
 reg acc_q; reg [3:0] acc_sd; // acc_sd: copies for the 512-bit staging load
 reg [11:0] acc_x;    // more copies of acc_q: [0] command fields, [1] ident, [2] key/pos, [3+g] ident_tg/pos_tg group g, [7+g] snapshot group g
 reg [2:0] cin_op; reg [63:0] cin_ident, cin_seq, cin_producer; reg [19:0] cin_key; reg [10:0] cin_pc;
 reg [12:0] cin_km1;
 // Four row-group copies (rows 18g..18g+17) of the sampled fields the per-row snapshot compares read.
 reg [64*4-1:0] cid_g, cpr_g; reg [13*4-1:0] ckey_g, ckm1_g;
 for(genvar g=0;g<4;g=g+1) begin:cin_grp
  for(genvar i=0;i<64;i=i+1) begin:b64
   (* keep *) always @(posedge clk) cid_g[g*64+i]<=cmd_identity[i];
   (* keep *) always @(posedge clk) cpr_g[g*64+i]<=cmd_producer[i];
  end
  for(genvar i=0;i<13;i=i+1) begin:b13
   (* keep *) always @(posedge clk) ckey_g[g*13+i]<=cmd_key[i];
  end
  (* keep *) always @(posedge clk) ckm1_g[g*13+:13]<=cmd_key[12:0]-1'b1;
 end
 reg cin_cstage; reg [3:0] cin_beat; reg [511:0] cin_stage_data; reg [9:0] cin_base; reg [4:0] cin_SM;
 reg [33:0] cin_K, cin_V; reg [71:0] cin_rowsel; reg cin_sc, cin_sb;
 always @(posedge clk) begin
  cin_op<=cmd_op; cin_ident<=cmd_identity; cin_key<=cmd_key; cin_seq<=cmd_sequence;
  cin_producer<=cmd_producer; cin_pc<=cmd_PC; cin_cstage<=cmd_consumer; cin_beat<=cmd_stage_beat;
  cin_stage_data<=cmd_stage_data; cin_base<=cmd_stage_base; cin_SM<=cmd_stage_SM; cin_K<=cmd_K_base; cin_V<=cmd_V_base;
  cin_rowsel<=row_onehot(cmd_key); cin_km1<=cmd_key[12:0]-1'b1;
  // Port-only parts of the common and BEGIN checks.
  cin_sc<=({cmd_key[19:14],cmd_key[13]}>=72 || cmd_PC>=1737 || cmd_op>RELEASE);
  cin_sb<=(cmd_stage_base>1008 || cmd_K_base[4:0]!=0 || cmd_V_base[4:0]!=0
       || {1'b0,cmd_K_base}+35'd4194304>35'h400000000
       || {1'b0,cmd_V_base}+35'd4194304>35'h400000000
       || (cmd_K_base<cmd_V_base ? cmd_V_base-cmd_K_base<4194304 : cmd_K_base-cmd_V_base<4194304));
 end
 wire acc_now = cmd_valid && cmd_ready;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin
   row_select<=0; op<=0; key[19:13]<=0; seq<=0; producer<=0; pc<=0; cstage<=0;
   incoming_base<=0; incoming_SM<=0; incoming_K<=0; incoming_V<=0;
  end else begin
   if(acc_x[0]) begin
    row_select<=cin_rowsel; op<=cin_op; key[19:13]<=cin_key[19:13];
    seq<=cin_seq; producer<=cin_producer; pc<=cin_pc; cstage<=cin_cstage;
    incoming_base<=cin_base; incoming_SM<=cin_SM; incoming_K<=cin_K; incoming_V<=cin_V;
   end
  end
 end

 // Completion events keep their original ready, are captured on the accepting edge, and are
 // checked and applied from registered copies (per-row compares, then one selected bit).
 reg payload_v_q, payload_wide_bad_q;
 reg metadata_v_q, metadata_wide_bad_q;
 reg metadata_record_q;
 reg consumer_v_q;
 reg [63:0] consumer_identity_q;
 reg [19:0] consumer_key_q;
 reg consumer_stage_q, consumer_accepted_q, consumer_reverse_q;
 reg reader_metadata_v_q;
 reg [63:0] reader_metadata_identity_q;
 reg [19:0] reader_metadata_key_q;
 reg reader_metadata_stage_q;
 reg drain_done_v_q, drain_bad_q;
 reg hydrate_v_q;
 reg [19:0] hydrate_key_q;
 reg [63:0] hydrate_producer_q;
 reg [71:0] c1_oh, m1_oh, h1_oh;
 // Four row-group copies of the event identity/position for the per-row compares.
 reg [64*4-1:0] cev_id_g, mev_id_g; reg [13*4-1:0] cev_pos_g, mev_pos_g;
 for(genvar g=0;g<4;g=g+1) begin:ev_grp
  for(genvar i=0;i<64;i=i+1) begin:b64
   (* keep *) always @(posedge clk) cev_id_g[g*64+i]<=consumer_identity[i];
   (* keep *) always @(posedge clk) mev_id_g[g*64+i]<=reader_metadata_identity[i];
  end
  for(genvar i=0;i<13;i=i+1) begin:b13
   (* keep *) always @(posedge clk) cev_pos_g[g*13+i]<=consumer_key[i];
   (* keep *) always @(posedge clk) mev_pos_g[g*13+i]<=reader_metadata_key[i];
  end
 end
 reg [33:0] expected_payload_addr;
 // Registered request address: addr(c) for the current cursor. addr(c+1) and addr(0) are precomputed every
 // edge; the cursor never moves on two edges less than three apart, and the bases/key only change at BEGIN.
 function [33:0] sector_addr(input [8:0] c, input [33:0] kb, input [33:0] vb, input [12:0] k);
  sector_addr = !c[8] ? kb + {12'd0, c[7:6], k[12:4], c[5:0], 5'd0} : vb + {12'd0, c[3:2], k[12:0], c[1:0], 5'd0};
 endfunction
 reg [33:0] addr_q, addr_n1, addr_0;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin addr_q<=0; addr_n1<=0; addr_0<=0; end
  else begin
   addr_n1<=sector_addr(sc_d+1'b1, K_base, V_base, w_key[12:0]);
   addr_0<=sector_addr(9'd0, K_base, V_base, w_key[12:0]);
   if(w_adv) addr_q<=addr_n1; else if(cm_q && commit_ready) addr_q<=addr_0;
  end
 end
 // K: K_base + (((c>>6)*512 + (key>>4))*128 + (c&63)*2)*16, V: V_base + (((c-256)>>2)*8192 + key)*128 + ((c-256)&3)*32;
 // the offset fields do not overlap, so each is one add of a concatenation (c<256 resp. 256<=c<=271).
 wire [33:0] expected_K_addr=K_base + {12'd0, sc_d[7:6], w_key[12:4], sc_d[5:0], 5'd0};
 wire [33:0] expected_V_addr=V_base + {12'd0, sc_d[3:2], w_key[12:0], sc_d[1:0], 5'd0};
 always @(posedge clk) begin
  expected_payload_addr <= sc_d<256 ? expected_K_addr : expected_V_addr;
  metadata_record_q <= metadata_record;
  consumer_identity_q <= consumer_identity;
  consumer_key_q <= consumer_key;
  consumer_stage_q <= consumer_stage;
  consumer_accepted_q <= consumer_accepted;
  consumer_reverse_q <= consumer_reverse;
  reader_metadata_identity_q <= reader_metadata_identity;
  reader_metadata_key_q <= reader_metadata_key;
  reader_metadata_stage_q <= reader_metadata_stage;
  hydrate_key_q <= hydrate_key;
  hydrate_producer_q <= hydrate_producer;
  c1_oh <= row_onehot(consumer_key);
  m1_oh <= row_onehot(reader_metadata_key);
  h1_oh <= row_onehot(hydrate_key);
 end
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin payload_v_q<=0; payload_wide_bad_q<=0; metadata_v_q<=0; metadata_wide_bad_q<=0; consumer_v_q<=0; reader_metadata_v_q<=0; drain_done_v_q<=0; drain_bad_q<=0; hydrate_v_q<=0; end
  else begin
   payload_v_q <= payload_valid && payload_ready;
   payload_wide_bad_q <= payload_identity!=w_identity || payload_key!=w_key || payload_sector!=sector_cursor
       || payload_source_addr!=expected_payload_addr;
   metadata_v_q <= metadata_valid && metadata_ready;
   metadata_wide_bad_q <= metadata_identity!=w_identity || metadata_key!=w_key;
   consumer_v_q <= consumer_valid && consumer_ready;
   reader_metadata_v_q <= reader_metadata_valid && reader_metadata_ready;
   drain_done_v_q <= drain_done_valid && drain_done_ready;
   drain_bad_q <= drain_done_identity!=ident || drain_done_key!=key || drain_done_allcopies!=8'hff;
   hydrate_v_q <= hydrate_valid && hydrate_ready;
  end
 end

 wire [6:0] event_row={consumer_key_q[19:14],consumer_key_q[13]};
 wire [6:0] reader_metadata_row={reader_metadata_key_q[19:14],reader_metadata_key_q[13]};
 wire [6:0] hydrate_row={hydrate_key_q[19:14],hydrate_key_q[13]};

 // Row-indexed event stage 2 (per-row identity/position compares, row record bits) and stage 3
 // (selected compare bits; masks read with the acting stage's same-row update forwarded); stage 3 acts.
 reg c2_v, c2_bad_row, c2_live, c2_stage, c2_acc, c2_rev; reg [6:0] c2_row; reg [71:0] c2_oh, c2_tne, c2_pne;
 reg m2_v, m2_bad_row, m2_live, m2_stage; reg [6:0] m2_row; reg [71:0] m2_oh, m2_tne, m2_pne;
 reg c3_bad, m3_bad;
 reg c3_v, c3_bad_row, c3_live, c3_tag_ne, c3_pos_ne, c3_stage, c3_acc, c3_rev; reg [6:0] c3_row; reg [71:0] c3_oh; reg [1:0] c3_cm, c3_crm;
 reg m3_v, m3_bad_row, m3_live, m3_tag_ne, m3_pos_ne, m3_stage; reg [6:0] m3_row; reg [71:0] m3_oh; reg [1:0] m3_resp, m3_rmm;
 wire c_fwd = c3_v && c3_row == c2_row;
 wire m_fwd = m3_v && m3_row == m2_row;
 reg h2_v, h2_bad_row, h2_live, h2_pubv; reg [6:0] h2_row; reg [71:0] h2_oh; reg [12:0] h2_pos; reg [63:0] h2_producer;
 wire [71:0] consumer_mask_lo, consumer_mask_hi, reverse_mask_lo, reverse_mask_hi;
 for(genvar r=0;r<72;r=r+1) begin:mask_cols
  assign consumer_mask_lo[r]=consumer_mask[2*r]; assign consumer_mask_hi[r]=consumer_mask[2*r+1];
  assign reverse_mask_lo[r]=consumer_reverse_mask[2*r]; assign reverse_mask_hi[r]=consumer_reverse_mask[2*r+1];
 end
 // Stage-3 mask views and the whole event check, registered on the stage-2 -> 3 edge.
 wire [1:0] c3_cm_d = sel2(consumer_mask, c2_oh) | ((c_fwd && c3_acc) ? (2'b01 << c3_stage) : 2'b00);
 wire [1:0] c3_crm_d = sel2(consumer_reverse_mask, c2_oh) | ((c_fwd && c3_rev) ? (2'b01 << c3_stage) : 2'b00);
 wire c_bad_d = c2_bad_row || !c2_live || |(c2_tne & c2_oh) || |(c2_pne & c2_oh)
       || (!c2_acc && !c2_rev)
       || (c2_acc && c3_cm_d[c2_stage])
       || (c2_rev && c3_crm_d[c2_stage])
       || (c2_rev && !c2_acc && !c3_cm_d[c2_stage])
       || (c2_stage && !(c3_cm_d[0] && c3_crm_d[0]));
 wire [1:0] m3_resp_d = sel2(responded_mask, m2_oh);
 wire [1:0] m3_rmm_d = sel2(reader_metadata_mask, m2_oh) | (m_fwd ? (2'b01 << m3_stage) : 2'b00);
 wire m_bad_d = m2_bad_row || !m2_live || |(m2_tne & m2_oh) || |(m2_pne & m2_oh)
       || !m3_resp_d[m2_stage]
       || m3_rmm_d[m2_stage]
       || (m2_stage && !m3_rmm_d[0]);
 wire h2_bad_row_d = hydrate_row >= 72;
 wire h2_live_d = |(reader_live & h1_oh);
 wire h2_pubv_d = |(pub_valid & h1_oh) | (h2_v && h2_row == hydrate_row);
 // Per-row compares (event identity/position against each row's reader record).
 for(genvar r=0;r<72;r=r+1) begin:row_cmp
  always @(posedge clk) begin
   c2_tne[r] <= reader_tag[r*64+:64] != cev_id_g[(r/18)*64+:64];
   c2_pne[r] <= reader_pos[r*13+:13] != cev_pos_g[(r/18)*13+:13];
   m2_tne[r] <= reader_tag[r*64+:64] != mev_id_g[(r/18)*64+:64];
   m2_pne[r] <= reader_pos[r*13+:13] != mev_pos_g[(r/18)*13+:13];
  end
 end
 always @(posedge clk) begin
  wc_ok_q <= cstage ? |(row_select & consumer_mask_hi & reverse_mask_hi) : |(row_select & consumer_mask_lo & reverse_mask_lo);
  c2_row <= event_row; c2_bad_row <= event_row >= 72; c2_oh <= c1_oh;
  c2_live <= |(reader_live & c1_oh);
  c2_stage <= consumer_stage_q; c2_acc <= consumer_accepted_q; c2_rev <= consumer_reverse_q;
  c3_row <= c2_row; c3_oh <= c2_oh; c3_bad_row <= c2_bad_row; c3_live <= c2_live; c3_stage <= c2_stage;
  c3_acc <= c2_acc; c3_rev <= c2_rev; c3_tag_ne <= |(c2_tne & c2_oh); c3_pos_ne <= |(c2_pne & c2_oh);
  c3_cm <= c3_cm_d; c3_crm <= c3_crm_d; c3_bad <= c_bad_d;
  m2_row <= reader_metadata_row; m2_bad_row <= reader_metadata_row >= 72; m2_oh <= m1_oh;
  m2_live <= |(reader_live & m1_oh); m2_stage <= reader_metadata_stage_q;
  m3_row <= m2_row; m3_oh <= m2_oh; m3_bad_row <= m2_bad_row; m3_live <= m2_live; m3_stage <= m2_stage;
  m3_tag_ne <= |(m2_tne & m2_oh); m3_pos_ne <= |(m2_pne & m2_oh);
  m3_resp <= m3_resp_d; m3_rmm <= m3_rmm_d; m3_bad <= m_bad_d;
  h2_row <= hydrate_row; h2_oh <= h1_oh; h2_bad_row <= h2_bad_row_d; h2_live <= h2_live_d;
  h2_pubv <= h2_pubv_d;
  h2_pos <= hydrate_key_q[12:0]; h2_producer <= hydrate_producer_q;
 end
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin c2_v<=0; m2_v<=0; h2_v<=0; c3_v<=0; m3_v<=0; end
  else begin c2_v <= consumer_v_q; m2_v <= reader_metadata_v_q; h2_v <= hydrate_v_q; c3_v <= c2_v; m3_v <= m2_v; end
 end

 // ---------------- command snapshot (sampling edge) ----------------
 // Per row, the refusal of the sampled op against that row's record; the original snapshot
 // checks are begin_snap_bad / acq_bad (row part) / cons_bad / rel_bad.
 // SNAP (sampling edge): the wide per-row compares against the sampled fields are registered;
 // SNAP2: each row combines them with its record bits (unchanged since the sampling edge: no row
 // write can land on the two edges after an acceptance) into its refusal for the op.
 reg [71:0] f_rt, f_rp, f_pt, f_pk, f_pkm1; reg f_k0;
 always @(posedge clk or negedge por_n) if(!por_n) f_k0<=0; else if(acc_x[0]) f_k0<=cin_key[12:0]!=0;
 for(genvar r=0;r<72;r=r+1) begin:row_snap
  wire pv=pub_valid[r], rl=reader_live[r];
  wire [12:0] pp=pub_pos[r*13+:13];
  wire [63:0] g_id=cid_g[(r/18)*64+:64], g_pr=cpr_g[(r/18)*64+:64];
  wire [12:0] g_key=ckey_g[(r/18)*13+:13], g_km1=ckm1_g[(r/18)*13+:13];
  always @(posedge clk or negedge por_n) begin
   if(!por_n) begin f_rt[r]<=0; f_rp[r]<=0; f_pt[r]<=0; f_pk[r]<=0; f_pkm1[r]<=0; end
   else if(acc_x[7+r/18]) begin
    f_rt[r]<=reader_tag[r*64+:64]!=g_id; f_rp[r]<=reader_pos[r*13+:13]!=g_key;
    f_pt[r]<=pub_tag[r*64+:64]!=g_pr; f_pk[r]<=pp!=g_key; f_pkm1[r]<=pp!=g_km1;
   end
  end
  wire [1:0] rsm=responded_mask[r*2+:2];
  wire b_begin = rl || (pv ? (pp==8191 || f_pkm1[r]) : f_k0);
  wire b_acq = !pv || f_pk[r] || f_pt[r] || rl;
  wire b_cons = !rl || f_rt[r] || f_rp[r] || rsm[cstage];
  wire b_rel = !rl || f_rt[r] || f_rp[r] || !(&consumer_mask[r*2+:2]) || !(&consumer_reverse_mask[r*2+:2])
        || !(&rsm) || !(&reader_metadata_mask[r*2+:2]);
  always @(posedge clk or negedge por_n) begin
   if(!por_n) bad_row[r]<=0;
   else if(st[SNAP2]) bad_row[r] <= op==BEGIN ? b_begin : op==ACQUIRE ? b_acq :
                                    op==CONSUMER ? b_cons : op==RELEASE ? b_rel : 1'b0;
  end
 end
 // Writer-record/port checks: the wide compares are registered on the sampling edge, the
 // op-dependent combination on the SNAP2 edge (nothing they read changes in between).
 reg f_idne, f_keyne, f_rec_ne, f_sc, f_sb, f_smb;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) {f_idne,f_keyne,f_rec_ne,f_sc,f_sb,f_smb}<=0;
  else if(acc_x[0]) begin
   f_idne<=cin_ident!=w_identity; f_keyne<=cin_key!=w_key;
   f_rec_ne<=cin_base!=stage_base || cin_K!=K_base || cin_V!=V_base || cin_SM!=stage_SM;
   f_sc<=cin_sc; f_sb<=cin_sb; f_smb<=stage_mask[cin_beat];
  end
 end
 always @(posedge clk or negedge por_n) begin
  if(!por_n) s_any<=0;
  else if(st[SNAP2]) begin
   s_any <= f_sc || (op>=STAGE && op<=PUBLISH && f_rec_ne)
     || (op==BEGIN && (writer_live || f_sb))
     || (op==STAGE && (!writer_live || f_idne || f_keyne || commit_sent || f_smb || stage_base>1008))
     || (op==COMMIT && (!writer_live || f_idne || f_keyne || !(&stage_mask) || commit_sent))
     || (op==PUBLISH && (!writer_live || f_idne || f_keyne || !commit_sent))
     || (op==ACQUIRE && writer_live);
  end
 end
 wire ref_d = s_any || |(bad_row & row_select);

 // ---------------- checks ----------------
 wire h_bad = h2_bad_row || h2_live || h2_pubv;
 wire c_bad = c3_bad;
 wire m_bad = m3_bad;
 wire narrow_bad = payload_write!=st[NEW_ACK]
       || (!payload_visible && !payload_reverse)
       || (payload_visible && receipt_visible) || (payload_reverse && receipt_reverse)
       || (payload_reverse && !payload_visible && !receipt_visible);
 wire pay_acc = payload_valid && pr_i; // payload_ready (pr_q == pr_i) already includes active
 wire pay_ok = pay_acc && !narrow_bad;
 wire meta_bad = metadata_wide_bad_q
       || metadata_mask[metadata_record_q] || (metadata_record_q && !metadata_mask[0])
       || !vis_all || !rev_all;
 // Refusal sources, in the original statement order (each also gated by `active`).
 wire rf_h  = h2_v && h_bad;
 wire rf_p  = pay_acc && narrow_bad;
 wire rf_pw = payload_v_q && payload_wide_bad_q;
 wire rf_m  = metadata_v_q && meta_bad;
 wire rf_c  = c3_v && c_bad;
 wire rf_r  = m3_v && m_bad;
 wire rf_act= st[ACT] && go_ref;
 wire rf_rd = st[READ_CHK] && rd_bad_q;
 wire rf_dr = st[WAIT_DRAIN] && drain_done_v_q && drain_bad_q;
 wire any_rf = rf_h || rf_p || rf_pw || rf_m || rf_c || rf_r || rf_act || rf_rd || rf_dr;
 // Completion sources.
 wire act_go = st[ACT] && !go_ref;
 wire cp_act = act_go && (op==BEGIN || op==ACQUIRE);
 wire cp_rd  = st[READ_CHK] && !rd_bad_q;
 wire rvrr = receipt_visible && receipt_reverse;
 wire na_go = st[NEW_ACK] && rvrr;
 wire cp_new = na_go && c_last;
 wire ok_pub = metadata_mask[0] && metadata_mask[1];
 wire cp_pub = st[WAIT_PUBLISH] && ok_pub;
 wire cp_wc  = st[WAIT_CONSUMER] && wc_ok_q;
 wire dr_ok = drain_done_v_q && !drain_bad_q;
 wire cp_dr  = st[WAIT_DRAIN] && dr_ok;
 wire any_cp = cp_act || cp_rd || cp_new || cp_pub || cp_wc || cp_dr;
 wire commit_fire = commit_valid && commit_ready; // commit_valid includes active

 // ---------------- control next state ----------------
 // One-hot state: each bit is (entered) | (held and not left); the states are exclusive, so this
 // equals the original case statement. Refusals never move the state (the fault freezes it).
 reg [NS-1:0] st_e, st_x; // enter / leave terms (before `active`)
 always @* begin
  st_e=0; st_x=0;
  st_e[SNAP]=acc_now;                                   st_x[SNAP]=1'b1;
  st_e[SNAP2]=st[SNAP];                                 st_x[SNAP2]=1'b1;
  st_e[CHECK]=st[SNAP2];                                st_x[CHECK]=1'b1;
  st_e[ACT]=st[CHECK];                                  st_x[ACT]=!go_ref;
  st_e[IDLE]=(act_go && (op==BEGIN || op==ACQUIRE)) || cp_rd || cp_new || cp_pub || cp_wc || cp_dr;
  st_x[IDLE]=acc_now;
  st_e[WRITE]=act_go && op==STAGE;                      st_x[WRITE]=shared_ready;
  st_e[WRITE_ACK]=st[WRITE] && shared_ready;            st_x[WRITE_ACK]=shared_done;
  st_e[READ]=st[WRITE_ACK] && shared_done;              st_x[READ]=shared_ready;
  st_e[READ_ACK]=st[READ] && shared_ready;              st_x[READ_ACK]=shared_done;
  st_e[READ_CHK]=st[READ_ACK] && shared_done;           st_x[READ_CHK]=!rd_bad_q;
  st_e[WAIT_COMMIT]=act_go && op==COMMIT;               st_x[WAIT_COMMIT]=commit_fire;
  st_e[LOAD]=(st[WAIT_COMMIT] && commit_fire) || (na_go && !c_last && !c_cont);
  st_x[LOAD]=shared_ready;
  st_e[LOAD_ACK]=st[LOAD] && shared_ready;              st_x[LOAD_ACK]=shared_done;
  st_e[OLD_REQ]=(st[LOAD_ACK] && shared_done && c_lt256) || (na_go && !c_last && c_cont && c_lt255);
  st_x[OLD_REQ]=payload_req_ready;
  st_e[OLD_ACK]=st[OLD_REQ] && payload_req_ready;       st_x[OLD_ACK]=rvrr;
  st_e[NEW_REQ]=(st[LOAD_ACK] && shared_done && !c_lt256) || (st[OLD_ACK] && rvrr) || (na_go && !c_last && c_cont && !c_lt255);
  st_x[NEW_REQ]=payload_req_ready;
  st_e[NEW_ACK]=st[NEW_REQ] && payload_req_ready;       st_x[NEW_ACK]=rvrr;
  st_e[WAIT_PUBLISH]=act_go && op==PUBLISH;             st_x[WAIT_PUBLISH]=ok_pub;
  st_e[WAIT_CONSUMER]=act_go && op==CONSUMER;           st_x[WAIT_CONSUMER]=wc_ok_q;
  st_e[WAIT_DRAIN]=act_go && op==RELEASE;               st_x[WAIT_DRAIN]=dr_ok;
 end
 wire [NS-1:0] st_n = active ? (st_e | (st & ~st_x)) : st;
 wire rq_clr = (st[OLD_REQ] || st[NEW_REQ]) && payload_req_ready;
 wire rv_n = active ? ((receipt_visible || (pay_ok && payload_visible)) && !rq_clr) : receipt_visible;
 wire rr_n = active ? ((receipt_reverse || (pay_ok && payload_reverse)) && !rq_clr) : receipt_reverse;
 wire meta_set = metadata_v_q && !meta_bad;
 wire begin_act = act_go && op==BEGIN;
 wire [1:0] mm_n = !active ? metadata_mask : begin_act ? 2'b00 :
                   metadata_mask | (meta_set ? (2'b01 << metadata_record_q) : 2'b00);
 wire go_ref_n = (active && st[CHECK]) ? ref_d : go_ref;
 wire commit_sent_n = !active ? commit_sent : begin_act ? 1'b0 : (commit_sent || (st[WAIT_COMMIT] && commit_fire));
 wire writer_live_n = !active ? writer_live : begin_act ? 1'b1 : (writer_live && !cp_pub);
 wire drain_sent_n = !active ? drain_sent : (act_go && op==RELEASE) ? 1'b0 :
                     (drain_sent || (st[WAIT_DRAIN] && drain_valid && drain_ready));
 wire fault_n = fault || (active && any_rf);
 wire act_n = ENABLE && run_enable && !fault_n;          // == active on the next edge
 // STAGE readback compare, registered per 32-bit chunk; rd_bad_q is their OR.
 reg [15:0] rd_part;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) rd_part<=0;
  else for(integer k=0;k<16;k=k+1) if(st[READ_ACK]) rd_part[k]<=shared_rdata[k*32+:32]!=stage_data[k*32+:32];
 end
 assign rd_bad_q = |rd_part;

 // Registered outputs (exact next-cycle values).
 reg pr_q, pr_i, cm_q;   // pr_i: internal copy of payload_ready
 wire pr_d = act_n && writer_live_n && commit_sent_n && (st_n[OLD_ACK] || st_n[NEW_ACK]);
 (* keep *) always @(posedge clk or negedge por_n) if(!por_n) pr_q<=0; else pr_q<=pr_d;
 (* keep *) always @(posedge clk or negedge por_n) if(!por_n) pr_i<=0; else pr_i<=pr_d;
 always @(posedge clk or negedge por_n) if(!por_n) cm_q<=0; else cm_q<=act_n && st_n[WAIT_COMMIT] && !commit_sent_n;

 // ---------------- group enables (current-cycle flops only) ----------------
 // Each equals the original registered strobe (next-cycle active && condition) on its edge.
 // Row-table write enables per group of 9 rows: registered next values of active and of
 //   ACQUIRE: st[ACT] && !go_ref && op==ACQUIRE   PUBLISH: st[WAIT_PUBLISH] && ok_pub   hydrate: h2_v && !h_bad
 reg [7:0] act_g, acq_g, pub_g, hyd_g;
 wire [2:0] op_n = acc_q ? cin_op : op;
 for(genvar g=0;g<8;g=g+1) begin:en_grp
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) act_g[g]<=0; else act_g[g]<=act_n;
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) acq_g[g]<=0; else acq_g[g]<=st_n[ACT] && !go_ref_n && op_n==ACQUIRE;
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) pub_g[g]<=0; else pub_g[g]<=st_n[WAIT_PUBLISH] && mm_n[0] && mm_n[1];
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) hyd_g[g]<=0; else hyd_g[g]<=hydrate_v_q && !(h2_bad_row_d || h2_live_d || h2_pubv_d);
 end
 wire c_fire = act_e && c3_v && !c_bad;
 wire m_fire = act_e && m3_v && !m_bad;
 wire wc_fire = act_t && cp_wc;
 wire drn_fire = act_t && cp_dr;
 wire w_begin = act_w && st[ACT] && !go_ref && op==BEGIN;
 wire w_cap  = act_w && cp_rd;
 wire w_ld   = act_w && st[LOAD_ACK] && shared_done;
 wire w_adv  = act_w && na_go && !c_last;

 // Response load flags: the response is written one edge after its decision.
 wire rsp_busy = rsp_valid;
 assign cmd_ready=active && (!quiesce || (cmd_op!=BEGIN && cmd_op!=ACQUIRE))
    && st[IDLE] && !rsp_busy && !hydrate_valid && !hydrate_v_q && !h2_v
    && !(consumer_v_q || c2_v || c3_v || reader_metadata_v_q || m2_v || m3_v || metadata_v_q); // accepted events land first
 assign writer_retained=writer_live;
 assign writer_identity=w_identity; assign writer_key=w_key;
 assign writer_stage_base=stage_base; assign writer_stage_SM=stage_SM;
 assign shared_SM=stage_SM; assign shared_rank=w_key[13];
 assign writer_K_base=K_base; assign writer_V_base=V_base;
 assign idle=st[IDLE] && !rsp_busy && !writer_live && reader_count==0;
 assign shared_valid=active && (st[WRITE] || st[READ] || st[LOAD]);
 assign shared_write=st[WRITE];
 assign shared_addr=stage_base + (st[LOAD] || st[LOAD_ACK] ? wanted_beat : beat); assign shared_wdata=stage_data;
 assign shared_done_ready=active && (st[WRITE_ACK] || st[READ_ACK] || st[LOAD_ACK]);
 assign commit_valid=cm_q;
 assign payload_ready=pr_q;
 assign payload_req_valid=active && (st[OLD_REQ] || st[NEW_REQ]);
 assign payload_req_write=st[NEW_REQ];
 assign payload_req_sector=sc_d;
 assign payload_req_source_addr=addr_q;
 assign payload_req_rmw=sc_d<256;
 assign payload_req_rmw_last=sc_d<256 && st[NEW_REQ];
 // Sector request data, from registers through one lane mux. The original is
 //   c<256 ? (old_sector & ~mask(key)) | lo/hi bytes of stage_data[(c&31)*16+:16] at lanes key[3:0], key[3:0]+16
 //         : stage_data[(c&1)*256+:256].
 // sd_sh holds stage_data >> offset(c) while sectors are issued: it is loaded with stage_data's SRAM load
 // (offset 0: every load starts a beat) and shifted by 16 (K) / 256 (V) when the cursor advances in the beat.
 reg [511:0] sd_sh; reg [31:0] lane_lo, lane_hi;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin sd_sh<=0; lane_lo<=0; lane_hi<=0; end
  else begin
   for(integer j=0;j<16;j=j+1) begin lane_lo[j]<=w_key[3:0]==j; lane_hi[j]<=1'b0; lane_lo[j+16]<=1'b0; lane_hi[j+16]<=w_key[3:0]==j; end
   if(w_ld) sd_sh<=shared_rdata;
   else if(w_adv && c_cont) sd_sh<=c_lt256 ? sd_sh>>16 : sd_sh>>256;
  end
 end
 for(genvar j=0;j<32;j=j+1) begin:req_lane
  assign payload_req_data[j*8+:8] = sc_d[8] ? sd_sh[j*8+:8] :
         lane_lo[j] ? sd_sh[7:0] : lane_hi[j] ? sd_sh[15:8] : old_sector[j*8+:8];
 end
 assign metadata_ready=active && writer_live && commit_sent;
 assign consumer_ready=active; assign reader_metadata_ready=active;
 assign hydrate_ready=active && !quiesce && st[IDLE] && !writer_live && !rsp_busy;
 assign drain_valid=active && st[WAIT_DRAIN] && !drain_sent;
 assign drain_identity=ident; assign drain_key=key;
 assign drain_done_ready=active && st[WAIT_DRAIN] && drain_sent;


 // ---------------- fan-out copies ----------------
 // Logically identical registers, each in its own keep-attributed process so synthesis keeps
 // them apart (a keep on the wire does not stop bit-level register merging).
 (* keep *) always @(posedge clk or negedge por_n) if(!por_n) act_c<=0; else act_c<=act_n;
 (* keep *) always @(posedge clk or negedge por_n) if(!por_n) act_t<=0; else act_t<=act_n;
 (* keep *) always @(posedge clk or negedge por_n) if(!por_n) act_e<=0; else act_e<=act_n;
 (* keep *) always @(posedge clk or negedge por_n) if(!por_n) act_w<=0; else act_w<=act_n;
 (* keep *) always @(posedge clk or negedge por_n) if(!por_n) acc_q<=0; else acc_q<=acc_now;
 for(genvar q=0;q<12;q=q+1) begin:accx_cp
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) acc_x[q]<=0; else acc_x[q]<=acc_now;
 end
 for(genvar q=0;q<4;q=q+1) begin:acc_cp
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) acc_sd[q]<=0; else acc_sd[q]<=acc_now;
 end
 for(genvar i=0;i<64;i=i+1) begin:ident_cp
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) ident[i]<=0; else if(acc_x[1]) ident[i]<=cin_ident[i];
  for(genvar g=0;g<4;g=g+1) begin:tg
   (* keep *) always @(posedge clk or negedge por_n) if(!por_n) ident_tg[g*64+i]<=0; else if(acc_x[3+g]) ident_tg[g*64+i]<=cin_ident[i];
  end
 end
 for(genvar i=0;i<13;i=i+1) begin:pos_cp
  (* keep *) always @(posedge clk or negedge por_n) if(!por_n) key[i]<=0; else if(acc_x[2]) key[i]<=cin_key[i];
  for(genvar g=0;g<4;g=g+1) begin:tg
   (* keep *) always @(posedge clk or negedge por_n) if(!por_n) pos_tg[g*13+i]<=0; else if(acc_x[3+g]) pos_tg[g*13+i]<=cin_key[i];
  end
 end
 // Datapath copy of the sector cursor with its own incrementer (same updates as sector_cursor).
 always @(posedge clk or negedge por_n) begin
  if(!por_n) sc_d<=0;
  else if(w_adv) sc_d<=sc_d+1'b1;
  else if(cm_q && commit_ready) sc_d<=0;
 end

 // ---------------- row table ----------------
 // Later writes win in the original statement order (hydrate < publish; event set < ACQUIRE clear).
 for(genvar r=0;r<72;r=r+1) begin:rows
  always @(posedge clk or negedge por_n) begin
   if(!por_n) begin
    pub_valid[r]<=0; pub_pos[r*13+:13]<=0; pub_tag[r*64+:64]<=0;
    reader_live[r]<=0; reader_tag[r*64+:64]<=0; reader_pos[r*13+:13]<=0;
    consumer_mask[r*2+:2]<=0; consumer_reverse_mask[r*2+:2]<=0; responded_mask[r*2+:2]<=0; reader_metadata_mask[r*2+:2]<=0;
   end else begin
    if(act_g[r/9] && hyd_g[r/9] && h2_oh[r]) begin pub_valid[r]<=1; pub_pos[r*13+:13]<=h2_pos; pub_tag[r*64+:64]<=h2_producer; end
    if(act_g[r/9] && pub_g[r/9] && row_select[r]) begin pub_valid[r]<=1; pub_pos[r*13+:13]<=pos_tg[(r/18)*13+:13]; pub_tag[r*64+:64]<=ident_tg[(r/18)*64+:64]; end
    if(c_fire && c3_oh[r]) begin
     if(c3_acc) consumer_mask[r*2+:2]<=consumer_mask[r*2+:2] | (2'b01 << c3_stage);
     if(c3_rev) consumer_reverse_mask[r*2+:2]<=consumer_reverse_mask[r*2+:2] | (2'b01 << c3_stage);
    end
    if(m_fire && m3_oh[r]) reader_metadata_mask[r*2+:2]<=reader_metadata_mask[r*2+:2] | (2'b01 << m3_stage);
    if(act_g[r/9] && acq_g[r/9] && row_select[r]) begin
     reader_live[r]<=1; reader_tag[r*64+:64]<=ident_tg[(r/18)*64+:64]; reader_pos[r*13+:13]<=pos_tg[(r/18)*13+:13];
     consumer_mask[r*2+:2]<=0; consumer_reverse_mask[r*2+:2]<=0; responded_mask[r*2+:2]<=0; reader_metadata_mask[r*2+:2]<=0;
    end
    if(wc_fire && row_select[r]) responded_mask[r*2+:2]<=responded_mask[r*2+:2] | (2'b01 << cstage);
    if(drn_fire && row_select[r]) reader_live[r]<=0;
   end
  end
 end

 // ---------------- wide data groups ----------------
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin
   stage_data<=0; beat<=0; rsp_capture<=0; stage_mask<=0; old_sector<=0;
   visible_mask<=0; reverse_mask<=0; vis_all<=0; rev_all<=0;
   w_identity<=0; w_key<=0; stage_base<=0; K_base<=0; V_base<=0; stage_SM<=0;
   sector_cursor<=0; cur_oh<=0; {c_lt256,c_lt255,c_last,c_cont}<=0;
  end else begin
   // Staging bytes/beat: accepted command (moved by acc_q, independent of pause), SRAM load.
   if(acc_q) beat<=cin_beat;
   for(integer q=0;q<4;q=q+1) if(acc_sd[q]) stage_data[q*128+:128]<=cin_stage_data[q*128+:128];
   if(cm_q && commit_ready) beat<=0;
   if(w_ld) begin stage_data<=shared_rdata; beat<=wanted_beat; end
   if(w_cap) stage_mask[beat]<=1;
   if(w_cap) rsp_capture<=stage_data;
   // Payload receipts (payload_ready is the registered pr_q).
   if(pay_ok && payload_visible) begin
    if(st[OLD_ACK]) old_sector<=payload_rdata;
    else begin visible_mask<=visible_mask|cur_oh; vis_all<=&(visible_mask|cur_oh); end
   end
   if(pay_ok && payload_reverse && st[NEW_ACK]) begin reverse_mask<=reverse_mask|cur_oh; rev_all<=&(reverse_mask|cur_oh); end
   // Sector cursor (one-hot copy and decision flags move with it).
   if(cm_q && commit_ready) begin sector_cursor<=0; cur_oh<=272'd1; {c_lt256,c_lt255,c_last,c_cont}<=cursor_flags(9'd0); end
   if(w_adv) begin
    sector_cursor<=sector_cursor+1'b1; cur_oh<=cur_oh<<1; {c_lt256,c_lt255,c_last,c_cont}<=cursor_flags(sector_cursor+1'b1);
   end
   // Writer record (BEGIN) wins over the receipts above, as in the original order.
   if(w_begin) begin
    w_identity<=ident; w_key<=key; stage_base<=incoming_base; stage_SM<=incoming_SM; K_base<=incoming_K; V_base<=incoming_V;
    stage_mask<=0; visible_mask<=0; reverse_mask<=0; vis_all<=0; rev_all<=0;
   end
  end
 end

 // ---------------- control registers and responses ----------------
 // Responses: the original wrote refusals (event sources first, then the FSM) and completions
 // in one ordered block; the FSM sources are mutually exclusive and come last, so a completion
 // overrides an event refusal on the same edge and otherwise any refusal loads the response.
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin
   st<=ONE<<IDLE; receipt_visible<=0; receipt_reverse<=0; metadata_mask<=0; go_ref<=0;
   commit_sent<=0; writer_live<=0; drain_sent<=0; reader_count<=0;
   run_en_q<=0; fault<=0;
   rsp_valid<=0; rsp_fault<=0;
   rsp_producer<=0; rsp_consumer<=0; rsp_stage_beat<=0;
   rsp_op<=0; rsp_identity<=0; rsp_key<=0; rsp_sequence<=0; rsp_PC<=0;
  end else begin
   st<=st_n; receipt_visible<=rv_n; receipt_reverse<=rr_n; metadata_mask<=mm_n; go_ref<=go_ref_n;
   commit_sent<=commit_sent_n; writer_live<=writer_live_n; drain_sent<=drain_sent_n;
   run_en_q<=run_enable; fault<=fault_n;
   if(active) begin
    if(any_rf || any_cp) rsp_valid<=1; else if(rsp_valid && rsp_ready) rsp_valid<=0;
    if(any_cp) begin
     rsp_fault<=0; rsp_op<=op; rsp_identity<=ident; rsp_key<=key; rsp_sequence<=seq; rsp_PC<=pc;
     rsp_producer<=producer; rsp_consumer<=cstage; rsp_stage_beat<=beat;
    end else if(any_rf) begin
     rsp_fault<=1; rsp_op<=acc_q ? cin_op : op; rsp_identity<=acc_q ? cin_ident : ident; rsp_key<=acc_q ? cin_key : key;
     rsp_sequence<=acc_q ? cin_seq : seq; rsp_PC<=acc_q ? cin_pc : pc;
    end
   end
   if(active) begin
    if(cp_act && op==ACQUIRE) reader_count<=reader_count+1'b1;
    if(cp_dr) reader_count<=reader_count-1'b1;
   end
  end
 end
endmodule
