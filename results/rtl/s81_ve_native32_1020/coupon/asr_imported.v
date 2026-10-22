module DFFASRHQNx1_ASAP7_75t_R(CLK, D, QN, RESETN, SETN);
  input CLK;
  wire CLK;
  input D;
  wire D;
  output QN;
  wire QN;
  input RESETN;
  wire RESETN;
  input SETN;
  wire SETN;
  reg _00_;
  wire _01_;
  wire _02_;
  wire _03_;
  wire _04_;
  wire _05_;
  reg IQN;
  wire IQNN;
  assign IQNN = ~_00_;
  always @(posedge CLK, posedge _04_, posedge _01_)
    if (_01_) IQN <= 1'b0;
    else if (_04_) IQN <= 1'b1;
    else IQN <= _02_;
  always @(posedge CLK, posedge _03_, posedge _05_)
    if (_05_) _00_ <= 1'b0;
    else if (_03_) _00_ <= 1'b1;
    else _00_ <= _02_;
  assign _05_ = _01_ & ~(_03_);
  assign _04_ = _03_ & ~(_01_);
  assign _01_ = ~SETN;
  assign _02_ = ~D;
  assign _03_ = ~RESETN;
  assign QN = IQN;
endmodule
