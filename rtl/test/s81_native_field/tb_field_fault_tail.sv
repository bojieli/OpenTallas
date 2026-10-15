`timescale 1ns/1ps
// Four-state wiring regression only. Arithmetic children are deliberately not
// elaborated (-i); their VALID fault drivers are forced low so this test checks
// that unused fault fan-in bits are neutral in a multi-root field forest.
// This is not a compute/component/native-layer qualification.
module fault_case #(parameter integer R=1) (output reg done=0);
    wire fault;
    ot_v41_field_w17w10 #(.NP(4),.R(R),.NBF(1),.EXTERNAL_ROOTS(1)) dut (
        .clk(1'b0),.rst_n(1'b0),.cfg_go(1'b0),.cfg_ph(6'd0),.cfg_np(3'd0),
        .go(1'b0),.go_bf(1'b0),.xs_v(1'b0),.xs_p(8'd0),.xs_b(3'd0),.xs_sv(2'd0),
        .xs_q0(256'd0),.xs_e0(10'd0),.xs_q1(256'd0),.xs_e1(10'd0),.xs_pos(3'd0),
        .xb_pos(3'd0),.xb_v(1'b0),.xb_b(3'd0),.xb_sv(4'd0),.xb_u(32'd0),.xb_d(1024'd0),
        .tree_fault(fault));
    initial begin
        force dut.p_fault=0;
        force dut.n_fault[8-R-1:0]=0;
        #1;
        if (fault !== 1'b0) $fatal(1,"unused tree fault bits undriven at R=%0d: %b",R,dut.n_fault);
        done=1;
    end
endmodule
module tb_field_fault_tail;
    wire a,b,c;
    fault_case #(.R(1)) x(a);
    fault_case #(.R(2)) y(b);
    fault_case #(.R(4)) z(c);
    initial begin
        #2;
        if ({a,b,c} !== 3'b111) $fatal(1,"fault cases incomplete");
        $display("FIELD_FAULT_TAIL PASS R1,R2,R4 (wiring only)");
        $finish;
    end
endmodule
