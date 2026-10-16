`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_svcio_job (s81-svceng-1011, 2026-10-11): the engine-4 job TILE of one scan-service slab, at the IO hub's N-E
// pin group beside dsfd_svcio_q.  ot_s81_svc_job between the die q pin and the closed q tile (q: pin flop -> gate ->
// output flop, +2 cycles), and END observation by TAPS of the hub output tiles' pin flops (per stream {v, data[507:495],
// data[491:480]} = 26 b, registered here: the frame parse runs one cycle behind the pins, no added cycle on any
// output).  j = {v, arg 24, tag 8} from dsfd_svc_join, jd = {fault, done} back (flops at both ends).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_svcio_job #(parameter integer MUT = 0) (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,
    input  wire [32:0]  j,
    output wire [1:0]   jd,
    input  wire [514:0] q,          // die pin
    output reg  [514:0] q_o,        // -> dsfd_svcio_q q
    input  wire [25:0]  t_a0, t_a1, t_x, t_od     // taps {data[491:480], data[507:495], v}
);
    reg [1:0] rs_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    reg [514:0] q_i; reg [25:0] a0_q, a1_q, x_q, od_q;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin q_i[0] <= 1'b0; a0_q[0] <= 1'b0; a1_q[0] <= 1'b0; x_q[0] <= 1'b0; od_q[0] <= 1'b0; q_o[0] <= 1'b0; end
        else begin q_i[0] <= q[0]; a0_q[0] <= t_a0[0]; a1_q[0] <= t_a1[0]; x_q[0] <= t_x[0]; od_q[0] <= t_od[0]; q_o[0] <= cq[0]; end
    always @(posedge ck[0]) begin
        q_i[514:1] <= q[514:1]; a0_q[25:1] <= t_a0[25:1]; a1_q[25:1] <= t_a1[25:1]; x_q[25:1] <= t_x[25:1]; od_q[25:1] <= t_od[25:1];
        q_o[514:1] <= cq[514:1];
    end
    function automatic [511:0] wd(input [25:0] t);
        begin wd = 512'd0; wd[507:495] = t[13:1]; wd[491:480] = t[25:14]; end
    endfunction
    wire [514:0] cq;
    ot_s81_svc_job #(.MUT(MUT)) u_j (.ck(ck[0]), .rs_n(rn), .j_cmd(j), .j_dn(jd), .q(q_i), .core_q(cq),
        .ad({wd(a1_q), a1_q[0], wd(a0_q), a0_q[0]}), .xd({wd(x_q), x_q[0], 1'b1}), .od({wd(od_q), od_q[0], 1'b1}));
endmodule

