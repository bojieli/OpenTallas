`timescale 1ns/1ps
// ot_v41_chain4_rp (S81-C199 reset partition, 2026-10-19, opt-in OT_BF_RSTPART): ot_v41_chain4 (body unchanged) whose
// reset input is the RAW reset source rst_pin (the column's landed reset copy, a register on the same free clock), and
// which holds three kept same-edge synchroniser copies (ot_v41_rst_copy): u_rb -> the chain body (valid / pv / accf /
// fault / sp_v), u_rf -> the ND kept forward-select registers; the adder is ot_v41_fadd2_rp (its own two copies).  Each copy is the same
// register function as the caller's single synchroniser it replaces (d = 1, async clear from the same source, same
// clock), so every reset releases on the same edge; no register drives more than one region's resets.
// Only valid when clk is the free-running clock the source register runs on (OT_BF_TILE_FREECLK).
// FOREP (S81-C199-FANOUT 2026-10-19, opt-in define OT_BF_FOREP, default off = unchanged): no register drives more
// than ~32 loads (through BUF/INV).  (1) The slot-wide accumulator read acc[slot] (a 16:1 x 33-bit mux: the slot LSB
// drove 1,060 loads) becomes an AND-OR over OHK kept copies of the slot's ONE-HOT decode, supplied by the caller on
// slot_oh and registered on the same edge as slot (the producer decodes it one stage earlier): copy j selects bit
// slice j of the word.  (2) first_r and the forward selects are held as kept same-edge copies per operand slice:
// ND copies for the adder operand a, 2*ND for the PD step-0 bundle.  Same values, same edges: zero cycles.
module ot_v41_chain4_rp #(
    parameter integer ND = 4,
    parameter integer NCH = 16,
    parameter integer TW = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8]
,
    parameter integer PD = 0,
    parameter integer OHK = 2) (
    input  wire                     clk,
    input  wire                     rst_pin,
    input  wire                     v,
    input  wire [$clog2(NCH)-1:0]   slot,
`ifdef OT_BF_FOREP
    input  wire [OHK*NCH-1:0]       slot_oh,   // OHK copies of onehot(slot), same edge as slot (copy j at [j*NCH +: NCH])
`endif
    input  wire                     first,
    input  wire                     last,
    input  wire [31:0]              term,
    input  wire                     term_f,
    input  wire [TW-1:0]            tag,
    output wire                     ov,
`ifdef OT_BF_N32
    output wire [3:0]               ov_k,      // S81-BF6: 4 kept copies of ov (ot_v41_n32_kand2), byte selects of the caller
`endif
    output wire [31:0]              osum,
    output wire                     of,
    output wire [TW-1:0]            otag,
    output reg                      fault
);
    localparam integer SW = $clog2(NCH);
    wire rst_n, rst_f;
    ot_v41_rst_copy u_rb (.clk(clk), .rst_pin(rst_pin), .rst_n(rst_n));
    ot_v41_rst_copy u_rf (.clk(clk), .rst_pin(rst_pin), .rst_n(rst_f));
`ifndef OT_BF_ACC_SRAM
    reg [31:0] acc [0:NCH-1];
`endif
    reg [NCH-1:0] accf;
    // input register: the chain slot's stored sum is read one cycle before the term meets the adder, so the
    // adder's operand is a 4-way choice (+0, the sum leaving the adder now, the one that left a cycle ago, the
    // stored sum) rather than a slot-wide read in front of the adder's first stage
    reg          v_r, first_r, last_r, termf_r, accf_r;
    reg [SW-1:0] slot_r;
    reg [31:0] term_r;
`ifdef OT_BF_ACC_SRAM
    wire [31:0] acc_r;
`else
    reg [31:0] acc_r;
`endif
    reg [TW-1:0] tag_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) v_r <= 1'b0; else v_r <= v;
`ifdef OT_BF_FOREP
    // registered one-hot slot read: copy j of slot_oh selects word slice j (and copy 0 the fault bit)
    reg [31:0] acc_rd;
    reg        accf_rd;
    integer oj, oe;
    always @* begin
        acc_rd = 32'd0;
`ifndef OT_BF_ACC_SRAM
        for (oj = 0; oj < OHK; oj = oj + 1)
            for (oe = 0; oe < NCH; oe = oe + 1)
                if (slot_oh[oj*NCH + oe]) acc_rd = acc_rd | (acc[oe] & (((33'd1 << ((32 * (oj + 1)) / OHK)) - 33'd1) ^
                                                                        ((33'd1 << ((32 * oj) / OHK)) - 33'd1)));
`endif
        accf_rd = |(slot_oh[NCH-1:0] & accf);
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && v)
        for (int j = 0; j < OHK; j++) if (slot_oh[j*NCH +: NCH] != (NCH'(1) << slot))
            $fatal(1, "FOREP: slot_oh copy %0d %b != onehot(slot %0d)", j, slot_oh[j*NCH +: NCH], slot);
`endif
    (* keep *) reg [ND-1:0]   first_a;    // operand a slice g
    (* keep *) reg [2*ND-1:0] first_e;    // PD step-0 bundle slice
    always @(posedge clk) begin
        slot_r <= slot; first_r <= first; last_r <= last; term_r <= term; termf_r <= term_f; tag_r <= tag;
`ifndef OT_BF_ACC_SRAM
        acc_r <= acc_rd;
`endif
        accf_r <= accf_rd;
        first_a <= {ND{first}}; first_e <= {(2*ND){first}};
    end
`else
    always @(posedge clk) begin
        slot_r <= slot; first_r <= first; last_r <= last; term_r <= term; termf_r <= term_f; tag_r <= tag;
`ifndef OT_BF_ACC_SRAM
        acc_r <= acc[slot];
`endif
        accf_r <= accf[slot];
    end
`endif
    reg [LAT-1:0] pv;
    reg [SW-1:0] ps [0:LAT-1];
    integer k;
    reg hazard;
    always @* begin
        hazard = 1'b0;
        for (k = 0; k < LAT - 1; k = k + 1) if (pv[k] && ps[k] == slot_r) hazard = 1'b1;
    end
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    wire [31:0] a;
    wire af;
    // PD: the adder's step 0 formed on every forward candidate in parallel, the bundle selected (see the header)
    wire [104:0] o0_ext;
    ot_v41_fadd2_rp #(.CUT(CUT), .EXT0(PD != 0 ? 1 : 0)) u_add (.clk(clk), .rst_pin(rst_pin), .valid_in(v_r), .a(a), .b(term_r),
                                     .o0_ext(o0_ext), .y(sum), .err(err), .valid_out(sv));
    wire [TW+2:0] dt;
`ifdef OT_BF_TAG_RING
    ot_v41_bf_tag_ring #(.W(TW+3),.D(LAT)) u_t (.clk(clk),.rst_w(rst_n),.rst_r(rst_f),
        .d({tag_r,last_r,af|termf_r,1'b0}),.q(dt));
`else
    ot_hdc_delay #(.W(TW + 3), .D(LAT)) u_t (.clk(clk), .rst_n(rst_n), .d({tag_r, last_r, af | termf_r, 1'b0}), .q(dt));
`endif
    wire d_last = dt[2];
    wire d_f = dt[1] | (err != 2'd0);
    // the slot's previous sum: leaving the adder now (5 cycles ago), or one cycle ago (not yet in acc_r)
    reg          sp_v, sp_f;
    reg [SW-1:0] sp_slot;
    reg [31:0]   sp_val;
    // forwarding decisions are made a cycle ahead against the incoming slot and registered (the compare no
    // longer sits in front of the adder): fwd5 = the slot's sum leaves the adder in the operand cycle,
    // fwd6 = it left one cycle before
    reg [LAT-1:0] pl;
    wire [ND-1:0] fwd5, fwd6;
    wire fwd5_d = pv[LAT-2] && !pl[LAT-2] && ps[LAT-2] == slot;
    wire fwd6_d = sv && !d_last && ps[LAT-1] == slot;
    genvar g;
    for (g = 0; g < ND; g = g + 1) begin : g_fw
        ot_v41_kreg #(.W(2), .AR(1), .RV(2'b00)) u_f (.clk(clk), .arst_n(rst_f), .d({fwd6_d, fwd5_d}),
                                                       .q({fwd6[g], fwd5[g]}));
        localparam integer LO = (32 * g) / ND, HI = (32 * (g + 1)) / ND;
`ifdef OT_BF_FOREP
        assign a[HI-1:LO] = first_a[g] ? {(HI-LO){1'b0}} : (fwd5[g] ? sum[HI-1:LO] : (fwd6[g] ? sp_val[HI-1:LO] : acc_r[HI-1:LO]));
`else
        assign a[HI-1:LO] = first_r ? {(HI-LO){1'b0}} : (fwd5[g] ? sum[HI-1:LO] : (fwd6[g] ? sp_val[HI-1:LO] : acc_r[HI-1:LO]));
`endif
    end
`ifdef OT_BF_FOREP
    // the PD step-0 bundle's own forward-select copies (2*ND slices), so a fwd copy no longer feeds both a and o0_ext
    wire [2*ND-1:0] fwd5e, fwd6e;
    for (g = 0; g < 2 * ND; g = g + 1) begin : g_fwe
        ot_v41_kreg #(.W(2), .AR(1), .RV(2'b00)) u_f (.clk(clk), .arst_n(rst_f), .d({fwd6_d, fwd5_d}),
                                                       .q({fwd6e[g], fwd5e[g]}));
    end
`endif
    always @(posedge clk) pl <= {pl[LAT-2:0], last_r};
    if (PD != 0) begin : g_pd
        wire [104:0] c5, c6, ca, cz;
`ifdef OT_BF_N32
        // S81-BF6: each candidate step 0 reads its own kept same-edge copy of term's exponent field (term_r[30:23]
        // fed the four candidate bundles' field / class / compare logic: 34..40 loads per bit, native93)
        (* keep *) reg [7:0] term_ek [0:3];
        always @(posedge clk) for (int ke = 0; ke < 4; ke++) term_ek[ke] <= term[30:23];
        ot_v41_fadd_s0 u_s5 (.valid_in(v_r), .a(sum),    .b({term_r[31], term_ek[0], term_r[22:0]}), .o0(c5));
        ot_v41_fadd_s0 u_s6 (.valid_in(v_r), .a(sp_val), .b({term_r[31], term_ek[1], term_r[22:0]}), .o0(c6));
        ot_v41_fadd_s0 u_sa (.valid_in(v_r), .a(acc_r),  .b({term_r[31], term_ek[2], term_r[22:0]}), .o0(ca));
        ot_v41_fadd_s0 u_sz (.valid_in(v_r), .a(32'd0),  .b({term_r[31], term_ek[3], term_r[22:0]}), .o0(cz));
`else
        ot_v41_fadd_s0 u_s5 (.valid_in(v_r), .a(sum),    .b(term_r), .o0(c5));
        ot_v41_fadd_s0 u_s6 (.valid_in(v_r), .a(sp_val), .b(term_r), .o0(c6));
        ot_v41_fadd_s0 u_sa (.valid_in(v_r), .a(acc_r),  .b(term_r), .o0(ca));
        ot_v41_fadd_s0 u_sz (.valid_in(v_r), .a(32'd0),  .b(term_r), .o0(cz));
`endif
`ifdef OT_BF_FOREP
        for (genvar g2 = 0; g2 < 2 * ND; g2 = g2 + 1) begin : g_ps
            localparam integer LO = (105 * g2) / (2 * ND), HI = (105 * (g2 + 1)) / (2 * ND);
`ifdef OT_BF_FOREP_MUT_CHAIN
            // negative control: slice 1's first copy ignored (a chain's first term adds the stale slot sum)
            assign o0_ext[HI-1:LO] = (first_e[g2] && g2 != 1) ? cz[HI-1:LO] : (fwd5e[g2] ? c5[HI-1:LO] : (fwd6e[g2] ? c6[HI-1:LO] : ca[HI-1:LO]));
`else
            assign o0_ext[HI-1:LO] = first_e[g2] ? cz[HI-1:LO] : (fwd5e[g2] ? c5[HI-1:LO] : (fwd6e[g2] ? c6[HI-1:LO] : ca[HI-1:LO]));
`endif
        end
`else
        for (genvar g2 = 0; g2 < ND; g2 = g2 + 1) begin : g_ps
            localparam integer LO = (105 * g2) / ND, HI = (105 * (g2 + 1)) / ND;
`ifdef CH_MUTANT_PD
            assign o0_ext[HI-1:LO] = first_r ? cz[HI-1:LO] : (fwd5[g2] ? c6[HI-1:LO] : (fwd6[g2] ? c5[HI-1:LO] : ca[HI-1:LO]));   // negative control: forward candidates swapped (a priority swap is equivalent: fwd5 and fwd6 are never both set, a back-to-back slot is a hazard)
`else
            assign o0_ext[HI-1:LO] = first_r ? cz[HI-1:LO] : (fwd5[g2] ? c5[HI-1:LO] : (fwd6[g2] ? c6[HI-1:LO] : ca[HI-1:LO]));
`endif
        end
`endif
    end else begin : g_npd
        assign o0_ext = '0;
    end
    assign af = first_r ? 1'b0 : (fwd5[0] ? d_f : (fwd6[0] ? sp_f : accf_r));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pv <= '0; fault <= 1'b0; accf <= '0; sp_v <= 1'b0;
        end else begin
            pv <= {pv[LAT-2:0], v_r};
            if (v_r && hazard) fault <= 1'b1;
            if (sv && !d_last) accf[ps[LAT-1]] <= d_f;
            sp_v <= sv && !d_last;
        end
    end
    always @(posedge clk) begin
        ps[0] <= slot_r;
        for (k = 1; k < LAT; k = k + 1) ps[k] <= ps[k-1];
`ifndef OT_BF_ACC_SRAM
        if (sv && !d_last) acc[ps[LAT-1]] <= sum;
`endif
        sp_slot <= ps[LAT-1]; sp_val <= sum; sp_f <= d_f;
    end
`ifdef OT_BF_ACC_SRAM
    // Exact old acc_r read edge; old-read SRAM semantics and the existing
    // fwd5/fwd6 paths preserve same-slot collisions. No array reset was present.
    initial if(NCH>128) $fatal(1,"BF chain accumulator SRAM capacity exceeded");
`ifdef OT_BF_ACC_SRAM_MUT_ADDR
    wire[6:0] acc_ra=7'(slot)^7'd1;
`else
    wire[6:0] acc_ra=7'(slot);
`endif
    ot_v41_bf_held128x32 u_acc_mem (.clk(clk),.ren(1'b1),.ra(acc_ra),.rd(acc_r),
        .wen(sv && !d_last),.wa(7'(ps[LAT-1])),.wd(sum));
`endif
    assign ov = sv && d_last;
`ifdef OT_BF_N32
    for (genvar gk = 0; gk < 4; gk = gk + 1) begin : g_ovk
`ifdef OT_BF_N32_MUT_OVK
        // negative control: copy 2 ignores d_last (byte 2 of the pair pass value follows every chain-0 valid)
        ot_v41_n32_kand2 u_k (.a(sv), .b(gk == 2 ? 1'b1 : d_last), .y(ov_k[gk]));
`else
        ot_v41_n32_kand2 u_k (.a(sv), .b(d_last), .y(ov_k[gk]));
`endif
    end
`endif
    assign osum = sum;
    assign of = d_f;
    assign otag = dt[TW+2:3];
endmodule

`ifdef OT_BF_TAG_RING
// D-edge tag delay as a D-1 slot ring plus the existing final read register.
// Separate onehot read/write token copies cap the read and write-control loads.
// rst_w/rst_r are the chain's same-edge reset copies. Data stays unreset.
module ot_v41_bf_tag_ring #(parameter integer W=11,D=8)(
 input wire clk,rst_w,rst_r,input wire[W-1:0] d,output reg[W-1:0] q);
 localparam integer N=D-1;
 (* keep *) reg[N-1:0] wp,rp;
 reg[W-1:0] mem[0:N-1];
 always @(posedge clk or negedge rst_w) if(!rst_w) wp<=1;else wp<={wp[N-2:0],wp[N-1]};
 always @(posedge clk or negedge rst_r) if(!rst_r) begin
`ifdef OT_BF_TAG_RING_MUT_AGE
  rp<=2;
`else
  rp<=1;
`endif
 end else rp<={rp[N-2:0],rp[N-1]};
 reg[W-1:0] rd;
 always @* begin rd=0;for(integer i=0;i<N;i++) rd=rd|({W{rp[i]}}&mem[i]);end
 always @(posedge clk) begin
  q<=rd;
  for(integer i=0;i<N;i++) if(wp[i]) mem[i]<=d;
 end
 initial if(D<3 || D>8 || W>15) $fatal(1,"BF tag ring shape exceeds native32 budget");
endmodule
`endif
