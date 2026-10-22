module DFFHQNx1_ASAP7_75t_R(CLK, D, QN);
  input CLK;
  wire CLK;
  input D;
  wire D;
  output QN;
  wire QN;
  reg _0_;
  wire _1_;
  reg IQN;
  wire IQNN;
  assign IQNN = ~_0_;
  always @(posedge CLK)
    IQN <= _1_;
  always @(posedge CLK)
    _0_ <= _1_;
  assign _1_ = ~D;
  assign QN = IQN;
endmodule
