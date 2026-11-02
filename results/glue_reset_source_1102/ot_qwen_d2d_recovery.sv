module ot_qwen_d2d_recovery #(
    parameter integer MASTER = 1, DRAIN = 32, RSTC = 16, BUMP = 3
) (
    input  wire       ck,
    input  wire       por_n,          // power-on only: epoch counter
    input  wire       rst_n,
    input  wire       abort,          // end epoch_abort | end_fault
    input  wire [7:0] fault_cause,
    input  wire       end_fault,
    input  wire       p_tx_up,
    input  wire       p_tx_v, p_rx_v,
    input  wire       reset_req,      // MASTER: HOST lifecycle link_reset_request (level, sampled in DRAINED)
    input  wire       recovery_clear, // MASTER: HOST recovery_complete after retrained (pulse)
    input  wire       boot_begin,     // MASTER: HOST boot_go (level; its rising edge starts the first epoch); FOLLOWER: unused
    input  wire       fwd_epoch_i,    // FOLLOWER: forwarded epoch strobe from the bump
    output wire       fwd_epoch_o,    // MASTER: forwarded epoch strobe to the bump (registered)
    output wire       fwd_link_rst_n, // MASTER: forwarded link reset to the compute die PHY (registered)
    output wire       phy_rst_n,      // own PHY reset
    output reg        epoch_begin,
    output reg  [7:0] epoch,
    output reg        link_up,        // registered (pin flop): PHY tx_up is on the N face, HOST status on E (gate reach)
    output wire       links_drained,
    output wire       link_reset_seen,
    output wire       retrained,
    output reg  [7:0] transport_fault,// typed, sticky until the next epoch_begin
    output wire       recovering,
    output reg  [31:0] recovery_cycles // measured length of the last exceptional episode (abort -> epoch_begin)
);
    localparam [2:0] S_RUN = 0, S_DRAIN = 1, S_DRAINED = 2, S_RST = 3, S_TRAIN = 4, S_READY = 5;
    reg [2:0] st; reg [15:0] n; reg seen, lrst, fep, bq;
    reg [BUMP-1:0] eq;            // MASTER local copy of the forwarded strobe delay
    reg [BUMP-1:0] fq;            // FOLLOWER capture flops
    reg counting;
    assign fwd_epoch_o = fep;
    assign fwd_link_rst_n = ~lrst;
    assign phy_rst_n = rst_n & ~lrst;
    assign links_drained = (st == S_DRAINED) || (st == S_RST) || (st == S_TRAIN) || (st == S_READY);
    assign link_reset_seen = seen;
    assign retrained = (st == S_READY);
    assign recovering = (st != S_RUN);
    wire begin_now = MASTER ? eq[BUMP-1] : fq[BUMP-1];
    always @(posedge ck or negedge por_n)
        if (!por_n) begin epoch <= 8'd0; end
        else if (epoch_begin) epoch <= epoch + 8'd1;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_RUN; n <= 0; seen <= 0; lrst <= 0; fep <= 0; eq <= 0; fq <= 0; epoch_begin <= 0; bq <= 0; link_up <= 0;
            transport_fault <= 0; counting <= 0; recovery_cycles <= 0;
        end else begin
            fep <= 1'b0; epoch_begin <= begin_now; bq <= boot_begin;
            link_up <= p_tx_up && (st == S_RUN) && !abort;   // = the former combinational level, one edge later
            eq <= {eq, fep}; fq <= {fq, fwd_epoch_i};
            if (counting) recovery_cycles <= recovery_cycles + 1;
            if (begin_now) begin st <= S_RUN; seen <= 0; counting <= 0; transport_fault <= 0; end
            case (st)
            S_RUN: begin
                if (MASTER && boot_begin && !bq) fep <= 1'b1;
                if (abort && !epoch_begin) begin
                    st <= MASTER ? S_DRAIN : S_READY; n <= 0; counting <= 1; recovery_cycles <= 0;
                    transport_fault <= fault_cause | {end_fault, 7'd0};
                end
            end
            S_DRAIN: if (p_tx_v || p_rx_v) n <= 0; else if (n == DRAIN - 1) st <= S_DRAINED; else n <= n + 1;
            S_DRAINED: if (reset_req) begin st <= S_RST; n <= 0; lrst <= 1; end
            S_RST: begin
                if (!p_tx_up) seen <= 1;
                if (n == RSTC - 1) begin lrst <= 0; st <= S_TRAIN; end else n <= n + 1;
            end
            S_TRAIN: if (seen && p_tx_up) st <= S_READY;
            S_READY: if (MASTER && recovery_clear) fep <= 1'b1;
            default: st <= S_RUN;
            endcase
        end
    end
endmodule
