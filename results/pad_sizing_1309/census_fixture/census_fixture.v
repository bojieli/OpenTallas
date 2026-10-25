module census_fixture(input clk, input din, output dout); wire mid; DFFHQNx1_ASAP7_75t_R launch(.CLK(clk), .D(din), .QN(mid)); DFFHQNx1_ASAP7_75t_R capture(.CLK(clk), .D(mid), .QN(dout)); endmodule
