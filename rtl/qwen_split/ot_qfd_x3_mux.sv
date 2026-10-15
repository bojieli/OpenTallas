`timescale 1ns/1ps
// Real Q/KVN transport owner. The compiler schedules source arrivals and
// dispatch slots, including the one-edge registered output stage. Two entries
// per source absorb the statically reserved burst. No runtime credits, ready
// signals, backpressure or arbitration can alter the compiled timeline.
// No packet payload or tag is synthesized here. Q belongs to tag 001 only;
// the KVN producer cannot inject Q. The compiler selects the source in each slot.
module ot_qfd_x3_mux #(
    parameter integer MUT = 0
) (
    input wire ck, input wire rst_n,
    input wire [523:0] q,
    input wire kvn_v,
    input wire [511:0] kvn_d,
    input wire [10:0] kvn_tag,
    input wire slot_v,
    input wire slot_q,
    output reg x3_v,
    output reg [511:0] x3_d,
    output reg [10:0] x3_tag,
    output reg fault
);
    reg [522:0] qf [0:1], kf [0:1];
    reg qr, qw, kr, kw;
    reg [1:0] qn, kn;
    wire choose_q = MUT == 1 ? !slot_q : slot_q;
    // An invalid schedule terminates with fault; it cannot defer the slot or
    // grant it to the other source. Valid executions always dispatch as planned.
    wire available = choose_q ? qn != 0 : kn != 0;
    wire send = slot_v && available && !fault;
    wire qp = send && choose_q, kp = send && !choose_q;
    wire bad_q = q[523] && (q[522:520] != 3'b001 || q[519:518] != 0 || q[517]);
    wire bad_k = kvn_v && kvn_tag[10:8] == 3'b001;
    wire qi = q[523] && !bad_q && (qn < 2 || qp) && !fault;
    wire ki = kvn_v && !bad_k && (kn < 2 || kp) && !fault;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qw <= 0; kr <= 0; kw <= 0;
            qn <= 0; kn <= 0;
            x3_v <= 0; x3_d <= 0; x3_tag <= 0; fault <= 0;
        end else begin
            x3_v <= send;
            if (bad_q || bad_k || (q[523] && !bad_q && !qi) || (kvn_v && !bad_k && !ki)) fault <= 1;
            if (slot_v && !available) fault <= 1;
            if (send) begin
                {x3_tag, x3_d} <= choose_q ? qf[qr] : kf[kr];
                if (MUT == 2 && choose_q) x3_d <= qf[qr][511:0] ^ 512'b1;
            end
            if (qi) begin qf[qw] <= q[522:0]; qw <= !qw; end
            if (ki) begin kf[kw] <= {kvn_tag,kvn_d}; kw <= !kw; end
            if (qp) qr <= !qr;
            if (kp) kr <= !kr;
            case ({qi,qp})
                2'b10: qn <= qn + 1'b1;
                2'b01: qn <= qn - 1'b1;
                default: ;
            endcase
            case ({ki,kp})
                2'b10: kn <= kn + 1'b1;
                2'b01: kn <= kn - 1'b1;
                default: ;
            endcase
        end
    end
endmodule
