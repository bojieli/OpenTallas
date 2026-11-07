module gold(input ck,rr_c_l28,_1021_,mb,input [3:0]state,output reg[31:0]count);
wire[31:0]_0856_,_1610_,_1611_,_0674_;wire _1612_;
  assign _0856_ = count  + 1'h1;
  assign _1610_ = _1021_ ?  _0856_ : count ;
  assign _1611_ = mb  ?  _1610_ : count ;
  assign _0674_ = _1612_ ?  _1611_ : count ;
  assign _1612_ = state  ==  4'hb;
  always @(posedge ck, negedge rr_c_l28)
    if (!rr_c_l28) count <= 32'd0;
    else count  <= _0674_;

endmodule
module cand(input ck,rr_c_l28,_1021_,mb,input [3:0]state,output reg[31:0]count);
wire[31:0]_0856_,_1610_,_1611_,_0674_;wire _1612_;
  assign _0856_ = { (count [31:24] + ot_creq_c24),
                    (count [23:16] + ot_creq_c16),
                    (count [15:8] + ot_creq_c8),
                    (count [7:0] + 8'd1) };
  assign _1610_ = _1021_ ?  _0856_ : count ;
  assign _1611_ = mb  ?  _1610_ : count ;
  assign _0674_ = _1612_ ?  _1611_ : count ;
  assign _1612_ = state  ==  4'hb;
  always @(posedge ck, negedge rr_c_l28)
    if (!rr_c_l28) count <= 32'd0;
    else count  <= _0674_;
  reg ot_creq_c8, ot_creq_c16, ot_creq_c24;
  wire ot_creq_inc = _1612_ & mb  & _1021_;
  always @(posedge ck, negedge rr_c_l28)
    if (!rr_c_l28) begin
      ot_creq_c8 <= 1'b0;
      ot_creq_c16 <= 1'b0;
      ot_creq_c24 <= 1'b0;
    end else if (ot_creq_inc) begin
      ot_creq_c8 <= (count [7:0] == 8'hfe);
      ot_creq_c16 <= (count [15:0] == 16'hfffe);
      ot_creq_c24 <= (count [23:0] == 24'hfffffe);
    end

endmodule
module mutant(input ck,rr_c_l28,_1021_,mb,input [3:0]state,output reg[31:0]count);
wire[31:0]_0856_,_1610_,_1611_,_0674_;wire _1612_;
  assign _0856_ = { (count [31:24] + ot_creq_c24),
                    (count [23:16] + ot_creq_c16),
                    (count [15:8] + ot_creq_c16),
                    (count [7:0] + 8'd1) };
  assign _1610_ = _1021_ ?  _0856_ : count ;
  assign _1611_ = mb  ?  _1610_ : count ;
  assign _0674_ = _1612_ ?  _1611_ : count ;
  assign _1612_ = state  ==  4'hb;
  always @(posedge ck, negedge rr_c_l28)
    if (!rr_c_l28) count <= 32'd0;
    else count  <= _0674_;
  reg ot_creq_c8, ot_creq_c16, ot_creq_c24;
  wire ot_creq_inc = _1612_ & mb  & _1021_;
  always @(posedge ck, negedge rr_c_l28)
    if (!rr_c_l28) begin
      ot_creq_c8 <= 1'b0;
      ot_creq_c16 <= 1'b0;
      ot_creq_c24 <= 1'b0;
    end else if (ot_creq_inc) begin
      ot_creq_c8 <= (count [7:0] == 8'hfe);
      ot_creq_c16 <= (count [15:0] == 16'hfffe);
      ot_creq_c24 <= (count [23:0] == 24'hfffffe);
    end

endmodule
