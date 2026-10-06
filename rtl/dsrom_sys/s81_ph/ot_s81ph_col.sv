`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE S81-PH (2026-10-06): the S81 die COLLECTOR slab (dsfd_bk_collector).  Contract:
// results/rtl/s81_ph_20261006/collector/contract.json.
//
// DECISION (Claude, owner rule): attention stays UNSPLIT in arithmetic.  The core's attention engine
// (ot_hdc_v41x_attn) computes s = q.k with a csum over the D dims and pv = p.v with a csum over the T rows in golden
// row order (padded pairwise tree over ceil(T/8) chunk sums); the softmax is on the stream unit.  A per-stack
// partial of p.v over the stack's own rows (or any max/LSE rescale merge) changes the FP32 summation order and is
// NOT bit-exact with the golden.  So no arithmetic crosses stacks here: each scan service sends only FINISHED,
// exact result frames for outputs it owns completely (score rows of the rows it holds, p.v dims it owns, or forwarded
// rows), each frame carrying its own VM destination in its header; the collector is a frame-atomic row gather that
// merges the four stack streams into the one 512-b lane to the VM.  The VM writes every beat at the address its frame
// names, so the VM image is independent of the arrival interleave = the golden image.  No arithmetic, only FIFOs and
// register stages: exact by construction.
//
// Die lanes (stream 1.2 GHz, valid-only, no back-pressure; hub end blocks dsfd_m2l_vr_512x1__hco_<st> deliver
// {fault, live, data 512, valid} in ck): cSW, cSE, cNW, cNE.  Framing = the hub common framing
// (contracts_hub.json common_rules.framing): a header word, then len raw data words.
//   header  data[511:508] type, [507:500] tag, [499:492] op, [491:480] len (data words that follow), [479:0] payload
//           (the VM destination and whatever the producer defines; carried unchanged)
//     type 1 op descriptor, 2 operand/data, 3 result      forwarded whole (header + len words)
//     type 5 fault                                        forwarded whole, and raises fault bit 15
//     type 4 done/status (len must be 0)                  NOT forwarded: one per stack per job; when all four stacks'
//                                                         DONE heads are present (tags equal) the collector emits ONE
//                                                         DONE, after every frame those stacks sent before their DONE
// Output vd (vr format: [0] rst_n, [1] valid, [513:2] data) to the VM through the station chain and the VM's ratio CDC
// (dsfd_r2l_vr_512x1__hcol: no w_rdy back) -> at most one word every PACE cycles (PACE 2: 0.6 G words/s into the
// 0.9 GHz reader, as the selector).  Frames leave atomically (no interleave inside a frame), each stack's frames in
// its own order, a frame only once all its words are buffered.  Collector words:
//     4 DONE   [507:500] tag, [15:11] 0, [10:0] OR of the four stacks' DONE [10:0]
//     5 FAULT  [507:500] tag of the last DONE, [15:11] sticky fault bits (fail closed: no data / DONE after it until
//              reset; a frame in flight is completed first, with zero words if its data is gone)
// Fault bits: [11] buffer overflow (a stack sent more than DEPTH words not yet drained), [12] format (unknown type,
// DONE with len != 0, frame longer than DEPTH-1 words), [13] the four DONE tags differ, [14] input link fault or a
// valid word while the lane is not live, [15] a stack sent a fault frame.
// Capacity contract (no back-channel to the stacks): per job each stack sends <= DEPTH (256) words; the VM issues the
// next job's work to the stacks only after this job's DONE.
// Margin-first: every used die input bit is captured at its pin and STG register stages carry it to the slab centre
// (the 5.27 mm block, pins on the W / E faces: <= ~380 um a stage); the buffers and the merger sit at the centre; the
// merged word passes OSTG stages and leaves from a flop at its pin.  The merge decision is registered one cycle
// before the slot (PACE >= 2), so pops and the 4:1 word mux are driven from flops.
// ---------------------------------------------------------------------------

// one input lane: pin register + STG transport stages + frame parser + SRAM FIFO (2 x 256x256 macros)
module ot_s81ph_col_in #(
    parameter integer STG   = 7,
    parameter integer DEPTH = 256
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [514:0] lane,
    input  wire         pop,
    output wire         hv,
    output wire [511:0] head,
    output reg          fc_inc,        // a complete frame entered the FIFO (its last word pushed this cycle)
    output reg          e_fmt,         // pulses
    output reg          e_link,
    output reg          e_svc,
    output wire         ovf            // sticky (FIFO)
);
    reg  [514:0] s [0:STG];
    integer i;
    always @(posedge clk) begin
        s[0] <= lane;
        for (i = 1; i <= STG; i = i + 1) s[i] <= s[i-1];
    end
    wire [514:0] w   = s[STG];
    wire         v   = w[0];
    wire [511:0] d   = w[512:1];
    wire [3:0]   typ = d[511:508];
    wire [11:0]  len = d[491:480];
    reg          inf, drop;
    reg  [11:0]  rem;
    reg          push;
    reg  [511:0] pd;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            inf <= 1'b0; drop <= 1'b0; rem <= 12'd0; push <= 1'b0; fc_inc <= 1'b0;
            e_fmt <= 1'b0; e_link <= 1'b0; e_svc <= 1'b0;
        end else begin
            push <= 1'b0; fc_inc <= 1'b0; e_fmt <= 1'b0; e_svc <= 1'b0;
            e_link <= w[514] | (v & ~w[513]);
            if (v) begin
                if (inf) begin
                    push <= ~drop;
                    rem <= rem - 1'b1;
                    if (rem == 12'd1) begin inf <= 1'b0; fc_inc <= ~drop; drop <= 1'b0; end
                end else begin
                    case (typ)
                        4'd1, 4'd2, 4'd3, 4'd5: begin
                            if (typ == 4'd5) e_svc <= 1'b1;
                            if (len > DEPTH - 1) begin
                                e_fmt <= 1'b1; drop <= 1'b1; inf <= (len != 12'd0); rem <= len;
                            end else begin
                                push <= 1'b1; drop <= 1'b0;
                                if (len == 12'd0) fc_inc <= 1'b1;
                                else begin inf <= 1'b1; rem <= len; end
                            end
                        end
                        4'd4: begin
                            if (len != 12'd0) begin e_fmt <= 1'b1; drop <= 1'b1; inf <= 1'b1; rem <= len; end
                            else begin push <= 1'b1; fc_inc <= 1'b1; end
                        end
                        default: e_fmt <= 1'b1;
                    endcase
                end
            end
        end
    end
    always @(posedge clk) pd <= d;
    ot_fifo_sram_fwft #(.W(512), .DEPTH(DEPTH), .MACRO(1)) u_q (.clk(clk), .rst_n(rst_n), .push(push), .wdata(pd),
        .pop(pop), .hv(hv), .head(head), .ovf(ovf));
endmodule

// four lanes, the frame-atomic merger and the paced output word
module ot_s81ph_col_core #(
    parameter integer STG   = 7,
    parameter integer OSTG  = 1,
    parameter integer DEPTH = 256,
    parameter integer PACE  = 2
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4*515-1:0] lanes,     // {NE, NW, SE, SW}: lane index 0 SW, 1 SE, 2 NW, 3 NE
    output wire          o_v,
    output wire [511:0]  o_d,
    output wire [15:0]   dbg_fault
);
    localparam integer Q = 4;
    localparam integer FW = $clog2(DEPTH + 1);
`ifndef SYNTHESIS
    initial if (PACE < 2) $fatal(1, "ot_s81ph_col_core: PACE must be >= 2 (registered merge decision)");
`endif
    reg  [Q-1:0]   pop;
    wire [Q-1:0]   hv, fci, efmt, elink, esvc, ovf;
    wire [512*Q-1:0] hd;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_in
        ot_s81ph_col_in #(.STG(STG), .DEPTH(DEPTH)) u_in (.clk(clk), .rst_n(rst_n), .lane(lanes[515*g +: 515]),
            .pop(pop[g]), .hv(hv[g]), .head(hd[512*g +: 512]), .fc_inc(fci[g]), .e_fmt(efmt[g]), .e_link(elink[g]),
            .e_svc(esvc[g]), .ovf(ovf[g]));
    end endgenerate

    // ---- per-lane complete-frame counts
    reg  [FW-1:0]  fc [0:Q-1];
    reg  [Q-1:0]   fc_dec;
    reg  [Q-1:0]   fc_nz;
    integer l;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (l = 0; l < Q; l = l + 1) fc[l] <= {FW{1'b0}};
            fc_nz <= {Q{1'b0}};
        end else
            for (l = 0; l < Q; l = l + 1) begin
                fc[l] <= fc[l] + (fci[l] ? 1'b1 : 1'b0) - (fc_dec[l] ? 1'b1 : 1'b0);
                fc_nz[l] <= (fc[l] + (fci[l] ? 1'b1 : 1'b0) - (fc_dec[l] ? 1'b1 : 1'b0)) != 0;
            end
    end
    wire [Q-1:0] hdone;
    wire [7:0]   htag [0:Q-1];
    generate for (g = 0; g < Q; g = g + 1) begin : g_h
        assign hdone[g] = hd[512*g + 508 +: 4] == 4'd4;
        assign htag[g]  = hd[512*g + 500 +: 8];
    end endgenerate

    // ---- merger state
    reg  [$clog2(PACE+1)-1:0] pc;
    wire          pre  = (pc == PACE - 1);
    wire          slot = (pc == 0);
    reg           busy;              // inside a frame
    reg  [1:0]    cl;                // its lane
    reg  [11:0]   rem;               // its data words still to send
    reg  [1:0]    rr;                // last lane granted a frame
    reg  [4:0]    flt, flt_rep;
    reg           halt;              // a fault: no data / DONE until reset
    reg  [7:0]    ltag;
    // registered decision (taken on the pre cycle, acted on at the slot)
    localparam [2:0] D_NONE = 0, D_BEAT = 1, D_HDR = 2, D_DONE = 3, D_FAULT = 4, D_PAD = 5;
    reg  [2:0]    dec;
    reg  [1:0]    dl;
    wire [4:0]    flt_new = flt & ~flt_rep;
    reg           e_tag;
    // round-robin pick of a lane with a complete non-DONE frame at its head
    reg  [1:0]    pk;
    reg           pk_ok;
    integer k;
    always @(*) begin
        pk = rr; pk_ok = 1'b0;
        for (k = Q; k >= 1; k = k - 1)
            if (fc_nz[(rr + k) % Q] && hv[(rr + k) % Q] && !hdone[(rr + k) % Q]) begin
                pk = (rr + k) % Q; pk_ok = 1'b1;
            end
    end
    wire all_done = &(fc_nz & hv & hdone);
    wire tags_eq  = (htag[0] == htag[1]) && (htag[0] == htag[2]) && (htag[0] == htag[3]);
    wire [10:0] dcode = hd[0 +: 11] | hd[512 +: 11] | hd[1024 +: 11] | hd[1536 +: 11];

    reg          ov;
    reg  [511:0] od;
    always @(*) begin
        pop = {Q{1'b0}}; fc_dec = {Q{1'b0}};
        if (slot)
            case (dec)
                D_BEAT: if (hv[dl]) begin pop[dl] = 1'b1; fc_dec[dl] = (rem == 12'd1); end
                D_HDR:  begin pop[dl] = 1'b1; fc_dec[dl] = (hd[512*dl + 480 +: 12] == 12'd0); end
                D_DONE: begin pop = {Q{1'b1}}; fc_dec = {Q{1'b1}}; end
                default: ;
            endcase
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 0; busy <= 1'b0; cl <= 2'd0; rem <= 12'd0; rr <= 2'd3; flt <= 5'd0; flt_rep <= 5'd0;
            halt <= 1'b0; ltag <= 8'd0; dec <= D_NONE; dl <= 2'd0; e_tag <= 1'b0; ov <= 1'b0; od <= 512'd0;
        end else begin
            pc <= (pc == PACE - 1) ? 0 : pc + 1'b1;
            flt <= flt | {|esvc, |elink, e_tag, |efmt, |ovf};
            e_tag <= 1'b0;
            // decision for the next slot
            if (pre) begin
                dec <= D_NONE;
                if (busy) begin
`ifdef OT_S81PH_COLMUT1
                    // MUTANT 1: frame interleave (a new frame may start inside another)
                    if (!(|flt) && pk_ok && pk != cl) begin dec <= D_HDR; dl <= pk; end
                    else
`endif
                    begin dec <= (|flt && !hv[cl]) ? D_PAD : D_BEAT; dl <= cl; end
                end else if (|flt_new)
                    dec <= D_FAULT;
                else if (!halt && !(|flt)) begin
`ifdef OT_S81PH_COLMUT2
                    // MUTANT 2: DONE as soon as ONE stack's DONE is at its head
                    if (|(fc_nz & hv & hdone)) dec <= D_DONE;
`else
                    if (all_done) begin
                        if (tags_eq) dec <= D_DONE; else e_tag <= 1'b1;
                    end
`endif
                    else if (pk_ok) begin dec <= D_HDR; dl <= pk; end
                end
            end
            // act at the slot
            ov <= 1'b0;
            if (slot)
                case (dec)
                    D_BEAT, D_PAD: if (hv[dl] || dec == D_PAD) begin
                        ov <= 1'b1; od <= (dec == D_PAD) ? 512'd0 : hd[512*dl +: 512];
                        rem <= rem - 1'b1;
                        if (rem == 12'd1) busy <= 1'b0;
                    end
                    D_HDR: begin
                        ov <= 1'b1; od <= hd[512*dl +: 512];
                        rr <= dl; cl <= dl;
                        rem <= hd[512*dl + 480 +: 12];
                        busy <= hd[512*dl + 480 +: 12] != 12'd0;
                    end
                    D_DONE: begin
                        ov <= 1'b1; od <= {4'd4, htag[0], 484'd0, 5'd0, dcode};
                        ltag <= htag[0];
                    end
                    D_FAULT: begin
                        ov <= 1'b1; od <= {4'd5, ltag, 484'd0, flt, 11'd0};
                        flt_rep <= flt; halt <= 1'b1;
                    end
                    default: ;
                endcase
        end
    end
    // OSTG register stages to the output pin flop (in the top)
    reg  [512:0] os [0:OSTG];
    integer j;
    always @(posedge clk) begin
        os[0] <= {od, ov & rst_n};
        for (j = 1; j <= OSTG; j = j + 1) os[j] <= os[j-1];
    end
    assign o_v = os[OSTG][0];
    assign o_d = os[OSTG][512:1];
    assign dbg_fault = {flt, 11'd0};
endmodule
