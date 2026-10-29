module raw_export_synth(input wire clk,d,output wire q,export_q);
    ot_dp_head_raw_export_pair dut(.clk(clk),.d(d),.q(q),.export_q(export_q));
endmodule
