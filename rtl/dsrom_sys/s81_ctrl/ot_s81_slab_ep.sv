`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_slab_ep (s81-ctl-1011 under ds-1010, 2026-10-11): the command / start / done endpoint of one S81 slab master
// (physical/s81_ctrl/ADAPTER_CONTRACT_1011.json v2).  It is the pinned ot_s81_engine_adapter (QD 8, done-credit, pulse
// CDC both ways) plus
//   * die pins: c_cmd = {v, descriptor 84} from dsfd_sp_ctrl_e c<e> (captured in pin flops), c_done = {v, tag 8} and
//     c_st = {online, fault} to dsfd_sp_ctrl_e d<e> / the slab status (launched from flops);
//   * an in-order job queue on the engine side (JQ entries): the slab logic sees the head descriptor (j_v / j_d),
//     reports its REAL completion of that head (j_done, never a constant) and the queue returns the head's tag
//     {slot, op} = {d[83], d[6:0]} as e_done_tag.  e_cmd_ready = queue not full; e_inputs_present = j_present (the
//     slab's operand condition for the next descriptor).
// The slab master decides what start and completion mean (gather: phase issue / capture drained; selector /
// collector: DONE word of the job); the adapter's credit (one credit returned only by a validated done) bounds the
// descriptors in flight to QD across the die nets, the adapter queues and this job queue together.
// Faults (sticky, fail closed, on c_st[0]): the adapter's (command without credit, duplicate pending tag, done for a
// non-pending tag), j_done with an empty queue, and slab_fault.
// Negative controls (MUT): 2 wrong done tag (the adapter's MUT 2), 3 early start (the adapter sees inputs present
// regardless of j_present), 4 dropped done (the second completion of the run never reaches the adapter).
// Latency: +1 pin flop on c_cmd, +1 output flop on c_done beyond the adapter's ~2 sync + 2 register cycles each way.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_slab_ep #(parameter integer QD = 8, JQ = 2, MUT = 0) (
    input  wire         c_clk, c_rst_n,
    input  wire [84:0]  c_cmd,           // {v, d84}: die pins
    output reg  [8:0]   c_done,          // {v, tag8}: die pins
    output reg  [1:0]   c_st,            // {online, fault}
    input  wire         e_clk, e_rst_n,
    output wire         j_v,             // head descriptor valid
    output wire [83:0]  j_d,
    output wire         j_new,           // one-cycle pulse: a descriptor entered the queue (this cycle)
    output wire [83:0]  j_new_d,
    input  wire         j_present,       // operands of the next descriptor present (gates issue)
    input  wire         j_done,          // REAL completion of the head descriptor
    input  wire         slab_fault,
    output wire         ep_fault          // engine-side sticky fault (j_done with no job)
);
    // pin capture
    reg cv_q; reg [83:0] cd_q;
    always @(posedge c_clk or negedge c_rst_n) if (!c_rst_n) cv_q <= 1'b0; else cv_q <= c_cmd[84];
    always @(posedge c_clk) cd_q <= c_cmd[83:0];
    wire a_dv; wire [7:0] a_dt; wire a_f, a_on;
    wire e_cv, e_cr, e_ip; wire [83:0] e_cd; wire e_dv; wire [7:0] e_dt;
    ot_s81_engine_adapter #(.QD(QD), .MUT(MUT == 2 ? 2 : 0)) u_ad (
        .c_clk(c_clk), .c_rst_n(c_rst_n), .c_cmd_v(cv_q), .c_cmd_d(cd_q), .c_done_v(a_dv), .c_done_tag(a_dt),
        .fault(a_f), .online(a_on),
        .e_clk(e_clk), .e_rst_n(e_rst_n), .e_cmd_v(e_cv), .e_cmd_d(e_cd), .e_cmd_ready(e_cr),
        .e_inputs_present(e_ip), .e_done_v(e_dv), .e_done_tag(e_dt));
    // engine-side job queue
    localparam integer AW = (JQ <= 2) ? 1 : $clog2(JQ);
    reg [83:0] q [0:JQ-1]; reg [AW-1:0] wp, rp; reg [AW:0] n;
    reg ef, dropped, cnt1;
    assign e_cr = (n < JQ);
    assign e_ip = (MUT == 3) ? 1'b1 : j_present;
    wire push = e_cv && e_cr;
    wire pop  = j_done && (n != 0);
    assign j_v = (n != 0);
    assign j_d = q[rp];
    assign j_new = push;
    assign j_new_d = e_cd;
    wire drop = (MUT == 4) && pop && !dropped && cnt1;
    assign e_dv = pop && !drop;
    assign e_dt = {q[rp][83], q[rp][6:0]};
    assign ep_fault = ef;
    always @(posedge e_clk or negedge e_rst_n)
        if (!e_rst_n) begin wp <= 0; rp <= 0; n <= 0; ef <= 1'b0; dropped <= 1'b0; cnt1 <= 1'b0; end
        else begin
            if (push) begin q[wp] <= e_cd; wp <= (wp == JQ - 1) ? 0 : wp + 1'b1; end
            if (pop) begin rp <= (rp == JQ - 1) ? 0 : rp + 1'b1; cnt1 <= 1'b1; end
            if (drop) dropped <= 1'b1;
            case ({push, pop}) 2'b10: n <= n + 1'b1; 2'b01: n <= n - 1'b1; default: n <= n; endcase
            if (j_done && n == 0) ef <= 1'b1;
        end
    // slab / engine-side faults into the controller domain (sticky level, 2-flop)
    reg sf1, sf2;
    always @(posedge c_clk or negedge c_rst_n)
        if (!c_rst_n) begin sf1 <= 1'b0; sf2 <= 1'b0; end else begin sf1 <= ef | slab_fault; sf2 <= sf1; end
    always @(posedge c_clk or negedge c_rst_n)
        if (!c_rst_n) begin c_done <= 9'd0; c_st <= 2'b00; end
        else begin c_done <= {a_dv, a_dt}; c_st <= {a_on, a_f | sf2}; end
endmodule
