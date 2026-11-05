`timescale 1ns/1ps
// DIE-KV-70/ING 11-04: ot_hdc_ingest_fp8q cut in two (+1 edge in the engine, class Exact: same function of f, proved by
// miter against ot_hdc_ingest_fp8q, results/kv_ing_rf_1104/bench/run_fp8q.sh).
// p = {s, kind[1:0], mant[3:0], up, eb[3:0]}; kind 0 zero, 1 saturate, 2 normal, 3 subnormal.
module ot_hdc_ingest_fp8q_s1 (input wire [31:0] f, output reg [11:0] p);
    wire        s = f[31];
    wire [7:0]  e = f[30:23];
    wire [23:0] m = {1'b1, f[22:0]};
    reg  [1:0]  kind;
    reg  [3:0]  mant, eb;
    reg         up;
    always @* begin
        kind = 2'd0; mant = 4'd0; eb = 4'd0; up = 1'b0;
        if (e == 8'd0) kind = 2'd0;
        else if (e > 8'd135) kind = 2'd1;
        else if (e >= 8'd121) begin
            kind = 2'd2;
            mant = m[23:20];
            up = m[19] && ((|m[18:0]) || m[20]);
            eb = e[3:0] - 4'd8;                        // e - 120, 1 .. 15 (120 mod 16 = 8)
        end else begin
            kind = 2'd3;
            case (e)
                8'd120: begin mant = {1'b0, m[23:21]}; up = m[20] && ((|m[19:0]) || m[21]); end
                8'd119: begin mant = {2'b0, m[23:22]}; up = m[21] && ((|m[20:0]) || m[22]); end
                8'd118: begin mant = {3'b0, m[23]};    up = m[22]; end
                8'd117: begin mant = 4'd0;             up = |m[22:0]; end
                default: begin mant = 4'd0;            up = 1'b0; end   // e 116 below half the quantum; e < 116
            endcase
        end
    end
    always @* p = {s, kind, mant, up, eb};
endmodule

module ot_hdc_ingest_fp8q_s2 (input wire [11:0] p, output reg [7:0] q);
    wire       s    = p[11];
    wire [1:0] kind = p[10:9];
    wire [3:0] mant = p[8:5];
    wire       up   = p[4];
    wire [3:0] eb   = p[3:0];
    wire [4:0] qn0  = {1'b0, mant} + {4'd0, up};
    wire [4:0] eb1  = {1'b0, eb} + {4'd0, qn0[4]};
    wire [2:0] fr   = qn0[4] ? 3'd0 : qn0[2:0];
    wire       sat  = eb1[4] || (eb1[3:0] == 4'd15 && fr == 3'd7);
    always @* begin
        q = 8'h00;
        case (kind)
            2'd0: q = 8'h00;
            2'd1: q = {s, 7'h7E};
            2'd2: q = sat ? {s, 7'h7E} : {s, eb1[3:0], fr};
            2'd3: if (qn0[3:0] == 4'd0) q = 8'h00;
                  else if (qn0[3]) q = {s, 7'h08};
                  else q = {s, 4'd0, qn0[2:0]};
        endcase
    end
endmodule
