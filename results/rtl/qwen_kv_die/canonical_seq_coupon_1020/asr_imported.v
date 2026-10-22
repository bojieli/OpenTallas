module DFFASRHQNx1_ASAP7_75t_R(CLK, D, QN, RESETN, SETN);
  (* capacitance = "0.462899" *)
  input CLK;
  wire CLK;
  (* capacitance = "0.561679" *)
  input D;
  wire D;
  output QN;
  wire QN;
  (* capacitance = "0.73979" *)
  input RESETN;
  wire RESETN;
  (* capacitance = "1.07945" *)
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
  always @(posedge CLK, negedge _04_, negedge SETN)
    if (!SETN) IQN <= 1'b0;
    else if (!_04_) IQN <= 1'b1;
    else IQN <= _02_;
  always @(posedge CLK, negedge RESETN, negedge _05_)
    if (!_05_) _00_ <= 1'b0;
    else if (!RESETN) _00_ <= 1'b1;
    else _00_ <= _02_;
  assign _05_ = SETN & ~(RESETN);
  assign _04_ = RESETN & ~(SETN);
  assign _01_ = ~SETN;
  assign _02_ = ~D;
  assign _03_ = ~RESETN;
  assign QN = IQN;
endmodule
