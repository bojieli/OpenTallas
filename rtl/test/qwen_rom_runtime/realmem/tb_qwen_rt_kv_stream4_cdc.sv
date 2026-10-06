`timescale 1ns/1ps
// CDC variant (same module name; compile ONE of the bench tops): the backend is ot_qwen_hbm_stream4_cdc
// (the same 4-stack controllers, DRAM checker and backing array, on an EXTERNAL periodic hclk input,
// every per-PC crossing the hardened gray-pointer element ot_qwen_stream4_cdc_pc), driven by
// tb_qwen_rt_kv_stream4.cpp built with -DCDC (hclk period KVB_HFS fs, phase KVB_HPHASE fs).
// Standalone bench top (Verilator, driven by tb_qwen_rt_kv_stream4.cpp): the 4-stack KV service
// ot_qwen_rt_kv_stream4_service and ot_qwen_hbm_stream4_ack (NSTK stacks, 32 * NSTK PCs), with the
// kv_free / early_go / posted_wb straps as inputs.  Derived from tb_qwen_rt_kv_stream.sv:
// the HBM_STREAM KV
// service (ot_qwen_rt_kv_stream_service) and the streaming HBM (ot_qwen_hbm_stream_ack: the
// near-HBM stream controller + DRAM checker, write-done), and the 1,536 tiles' KV slices as
// behavioural registered-port memories (the hardened tile's kvw_* register, then the
// masked SRAM write).  The C++ host preloads HBM, writes token K/V like the stream unit,
// and checks every slice word and the written-back HBM sectors against an independent map.
module tb_qwen_rt_kv_stream4 #(
    parameter integer NSTK = 4,
    parameter integer NPC = 32 * NSTK,
    parameter integer KV_IDEAL = 0,
    parameter integer LAYERS = 2,
    parameter integer WBW = 1,
    parameter integer PHASE = 0,
    parameter integer PULLIN = 0,
    parameter integer PROTECTED = 0,
    parameter integer SYNC = 2,
    parameter integer RSEL = 0,
    parameter integer RNG = 10,
    parameter integer KV_MAP = 0,          // option-M stripe (service and HBM)
    parameter integer KV_MAP_HBM = -1,     // negative control: HBM map differing from the service's (-1: = KV_MAP)
    parameter integer CDC_MARGIN = 0,      // ot_qwen_stream4_cdc_pc MARGIN + receiver landing queue
    parameter integer CDC_NEG = 0          // negative control: MARGIN element, no receiver queue
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [17:0]       pos,
    input  wire [7:0]        layer,
    input  wire [7:0]        nx_layer,
    input  wire [17:0]       pos_hint,
    input  wire              kv_free,
    input  wire              early_go,
    input  wire              posted_wb,
    output wire              wb_busy,
    input  wire              kvd_v,
    input  wire [17:0]       kvd_pos,
    output wire              kv_ok,
    input  wire [63:0]       kv_we,
    input  wire [64*24-1:0]  kv_waddr,
    input  wire [64*32-1:0]  kv_wdata,
    output wire              kv_write_drained,
    output wire              fault,
    output wire [15:0]       fault_code,
    output wire [31:0]       st_fill_cycles, st_fill_sectors, st_wr_sectors, st_rsp_stall,
    output wire [31:0]       st_kvok_low_desc, st_drain_low, st_wr_lat_max, st_fill_exposed,
    input  wire              hclk
);
    localparam integer NT = 1536;
    wire [NT-1:0] kvw_ce; wire [NT*7-1:0] kvw_addr; wire [NT*512-1:0] kvw_data, kvw_mask;
    wire hd_v, hd_rdy, h_go; wire [18:0] hd_row; wire [10:0] hd_n;
    wire [NPC-1:0] hl_v, hl_pop, hw_v, hw_room, hwd_v;
    wire [NPC*17-1:0] hl_sec; wire [NPC*8-1:0] hl_row; wire [NPC*256-1:0] hl_data, hw_data;
    wire [NPC*24-1:0] hw_sec; wire [NPC*9-1:0] hw_tag, hwd_tag;
    wire svc_fault, hbm_fault; wire [15:0] svc_code, hbm_code;
    ot_qwen_rt_kv_stream4_service #(.NSTK(NSTK), .NPC(NPC), .KV_IDEAL(KV_IDEAL), .WBW(WBW), .KV_MAP(KV_MAP)) u_svc (
        .clk(clk), .rst_n(rst_n), .start(start), .ideal_in(1'b0), .pos(pos), .layer(layer),
        .nx_layer(nx_layer), .pos_hint(pos_hint),
        .kv_free(kv_free), .early_go_in(early_go), .posted_wb_in(posted_wb), .wb_busy(wb_busy),
        .kvd_v(kvd_v), .kvd_pos(kvd_pos), .kvd_kindk(1'b0), .kv_ok(kv_ok),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .kv_write_drained(kv_write_drained),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask),
        .d_v(hd_v), .d_rdy(hd_rdy), .d_row(hd_row), .d_n(hd_n), .go(h_go),
        .l_v(hl_v), .l_sec(hl_sec), .l_row(hl_row), .l_data(hl_data), .l_pop(hl_pop),
        .w_v(hw_v), .w_sec(hw_sec), .w_data(hw_data), .w_tag(hw_tag), .w_room(hw_room), .wd_v(hwd_v), .wd_tag(hwd_tag),
        .fault(svc_fault), .fault_code(svc_code), .st_fill_cycles(st_fill_cycles), .st_fill_sectors(st_fill_sectors),
        .st_wr_sectors(st_wr_sectors), .st_rsp_stall(st_rsp_stall), .st_kvok_low_desc(st_kvok_low_desc),
        .st_drain_low(st_drain_low), .st_wr_lat_max(st_wr_lat_max), .st_fill_exposed(st_fill_exposed));
    ot_qwen_hbm_stream4_cdc #(.NSTK(NSTK), .NPC(NPC), .MEM_WORDS(LAYERS * 131072), .TAGW(9), .PHASE(PHASE), .PULLIN(PULLIN),
        .PROTECTED(PROTECTED), .SYNC(SYNC), .RSEL(RSEL), .RNG(RNG), .KV_MAP(KV_MAP_HBM < 0 ? KV_MAP : KV_MAP_HBM),
        .CDC_MARGIN(CDC_MARGIN), .CDC_NEG(CDC_NEG)) u_hbm (
        .clk(clk), .rst_n(rst_n), .warm_rst_n(1'b1), .hclk(hclk), .d_v(hd_v), .d_rdy(hd_rdy), .d_row(hd_row), .d_n(hd_n), .go(h_go),
        .l_v(hl_v), .l_sec(hl_sec), .l_row(hl_row), .l_data(hl_data), .l_pop(hl_pop),
        .w_v(hw_v), .w_sec(hw_sec), .w_data(hw_data), .w_tag(hw_tag), .w_room(hw_room), .wd_v(hwd_v), .wd_tag(hwd_tag),
        .fault(hbm_fault), .fault_code(hbm_code));
    assign fault = svc_fault | hbm_fault;
    assign fault_code = svc_code | (hbm_fault ? 16'h8000 : 16'h0);
    // tile slices: the hardened tile's registered kvw port, then the masked write
    reg [511:0] slice [0:NT-1][0:127] /*verilator public_flat_rw*/;
    reg [NT-1:0] ce_q; reg [6:0] a_q [0:NT-1]; reg [511:0] d_q [0:NT-1]; reg [511:0] m_q [0:NT-1];
    integer i;
    always @(posedge clk) begin
        for (i = 0; i < NT; i = i + 1) begin
            ce_q[i] <= rst_n && kvw_ce[i];
            if (kvw_ce[i]) begin a_q[i] <= kvw_addr[i*7 +: 7]; d_q[i] <= kvw_data[i*512 +: 512]; m_q[i] <= kvw_mask[i*512 +: 512]; end
            if (ce_q[i]) slice[i][a_q[i]] <= (slice[i][a_q[i]] & ~m_q[i]) | (d_q[i] & m_q[i]);
        end
    end
`ifdef KVTRACE
    // landing trace for the die landing-crossbar study (qfd_kvc): every accepted landed beat with the cycle it
    // was first offered (CDC l_v), the cycle it was accepted, the PC and its slice writes' tiles (1 K, 2 V halves)
    integer kv_fd = 0; integer kv_cyc = 0; reg [NPC-1:0] kv_wait = 0; integer kv_first [0:NPC-1];
    string kv_fn;
    initial begin
        if (!$value$plusargs("kvtrace=%s", kv_fn)) kv_fn = "kvtrace.txt";
        kv_fd = $fopen(kv_fn, "a");
    end
    always @(posedge clk) begin
        kv_cyc <= kv_cyc + 1;
        if (kv_fd != 0) for (int p = 0; p < NPC; p++) begin
            if (u_svc.l_v[p] && !kv_wait[p]) begin kv_wait[p] = 1'b1; kv_first[p] = kv_cyc; end
            if (u_svc.l_v[p] && u_svc.l_pop[p]) begin
                $fwrite(kv_fd, "%0d %0d %0d %0d %0d %0d\n", kv_cyc, kv_first[p], p,
                        u_svc.b_n[p], u_svc.b_tile[p][0], u_svc.b_tile[p][1]);
                kv_wait[p] = 1'b0;
            end
        end
    end
`endif
endmodule
