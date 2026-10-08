`timescale 1ns/1ps
// Opt-in front_s request FIFO candidate, modeled by
// tools/hbm_smh_front_s_fifo_model.py. Baseline f7f1a0ee4.
// Dual-rail cached state detects a single cached-bit upset and suppresses a
// transfer until resynchronization. Post-synthesis independent storage and
// physical checker timing remain adoption gates. Count/pointer scope unchanged.
module ot_hbm_accel_smh_csnk_ne #(
    parameter integer W = 8,
    parameter integer PK = 1,
    parameter integer PRK = 1,
    parameter integer DEPTH = 9
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         i_v,
    input  wire [W-1:0] i_d,
    output wire         o_ret,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data,
    output wire         state_fault
);
    localparam integer CW = $clog2(DEPTH + 1);
    localparam integer AW = (DEPTH <= 1) ? 1 : $clog2(DEPTH);
    wire          f_v;
    wire [W-1:0]  f_d;
    ot_hbm_accel_smv_chain #(.W(1), .D(PK), .RST(1)) u_fv (.clk(clk), .rst_n(rst_n), .d(i_v), .q(f_v));
    ot_hbm_accel_smv_chain #(.W(W), .D(PK), .RST(0)) u_fd (.clk(clk), .rst_n(rst_n), .d(i_d), .q(f_d));
    reg  [W-1:0]  mem [0:DEPTH-1];
    reg  [AW-1:0] wp, rp, rp1;
    reg  [CW-1:0] cnt;
    reg  [W-1:0]  head;
    wire          pop = m_valid && m_ready;
    (* keep = 1, dont_touch = 1 *) reg nonempty;
    (* keep = 1, dont_touch = 1 *) reg empty;
    assign m_valid = nonempty && !empty;
    assign state_fault = (nonempty == empty);
    // Cache exactly the old cnt!=0 predicate.  The last-pop comparator ends
    // at this one flop, outside the head-data enable path.  No latency changes.
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin nonempty <= 1'b0; empty <= 1'b1; end
        else case ({f_v, pop})
            2'b10: begin nonempty <= 1'b1; empty <= 1'b0; end
            2'b01: begin nonempty <= (cnt != 1); empty <= (cnt == 1); end
            default: begin nonempty <= (cnt != 0); empty <= (cnt == 0); end
        endcase
    assign m_data = head;
    wire [AW-1:0] wp1 = (wp == DEPTH - 1) ? {AW{1'b0}} : wp + 1'b1;
    wire [AW-1:0] rp2 = (rp1 == DEPTH - 1) ? {AW{1'b0}} : rp1 + 1'b1;
    wire          land_head = f_v && (pop ? (wp == rp1) : (wp == rp));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; rp1 <= (DEPTH == 1) ? {AW{1'b0}} : 1; cnt <= 0; end
        else begin
            if (f_v) wp <= wp1;
            if (pop) begin rp <= rp1; rp1 <= rp2; end
            cnt <= cnt + f_v - pop;
        end
    always @(posedge clk) begin
        if (f_v) mem[wp] <= f_d;
        if (land_head) head <= f_d;
        else if (pop) head <= mem[rp1];
    end
    ot_hbm_accel_smv_chain #(.W(1), .D(PRK), .RST(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(pop), .q(o_ret));
endmodule
