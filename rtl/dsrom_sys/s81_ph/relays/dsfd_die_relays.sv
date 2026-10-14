`timescale 1ns/1ps
// Fixed hard masters for the existing die composition state. All stages retain
// the source latency and reset bits; payload registers remain reset-free.
(* keep_hierarchy = "yes" *)
module dsfd_die_rstsync(input wire ck, rst, output wire rn);
    reg [1:0] q;
    always @(posedge ck or negedge rst) if (!rst) q <= 2'b00; else q <= {q[0],1'b1};
    assign rn=q[1];
endmodule
(* keep_hierarchy = "yes" *)
module dsfd_be_r55(input wire ck, input wire [54:0] i, output reg [54:0] o);
    always @(posedge ck) o <= i;
endmodule
(* keep_hierarchy = "yes" *)
module dsfd_die_r1(input wire ck, input wire i, output reg o);
    always @(posedge ck) o <= i;
endmodule

(* keep_hierarchy = "yes" *)
module dsfd_hrow_r15(input wire ck, rn, input wire [14:0] i, output reg [14:0] o);
    always @(posedge ck or negedge rn) if (!rn) o[0] <= 1'b0; else o[0] <= i[0];
    always @(posedge ck) o[14:1] <= i[14:1];
endmodule

(* keep_hierarchy = "yes" *)
module dsfd_hrow_r23(input wire ck, rn, input wire [22:0] i, output reg [22:0] o);
    always @(posedge ck or negedge rn) if (!rn) o[0] <= 1'b0; else o[0] <= i[0];
    always @(posedge ck or negedge rn) if (!rn) o[21] <= 1'b0; else o[21] <= i[21];
    always @(posedge ck) o[20:1] <= i[20:1];
    always @(posedge ck) o[22] <= i[22];
endmodule

(* keep_hierarchy = "yes" *)
module dsfd_hrow_r1025(input wire ck, rn, input wire [1024:0] i, output reg [1024:0] o);
    always @(posedge ck or negedge rn) if (!rn) o[0] <= 1'b0; else o[0] <= i[0];
    always @(posedge ck) o[1024:1] <= i[1024:1];
endmodule

(* keep_hierarchy = "yes" *)
module dsfd_hrow_r2079(input wire ck, rn, input wire [2078:0] i, output reg [2078:0] o);
    always @(posedge ck or negedge rn) if (!rn) o[0] <= 1'b0; else o[0] <= i[0];
    always @(posedge ck or negedge rn) if (!rn) o[1039] <= 1'b0; else o[1039] <= i[1039];
    always @(posedge ck or negedge rn) if (!rn) o[1054] <= 1'b0; else o[1054] <= i[1054];
    always @(posedge ck) o[1038:1] <= i[1038:1];
    always @(posedge ck) o[1053:1040] <= i[1053:1040];
    always @(posedge ck) o[2078:1055] <= i[2078:1055];
endmodule

// Optional FE sticky-status transport. Clock/reset are the BE serial domain;
// synchronous reset uses the existing BE die synchroniser, with no extra CDC.
(* keep_hierarchy = "yes" *)
module dsfd_be_f16(input wire ck, rn, input wire [15:0] i, output reg [15:0] o);
    always @(posedge ck) if (!rn) o <= 16'd0; else o <= i;
endmodule
module dsfd_be_fault_path #(parameter integer STAGES = 0)(
    input wire ck, rn, input wire [15:0] i, output wire [15:0] o
);
    initial if (STAGES < 0) $error("dsfd_be_fault_path: STAGES must be nonnegative");
    wire [15:0] q [0:STAGES];
    assign q[0] = i;
    genvar s;
    generate for (s = 0; s < STAGES; s = s + 1) begin : g_stage
        dsfd_be_f16 u_r (.ck(ck), .rn(rn), .i(q[s]), .o(q[s+1]));
    end endgenerate
`ifdef OT_BE_FAULT_MUT_BYPASS
    assign o = i;
`elsif OT_BE_FAULT_MUT_WRONG_STAGE
    generate if (STAGES > 0) begin : g_mut
        assign o = q[STAGES-1];
    end else begin : g_zero
        assign o = i;
    end endgenerate
`else
    assign o = q[STAGES];
`endif
endmodule
