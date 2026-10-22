`timescale 1ns/1ps
`default_nettype none
// Col8-only opt-in of the landed LAT7/DRST0 bounded native helper.
(* keep_hierarchy="yes" *) module ot_hbm_idx_tail_col8_f32 (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  i_v,
    input  wire [NKT-1:0]        i_kv,
    input  wire [NKT-1:0]        i_keep,
    input  wire [NKT*NCH*32-1:0] i_sum,     // key g, chunk c at [(g*NCH+c)*32 +: 32]
    input  wire [NKT*NCH-1:0]    i_fault,
    output reg                   o_v,
    output reg  [NKT-1:0]        o_kv,
    output reg  [NKT*16-1:0]     o_score,
    output reg  [NKT-1:0]        o_fault

);
 localparam integer NCH=4,NKT=4,FPL=7;

    localparam integer LV = (NCH <= 1) ? 0 : $clog2(NCH);
    // reset (H-NETLIST/TAIL 1300): the rst_n PORT drives only ot_rst_relay (async assert, synchronous release after
    // SYNC_STAGES + TREE_STAGES = 3 edges).  Region 0 resets the valid line (rv, u_vl, o_v); region 1+g resets key g's
    // adder tree.  The adders are DRST 0 (only their valid bits reset; data flops plain, qualified by the tail's own
    // reset valid line vl), so no copy drives more than the 9 x 14 valid-line flops.  The port no longer gates data
    // (was rv <= i_v && rst_n: a 5,228-load async net + datapath AND, native capture 402.8 ps).  Data timing unchanged.
    localparam integer RR = NKT + 1 + 5;
    wire [RR-1:0]        rr;
    ot_hidx_rst_tree_3e_f32 #(.REGIONS(RR)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg                  rv;
    reg [NKT-1:0]        rkv, rkeep;
    reg [NKT*NCH*32-1:0] rsum;
    reg [NKT*NCH-1:0]    rf;
    always @(posedge clk) begin
        rv <= i_v && rr[0];
        rkv <= i_kv;
        rkeep <= i_keep;
        rsum <= i_sum;
        rf <= i_fault;
    end
    wire [2*NKT:0] vl;
    wire[2*NKT:0] vin={rkeep,rkv,rv};
    // Measured old rr[0] fanout was 128. Each equal-age copy now clears
    // at most 2 x 14 = 28 valid bits; the calendar stays fourteen edges.
    for(genvar vg=0;vg<5;vg=vg+1)begin:g_valid_group
      localparam integer V=(2*NKT+1-2*vg<2)?2*NKT+1-2*vg:2;
      ot_hdc_delay #(.W(V),.D(FPL*LV),.RESET(1))u_vl(.clk(clk),.rst_n(rr[NKT+1+vg]),.d(vin[2*vg+:V]),.q(vl[2*vg+:V]));
    end
    genvar g, l, i;
    generate
        for (g = 0; g < NKT; g = g + 1) begin : g_key
            // level l holds NCH >> l partial sums
            // level l, partial i at index l * NCH + i
            wire [(LV+1)*NCH*32-1:0] t;
            wire [(LV+1)*NCH-1:0]    tf;
            for (i = 0; i < NCH; i = i + 1) begin : g_in
                assign t[32*i +: 32] = rsum[(g * NCH + i) * 32 +: 32];
                assign tf[i] = rf[g * NCH + i];
            end
            for (l = 0; l < LV; l = l + 1) begin : g_lv
                for (i = 0; i < (NCH >> (l + 1)); i = i + 1) begin : g_add
                    wire [1:0] err;
                    wire       vo_unused;
                    ot_hdc_fp32_add_lat_fan32 #(.LAT(FPL), .DRST(0), .SAFE_DIST(1)) u_a (.clk(clk), .rst_n(rr[1 + g]), .valid_in(1'b1),
                        .a(t[32*(l*NCH+2*i) +: 32]), .b(t[32*(l*NCH+2*i+1) +: 32]),
                        .y(t[32*((l+1)*NCH+i) +: 32]), .err(err), .valid_out(vo_unused));
                    wire pf;
                    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(rr[1 + g]),
                        .d(tf[l*NCH+2*i] || tf[l*NCH+2*i+1]), .q(pf));
                    assign tf[(l+1)*NCH+i] = pf || (err != 2'd0);
                end
            end
            wire [15:0] s16;
            wire        so;
            ot_hdc_v41x_bf16 u_b (.x(t[32*LV*NCH +: 32]), .y(s16), .ovf(so));
            always @(posedge clk) begin
                o_fault[g] <= tf[LV*NCH] || so;
                o_score[16*g +: 16] <= (tf[LV*NCH] || so) ? 16'd0 : (vl[1 + NKT + g] ? s16 : 16'hFF80);
            end
        end
    endgenerate
    always @(posedge clk) begin
        o_v <= vl[0] && rr[0];
        o_kv <= vl[NKT:1];
    end
endmodule
`default_nettype wire
