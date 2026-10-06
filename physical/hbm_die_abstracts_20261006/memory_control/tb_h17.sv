module tb_h17 #(parameter integer LB=2);
 ot_hbm_accel_bd_col #(.LB(LB),.IL(8),.TAGW(16)) bd(.clk(1'b0),.rst_n(1'b0),.v(1'b0),.first(1'b0),.last(1'b0),.fp4(1'b0),.tag(16'b0),.wq(512'b0),.we(20'b0),.xq(512'b0),.xe(20'b0),.ov(),.y(),.otag(),.fault());
 ot_hbm_accel_tc16 #(.IL(8),.TAGW(16)) tc(.clk(1'b0),.rst_n(1'b0),.v(1'b0),.first(1'b0),.last(1'b0),.tag(16'b0),.w(256'b0),.x(256'b0),.ov(),.y(),.otag(),.fault());
 initial begin #1;$display("PASS H17 actual fixed-shape parameterized declarations");$finish;end
endmodule
