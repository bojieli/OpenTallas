// ot_chip_v41_pg_ctrl -- stage power-gating controller of the V4.1 ROM layer die (W18).
//
// One controller per gated power domain.  It lives in the die's ALWAYS-ON island (the hub's VM column,
// W10 re-fit) and drives the domain's header-switch rings (tools/w18/die_pdn.py switch_ring), its output
// isolation, its reset and its clock enable.  The domain is split into NSUB sub-domains (switch-ring
// segments) that are enabled one after another, ``cfg_step`` cycles apart and only after the previous
// segment's ring has acknowledged (the ack is the last header cell of the ring's enable daisy chain), which
// bounds the rush current: the W14 model's staggered wake is ~100 ten-cycle sub-domains in 1 us
// (ReGate 10-cycle domains), i.e. NSUB = 100, cfg_step = 10 at 1.087 GHz.
//
// Power-up   : OFF -> (req_on) UP: sw_en[i] rises in order, each >= cfg_step cycles after the previous and
//              after sw_ack[i-1] -> all acks -> RST: domain reset held cfg_rst cycles with its clock enabled
//              (synchronous reset needs edges) -> ISO release -> ON (pwr_good).
// Power-down : ON -> (!req_on) clock off -> isolate -> assert reset -> all switches off at once (turn-off
//              draws no rush current) -> all acks low -> OFF.
// A request that changes mid-sequence completes the sequence in progress first.
// An ack that does not arrive within cfg_ack_to cycles (a dead ring segment) latches ``fault`` and holds
// the domain isolated and in reset; only rst_n clears it.
module ot_chip_v41_pg_ctrl #(
    parameter int NSUB = 100,
    parameter int CW   = 16
) (
    input  logic            clk,        // always-on clock
    input  logic            rst_n,      // always-on reset
    input  logic            req_on,     // level: the schedule wants the domain powered
    input  logic [CW-1:0]   cfg_step,   // cycles between consecutive segment enables (>= 1)
    input  logic [7:0]      cfg_rst,    // domain reset cycles after the last ack (>= 1)
    input  logic [CW-1:0]   cfg_ack_to, // ack timeout, cycles
    output logic [NSUB-1:0] sw_en,      // header ring segment enables (1 = switches on)
    input  logic [NSUB-1:0] sw_ack,     // ring segment acknowledges (daisy-chain tail)
    output logic            iso_n,      // 0 = domain outputs clamped
    output logic            dom_rst_n,  // domain reset
    output logic            clk_en,     // domain clock enable (to the domain's root ICG)
    output logic            pwr_good,   // domain usable
    output logic            fault
);
    typedef enum logic [2:0] {S_OFF, S_UP, S_RST, S_ISO, S_ON, S_DN_CLK, S_DN_ISO, S_DN_SW} st_t;
    st_t st;
    localparam int IW = (NSUB > 1) ? $clog2(NSUB + 1) : 1;
    logic [IW-1:0] idx;          // next segment to enable
    logic [CW-1:0] cnt;
    logic          all_ack, none_ack;
    assign all_ack  = &sw_ack;
    assign none_ack = ~|sw_ack;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_OFF; idx <= '0; cnt <= '0; sw_en <= '0;
            iso_n <= 1'b0; dom_rst_n <= 1'b0; clk_en <= 1'b0; pwr_good <= 1'b0; fault <= 1'b0;
        end else if (fault) begin
            iso_n <= 1'b0; dom_rst_n <= 1'b0; clk_en <= 1'b0; pwr_good <= 1'b0;
        end else begin
            case (st)
                S_OFF: if (req_on && none_ack) begin
                    st <= S_UP; idx <= '0; cnt <= cfg_step;   // first segment enables immediately
                end
                S_UP: begin
                    // enable segment idx once the spacing has elapsed and the previous segment has acked
                    if (idx == IW'(NSUB)) begin
                        if (all_ack) begin st <= S_RST; cnt <= CW'(cfg_rst); clk_en <= 1'b1; end
                        else if (cnt >= cfg_ack_to) fault <= 1'b1;
                        else cnt <= cnt + 1'b1;
                    end else if (cnt >= cfg_step && (idx == '0 || sw_ack[idx - 1'b1])) begin
                        sw_en[idx] <= 1'b1; idx <= idx + 1'b1; cnt <= 1;
                    end else if (idx != '0 && !sw_ack[idx - 1'b1] && cnt >= cfg_ack_to) begin
                        fault <= 1'b1;
                    end else cnt <= cnt + 1'b1;
                end
                S_RST: if (cnt <= 1) begin dom_rst_n <= 1'b1; st <= S_ISO; end
                       else cnt <= cnt - 1'b1;
                S_ISO: begin iso_n <= 1'b1; pwr_good <= 1'b1; st <= S_ON; end
                S_ON: if (!req_on) begin pwr_good <= 1'b0; clk_en <= 1'b0; st <= S_DN_CLK; end
                S_DN_CLK: begin iso_n <= 1'b0; st <= S_DN_ISO; end
                S_DN_ISO: begin dom_rst_n <= 1'b0; sw_en <= '0; cnt <= '0; st <= S_DN_SW; end
                S_DN_SW: if (none_ack) st <= S_OFF;
                         else if (cnt >= cfg_ack_to) fault <= 1'b1;
                         else cnt <= cnt + 1'b1;
                default: st <= S_OFF;
            endcase
        end
    end
endmodule
