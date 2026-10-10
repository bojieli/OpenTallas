`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM Engram row sink, one per TP rank die of an Engram home stage.
//
// Merges the row beats of the NSRC lookup engines of the layer (this rank's
// own and the three that arrive over the TP4 all-gather), decodes every beat
// FP8 E4M3 x 2^(scale-127) -> BF16 (ot_hdc_engram_e4m3_bf16, the golden's
// to_bf16((E4M3[codes] * np.exp2(sc)).astype(F)) bit for bit) and writes the
// prefetch buffer that the Engram wkv matvec reads.
//
// Beat (from ot_dsrom_engram_lookup): col (0..23), beat (0..7), slot, data =
// {scale byte, 32 codes}.  Every beat carries its row's scale, so the sink
// keeps no per-row state and the sources may interleave freely.
//
// Buffer: one write port, 32 BF16 (512 bits) a cycle at {slot, col, beat};
// word k of column c holds elements 32k .. 32k+31 of that row.  rdy[s] rises
// when all 192 beats of slot s are written (the edge after the last write
// commits) AND all 24 row statuses of slot s have arrived; perr[s] is set when
// any of them reported a CRC error (poison: the consumer must not use the
// slot).  Counting statuses makes rdy independent of the order in which data
// and statuses travel.  rel_valid/rel_slot frees a
// slot and is forwarded to the engines as their credit.
//
// Arbitration: round-robin one-hot over NSRC with a 1-entry skid per source
// (in_ready is a flop); stage 1 registers the granted beat, stage 2 decodes
// and writes.  One beat a cycle: 192 beats a token in 192 cycles.
// ---------------------------------------------------------------------------
module ot_dsrom_engram_rowsink #(
    parameter integer PIN_CAPTURE = 0, // opt-in reserved pin capture + four-entry source queues
    parameter integer NSRC  = 4,
    parameter integer NC    = 24,
    parameter integer NSLOT = 2,
    parameter integer LANES = 32,
    parameter integer SLW   = (NSLOT > 1) ? $clog2(NSLOT) : 1,
    parameter integer BW    = 264,
    parameter integer BAW   = SLW + 5 + 3
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [NSRC-1:0]          in_valid,
    output reg  [NSRC-1:0]          in_ready,
    input  wire [NSRC*5-1:0]        in_col,
    input  wire [NSRC*3-1:0]        in_beat,
    input  wire [NSRC*SLW-1:0]      in_slot,
    input  wire [NSRC*BW-1:0]       in_data,
    // row status from the engines (one per row: CRC good / bad)
    input  wire [NSRC-1:0]          st_valid,
    input  wire [NSRC*SLW-1:0]      st_slot,
    input  wire [NSRC-1:0]          st_bad,
    // prefetch buffer write port
    output reg                      wr_en,
    output reg  [BAW-1:0]           wr_addr,
    output reg  [16*LANES-1:0]      wr_data,
    // status and release
    output wire [NSLOT-1:0]         rdy,
    output reg  [NSLOT-1:0]         perr,
    input  wire                     rel_valid,
    input  wire [SLW-1:0]           rel_slot
);
    localparam integer TOT = NC * 8;
    localparam integer TW  = $clog2(TOT + 1);
    localparam integer EW  = 5 + 3 + SLW + BW;

    // ---- per-source skid (1 entry) ----------------------------------------------------
    wire [NSRC-1:0] sv;
    wire [EW-1:0] sd [0:NSRC-1];
    wire [NSRC-1:0] take;
    integer i;
    genvar gs;
    generate
        for (gs = 0; gs < NSRC; gs = gs + 1) begin : g_src
            if (!PIN_CAPTURE) begin:g_legacy
                reg valid_q;
                reg [EW-1:0] data_q;
                wire acc = in_valid[gs] && in_ready[gs];
                assign sv[gs]=valid_q;
                assign sd[gs]=data_q;
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin valid_q <= 0; in_ready[gs] <= 0; end
                    else begin
                        valid_q <= (valid_q && !take[gs]) || acc;
                        in_ready[gs] <= !((valid_q && !take[gs]) || acc);
                    end
                end
                always @(posedge clk) if (acc)
                    data_q <= {in_col[5*gs +: 5], in_beat[3*gs +: 3], in_slot[SLW*gs +: SLW], in_data[BW*gs +: BW]};
            end else begin:g_pin
                reg accepted_q;
                reg [EW-1:0] pin_data;
                reg [EW-1:0] fifo [0:3];
                reg [1:0] rp,wp;
                reg [2:0] count;
                assign sv[gs]=(count!=0);
                assign sd[gs]=fifo[rp];
                // Every payload pin has an unconditional capture. Only one
                // valid flop loads the acceptance gate; no wide input enable.
                always @(posedge clk)
                    pin_data <= {in_col[5*gs +: 5], in_beat[3*gs +: 3], in_slot[SLW*gs +: SLW], in_data[BW*gs +: BW]};
                always @(posedge clk or negedge rst_n) begin
                    if(!rst_n) begin accepted_q<=0;in_ready[gs]<=0;rp<=0;wp<=0;count<=0;end
                    else begin
                        accepted_q<=in_valid[gs] && in_ready[gs];
                        // count + accepted_q already reserves the captured
                        // beat. Two spare entries reserve current acceptance
                        // and the acceptance under next cycle's ready.
                        in_ready[gs]<=({1'b0,count}+accepted_q<=2);
                        case({accepted_q,take[gs]})
                            2'b10:count<=count+1'b1;
                            2'b01:count<=count-1'b1;
                            default:count<=count;
                        endcase
                        if(accepted_q) begin fifo[wp]<=pin_data;wp<=wp+1'b1;end
                        if(take[gs]) rp<=rp+1'b1;
                    end
                end
            end
        end
    endgenerate

    // ---- round-robin grant ------------------------------------------------------------
    reg  [NSRC-1:0] pmask;
    wire [NSRC-1:0] vm   = sv & pmask;
    wire [NSRC-1:0] pick = (vm != 0) ? vm : sv;
    wire [NSRC-1:0] gnt  = pick & (~pick + 1'b1);
    assign take = gnt;
    reg  [EW-1:0] gsel;
    always @(*) begin
        gsel = {EW{1'b0}};
        for (i = 0; i < NSRC; i = i + 1) gsel = gsel | ({EW{gnt[i]}} & sd[i]);
    end
    reg          s1_v;
    reg [EW-1:0] s1_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin pmask <= {NSRC{1'b0}}; s1_v <= 1'b0; end
        else begin
            s1_v <= (sv != 0);
            if (sv != 0) pmask <= ~(gnt | (gnt - 1'b1));
        end
    end
    always @(posedge clk) if (sv != 0) s1_d <= gsel;

    // ---- decode + write ---------------------------------------------------------------
    wire [4:0]     s1_col  = s1_d[EW-1 -: 5];
    wire [2:0]     s1_beat = s1_d[EW-6 -: 3];
    wire [SLW-1:0] s1_slot = s1_d[BW +: SLW];
    wire [7:0]     s1_scl  = s1_d[BW-1 -: 8];
    wire [16*LANES-1:0] dec;
    genvar gq;
    generate
        for (gq = 0; gq < LANES; gq = gq + 1) begin : g_dec
            ot_hdc_engram_e4m3_bf16 u_dec (.code(s1_d[8*gq +: 8]), .scale(s1_scl), .bf16(dec[16*gq +: 16]));
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) wr_en <= 1'b0;
        else wr_en <= s1_v;
    end
    always @(posedge clk) if (s1_v) begin
        wr_addr <= {s1_slot, s1_col, s1_beat};
        wr_data <= dec;
    end

    // ---- completion, poison, release --------------------------------------------------
    wire [SLW-1:0] wslot = wr_addr[BAW-1 -: SLW];
    reg  [TW-1:0]  cnt [0:NSLOT-1];
    reg  [5:0]     scnt [0:NSLOT-1];
    reg  [2:0]     sinc [0:NSLOT-1];
    integer q;
    always @(*)
        for (q = 0; q < NSLOT; q = q + 1) begin
            sinc[q] = 3'd0;
            for (i = 0; i < NSRC; i = i + 1)
                if (st_valid[i] && st_slot[SLW*i +: SLW] == q) sinc[q] = sinc[q] + 1'b1;
        end
    genvar gt;
    generate
        for (gt = 0; gt < NSLOT; gt = gt + 1) begin : g_slot
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin cnt[gt] <= {TW{1'b0}}; scnt[gt] <= 6'd0; perr[gt] <= 1'b0; end
                else begin
                    if (rel_valid && rel_slot == gt) begin cnt[gt] <= {TW{1'b0}}; scnt[gt] <= 6'd0; perr[gt] <= 1'b0; end
                    else begin
                        if (wr_en && wslot == gt) cnt[gt] <= cnt[gt] + 1'b1;
                        scnt[gt] <= scnt[gt] + sinc[gt];
                        for (i = 0; i < NSRC; i = i + 1)
                            if (st_valid[i] && st_bad[i] && st_slot[SLW*i +: SLW] == gt) perr[gt] <= 1'b1;
                    end
                end
            end
            assign rdy[gt] = (cnt[gt] == TOT[TW-1:0]) && (scnt[gt] == NC[5:0]);
        end
    endgenerate
endmodule
