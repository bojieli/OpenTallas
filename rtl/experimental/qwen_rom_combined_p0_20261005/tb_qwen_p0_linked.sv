`timescale 1ns/1ps
// Minimum actual P0 KV consumer/producer join, one layer/type, full service
// shape. Existing ot_qwen_rt_kv_stream4_service and protected R14 simulation
// provider are instantiated unchanged. This is NOT a PHY substitute, token
// inference or producer32case gate. Released P8191 data drive the one linked
// protocol case and its ACK-identity negative. Tile slices retain existing
// registered-port/masked-write semantics. No shared/source-owner RTL edits.
module tb_qwen_p0_linked #(
    parameter integer NSTK = 4,
    parameter integer NPC = 32 * NSTK,
    parameter integer KV_IDEAL = 0,
    parameter integer LAYERS = 1,
    parameter integer WBW = 4,
    parameter integer PHASE = 0,
    parameter integer PULLIN = 0,
    parameter integer PROTECTED = 0,
    parameter integer SYNC = 2
) (
    // BENCH ONLY controls, no added controller/transport or payload backing.
    input wire warm_rst_n,
    input wire hold_rows,
    input wire bad_ack_tag,
    output wire join_desc_accepted, join_go,
    output wire join_desc_committed, join_go_committed,
    output wire [127:0] join_row_valid, join_row_take, join_ack_valid, join_write_accepted,
    output wire [128*17-1:0] join_row_sec,
    output wire [128*8-1:0] join_row_layer,
    output wire [128*256-1:0] join_row_data,
    output wire [6:0] join_debt,
    output wire join_bad_ack_seen,
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
    initial if(PROTECTED!=1 || NSTK!=4 || NPC!=128 || WBW!=4 || LAYERS!=1 || PULLIN!=0 || SYNC!=2)
        $fatal(1,"linked P0 bench requires explicit protected full service shape, one actual layer");
    wire hd_v, hd_rdy, h_go; wire [18:0] hd_row; wire [10:0] hd_n;
    wire [NPC-1:0] hl_v, hl_pop, hw_v, hw_room, hwd_v;
    wire [NPC*17-1:0] hl_sec; wire [NPC*8-1:0] hl_row; wire [NPC*256-1:0] hl_data, hw_data;
    wire [NPC*24-1:0] hw_sec; wire [NPC*9-1:0] hw_tag, hwd_tag;
    wire [NPC-1:0] producer_lv, producer_pop;
    wire [NPC*9-1:0] producer_ack_tag;
    assign hl_v=producer_lv & {NPC{!hold_rows}};
    assign producer_pop=hl_pop & {NPC{!hold_rows}};
    for(genvar p=0;p<NPC;p=p+1)begin:ack_test
        // Flip the write marker at the actual consumer ACK boundary. An ACK
        // is never suppressed, synthesized or moved into a new holding queue.
        assign hwd_tag[p*9+:9]=producer_ack_tag[p*9+:9] ^ (bad_ack_tag?9'h100:9'h0);
    end
    assign join_desc_accepted=hd_v&&hd_rdy;
    assign join_go=h_go;
    assign join_row_valid=producer_lv;
    assign join_row_sec=hl_sec;
    assign join_row_layer=hl_row;
    assign join_row_data=hl_data;
    assign join_row_take=producer_pop&producer_lv;
    assign join_ack_valid=hwd_v;
    assign join_bad_ack_seen=bad_ack_tag && (|hwd_v);
    wire svc_fault, hbm_fault; wire [15:0] svc_code, hbm_code;
    ot_qwen_p0_linked_consumer #(.NSTK(NSTK),.NPC(NPC),.KV_IDEAL(KV_IDEAL),.WBW(WBW)) u_consumer (
        .clk(clk), .rst_n(rst_n), .start(start), .pos(pos),
        .layer(layer), .nx_layer(nx_layer), .pos_hint(pos_hint), .kv_free(kv_free),
        .early_go(early_go), .posted_wb(posted_wb), .wb_busy(wb_busy), .kvd_v(kvd_v),
        .kvd_pos(kvd_pos), .kv_ok(kv_ok), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .kv_write_drained(kv_write_drained), .fault(svc_fault), .fault_code(svc_code),
        .st_fill_cycles(st_fill_cycles), .st_fill_sectors(st_fill_sectors), .st_wr_sectors(st_wr_sectors), .st_rsp_stall(st_rsp_stall),
        .st_kvok_low_desc(st_kvok_low_desc), .st_drain_low(st_drain_low), .st_wr_lat_max(st_wr_lat_max), .st_fill_exposed(st_fill_exposed),
        .hd_v(hd_v), .h_go(h_go), .hd_rdy(hd_rdy), .hd_row(hd_row),
        .hd_n(hd_n), .hl_v(hl_v), .hw_room(hw_room), .hwd_v(hwd_v),
        .hl_pop(hl_pop), .hw_v(hw_v), .hl_sec(hl_sec), .hl_row(hl_row),
        .hl_data(hl_data), .hw_data(hw_data), .hw_sec(hw_sec), .hw_tag(hw_tag),
        .hwd_tag(hwd_tag), .join_debt(join_debt));
    ot_qwen_p0_producer_exports #(.NSTK(NSTK), .NPC(NPC), .LAYERS(LAYERS), .PHASE(PHASE), .PULLIN(PULLIN),
        .PROTECTED(PROTECTED), .SYNC(SYNC)) u_producer (
        .clk(clk), .rst_n(rst_n), .warm_rst_n(warm_rst_n), .hclk(hclk), .d_v(hd_v), .d_rdy(hd_rdy), .d_row(hd_row), .d_n(hd_n), .go(h_go),
        .l_v(producer_lv), .l_sec(hl_sec), .l_row(hl_row), .l_data(hl_data), .l_pop(producer_pop),
        .w_v(hw_v), .w_sec(hw_sec), .w_data(hw_data), .w_tag(hw_tag), .w_room(hw_room), .wd_v(hwd_v), .wd_tag(producer_ack_tag),
        .fault(hbm_fault), .fault_code(hbm_code),
        .join_desc_committed(join_desc_committed), .join_go_committed(join_go_committed),
        .join_write_reserved(join_write_accepted));
    assign fault = svc_fault | hbm_fault;
    assign fault_code = svc_code | (hbm_fault ? 16'h8000 : 16'h0);
endmodule
