`timescale 1ns/1ps
// S81-SERDES 10-19: the small leaves of the wires-only SerDes column parent ot_pdie_serdes_col_flat (all glue of
// ot_pdie_serdes_col moved into children, so tools/landed_parent/lp.py can generate the landed column).
// ot_s81_col_live: the stream-valid flag of one clock family (tx_v of the encoder, p_v of the syndrome tile): 0 in reset,
//   1 from the first edge after release.  Replaces the old "valid = reset synchroniser output" glue (one edge later).
module ot_s81_col_live (
    input  wire clk,
    input  wire rst_n,
    output reg  q
);
    always @(posedge clk) if (!rst_n) q <= 1'b0; else q <= 1'b1;
endmodule

// ot_s81_col_sts: the column status CDC (pma_rck family -> core clk), a CDC child (lp.py child_pin_regions):
//   ck_r side: sticky uncorrectable flag (first beat of a frame flagged unc), lock input captured by the recovered clock;
//   ck_t side: 2-flop synchronisers of lock and the sticky flag, st = {lock, sticky fault | rm fault | enc fault}.
//   Same function as the status glue of ot_pdie_serdes_col / ot_pdie_serdes (synchronous resets: the lp reset runs).
module ot_s81_col_sts (
    input  wire       ck_r,
    input  wire       rst_r_n,
    input  wire       lock,
    input  wire       q_v,
    input  wire       q_first,
    input  wire       q_unc,
    input  wire       ck_t,
    input  wire       rst_t_n,
    input  wire       rm_flt,
    input  wire       e_flt,
    output reg  [1:0] st
);
    reg unc_r, lock_r;
    always @(posedge ck_r)
        if (!rst_r_n) begin unc_r <= 1'b0; lock_r <= 1'b0; end
        else begin lock_r <= lock; if (q_v && q_first && q_unc) unc_r <= 1'b1; end
    reg [1:0] lk_s, uf_s;
    always @(posedge ck_t)
        if (!rst_t_n) begin lk_s <= 2'b00; uf_s <= 2'b00; st <= 2'b00; end
        else begin
            lk_s <= {lk_s[0], lock_r}; uf_s <= {uf_s[0], unc_r};
            st <= {lk_s[1], st[0] | uf_s[1] | rm_flt | e_flt};
        end
endmodule
