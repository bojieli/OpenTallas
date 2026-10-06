`timescale 1ns/1ps
// Actual consumer and registered masked tile-slice endpoint. All producer
// wires are typed external ports; this module has no producer, PHY or reset
// injection mechanism. The unchanged service owns transaction/debt checks.
module ot_qwen_p0_linked_consumer #(
    parameter integer NSTK=4, NPC=128, KV_IDEAL=0, WBW=4
)(
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
    output wire hd_v, h_go,
    input wire hd_rdy,
    output wire [18:0] hd_row,
    output wire [10:0] hd_n,
    input wire [NPC-1:0] hl_v, hw_room, hwd_v,
    output wire [NPC-1:0] hl_pop, hw_v,
    input wire [NPC*17-1:0] hl_sec,
    input wire [NPC*8-1:0] hl_row,
    input wire [NPC*256-1:0] hl_data,
    output wire [NPC*256-1:0] hw_data,
    output wire [NPC*24-1:0] hw_sec,
    output wire [NPC*9-1:0] hw_tag,
    input wire [NPC*9-1:0] hwd_tag,
    output wire [6:0] join_debt
);
    localparam integer NT=1536;
    initial if(NSTK!=4 || NPC!=128 || KV_IDEAL!=0 || WBW!=4)
        $fatal(1,"linked consumer requires actual 4-stack/128-PC real KV shape");
    wire [NT-1:0] kvw_ce;
    wire [NT*7-1:0] kvw_addr;
    wire [NT*512-1:0] kvw_data, kvw_mask;
    wire svc_fault; wire [15:0] svc_code;
    assign fault=svc_fault;
    assign fault_code=svc_code;
    assign join_debt=7'($countones(u_svc.w_valid));
    ot_qwen_rt_kv_stream4_service #(.NSTK(NSTK), .NPC(NPC), .KV_IDEAL(KV_IDEAL), .WBW(WBW)) u_svc (
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
endmodule
