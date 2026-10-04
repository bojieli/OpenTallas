`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_d2d_link: one die's end of a full-duplex die-to-die link with a
// link layer -- sequence numbers, CRC-32, cumulative ACK, NAK, go-back-N
// replay from a replay buffer, a replay timer, and training -- the UCIe /
// PCIe-style protection AGENTS.md keeps for links after the no-ECC ROM
// decision (link protection is required; the ROM itself carries none).
// NEW, used by the Qwen ROM system top only.
//
// Upper side (the one-shot collective engine ot_rom_oneshot_die):
//   up_valid / up_ready / up_rec   a record to the far die (accepted only
//                                  while the replay buffer has room and the
//                                  link is up: the engine's tx_ready)
//   up_cr                          one engine credit to return to the far die
//   dn_valid / dn_rec              a record from the far die, exactly once and
//                                  in order (no ready: the engine's receive
//                                  FIFO is protected by its own credits)
//   dn_cr                          one engine credit from the far die
// PHY side: one flit per cycle each way (a serial PHY sends continuously).
//
// Flit: {crc32, up, seq_v, seq[S], ack_v, ack[S], nak, dv, ncr[CRB], rec[PW]}.
//   A SEQUENCED flit (seq_v) carries a record and/or engine credits; it is
//   held in the replay buffer until the far end acknowledges it.  An idle flit
//   carries only the training bit and the ACK/NAK state.
// Receive: a flit with a bad CRC is dropped (and NAKed once); a sequenced
//   flit is delivered only if it is the next expected sequence number,
//   otherwise dropped (and NAKed once).  Every flit sent carries the
//   cumulative ACK (last in-order sequence received).
// Transmit: an ACK frees the replay buffer up to it; a NAK rewinds the send
//   pointer to the oldest unacknowledged flit (go-back-N); with flits
//   outstanding and no ACK progress for TMO cycles the send pointer rewinds
//   too (a lost ACK/NAK).  MAXREP consecutive rewinds without progress latch
//   link_fault (the link is down; the system fault aggregator reports it).
// Training: link_up once RX has seen UPN consecutive good flits and the far
//   end reports the same (the `up` bit), so neither end sends traffic into a
//   link the other cannot yet receive.
// ---------------------------------------------------------------------------
module ot_qwen_d2d_link #(
    parameter integer PW     = 554,     // engine record bits
    parameter integer S      = 8,       // sequence number bits
    parameter integer LRB    = 5,       // log2 replay-buffer entries (< 2^(S-1))
    parameter integer CRB    = 3,       // credit-count bits per flit
    parameter integer TMO    = 96,      // replay timer, cycles (> round trip)
    parameter integer UPN    = 8,       // good flits to train
    parameter integer MAXREP = 64,
    parameter integer FW     = 32 + 1 + 1 + S + 1 + S + 1 + 1 + CRB + PW
) (
    input  wire          clk,
    input  wire          rst_n,
    // engine side
    input  wire          up_valid,
    output wire          up_ready,
    input  wire [PW-1:0] up_rec,
    input  wire          up_cr,
    output reg           dn_valid,
    output reg  [PW-1:0] dn_rec,
    output reg           dn_cr,
    // PHY side
    output reg  [FW-1:0] tx_flit,
    input  wire          rx_valid,
    input  wire [FW-1:0] rx_flit,
    // status
    output wire          link_up,
    output reg           link_fault,
    output reg  [31:0]   n_crc_err,
    output reg  [31:0]   n_replay,
    output reg  [31:0]   n_seq_drop,
    output reg  [31:0]   n_sent
);
    localparam integer RB = 1 << LRB;
    localparam integer BW = FW - 32;               // body (CRC input)
    localparam integer CRMAX = (1 << CRB) - 1;

    // body field offsets (LSB first)
    localparam integer O_REC = 0;
    localparam integer O_NCR = PW;
    localparam integer O_DV  = PW + CRB;
    localparam integer O_NAK = O_DV + 1;
    localparam integer O_ACK = O_NAK + 1;
    localparam integer O_AV  = O_ACK + S;
    localparam integer O_SEQ = O_AV + 1;
    localparam integer O_SV  = O_SEQ + S;
    localparam integer O_UP  = O_SV + 1;

    // ---------------------------------------------------------------- training
    reg         rx_up, far_up;
    reg [7:0]   good_run;
    assign link_up = rx_up && far_up;

    // ---------------------------------------------------------------- receive
    wire [BW-1:0] rbody = rx_flit[BW-1:0];
    wire [31:0]   rcrc  = rx_flit[FW-1 -: 32];
    wire [31:0]   ccrc;
    ot_link_crc32 #(.W(BW)) u_rcrc (.d(rbody), .crc(ccrc));
    wire          r_good = rx_valid && (rcrc == ccrc);
    wire          r_sv   = rbody[O_SV];
    wire [S-1:0]  r_seq  = rbody[O_SEQ +: S];
    wire          r_av   = rbody[O_AV];
    wire [S-1:0]  r_ack  = rbody[O_ACK +: S];
    wire          r_nak  = rbody[O_NAK];

    reg  [15:0]   cr_out_n;         // engine credits received, not yet pulsed
    reg  [S-1:0]  exp_seq;          // next sequence number expected
    reg           got_any;
    reg           nak_req, nak_sent;

    // ---------------------------------------------------------------- transmit
    reg  [PW-1:0]  rb_rec [0:RB-1];
    reg            rb_dv  [0:RB-1];
    reg  [CRB-1:0] rb_ncr [0:RB-1];
    reg  [S-1:0]   base, wr, sp;    // oldest unacknowledged, next new, next to send
    reg  [15:0]    cr_pend;
    reg  [15:0]    tmo_c;
    reg  [15:0]    rep_run;
    wire [S-1:0]   outst = wr - base;
    wire           room  = outst < RB;
    assign up_ready = link_up && room;
    wire           up_fire = up_valid && up_ready;
    // a sequenced flit is created for a record, or for pending credits
    wire           mk_cr  = link_up && room && !up_fire && (cr_pend != 0 || up_cr);
    wire           mk     = up_fire || mk_cr;
    wire [15:0]    cr_avail = cr_pend + (up_cr ? 16'd1 : 16'd0);
    wire [CRB-1:0] mk_ncr = (cr_avail > CRMAX) ? CRMAX[CRB-1:0] : cr_avail[CRB-1:0];

    // ACK of the received direction, carried on every flit
    wire [S-1:0]   my_ack = exp_seq - 1'b1;

    // send: the flit at sp, if any is pending; else idle
    wire           have = (sp != wr);
    wire [BW-1:0]  tbody;
    assign tbody[O_REC +: PW]  = have ? rb_rec[sp[LRB-1:0]] : {PW{1'b0}};
    assign tbody[O_NCR +: CRB] = have ? rb_ncr[sp[LRB-1:0]] : {CRB{1'b0}};
    assign tbody[O_DV]         = have ? rb_dv[sp[LRB-1:0]] : 1'b0;
    assign tbody[O_NAK]        = nak_req;
    assign tbody[O_ACK +: S]   = my_ack;
    assign tbody[O_AV]         = got_any;
    assign tbody[O_SEQ +: S]   = have ? sp : {S{1'b0}};
    assign tbody[O_SV]         = have;
    assign tbody[O_UP]         = rx_up;
    wire [31:0]    tcrc;
    ot_link_crc32 #(.W(BW)) u_tcrc (.d(tbody), .crc(tcrc));

    // ACK window check: ack in [base, wr)
    wire [S-1:0]   ack_off = r_ack - base;
    wire           ack_in  = r_good && r_av && (ack_off < outst);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_up <= 1'b0; far_up <= 1'b0; good_run <= 0;
            exp_seq <= 0; got_any <= 1'b0; nak_req <= 1'b0; nak_sent <= 1'b0;
            dn_valid <= 1'b0; dn_rec <= 0; dn_cr <= 1'b0;
            base <= 0; wr <= 0; sp <= 0; cr_pend <= 0; tmo_c <= 0; rep_run <= 0;
            tx_flit <= 0; link_fault <= 1'b0;
            n_crc_err <= 0; n_replay <= 0; n_seq_drop <= 0; n_sent <= 0;
        end else begin
            dn_valid <= 1'b0; dn_cr <= 1'b0;

            // ---- training
            if (rx_valid) begin
                if (r_good) begin
                    if (good_run != 8'hFF) good_run <= good_run + 1'b1;
                    if (good_run + 1 >= UPN) rx_up <= 1'b1;
                    far_up <= rbody[O_UP];
                end else good_run <= 0;
            end

            // ---- transmit: the flit of this cycle
            tx_flit <= {tcrc, tbody};
            if (have) sp <= sp + 1'b1;
            if (have) n_sent <= n_sent + 1;
            if (nak_req) begin nak_req <= 1'b0; nak_sent <= 1'b1; end

            // ---- new sequenced flit into the replay buffer
            if (mk) begin
                rb_rec[wr[LRB-1:0]] <= up_fire ? up_rec : {PW{1'b0}};
                rb_dv[wr[LRB-1:0]]  <= up_fire;
                rb_ncr[wr[LRB-1:0]] <= mk_ncr;
                wr <= wr + 1'b1;
                cr_pend <= cr_avail - mk_ncr;
            end else if (up_cr) cr_pend <= cr_pend + 1'b1;

            // ---- receive
            if (rx_valid && !r_good && rx_up) begin
                n_crc_err <= n_crc_err + 1;
                if (!nak_sent && !nak_req) nak_req <= 1'b1;
            end
            if (r_good && rx_up) begin
                // acknowledgements of our direction
                if (ack_in) begin
                    base <= r_ack + 1'b1;
                    tmo_c <= 0; rep_run <= 0;
                    // a send pointer behind the new base would resend acknowledged flits
                    if ((sp - base) <= ack_off) sp <= r_ack + 1'b1;
                end
                if (r_nak) begin
                    sp <= ack_in ? r_ack + 1'b1 : base;
                    n_replay <= n_replay + 1;
                    rep_run <= rep_run + 1'b1;
                end
                // the far direction's sequenced flits: exactly once, in order
                if (r_sv) begin
                    if (r_seq == exp_seq) begin
                        exp_seq <= exp_seq + 1'b1; got_any <= 1'b1; nak_sent <= 1'b0;
                        dn_valid <= rbody[O_DV];
                        dn_rec <= rbody[O_REC +: PW];
                        // credits are delivered one per cycle through the counter below
                    end else begin
                        n_seq_drop <= n_seq_drop + 1;
                        if (!nak_sent && !nak_req) nak_req <= 1'b1;
                    end
                end
            end

            // ---- replay timer
            if (outst != 0 && !(r_good && rx_up && ack_in)) begin
                if (tmo_c >= TMO) begin
                    tmo_c <= 0; sp <= base; n_replay <= n_replay + 1; rep_run <= rep_run + 1'b1;
                end else tmo_c <= tmo_c + 1'b1;
            end else if (outst == 0) tmo_c <= 0;
            if (rep_run >= MAXREP) link_fault <= 1'b1;

            // ---- received credits: one engine credit pulse per cycle
            if (cr_out_n != 0) dn_cr <= 1'b1;
        end
    end

    // received engine credits, drained one per cycle
    wire       acc_cr = r_good && rx_up && r_sv && (r_seq == exp_seq);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) cr_out_n <= 0;
        else cr_out_n <= cr_out_n + (acc_cr ? rbody[O_NCR +: CRB] : 16'd0) - ((cr_out_n != 0) ? 16'd1 : 16'd0);
    end
endmodule
