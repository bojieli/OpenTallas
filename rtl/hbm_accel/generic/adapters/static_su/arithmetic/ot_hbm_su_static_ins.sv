`timescale 1ns/1ps
module ot_hbm_su_static_ins #(
    parameter integer W = 32,
    parameter integer K = 2,                 // depth choices
    parameter [16*K-1:0] DEPTHS = {16'd3, 16'd0},   // choice k = DEPTHS[16k +: 16]
    parameter integer DMAX = 3,              // max over DEPTHS
    parameter integer RESET_DATA = 0
) (
    input wire [3:0] clk,
    input  wire         rst_n,
    input  wire         v,
    input  wire [K-1:0] sel,                 // one-hot depth choice
    input  wire [W-1:0] d,
    output wire         vo,
    output wire [W-1:0] q,
    output wire         coll,
    output wire         busy                 // an item is in the line
);
    function automatic has(input integer p, input [K-1:0] s);
        integer k;
        begin
            has = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p && s[k]) has = 1'b1;
        end
    endfunction
    function automatic canbe(input integer p);
        integer k;
        begin
            canbe = 1'b0;
            for (k = 0; k < K; k = k + 1) if (DEPTHS[16*k +: 16] == p) canbe = 1'b1;
        end
    endfunction
    localparam integer SPR = ((DMAX + 3) / 4 > 48) ? (DMAX + 3) / 4 : 48;  // stages per clk root
    generate
        if (DMAX == 0) begin : g_wire
            assign vo = v; assign q = d; assign coll = 1'b0; assign busy = 1'b0;
        end else begin : g_line
            reg [W-1:0] r  [1:DMAX];
            reg         rv [1:DMAX];
            wire [DMAX+1:1] cl;
            assign cl[DMAX+1] = 1'b0;
            genvar p;
            for (p = 1; p <= DMAX; p = p + 1) begin : g_s
                wire [W-1:0] nx  = (p == DMAX) ? {W{1'b0}} : r[(p == DMAX) ? p : p + 1];
                wire         nxv = (p == DMAX) ? 1'b0 : rv[(p == DMAX) ? p : p + 1];
                if (canbe(p)) begin : g_ld
                    wire ld = v && has(p, sel);
                    assign cl[p] = ld && nxv;
                    always @(posedge clk[(p-1)/SPR] or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= ld || nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk[(p-1)/SPR] or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= ld ? d : nx;
                    end else begin : g_nd
                        always @(posedge clk[(p-1)/SPR]) r[p] <= ld ? d : nx;
                    end
                end else begin : g_sh
                    assign cl[p] = 1'b0;
                    always @(posedge clk[(p-1)/SPR] or negedge rst_n)
                        if (!rst_n) rv[p] <= 1'b0; else rv[p] <= nxv;
                    if (RESET_DATA != 0) begin : g_rd
                        always @(posedge clk[(p-1)/SPR] or negedge rst_n)
                            if (!rst_n) r[p] <= {W{1'b0}}; else r[p] <= nx;
                    end else begin : g_nd
                        always @(posedge clk[(p-1)/SPR]) r[p] <= nx;
                    end
                end
            end
            wire now = v && has(0, sel);
            assign vo = now || rv[1];
            assign q  = now ? d : r[1];
            assign coll = (|cl) || (now && rv[1]);
            reg any;
            integer b;
            always @(*) begin
                any = 1'b0;
                for (b = 1; b <= DMAX; b = b + 1) any = any | rv[b];
            end
            assign busy = any;
        end
    endgenerate
endmodule
