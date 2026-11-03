// PREP ONLY. No production file imports this fragment.
// Exact 14-bit projection of u_wtx W=110,N=2,P=62,MUT=0,IDLE_ZERO=0.
// b0 = d[61:48], owe = owe[0], q = hold[61:48], o = oq_p[61:48].
// No reset or initializer is added. start/owe are unconstrained at this cut.
module head_pad_fragment #(
    parameter integer PRESERVE_MODE = 0  // default OFF; 0 baseline, 1 wire-keep, 2 kept generic leaf, 3 native leaf
)(input wire ck, start, owe, input wire [13:0] b0,
  output reg [13:0] o);
    wire write_pad = start | owe;
    wire [13:0] q;
    generate if (PRESERVE_MODE == 3) begin : g_native
        for (genvar i=0; i<14; i=i+1) begin : g_pad
            // DFFHQN's true D stores q; QN is the complement of q.
            wire qn;
            wire d_pad = ~(qn | write_pad);
            (* keep = 1, dont_touch = 1 *)
            DFFHQNx1_ASAP7_75t_R u_state (.CLK(ck), .D(d_pad), .QN(qn));
            assign q[i] = ~qn;
        end
    end else if (PRESERVE_MODE == 2) begin : g_leaf
        // This probe has NOT established preservation inside the kept module.
        (* keep_hierarchy = 1, keep = 1 *) head_pad_generic_leaf u_state
            (.ck(ck), .write_pad(write_pad), .q(q));
    end else if (PRESERVE_MODE == 1) begin : g_wire_keep
        (* keep = 1, dont_touch = 1 *) reg [13:0] state;
        always @(posedge ck) if (write_pad) state <= 14'b0;
        assign q = state;
    end else begin : g_baseline
        reg [13:0] state;
        always @(posedge ck) if (write_pad) state <= 14'b0;
        assign q = state;
    end endgenerate
    always @(posedge ck)
        if (start) o <= b0;
        else o <= q;
endmodule

(* keep_hierarchy = 1 *)
module head_pad_generic_leaf(input wire ck, write_pad, output reg [13:0] q);
    always @(posedge ck) if (write_pad) q <= 14'b0;
endmodule
