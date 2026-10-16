`timescale 1ns/1ps
`default_nettype none
// Distinct physical candidate. Every input enters an unconditional capture FF.
// Actual state semantics are shifted one edge; current parents are unchanged.
// +164 FF/master, +1 edge to every read/write visibility, II=1.
module ot_hgi_coll_pring_static_state_capture_lane(
    input wire  clk,
    input wire  lp_we,
    input wire [2:0] lp_tag,
    input wire [31:0] lp_data,
    input wire  acc_we,
    input wire [2:0] acc_tag,
    input wire [31:0] acc_data,
    input wire [1:0] carry_we,
    input wire [2:0] carry0_tag,
    input wire [2:0] carry1_tag,
    input wire [1:0] carry0_src,
    input wire [1:0] carry1_src,
    input wire [31:0] carry0_data,
    input wire [31:0] carry1_data,
    input wire  read_add,
    input wire  read_tx,
    input wire  read_rr,
    input wire  read_rhs_acc,
    input wire  read_tx_acc,
    input wire [2:0] add_tag,
    input wire [2:0] tx_tag,
    input wire [2:0] rr_tag,
    input wire [1:0] add_src,
    output wire [31:0] rhs_add,
    output wire [31:0] carry_add,
    output wire [31:0] tx_data,
    output wire [31:0] acc_rr
);
    (* keep=1, dont_touch=1 *) reg  cap_lp_we;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_lp_tag;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_lp_data;
    (* keep=1, dont_touch=1 *) reg  cap_acc_we;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_acc_tag;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_acc_data;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_carry_we;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_carry0_tag;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_carry1_tag;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_carry0_src;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_carry1_src;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_carry0_data;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_carry1_data;
    (* keep=1, dont_touch=1 *) reg  cap_read_add;
    (* keep=1, dont_touch=1 *) reg  cap_read_tx;
    (* keep=1, dont_touch=1 *) reg  cap_read_rr;
    (* keep=1, dont_touch=1 *) reg  cap_read_rhs_acc;
    (* keep=1, dont_touch=1 *) reg  cap_read_tx_acc;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_add_tag;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_tx_tag;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_rr_tag;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_add_src;
    always @(posedge clk) begin
        cap_lp_we <= lp_we;
        cap_lp_tag <= lp_tag;
        cap_lp_data <= lp_data;
        cap_acc_we <= acc_we;
        cap_acc_tag <= acc_tag;
        cap_acc_data <= acc_data;
        cap_carry_we <= carry_we;
        cap_carry0_tag <= carry0_tag;
        cap_carry1_tag <= carry1_tag;
        cap_carry0_src <= carry0_src;
        cap_carry1_src <= carry1_src;
        cap_carry0_data <= carry0_data;
        cap_carry1_data <= carry1_data;
        cap_read_add <= read_add;
        cap_read_tx <= read_tx;
        cap_read_rr <= read_rr;
        cap_read_rhs_acc <= read_rhs_acc;
        cap_read_tx_acc <= read_tx_acc;
        cap_add_tag <= add_tag;
        cap_tx_tag <= tx_tag;
        cap_rr_tag <= rr_tag;
        cap_add_src <= add_src;
    end
    ot_hgi_coll_pring_static_state_lane u_state(
        .clk(clk),
        .lp_we(cap_lp_we),
        .lp_tag(cap_lp_tag),
        .lp_data(cap_lp_data),
        .acc_we(cap_acc_we),
        .acc_tag(cap_acc_tag),
        .acc_data(cap_acc_data),
        .carry_we(cap_carry_we),
        .carry0_tag(cap_carry0_tag),
        .carry1_tag(cap_carry1_tag),
        .carry0_src(cap_carry0_src),
        .carry1_src(cap_carry1_src),
        .carry0_data(cap_carry0_data),
        .carry1_data(cap_carry1_data),
        .read_add(cap_read_add),
        .read_tx(cap_read_tx),
        .read_rr(cap_read_rr),
        .read_rhs_acc(cap_read_rhs_acc),
        .read_tx_acc(cap_read_tx_acc),
        .add_tag(cap_add_tag),
        .tx_tag(cap_tx_tag),
        .rr_tag(cap_rr_tag),
        .add_src(cap_add_src),
        .rhs_add(rhs_add),
        .carry_add(carry_add),
        .tx_data(tx_data),
        .acc_rr(acc_rr)
    );
endmodule
`default_nettype wire
