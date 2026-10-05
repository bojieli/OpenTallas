`timescale 1ns/1ps
import ot_rom_coll_pkg::*;
// ---------------------------------------------------------------------------
// ot_dsrom_s81_head_amax_fh: ot_dsrom_s81_head_amax (rtl/dsrom_sys/s81_native_head,
// pinned, unchanged) plus the L1 FUSED DSpark draft head (main ec7b1ff18) on the S81
// full-shape head argmax path, default off (FH = 0: `capture` / `fuse` ignored, the
// as-built behaviour cycle for cycle).
//
// Why a successor: L1 was built on the reduced core's engine-0 matvec
// (rtl/hdc/v41/dspark_fused_head/ot_hdc_v41_matvec.sv i_oacc).  The S81 die runs
// ot_hdc_core_v41x with X_ME = 1 / X_ROM = 1 and argmaxes the ROM field's accepted
// FP32 writes here; the v41x core decodes the `ad` field only for the stream unit, so
// the fused encoding (ME op ad = AD_C, me_oen = 0, me_amax = 1) would argmax the Markov
// output alone.  Here the fusion sits where the S81 head takes its argmax.
//
// Golden (tools/hdc_golden_v41.py Model.draft): d_{i+1} = argmax(add(LG_i, markov(d_i))),
// LG_i = mv(head, xn_i), markov(d) = mv(markov_head.head, markov_head.embed[d]); one FP32
// RNE add (addend LG first), first maximum.
//
// FH = 1, per op (latched at `start`):
//   capture = 1  every accepted write's FP32 bits are stored in the addend memory at
//                row (address - obase); the argmax is the as-built one (verify head /
//                lm_head pass of a draft row).
//   fuse    = 1  every accepted write m (Markov row) becomes add(addend[row], m)
//                (ot_fp32_add_rne_pipe, one per lane), delayed with its mask / ids /
//                last by FH_LAT = 1 (synchronous addend read) + 5 (adder) cycles, then
//                the as-built ot_rom_argmax_rows.  An adder error (nonfinite operand,
//                overflow) faults.
// The addend memory is behavioural here (ROWS words, R ports).  On silicon it is banked
// by return lane (32,320 / 128 = 253 words a lane), which requires the Markov rows to
// return on the same lanes as the head rows (row-congruent placement of the two ROM
// tables), else a VM read path at R words a cycle.
// ---------------------------------------------------------------------------
module ot_dsrom_s81_head_amax_fh #(
    parameter integer R=128,AW=30,NW=21,RANK=0,
    parameter integer FH=0,
    parameter integer ROWS=32320
)(
    input wire clk,rst_n,start,
    input wire capture,fuse,
    input wire [46:0] identity,
    input wire [NW-1:0] nout,
    input wire [AW-1:0] obase,
    input wire [R-1:0] write_valid,write_accept,
    input wire [R*AW-1:0] write_address,
    input wire [R*32-1:0] write_bits,
    input wire upstream_valid,
    output wire upstream_ready,
    input wire [511:0] upstream_data,
    input wire upstream_last,
    input wire [46:0] upstream_identity,
    output wire downstream_valid,
    input wire downstream_ready,
    output wire [511:0] downstream_data,
    output wire downstream_last,
    output wire [46:0] downstream_identity,
    input wire final_valid,
    output wire final_ready,
    input wire [511:0] final_data,
    input wire [46:0] final_identity,
    output reg busy,result_seen,
    output reg [NW-1:0] am_idx,
    output reg [31:0] am_val,
    output reg am_any,fault
);
    localparam integer FH_LAT=6;
    reg [46:0] owner;
    reg [NW-1:0] expected,seen;
    reg [AW-1:0] base;
    reg up_owned,forwarded;
    reg cap_r,fuse_r;
    assign final_ready=busy && forwarded && !fault && final_identity==owner;
    wire [R-1:0] mask=write_valid & write_accept & {R{busy}};
    wire native_ready,native_fault,up_ready,dn_valid;
    wire [31:0] tokens;
    reg [R*32-1:0] ids;
    integer j,accepted;
    reg range_fault,nonfinite;
    always @* begin
        accepted=0;ids=0;range_fault=0;nonfinite=0;
        for(j=0;j<R;j=j+1) begin
            ids[32*j+:32]=RANK*32320+write_address[AW*j+:AW]-base;
            if(mask[j]) begin
                accepted=accepted+1;
                if(write_address[AW*j+:AW]<base || write_address[AW*j+:AW]>=base+expected) range_fault=1;
                if(write_bits[32*j+23+:8]==8'hff) nonfinite=1;
            end
        end
    end
    wire beat_v=(|mask) && !fault && !range_fault && !nonfinite;
    wire beat_last=(seen+accepted==expected);

    // ---- fused path (FH = 1, fuse op) ------------------------------------------------------
    wire fz=(FH!=0) && fuse_r;
    reg  [31:0] addm [0:ROWS-1];
    reg  [R*32-1:0] ra_q, rb_q;              // stage 1: addend (synchronous read), Markov bits
    reg  [R-1:0] p_mask [0:FH_LAT-1];
    reg  [R*32-1:0] p_ids [0:FH_LAT-1];
    reg  [FH_LAT-1:0] p_v, p_last;
    wire [R*32-1:0] f_bits;
    wire [R*2-1:0] f_err;
    wire [R-1:0] f_vo;
    integer k,s;
    generate if (FH!=0) begin : g_fh
        always @(posedge clk) begin
            for(k=0;k<R;k=k+1) begin
                if(busy && cap_r && mask[k])
                    addm[write_address[AW*k+:AW]-base] <= write_bits[32*k+:32];
                ra_q[32*k+:32] <= addm[(write_address[AW*k+:AW]-base) % ROWS];
            end
            rb_q <= write_bits;
        end
        genvar gl;
        for(gl=0;gl<R;gl=gl+1) begin : g_add
            ot_fp32_add_rne_pipe u_add(.clk(clk),.rst_n(rst_n),.valid_in(p_v[0] && p_mask[0][gl]),
                .a(ra_q[32*gl+:32]),.b(rb_q[32*gl+:32]),.y(f_bits[32*gl+:32]),.err(f_err[2*gl+:2]),
                .valid_out(f_vo[gl]));
        end
        always @(posedge clk or negedge rst_n) begin
            if(!rst_n) begin p_v<=0; p_last<=0; end
            else begin
                p_v<={p_v[FH_LAT-2:0], fz && beat_v};
                p_last<={p_last[FH_LAT-2:0], beat_last};
            end
        end
        always @(posedge clk) begin
            p_mask[0]<=mask; p_ids[0]<=ids;
            for(s=1;s<FH_LAT;s=s+1) begin p_mask[s]<=p_mask[s-1]; p_ids[s]<=p_ids[s-1]; end
        end
    end else begin : g_nfh
        assign f_bits=0; assign f_err=0; assign f_vo=0;
        always @* begin p_v=0; p_last=0; end
    end endgenerate
    wire fo_v=p_v[FH_LAT-1];
    wire [R-1:0] fo_mask=p_mask[FH_LAT-1];
    wire fo_err=fo_v && (|f_err);
`ifndef SYNTHESIS
    // the delay line and the adders agree on the latency (FH_LAT = 1 read + 5 adder stages)
    always @(posedge clk) if (rst_n && FH!=0 && fo_v && f_vo!=fo_mask)
        $fatal(1, "ot_dsrom_s81_head_amax_fh: adder latency differs from FH_LAT");
`endif

    wire          lg_v    = fz ? fo_v : beat_v;
    wire [R*32-1:0] lg_d  = fz ? f_bits : write_bits;
    wire [R-1:0]  lg_m    = fz ? fo_mask : mask;
    wire [R*32-1:0] lg_i  = fz ? p_ids[FH_LAT-1] : ids;
    wire          lg_l    = fz ? p_last[FH_LAT-1] : beat_last;

    wire match_owner=upstream_identity==owner;
    assign upstream_ready=busy && !fault && !up_owned && match_owner && up_ready;
    assign downstream_valid=busy && !fault && seen==expected && dn_valid;
    assign downstream_identity=owner;
    ot_rom_argmax_rows #(.LANES(R),.DEPTH(8),.FIRST(RANK==0),.SELF(RANK),.NEXT(RANK+1)) u_native (
        .clk(clk),.rst_n(rst_n),.lg_valid(lg_v),
        .lg_ready(native_ready),.lg_data(lg_d),.lg_mask(lg_m),.lg_ids(lg_i),.lg_base(32'd0),
        .lg_tag(8'd0),.lg_last(lg_l),
        .up_valid(upstream_valid && upstream_ready),.up_ready(up_ready),
        .up_data(upstream_data),.up_last(upstream_last),
        .dn_valid(dn_valid),.dn_ready(downstream_valid && downstream_ready),
        .dn_data(downstream_data),.dn_last(downstream_last),.tokens_out(tokens),.fault(native_fault));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            busy<=0;result_seen<=0;am_idx<=0;am_val<=0;am_any<=0;fault<=0;
            owner<=0;expected<=0;seen<=0;base<=0;up_owned<=0;forwarded<=0;cap_r<=0;fuse_r<=0;
        end else begin
            if(start) begin
                if(busy || fault || nout==0 || nout>32320 || (FH!=0 && capture && fuse)) fault<=1;
                else begin
                    busy<=1;result_seen<=0;owner<=identity;expected<=nout;seen<=0;
                    base<=obase;am_any<=0;up_owned<=0;forwarded<=0;
                    cap_r<=(FH!=0) && capture; fuse_r<=(FH!=0) && fuse;
                end
            end
            if(busy) begin
                if(native_fault || range_fault || nonfinite || seen+accepted>expected || ((fz ? lg_v : (|mask))&&!native_ready)) fault<=1;
                if(fz && fo_err) fault<=1;
                if(upstream_valid && !up_owned && !match_owner) fault<=1;
                if(upstream_valid && upstream_ready) up_owned<=1;
                seen<=seen+NW'(accepted);
                if(downstream_valid && downstream_ready) forwarded<=1;
                if(final_valid && final_ready) begin
                    if(final_data[H_KIND+:4]!=K_ARGMAX || !final_data[H_ARG_OK] ||
                       final_data[H_ARG_ID+:32]>=129280 || final_data[H_ARG_VAL+23+:8]==8'hff) fault<=1;
                    else begin
                        am_idx<=NW'(final_data[H_ARG_ID+:32]);am_val<=final_data[H_ARG_VAL+:32];
                        am_any<=1;result_seen<=1;busy<=0;
                    end
                end
            end
        end
    end
endmodule
