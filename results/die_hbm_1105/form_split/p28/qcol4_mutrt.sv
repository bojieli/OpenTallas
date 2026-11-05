`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/SPLIT 11-03 (OWNER TWO-STRIKES RE-FORM, HBM batch HBM-RF1 / plan event d44v): QCOL4 = four 32-bit payload
// columns of the q3 body q-slot switch, cut out of ot_hfd_coll_q3_body_core (280k cells > 150k) on the switch's own
// bit-slice boundary.  Four identical replicas per q3 body (slices 0-3, 4-7, 8-11, 12-15); the rest of the body is the
// CTL sub-block (ot_hfd_coll_q3_body_ctl, generated).  Per slice t (= g_qout[k] of ot_hfd_coll_q3_body_s):
//   capture data flop (ot_hgi_coll_qslots_capture_pin_v2: captured <= src_d, payload bits [32k +: 32] of the 11 sources)
//   -> captured_p (ot_hgi_coll_qslots_output pin flop) -> dst_d <= OR of the selected source (constant-source AND/OR,
//   verbatim from ot_hgi_coll_qslots_output, PWT 32).
// sel = ISA sink_select at uop-pipe d2, exported by CTL; with the two kit face flops (CTL out + QCOL in) it IS the uncut
// slice's sink_select_p (flop of inst_d3), so the column drops that flop: 0 added cycles (gen_q3_body_split.py header).
// dst_v / select_fault / unavailable_fault are not computed here (identical in every slice; CTL keeps slice 0's).
// MUT (bench only): 1 = dest 0 of slice 0 selects source sel+1 (ot_hgi_coll_qslots_output MUT_SELECT form);
//                   2 = slice 0 skips the capture flop (payload one edge early); 3 = sel one edge late.
module ot_hfd_coll_q3_qcol4 #(parameter integer MUT = 0) (
    input  wire              clk,
    input  wire [63:0]       sel,          // sink_select (16 dests x 4 b), from CTL ctl_sel_d2 through the faces
    input  wire [4*11*32-1:0] src,         // slice t, source s, bit b at [(t*11+s)*32+b]
    output reg  [4*16*32-1:0] dst          // slice t, dest d, bit b at [(t*16+d)*32+b]
);
    integer mut_rt = 0;
    initial if (MUT != 0) begin if (!$value$plusargs("MUT=%d", mut_rt)) mut_rt = 0; end
    localparam integer NS = 11, ND = 16, PWT = 32, SELW = 4, SPC = 4;
    reg [SPC*NS*PWT-1:0] cap, cap_p;
    reg [63:0] sel_x;
    wire [63:0] sel_u = (mut_rt == 3) ? sel_x : sel;
    always @(posedge clk) begin
        cap <= src;
        sel_x <= sel;
        cap_p <= cap;
        if (mut_rt == 2) cap_p[0 +: NS*PWT] <= src[0 +: NS*PWT];
    end
    always @(posedge clk) begin : outputs
        reg [PWT-1:0] selected;
        integer sl, d, s, ss;
        for (sl = 0; sl < SPC; sl = sl + 1)
            for (d = 0; d < ND; d = d + 1) begin
                selected = '0;
                ss = int'(sel_u[d*SELW +: SELW]);
                if (mut_rt == 1 && sl == 0 && d == 0) ss = (ss + 1) % NS;
                for (s = 0; s < NS; s = s + 1)
                    if (s == ss) selected = selected | cap_p[(sl*NS+s)*PWT +: PWT];
                dst[(sl*ND+d)*PWT +: PWT] <= selected;
            end
    end
endmodule
`default_nettype wire
