`timescale 1ns/1ps
// dsfd_sp_capture_c, CLUSTER form (s81-spwfc 2026-10-13): the die master dsfd_sp_capture_c as a ref_tile cluster over
// the CLOSED M5 leaves dsfd_capt_ctl (1), dsfd_capt_g2 (8) and dsfd_capt_x (8).  Ports and behaviour are those of
// ctrl_c/dsfd_sp_capture_c.sv built with S81PH_CAP_SAFE (dsfd_sp_capture CORE 3 = ot_s81ph_cap_t SAFE 1, KST 1) and
// LD 4; tools/s81_ph/capc_bench.sh runs the two in lockstep (t_vm and t_cd every cycle) under the gather -> capture
// golden bench.  Hard children carry no parameters (their defaults are the closed views' values: NR 16, LD 4, NT 8,
// KST 1).  The only cluster logic: the KST = 1 station on the ctl <-> group buses (one copy per group, placed between
// the control tile and its group: two hops <= 500 um), the serial reset synchroniser and the fld DONE word t_cd.
// Every die input lands in a child pin flop (f_gather) and every die output leaves from a child / cluster flop.
module dsfd_sp_capture_c (
    input wire [0:0] ck, input wire [0:0] rst, input wire [0:0] ckv, input wire [0:0] rsv,
    input wire [6946:0] f_gather,
    output wire [13375:0] t_vm,
    output reg [11:0] t_cd
);
    localparam integer NT = 8, KB = 99;      // KB = `CAPT_KB of ot_s81ph_cap_tile.sv
    wire [NT*KB-1:0] k_c; wire [NT*2-1:0] st; wire [63:0] sn_c;
    reg  [NT*KB-1:0] kd; reg [NT*2-1:0] sd; reg [63:0] nd;
    wire [NT*64-1:0] stv;
    dsfd_capt_ctl u_ctl (.ck(ck), .rst(rst), .f_ctl(f_gather[6946:6784]), .t_k(k_c), .f_sb(sd), .t_sn(sn_c));
    // station (ot_s81ph_cap_t g_st, KST 1): no reset, as the reference
    always @(posedge ck[0]) begin
`ifdef S81PH_CAPC_MUT_KSWAP
        kd <= {k_c[KB-1:0], k_c[NT*KB-1:KB]};   // mutant: every group takes its neighbour's constant bus
`else
        kd <= k_c;
`endif
        sd <= st; nd <= sn_c;
    end
    genvar g;
    generate for (g = 0; g < NT; g = g + 1) begin : g_t
        wire [16*52-1:0] w; wire [0:0] ho;
        wire [63:0] sn_g;
        if (g == NT / 2 - 1) begin : g_sn assign sn_g = nd; end else begin : g_z assign sn_g = 64'd0; end
        dsfd_capt_g2 u_g (.ck(ck), .rst(rst), .f_row(f_gather[53 * 16 * g +: 53 * 16]), .f_k(kd[KB * g +: KB]),
            .t_w(w), .f_ho(ho), .t_sb(st[2 * g +: 2]));
        dsfd_capt_x u_x (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_w(w), .t_vm(t_vm[104 * 16 * g +: 104 * 16]),
            .t_ho(ho), .f_sn(sn_g), .t_st(stv[64 * g +: 64]));
    end endgenerate
    wire [63:0] stw = stv[64 * (NT / 2 - 1) +: 64];   // the tile left of the control tile
    assign t_vm[13375:13312] = stw;
    // t_cd = {toggle, fault, phase 10} (serial domain), text of ctrl_c/dsfd_sp_capture_c.sv
    reg [1:0] rv_s;
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rv_s <= 2'b00; else rv_s <= {rv_s[0], 1'b1};
    reg dr_q, armed;
    always @(posedge ckv[0] or negedge rv_s[1])
        if (!rv_s[1]) begin dr_q <= 1'b0; armed <= 1'b0; t_cd <= 12'd0; end
        else begin
            dr_q <= stw[2];
            t_cd[10] <= stw[3];
            if (stw[0]) armed <= 1'b1;
            if (stw[2] && !dr_q && armed && !stw[0]) begin t_cd[9:0] <= stw[13:4]; t_cd[11] <= ~t_cd[11]; armed <= 1'b0; end
        end
endmodule
