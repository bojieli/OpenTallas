`timescale 1ns/1ps
// =====================================================================================================================
// qfd_sys_face -- Qwen3-8B TP8 split COMPUTE-die system face (Q-NETLIST, 2026-10-16).  Die master under its die name.
//
// Why: the strict die port-bind of the compute die (r2b2, 10-15) left 69 functional inputs with no producer on the die:
// the static D2D end's configuration / calendar start / STATUS+RESULT / program-record ports, the native59 service's HOST
// context and compiled slots, the embedding provider's row words, the sequencer's dh face and the TT's pw / kok / kwd /
// fab.  Every one of them is produced here by real hardware from real sources; nothing is tied and no reference data is
// injected.  Static cycle schedule (owner 10-14 18:59): every production event comes from a compiler image played by a
// fixed calendar; observations only fault, they never choose or stretch a cycle.  Run anchor: the forwarded epoch strobe
// (KV-die bump); the first token starts a compiled number of edges after it, later tokens back-to-back at the compiled
// token period, so both dies' sequencers stay aligned without any per-token handshake (Q-NETLIST/Q-LINK 10-16).
//
// Blocks (all synchronous to ck, one root):
//   * CONFIG ROM: one ot_rom_4096x72_m8 mask ROM (38.0 x 62.9 um), the compiler image tools/qwen_split/sys_face_image.py:
//       rows 0..1031       the installed program image, one 64-b word per row: PW0..1023 then DW0..7 ([71:64] = 0)
//       rows 2048..4095    boot records {target4 [71:68], addr8 [67:60], 28'd0, data32 [31:0]}; target
//                          3 token calendar T, 4 layer calendar L, 5 embedding calendar E, 6 first-token offset (edges
//                          after the epoch strobe), 15 END; addr8 = {seg1-base flag, entry7}.  The D2D calendars are the
//                          constants of qfd_d2d_cal_seq (Q-LINK), instantiated here as their only producer.  Any other target or a nonzero reserved
//                          field faults.
//   * BOOT (initialisation mode, explicit): after reset the boot records are replayed one per edge into the three face
//     calendars and the first-token offset, until END -> boot_done.
//   * PROGRAM REPLAY (initialisation mode): a HOST kind-13 BEGIN then AUTH accepted by the record port replays rows
//     0..1031 one per edge: PW i -> TT pw and the sequencer dh pw field (the TT and SU program copies, observed by their
//     own consumed-write ledgers in the record port), DW j -> dh dw field.  The HOST AUTH digest must match what the two
//     ledgers actually observed; the kind-14 witness reports it (qfd_program_record_port, existing RTL, unchanged).
//   * CALENDARS: three ot_qwen_d2d_cal engines (the Q-LINK calendar RTL, unchanged): T (NE 64, per token), L (NE 32,
//     per decode layer, started by T), E (NE 16, embedding row, started by T).  Event {port3 = class, kind4|beat5 = arg9}:
//       class 0 STAGE   T only: h_start pulse, stage = arg[5:0]; arg[6] L-calendar start (a decode layer; layers 2..36
//                       must coincide with qfd_d2d_cal_seq's cal_start seg 0, layer 1 = L0 rides the token run);
//                       arg[7] token run (E start; must coincide with cal_start seg 1); arg[8] RESULT capture (result_v from the
//                       sequencer's dc at this edge; s_done must be high)
//       class 5 MARK    T only: arg[6] / arg[7] as STAGE, without an h_start (e.g. the token-run start: the embedding
//                       stage's h_start follows once the row has landed)
//       class 1 LEVEL   kok = arg[0], kwd = arg[1] (compiled KV-ok / KV-write-drained levels), arg[2] token END (T)
//       class 2 QSLOT   native q_slot, q_slot_beat = arg[4:0] (bursts)
//       class 3 KVSLOT  native kv_word_slot, kv_word_index = arg[1:0]
//       class 4 VIS     native visibility_slot (arg[0] = 0) / complete_slot (arg[0] = 1)
//       class 6 EMBW    embedding expected word slot, word = arg[5:0]; arg[6] = the scale slot
//       class 7 FILL    embedding fill_begin
//     Two calendars driving one class on one edge, a class outside its calendar, or a nonzero unused arg bit fault.
//   * TOKEN LOOP: T (and the D2D sequencer, same go) starts first_ofs edges after the epoch strobe, then on its own END
//     event (back-to-back compiled token period); a go without boot / cal_ready / installed program faults, it never
//     waits.  The HOST context (kind 12) arrives in every token run before stage 0.  The token register takes the HOST
//     context's token / position on a context receive and the sequencer's argmax result (dc ntok, pos + 1) at the RESULT
//     capture; dh tp_token / tp_pos and the embedding fill / expected token come from it.
//   * EMBEDDING ROW RX (D2D port 2, kinds 6/7 code words, kind 8 row header): record layout (defined here, the KV-die
//     embedding provider owes the same): code word = {token18 [547:530], word6 [529:524], 12'd0, code512}; header =
//     {token18, 6'd0, 12'd0, 464'd0, epoch16 [47:32], 16'd0, scale16 [15:0]}.  The header arrives first; its actual token
//     / epoch identify the row; every code word's actual token must equal it.  One register edge.
//   * STATUS / RESULT (D2D kind 15): real sources only -- the sequencer dc {rom_fault, kv_write_flush, coll_busy,
//     core_fault, s_fault, s_done, ntok, nval}, the collective's cmd_free, the constant-ROM groups' fault codes, the
//     calendar state.  fab = registered OR of the die's open fault outputs (collective, D2D, native59, result-train
//     issue, this face).
// Added cycles: boot / program replay are initialisation; a calendar event of compiled cycle c reaches its consumer pin
// c edges after the edge that samples the calendar start (dt edges + the face output register; sys_face_image.py
// CAL_OUT_EDGES = 1).  EMB words: +1 edge (decode register) on the D2D emb_rx_v edge.
// MUT (bench only): 1 = T events one edge late, 2 = embedding word index off by one, 3 = PW replay skips row 7.
// =====================================================================================================================
module qfd_sys_face #(
    parameter integer MUT = 0,
    parameter integer GO_OFS = 3,              // qfd_d2d_cal_seq go-path edges = the T image's token-run cycle (sys_face_image.GO_OFS)
    parameter [20*36-1:0] START_ADJ = '0,
    parameter ROM_VIAMAP = "",
    parameter ROM_INSTANCE = "sys_face_cfg"
) (
    input  wire          ck,
    input  wire          rst_n,
    // ---------------- static D2D end (qfd_d2d_static) ----------------
    output wire          cfg_tx_we,
    output wire          cfg_rx_we,
    output wire [5:0]    cfg_addr,
    output wire [31:0]   cfg_data,
    output wire          cal_start,
    output wire          cal_seg,
    input  wire          fwd_epoch,            // forwarded epoch strobe (package bump from the KV die): the run anchor
    input  wire [547:0]  rx_payload,
    input  wire          prog_rx_v,
    input  wire          prog_witness_slot,
    input  wire          prog_auth_slot,
    input  wire          prog_context_slot,
    output wire          prog_tx_observed_v,
    output wire [547:0]  prog_tx_record,
    input  wire          emb_rx_v,
    input  wire          emb_rx_slot,
    input  wire          d2d_fault,
    input  wire          d2d_epoch_abort,
    output reg  [15:0]   status_epoch16,
    output reg           vm_drained,
    output reg           collective_drained,
    output reg           collective_busy,
    output reg           crom_fault,
    output reg           execution_active,
    output reg           admit_ready,
    output reg           result_v,
    output reg           result_done,
    output reg           result_fault,
    output reg  [3:0]    result_cause,
    output reg  [58:0]   result_tag,
    output reg  [1:0]    result_gen,
    output reg  [17:0]   result_token,
    output reg  [31:0]   result_value,
    output reg  [31:0]   result_cycles,
    // ---------------- ROM sequencer (qfd_seq_su_static) ----------------
    input  wire [55:0]   seq_dc,
    input  wire [75:0]   seq_program_obs,
    input  wire [68:0]   seq_descriptor_obs,
    input  wire          seq_cfg_image_ready,
    output reg  [186:0]  seq_dh,
    // ---------------- ME controller (qfd_tt_ctlm_static_s) ----------------
    input  wire [75:0]   tt_program_obs,
    input  wire          tt_control_stores_ready,
    input  wire          tt_layer_context_v,
    input  wire [5:0]    tt_command_stage,
    input  wire [17:0]   tt_native_tok,
    input  wire [17:0]   tt_native_pos,
    output reg  [74:0]   tt_pw,
    output reg           tt_kok,
    output reg           tt_kwd,
    output reg           tt_fab,
    // ---------------- native59 service ----------------
    output wire          host_epoch_valid,
    output wire          host_fused_capability,
    output wire [15:0]   host_epoch,
    output wire [58:0]   host_tag,
    output wire [1:0]    host_generation,
    output reg           q_slot,
    output reg  [4:0]    q_slot_beat,
    output reg           kv_word_slot,
    output reg  [1:0]    kv_word_index,
    output reg           visibility_slot,
    output reg           complete_slot,
    input  wire          native_fault,
    // ---------------- embedding provider (qfd_embedding_word_provider) ----------------
    output reg           emb_word_v,
    output reg  [511:0]  emb_word_data,
    output reg  [17:0]   emb_word_token,
    output reg  [5:0]    emb_word_index,
    output reg           emb_word_scale,
    output reg  [15:0]   emb_word_epoch,
    output reg           emb_expected_slot,
    output reg  [17:0]   emb_expected_token,
    output reg  [5:0]    emb_expected_word,
    output reg           emb_expected_scale,
    output reg  [15:0]   emb_expected_epoch,
    output reg           emb_fill_begin,
    output reg  [17:0]   emb_fill_token,
    output reg  [15:0]   emb_fill_epoch,
    output reg  [15:0]   emb_core_epoch,
    // ---------------- fault / status sources ----------------
    input  wire          io_cmd_free,
    input  wire          io_fault,
    input  wire          io_shared_fault,
    input  wire [15:0]   crom_fault_code,      // 8 constant-ROM groups x 2 b
    input  wire          res_issue_fault,
    output wire          fault
);
    // ================================================================ config ROM
    localparam [11:0] BOOT_BASE = 12'd2048;
    localparam integer PW_ROWS = 1024, IMG_ROWS = 1032;
    reg  [11:0] rom_a;
    reg         rom_ce;
    wire [71:0] rom_q;
    ot_rom_4096x72_m8 #(.VIAMAP(ROM_VIAMAP), .INSTANCE(ROM_INSTANCE)) u_rom (.clk(ck), .ce_in(rom_ce), .addr_in(rom_a), .rd_out(rom_q));

    // ================================================================ boot / program replay
    // Read pipeline: issue registers (rom_ce / rom_a + iss_*) at edge k, the macro samples at k+1, rom_q is decoded at
    // k+2 (rd_*).  One row per edge.
    localparam [2:0] S_RST = 3'd0, S_BOOT = 3'd1, S_IDLE = 3'd2, S_PROG = 3'd3, S_ARM = 3'd4;
    reg  [2:0]  st;
    reg         boot_done;
    reg         iss_boot, iss_prog, rd_boot, rd_prog;
    reg  [10:0] iss_idx, rd_idx, pidx;
    reg         boot_fault, prog_fault;
    wire        begin_v, rp_auth_v;
    wire [3:0]  b_tgt  = rom_q[71:68];
    wire [7:0]  b_addr = rom_q[67:60];
    wire        b_res  = |rom_q[59:32];
    reg         t_we, l_we, e_we;
    reg  [7:0]  c_addr;
    reg  [31:0] c_data;
    reg  [31:0] first_ofs;                     // compiled edges from the epoch strobe to the first token start
    reg  [142:0] dh_prog;                      // {dw_v, dw_addr3, dw_data64, pw_v, pw_addr10, pw_data64}
    reg  [43:0]  dh_run;                       // {kv_write_drained, h_start, stage6, tp_token18, tp_pos18}
    always @* seq_dh = {dh_prog, dh_run};
    wire        any_running;
    wire        boot_row = rd_boot && st == S_BOOT;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_RST; rom_ce <= 1'b0; rom_a <= 12'd0; iss_boot <= 1'b0; iss_prog <= 1'b0; rd_boot <= 1'b0; rd_prog <= 1'b0;
            iss_idx <= 11'd0; rd_idx <= 11'd0; pidx <= 11'd0; boot_done <= 1'b0; boot_fault <= 1'b0; prog_fault <= 1'b0;
            first_ofs <= 32'd0;
            t_we <= 1'b0; l_we <= 1'b0; e_we <= 1'b0; c_addr <= 8'd0; c_data <= 32'd0;
            tt_pw <= 75'd0; dh_prog <= 143'd0;
        end else begin
            rd_boot <= iss_boot; rd_prog <= iss_prog; rd_idx <= iss_idx;
            iss_boot <= 1'b0; iss_prog <= 1'b0; rom_ce <= 1'b0;
            t_we <= 1'b0; l_we <= 1'b0; e_we <= 1'b0;
            tt_pw[74] <= 1'b0; dh_prog[142] <= 1'b0; dh_prog[74] <= 1'b0;
            case (st)
                S_RST:  begin st <= S_BOOT; pidx <= 11'd0; end
                S_BOOT: begin
                    // stream the boot rows from BOOT_BASE until the END row is decoded
                    if (!boot_row || b_tgt != 4'd15) begin
                        rom_ce <= 1'b1; rom_a <= BOOT_BASE + {1'b0, pidx}; iss_boot <= 1'b1; pidx <= pidx + 11'd1;
                        if (pidx == 11'h7ff) boot_fault <= 1'b1;            // the table runs off the ROM without END
                    end
                    if (boot_row) begin
                        if (b_tgt == 4'd15) begin
                            st <= S_IDLE; boot_done <= 1'b1; pidx <= 11'd0;
                            if (b_res || b_addr != 8'd0 || rom_q[31:0] != 32'd0) boot_fault <= 1'b1;
                        end else begin
                            if (b_res) boot_fault <= 1'b1;
                            c_addr <= b_addr; c_data <= rom_q[31:0];
                            case (b_tgt)
                                // D2D calendars: written by qfd_d2d_cal_seq (single producer), not by this ROM
                                4'd6: begin first_ofs <= rom_q[31:0]; if (b_addr != 8'd0 || rom_q[31:0] == 32'd0) boot_fault <= 1'b1; end
                                4'd3: begin t_we <= 1'b1; if (b_addr[6]) boot_fault <= 1'b1; end
                                4'd4: begin l_we <= 1'b1; if (b_addr[6:5] != 2'd0) boot_fault <= 1'b1; end
                                4'd5: begin e_we <= 1'b1; if (b_addr[6:4] != 3'd0) boot_fault <= 1'b1; end
                                default: boot_fault <= 1'b1;
                            endcase
                        end
                    end
                end
                S_IDLE: begin
                    if (begin_v) begin
                        st <= S_ARM; pidx <= 11'd0;
                        if (any_running) prog_fault <= 1'b1;               // BEGIN while a token runs
                    end
                    if (rp_auth_v) prog_fault <= 1'b1;                      // AUTH without BEGIN
                end
                S_ARM: begin                                                // the ledgers take writes only after AUTH
                    if (begin_v) prog_fault <= 1'b1;
                    if (rp_auth_v) st <= S_PROG;
                end
                S_PROG: begin
                    if (begin_v || rp_auth_v) prog_fault <= 1'b1;           // second BEGIN / AUTH during the replay
                    if (pidx != IMG_ROWS[10:0]) begin
                        rom_ce <= 1'b1; iss_prog <= 1'b1; iss_idx <= pidx;
                        rom_a <= {1'b0, (MUT == 3 && pidx == 11'd7) ? pidx + 11'd1 : pidx};
                        pidx <= pidx + 11'd1;
                    end else if (!iss_prog && !rd_prog) st <= S_IDLE;
                end
            endcase
            if (begin_v && (st == S_BOOT || st == S_RST)) prog_fault <= 1'b1;
            // program row decode: PW i -> TT pw + dh pw (both program copies), DW j -> dh dw
            if (rd_prog) begin
                if (rom_q[71:64] != 8'd0) prog_fault <= 1'b1;
                if (rd_idx < PW_ROWS[10:0]) begin
                    tt_pw <= {1'b1, rd_idx[9:0], rom_q[63:0]};
                    dh_prog[74] <= 1'b1; dh_prog[73:64] <= rd_idx[9:0]; dh_prog[63:0] <= rom_q[63:0];
                end else begin
                    dh_prog[142] <= 1'b1; dh_prog[141:139] <= rd_idx[2:0]; dh_prog[138:75] <= rom_q[63:0];
                end
            end
        end
    end
    wire prog_busy = (st == S_PROG) || (st == S_ARM) || iss_prog || rd_prog;

    // ================================================================ program record port (existing RTL)
    wire        rp_program_ready, rp_fault;
    wire        rp_commit_v, rp_cap;
    wire [15:0] rp_begin_epoch, rp_auth_epoch, rp_program_epoch;
    wire [10:0] rp_expected_pw; wire [3:0] rp_expected_dw; wire [63:0] rp_auth_digest, rp_program_digest;
    wire        rp_tx_v;
    reg         t_running_q;
    qfd_program_record_port u_record (
        .ck(ck), .rst_n(rst_n), .auth_slot(prog_auth_slot), .context_slot(prog_context_slot), .witness_slot(prog_witness_slot),
        .rx_v(prog_rx_v), .rx_record(rx_payload), .execution_active(l_run),
        .program_obs2({seq_program_obs, tt_program_obs}), .descriptor_obs(seq_descriptor_obs),
        .cfg_image_ready({seq_cfg_image_ready, tt_control_stores_ready}),
        .head_context_v(tt_layer_context_v), .head_stage(tt_command_stage), .head_token(tt_native_tok), .head_position(tt_native_pos),
        .begin_v(begin_v), .auth_v(rp_auth_v), .begin_epoch(rp_begin_epoch), .auth_epoch(rp_auth_epoch),
        .expected_pw(rp_expected_pw), .expected_dw(rp_expected_dw), .auth_digest(rp_auth_digest),
        .program_ready(rp_program_ready), .installed_fusedcap(rp_cap), .commit_v(rp_commit_v),
        .program_epoch(rp_program_epoch), .program_digest(rp_program_digest),
        .host_epoch_valid(host_epoch_valid), .host_epoch(host_epoch), .host_tag(host_tag), .host_gen(host_generation),
        .tx_v(rp_tx_v), .tx_observed_v(prog_tx_observed_v), .tx_record(prog_tx_record), .fault(rp_fault));
    assign host_fused_capability = rp_cap;

    // ================================================================ calendars
    wire halt = d2d_epoch_abort;
    wire        t_go, l_go, ecal_go;
    wire        t_ev, l_ev, e_ev, t_run, l_run, e_run, t_cf, l_cf, e_cf;
    wire [2:0]  t_p, l_p, e_p; wire [3:0] t_k, l_k, e_k; wire [4:0] t_b, l_b, e_b;
    ot_qwen_d2d_cal #(.NE(64)) u_cal_t (.ck(ck), .rst_n(rst_n), .cfg_we(t_we), .cfg_addr({c_addr[7], c_addr[5:0]}), .cfg_data(c_data),
        .start(t_go), .start_seg(1'b0), .halt(halt), .ev_v(t_ev), .ev_port(t_p), .ev_kind(t_k), .ev_beat(t_b), .running(t_run), .fault(t_cf));
    ot_qwen_d2d_cal #(.NE(32)) u_cal_l (.ck(ck), .rst_n(rst_n), .cfg_we(l_we), .cfg_addr({c_addr[7], c_addr[4:0]}), .cfg_data(c_data),
        .start(l_go), .start_seg(1'b0), .halt(halt), .ev_v(l_ev), .ev_port(l_p), .ev_kind(l_k), .ev_beat(l_b), .running(l_run), .fault(l_cf));
    ot_qwen_d2d_cal #(.NE(16)) u_cal_e (.ck(ck), .rst_n(rst_n), .cfg_we(e_we), .cfg_addr({c_addr[7], c_addr[3:0]}), .cfg_data(c_data),
        .start(ecal_go), .start_seg(1'b0), .halt(halt), .ev_v(e_ev), .ev_port(e_p), .ev_kind(e_k), .ev_beat(e_b), .running(e_run), .fault(e_cf));
    assign any_running = t_run | l_run | e_run | t_running_q;
    // D2D link calendars: the Q-LINK sequencer (compiler images as constants) is the ONLY producer of the link end's
    // cfg_* / cal_start / cal_seg; its token start is this face's t_go; reload = the first epoch strobe after an epoch
    // abort (the HOST's recovery: the images are re-written before the new epoch's first token, first_ofs > 2 NE + 2).
    wire cal_ready, cs_running, cs_fault, cs_adm_done; wire [5:0] cs_layer;   // r2: admission run once per epoch (D2D_ADM_OFS after fwd_epoch)
    qfd_d2d_cal_seq #(.GO_OFS(GO_OFS), .START_ADJ(START_ADJ)) u_cseq (.ck(ck), .rst_n(rst_n),
        .reload(fwd_epoch && !fe_q && aborted), .tok_go(t_go), .epoch_go(fwd_epoch), .halt(halt),
        .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .cal_start(cal_start), .cal_seg(cal_seg), .cal_ready(cal_ready), .running(cs_running), .layer(cs_layer), .adm_done(cs_adm_done), .tok_start(), .fault(cs_fault));
    // bench mutant 1: T events one edge late
    reg t_ev_d; reg [2:0] t_p_d; reg [3:0] t_k_d; reg [4:0] t_b_d;
    always @(posedge ck) begin t_ev_d <= t_ev; t_p_d <= t_p; t_k_d <= t_k; t_b_d <= t_b; end
    wire       te = (MUT == 1) ? t_ev_d : t_ev;
    wire [2:0] tp = (MUT == 1) ? t_p_d : t_p;
    wire [8:0] ta = (MUT == 1) ? {t_k_d, t_b_d} : {t_k, t_b};
    wire [8:0] la = {l_k, l_b}, ea = {e_k, e_b};
    // decoded events (combinational from the calendar registers; registered at the outputs)
    wire ev_stage = te && tp == 3'd0;
    wire ev_mark  = te && tp == 3'd5;            // run start without an h_start
    wire ev_lay   = (ev_stage | ev_mark) && ta[6];  // L calendar start (layer 1 = L0 inside the token run)
    wire ev_tok   = (ev_stage | ev_mark) && ta[7];
    wire ev_res   = ev_stage && ta[8];
    wire ev_tlev  = te && tp == 3'd1;
    wire ev_llev  = l_ev && l_p == 3'd1;
    wire ev_end   = ev_tlev && ta[2];
    wire ev_q     = l_ev && l_p == 3'd2;
    wire ev_kv    = l_ev && l_p == 3'd3;
    wire ev_vis   = l_ev && l_p == 3'd4;
    wire ev_embw  = e_ev && e_p == 3'd6;
    wire ev_fill  = e_ev && e_p == 3'd7;
    assign l_go = ev_lay;
    assign ecal_go = ev_tok;
    // class placement / argument checks
    wire t_bad = te && ((tp >= 3'd2 && tp != 3'd5) || ((tp == 3'd0 || tp == 3'd5) && ta[6] && ta[7]) ||
                        (tp == 3'd1 && ta[8:3] != 0) || (tp == 3'd5 && (ta[8] || ta[5:0] != 0 || !(ta[6] || ta[7]))));
    reg  cal_exp, seg_exp;
    wire l_bad = l_ev && (l_p == 3'd0 || l_p >= 3'd5 || (l_p == 3'd1 && la[8:2] != 0) || (l_p == 3'd2 && la[8:5] != 0) ||
                          (l_p == 3'd3 && la[8:2] != 0) || (l_p == 3'd4 && la[8:1] != 0));
    wire e_bad = e_ev && (e_p < 3'd6 || (e_p == 3'd6 && ea[8:7] != 0) || (e_p == 3'd6 && ea[6] && ea[5:0] != 0) ||
                          (e_p == 3'd7 && ea != 0));
    wire lev_clash = ev_tlev && ev_llev;

    // ================================================================ token loop
    reg  [17:0] tok, pos;
    reg  [31:0] tcyc;
    reg         armed_fault;
    wire        face_fault;
    // Anchor: the first token starts first_ofs edges after the forwarded epoch strobe (both dies count from the same
    // strobe, so their token starts align without a per-token handshake); every later token starts on the edge of the
    // token calendar's END (the compiled token period).  A go that finds the program not installed faults (no wait).
    reg  [31:0] ecnt; reg ewait, fe_q;
    wire        e_go = ewait && ecnt == 32'd1;
    wire        loop_go = ev_end && !halt;
    assign t_go = (e_go || loop_go) && !face_fault;
    reg         go_fault, aborted;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) aborted <= 1'b0; else if (halt) aborted <= 1'b1; else if (fwd_epoch && !fe_q) aborted <= 1'b0;
    reg ctx_slot_q; reg [1:0] tstart_q;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            t_running_q <= 1'b0; tok <= 18'd0; pos <= 18'd0; tcyc <= 32'd0; ctx_slot_q <= 1'b0; armed_fault <= 1'b0; tstart_q <= 2'd0;
            ecnt <= 32'd0; ewait <= 1'b0; fe_q <= 1'b0; go_fault <= 1'b0;
        end else begin
            ctx_slot_q <= prog_context_slot;
            tstart_q <= {tstart_q[0], t_go};
            fe_q <= fwd_epoch;
            if (fwd_epoch && !fe_q) begin                            // epoch strobe: (re)arm the first-token count
                ewait <= 1'b1; ecnt <= first_ofs;
                if (!boot_done || first_ofs == 32'd0) go_fault <= 1'b1;
            end else if (ewait) begin ecnt <= ecnt - 32'd1; if (ecnt == 32'd1) ewait <= 1'b0; end
            if (t_go && (!boot_done || !cal_ready || !rp_program_ready || prog_busy)) go_fault <= 1'b1;
            if (e_go && t_running_q) go_fault <= 1'b1;
            if (t_go) begin t_running_q <= 1'b1; tcyc <= 32'd0; end
            else begin
                if (ev_end || halt) t_running_q <= 1'b0;
                if (t_running_q) tcyc <= tcyc + 32'd1;
            end
            if (ev_end && t_run) armed_fault <= 1'b1;                // END must be the token calendar's last entry
            if (t_running_q && !t_run && !ev_end && !t_go && !halt && tstart_q == 2'd0) armed_fault <= 1'b1;   // T stopped without END
            // context receive (record port registers it one edge after the slot): HOST token / position
            if (ctx_slot_q && host_epoch_valid) begin tok <= host_tag[36:19]; pos <= {5'd0, host_tag[18:6]}; end
            else if (ev_res) begin tok <= seq_dc[49:32]; pos <= pos + 18'd1; end
        end
    end

    // ================================================================ event outputs (registered)
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            cal_exp <= 1'b0; seg_exp <= 1'b0; dh_run <= 44'd0; tt_kok <= 1'b0; tt_kwd <= 1'b0;
            q_slot <= 1'b0; q_slot_beat <= 5'd0; kv_word_slot <= 1'b0; kv_word_index <= 2'd0;
            visibility_slot <= 1'b0; complete_slot <= 1'b0;
            emb_expected_slot <= 1'b0; emb_expected_word <= 6'd0; emb_expected_scale <= 1'b0; emb_expected_token <= 18'd0;
            emb_expected_epoch <= 16'd0; emb_fill_begin <= 1'b0; emb_fill_token <= 18'd0; emb_fill_epoch <= 16'd0;
            emb_core_epoch <= 16'd0;
        end else begin
            // the D2D sequencer's start must coincide with this calendar's layer / token-run flag (layer 1 = L0 rides the
            // token run): the two compiler images cannot drift apart unnoticed
            cal_exp <= ev_tok | (ev_lay && ta[5:0] != 6'd1); seg_exp <= ev_tok;
            dh_run[42] <= ev_stage; dh_run[41:36] <= ev_stage ? ta[5:0] : dh_run[41:36];
            dh_run[35:18] <= tok; dh_run[17:0] <= pos;
            if (ev_tlev) begin tt_kok <= ta[0]; tt_kwd <= ta[1]; end
            else if (ev_llev) begin tt_kok <= la[0]; tt_kwd <= la[1]; end
            dh_run[43] <= ev_tlev ? ta[1] : ev_llev ? la[1] : tt_kwd;
            q_slot <= ev_q; q_slot_beat <= ev_q ? la[4:0] : 5'd0;
            kv_word_slot <= ev_kv; kv_word_index <= ev_kv ? la[1:0] : 2'd0;
            visibility_slot <= ev_vis && !la[0]; complete_slot <= ev_vis && la[0];
            emb_expected_slot <= ev_embw; emb_expected_scale <= ev_embw && ea[6];
            emb_expected_word <= ev_embw ? ea[5:0] : 6'd0;
            emb_expected_token <= tok; emb_expected_epoch <= host_epoch;
            emb_fill_begin <= ev_fill; emb_fill_token <= tok; emb_fill_epoch <= host_epoch;
            emb_core_epoch <= host_epoch;
        end
    end

    // ================================================================ embedding row RX (D2D port 2, kinds 6/7/8)
    reg         row_v; reg [17:0] row_tok; reg [15:0] row_ep; reg emb_fault;
    wire [17:0] r_tok  = rx_payload[547:530];
    wire [5:0]  r_word = rx_payload[529:524];
    wire        r_hdr  = rx_payload[511:48] == 464'd0 && rx_payload[31:16] == 16'd0 && r_word == 6'd0;
    // the D2D end presents the compiled kind of the RX slot with the record; port 2 carries only EMB rows and the
    // compute die's own STATUS is TX-only, so the header is told apart from code words by the compiled E slot
    wire        is_hdr = ev_embw && ea[6];
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            emb_word_v <= 1'b0; emb_word_scale <= 1'b0; emb_word_index <= 6'd0; emb_word_token <= 18'd0; emb_word_epoch <= 16'd0;
            row_v <= 1'b0; row_tok <= 18'd0; row_ep <= 16'd0; emb_fault <= 1'b0;
        end else begin
            emb_word_v <= emb_rx_v;
            if (emb_rx_v !== emb_rx_slot) emb_fault <= 1'b1;
            if (emb_rx_v) begin
                if (rx_payload[523:512] != 12'd0) emb_fault <= 1'b1;
                if (is_hdr) begin
                    if (!r_hdr) emb_fault <= 1'b1;
                    row_v <= 1'b1; row_tok <= r_tok; row_ep <= rx_payload[47:32];
                    emb_word_scale <= 1'b1; emb_word_index <= 6'd0; emb_word_token <= r_tok; emb_word_epoch <= rx_payload[47:32];
                end else begin
                    if (!row_v || r_tok != row_tok) emb_fault <= 1'b1;
                    emb_word_scale <= 1'b0; emb_word_index <= (MUT == 2) ? r_word + 6'd1 : r_word;
                    emb_word_token <= r_tok; emb_word_epoch <= row_ep;
                end
            end
            if (emb_fill_begin) row_v <= 1'b0;
        end
    end
    always @(posedge ck) emb_word_data <= is_hdr ? {496'd0, rx_payload[15:0]} : rx_payload[511:0];

    // ================================================================ STATUS / RESULT (D2D kind 15) + fab
    reg cal_fault;
    // the sequencer's per-epoch ADMISSION start (layer 63, D2D_ADM_OFS after fwd_epoch) is not a T-calendar event;
    // every token / layer start must still coincide with the T image
    wire cal_adm = cal_start && cs_layer == 6'h3f, cal_tok = cal_start && cs_layer != 6'h3f;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            status_epoch16 <= 16'd0; vm_drained <= 1'b0; collective_drained <= 1'b0; collective_busy <= 1'b0; crom_fault <= 1'b0;
            execution_active <= 1'b0; admit_ready <= 1'b0; result_v <= 1'b0; result_done <= 1'b0; result_fault <= 1'b0;
            result_cause <= 4'd0; result_tag <= 59'd0; result_gen <= 2'd0; result_token <= 18'd0; result_value <= 32'd0;
            result_cycles <= 32'd0; tt_fab <= 1'b0; cal_fault <= 1'b0;
        end else begin
            status_epoch16 <= host_epoch;
            execution_active <= t_running_q;
            vm_drained <= !t_running_q;
            collective_busy <= seq_dc[53];
            collective_drained <= !seq_dc[53] && io_cmd_free;
            crom_fault <= seq_dc[55] | (|crom_fault_code);
            admit_ready <= boot_done && rp_program_ready && !t_running_q && !face_fault;
            result_v <= ev_res;
            if (ev_res) begin
                result_done <= seq_dc[50]; result_fault <= seq_dc[51] | seq_dc[52];
                result_cause <= {io_fault | io_shared_fault, native_fault, d2d_fault, face_fault};
                result_tag <= host_tag; result_gen <= host_generation; result_token <= seq_dc[49:32];
                result_value <= seq_dc[31:0]; result_cycles <= tcyc;
            end
            if (t_bad || l_bad || e_bad || lev_clash || (ev_res && !seq_dc[50]) || t_cf || l_cf || e_cf ||
                (ev_lay && l_run) || (ev_tok && e_run) || (t_go && !boot_done) || cs_fault ||
                cal_tok !== cal_exp || (cal_tok && cal_seg !== seg_exp) || (cal_adm && t_running_q))
                cal_fault <= 1'b1;
            tt_fab <= io_fault | io_shared_fault | d2d_fault | native_fault | res_issue_fault | face_fault;
        end
    end
    assign face_fault = boot_fault | prog_fault | cal_fault | emb_fault | rp_fault | armed_fault | go_fault;
    assign fault = face_fault;
endmodule
