// Generated opt-in candidate by tools/qwen_static_kv/qc_dcal_rom/build_rtl.py.
module ot_qwen_d2d_ovl_seq_image64 #(parameter string IMAGE_VIAMAP = "", parameter string IMAGE_INSTANCE = "qc_dcal_image",
    parameter integer MUT_HALT_REWIND = 0, // bench-only old mid-list restart behavior
    parameter integer NE = 32,
    parameter integer AW = 11,           // list ROM address width (2,048 words: one 4-user frame is 1,703 a list)
    parameter [31:0]      TX_SEG1 = '0,  // segment-1 bases (token head); ADM = 1: the admission bases first
    parameter [31:0]      RX_SEG1 = '0,
    parameter integer ADM = 0,
    parameter [31:0]      TX_SEG2 = '0,
    parameter [31:0]      RX_SEG2 = '0,
    parameter integer ADM_OFS = 72,
    parameter integer ADM_LEN = 1100,
    parameter integer FIRST_OFS = 1176,  // anchor edge of the start lists, edges after the anchored epoch strobe
    parameter integer EP_SKEW = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          reload,
    input  wire          epoch_go,
    input  wire          halt,
    output wire          cfg_tx_we,
    output wire          cfg_rx_we,
    output wire [5:0]    cfg_addr,
    output wire [31:0]   cfg_data,
    output wire          cal_start,
    output wire          cal_seg,
    output wire          cal_start_rx,
    output wire          cal_seg_rx,
    output wire [1:0]    cal_user_tx,
    output wire [1:0]    cal_user_rx,
    output wire [AW-1:0] tx_rom_addr,
    input  wire [31:0]   tx_rom_q,
    output wire [AW-1:0] rx_rom_addr,
    input  wire [31:0]   rx_rom_q,
    output wire          cal_ready,
    output wire          adm_done,
    output wire          running,
    output reg           fault
);
    localparam integer E_GO = EP_SKEW + FIRST_OFS;
    wire s_start, s_seg, s_run, s_fault, s_ready, s_adm;
    ot_qwen_d2d_cal_seq_image64 #(.IMAGE_VIAMAP(IMAGE_VIAMAP), .IMAGE_INSTANCE(IMAGE_INSTANCE), .NE(NE), .NL(1), .TX_SEG1(TX_SEG1), .RX_SEG1(RX_SEG1),
        .START('0), .ADM(ADM), .TX_SEG2(TX_SEG2), .RX_SEG2(RX_SEG2), .ADM_OFS(ADM_OFS), .ADM_LEN(ADM_LEN), .AUTO(0),
        .EP_SKEW(EP_SKEW)) u_seq (
        .ck(ck), .rst_n(rst_n), .reload(reload), .tok_go(1'b0), .epoch_go(epoch_go), .halt(halt),
        .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .cal_start(s_start), .cal_seg(s_seg), .cal_ready(s_ready), .running(s_run), .layer(), .adm_done(s_adm),
        .tok_start(), .fault(s_fault));
    assign cal_ready = s_ready;
    assign adm_done = s_adm;
    // anchor: the epoch strobe's rising edge + E_GO edges (the same absolute edge on both dies)
    reg ep_q, act; reg [31:0] e;
    wire go = act && e == E_GO;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin ep_q <= 1'b0; act <= 1'b0; e <= 32'd0; end
        else begin
            ep_q <= epoch_go;
            if (halt) act <= 1'b0;
            else if (epoch_go && !ep_q) begin act <= 1'b1; e <= 32'd1; end
            else if (act) begin e <= e + 32'd1; if (go) act <= 1'b0; end
        end
    wire t_start, t_seg, r_start, r_seg, t_run, r_run, t_f, r_f; wire [1:0] t_u, r_u;
    ot_qwen_d2d_list_play #(.AW(AW), .MUT_HALT_REWIND(MUT_HALT_REWIND)) u_tx (.ck(ck), .rst_n(rst_n), .go(go), .halt(halt | reload), .rom_addr(tx_rom_addr),
        .rom_q(tx_rom_q), .start(t_start), .seg(t_seg), .user(t_u), .running(t_run), .fault(t_f));
    ot_qwen_d2d_list_play #(.AW(AW), .MUT_HALT_REWIND(MUT_HALT_REWIND)) u_rx (.ck(ck), .rst_n(rst_n), .go(go), .halt(halt | reload), .rom_addr(rx_rom_addr),
        .rom_q(rx_rom_q), .start(r_start), .seg(r_seg), .user(r_u), .running(r_run), .fault(r_f));
    assign cal_start    = s_start | t_start;
    assign cal_seg      = s_start ? s_seg : t_seg;
    assign cal_start_rx = s_start | r_start;
    assign cal_seg_rx   = s_start ? s_seg : r_seg;
    assign cal_user_tx  = s_start ? 2'd0 : t_u;
    assign cal_user_rx  = s_start ? 2'd0 : r_u;
    assign running = s_run | t_run | r_run;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else if (s_fault || t_f || r_f || (s_start && (t_start || r_start)) || (go && (!s_ready || !s_adm || t_run || r_run)))
            fault <= 1'b1;
endmodule
