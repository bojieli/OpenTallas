`timescale 1ns/1ps
// Qwen ROM TP8 die (contract v4b, results/arch/hier_contract_1012/qwen_rom_tp8.json): slot cell of the three band result
// serialisers (slots sp_res_ser_0..2, 777.6 x 518.4), a hardened CLUSTER under its die master name.
//
// Body: the tile composition ot_qfd_res_tiles, re-cut for the floorplan (8 hard slot tiles ot_qfd_res_slot_tile + the
// serialiser head ot_qfd_res_tiles_ctl; both modules UNCHANGED).  The parent holds only registers and wires:
//   A   pin flops of i[4424:0] and me_en under the N face (every die input one flop at its pin)
//   B   second stage, one copy per tile and one for the head: the tile's 555-bit word {we, last, empty, addr, mask,
//       data} and its own {me_en, i_ov} pair.  last / empty are decoded from the eight A-stage we bits here, so no
//       logic sits behind a pin and no tile word waits on a net that spans the cluster.
//   C   third stage for the three bottom-row tiles only (N strip -> row 0 is > 300 um in one hop)
//   F   sticky tile-fault OR, registered tile to tile along the ring, then the registered fault pin
//   reset: ot_rst_relay (2 sync + 2 tree stages): region g = tile g with its own B / C strobes and fault flop, 8 = the head,
//       9 = the A strobes.  Release is 4 ck edges after the rst_n pin, the same edge everywhere.
//
// Die ports (one direction per bus; packing LSB first):
//   i  [4424:0] N in   {i_ov, i_we[7:0], i_addr[8*24-1:0], i_mask[8*16-1:0], i_data[8*512-1:0]}   i_ov = i[0]
//   o  [550:0]  E out  {o_data[511:0], o_mask[15:0], o_row[19:0], o_nul, o_end, o_v}  LSB first = o_data[0] at o[0],
//                      i.e. o = {o_v, o_end, o_nul, o_row, o_mask, o_data} in Verilog concatenation (o_v = o[550])
//   ok E out (rok), cr E in (o_cr credit), fault E out, me_en N in, rst_n N in, ck N in.
//
// Cycles (absorbed by the protocol): the head sees every burst LAT = 2 cycles later than ot_qfd_res_tiles does (A, B),
// so its ready is computed with RS + LAT: rok falls LAT bursts earlier and the engine's stopping debt of RS edges still
// fits the 64-entry store.  A tile sees its word D_g = 2 (rows 1, 2) or 3 (row 0) cycles late; the head asks slot g of
// a burst no earlier than LAT + 6 + 2 g cycles after the burst's edge and the tile's write lands D_g + 3 after it, so
// any D_g <= LAT + 3 + 2 g is safe (worst here: 3 <= 5).  Beats, their order and the 19-cycle conveyor are unchanged;
// o_* / rok / fault are registers at the pins (inside the head); cr is captured by the head's pin flop.
//
// Slot g = ring position g (slot_id strap g).  Ring order over the floorplan (column, row), every chain face on a
// tile's E side: (2,2) (1,2) (0,2) (0,1) (0,0) (1,0) (1,1) (2,0); the head is the ninth cell (2,1).
//
// OT_HARD_CHILDREN: the tiles are hard children (LEF / lib only, default parameters).  Without it (benches) the tile RTL
// is elaborated with USE_MACRO and the bench mutants (MUT = 1: one data bit of slot 1 inverted inside the tile; MUT = 2:
// the row-0 tiles' strobes bypass the C stage).
module qfd_sp_res_ser #(
    parameter integer RS        = 42,
    parameter integer CRB       = 16,
    parameter integer USE_MACRO = 1,
    parameter integer MUT       = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          me_en,
    input  wire [4424:0] i,
    output wire [550:0]  o,
    output wire          ok,
    input  wire          cr,
    output wire          fault
);
    localparam integer LAT = 2;                 // A + B in front of the head
    localparam [7:0]   ROW0 = 8'b1011_0000;     // ring positions on floorplan row 0: (0,0) = 4, (1,0) = 5, (2,0) = 7

    // ------------------------------------------------------------------ reset relay (region 8 head, 9 strobes)
    wire [9:0] rr_n;
    ot_rst_relay #(.REGIONS(10), .SYNC_STAGES(2), .TREE_STAGES(2)) u_rst (.clk(ck), .rst_n_in(rst_n), .rst_n(rr_n));

    // ------------------------------------------------------------------ A: pin flops
    reg          a_me, a_ov;
    reg  [7:0]   a_we;
    reg  [191:0] a_addr;
    reg  [127:0] a_mask;
    reg  [4095:0] a_data;
    always @(posedge ck) begin
        a_addr <= i[200:9];
        a_mask <= i[328:201];
        a_data <= i[4424:329];
        a_we   <= i[8:1];
    end
    always @(posedge ck or negedge rr_n[9]) begin
        if (!rr_n[9]) begin a_me <= 1'b0; a_ov <= 1'b0; end
        else          begin a_me <= me_en; a_ov <= i[0]; end
    end
    wire a_empty = (a_we == 8'd0);

    // ------------------------------------------------------------------ B / C: per-tile word and strobe pair
    wire [8:0]       qv, rv;
    wire [26:0]      qs;
    wire [53:0]      qp;
    wire [9*551-1:0] rd;
    wire [7:0]       sf;
    assign rv[0] = 1'b0;
    assign rd[0 +: 551] = 551'd0;

    reg b_me_h, b_ov_h;                         // the head's own copy
    always @(posedge ck or negedge rr_n[8]) begin
        if (!rr_n[8]) begin b_me_h <= 1'b0; b_ov_h <= 1'b0; end
        else          begin b_me_h <= a_me; b_ov_h <= a_ov; end
    end

    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_slot
            wire a_last = (a_we[g] && !(|(a_we >> (g + 1)))) || (g == 7 && a_we == 8'd0);
            // {data, mask, addr, empty, last, we}
            reg [554:0] b_w;
            reg         b_me, b_ov;
            always @(posedge ck)
                b_w <= {a_data[g*512 +: 512], a_mask[g*16 +: 16], a_addr[g*24 +: 24], a_empty, a_last, a_we[g]};
            always @(posedge ck or negedge rr_n[g]) begin
                if (!rr_n[g]) begin b_me <= 1'b0; b_ov <= 1'b0; end
                else          begin b_me <= a_me; b_ov <= a_ov; end
            end
            wire [554:0] t_w;
            wire         t_me, t_ov;
            if (ROW0[g]) begin : g_c
                reg [554:0] c_w;
                reg         c_me, c_ov;
                always @(posedge ck) c_w <= b_w;
                always @(posedge ck or negedge rr_n[g]) begin
                    if (!rr_n[g]) begin c_me <= 1'b0; c_ov <= 1'b0; end
                    else          begin c_me <= b_me; c_ov <= b_ov; end
                end
                // MUT == 2 (bench only): the row-0 strobes skip the C stage, so they lead their word by one cycle
                assign t_w = c_w;
                assign t_me = (MUT == 2) ? b_me : c_me;
                assign t_ov = (MUT == 2) ? b_ov : c_ov;
            end else begin : g_b
                assign t_w = b_w; assign t_me = b_me; assign t_ov = b_ov;
            end
            wire [2:0] sid = g;
`ifdef OT_HARD_CHILDREN
            ot_qfd_res_slot_tile u_t (
`else
            ot_qfd_res_slot_tile #(.USE_MACRO(USE_MACRO), .MUT(MUT == 1 && g == 1)) u_t (
`endif
                .clk(ck), .rst_n(rr_n[g]), .me_en(t_me), .i_ov(t_ov),
                .i_we(t_w[0]), .i_last(t_w[1]), .i_empty(t_w[2]),
                .i_addr(t_w[26:3]), .i_mask(t_w[42:27]), .i_data(t_w[554:43]), .slot_id(sid),
                .rq_v(qv[g]), .rq_slot(qs[g*3 +: 3]), .rq_ptr(qp[g*6 +: 6]),
                .rqf_v(qv[g+1]), .rqf_slot(qs[(g+1)*3 +: 3]), .rqf_ptr(qp[(g+1)*6 +: 6]),
                .rv(rv[g]), .rd(rd[g*551 +: 551]), .ov(rv[g+1]), .od(rd[(g+1)*551 +: 551]), .fault(sf[g]));
        end
    endgenerate

    // ------------------------------------------------------------------ head (ninth cell): control + output pin flops
    wire         cf;
    wire         o_v, o_end, o_nul;
    wire [19:0]  o_row;
    wire [15:0]  o_mask;
    wire [511:0] o_data;
    ot_qfd_res_tiles_ctl #(.RS(RS + LAT), .CRB(CRB)) u_ctl (
        .clk(ck), .rst_n(rr_n[8]), .me_en(b_me_h), .i_ov(b_ov_h), .o_cr(cr),
        .rv(rv[8]), .rd(rd[8*551 +: 551]),
        .rq_v(qv[0]), .rq_slot(qs[0 +: 3]), .rq_ptr(qp[0 +: 6]),
        .o_v(o_v), .o_end(o_end), .o_nul(o_nul), .o_row(o_row), .o_mask(o_mask), .o_data(o_data),
        .rok(ok), .fault(cf));
    assign o = {o_v, o_end, o_nul, o_row, o_mask, o_data};

    // ------------------------------------------------------------------ F: tile faults, registered along the ring
    wire [8:0] fq;
    assign fq[0] = 1'b0;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_f
            reg f;
            always @(posedge ck or negedge rr_n[g]) begin
                if (!rr_n[g]) f <= 1'b0;
                else          f <= fq[g] | sf[g];
            end
            assign fq[g+1] = f;
        end
    endgenerate
    reg fault_q;
    always @(posedge ck or negedge rr_n[8]) begin
        if (!rr_n[8]) fault_q <= 1'b0;
        else          fault_q <= fault_q | fq[8] | cf;
    end
    assign fault = fault_q;
endmodule
