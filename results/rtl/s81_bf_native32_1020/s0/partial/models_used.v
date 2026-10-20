module AND2x2_ASAP7_75t_R(A, B, Y);
  (* capacitance = "0.447496" *)
  input A;
  wire A;
  (* capacitance = "0.490388" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  assign _0_ = A & B;
  assign Y = _0_;
endmodule

module AND2x4_ASAP7_75t_R(A, B, Y);
  (* capacitance = "0.952813" *)
  input A;
  wire A;
  (* capacitance = "0.914873" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  assign _0_ = A & B;
  assign Y = _0_;
endmodule

module AND3x1_ASAP7_75t_R(A, B, C, Y);
  (* capacitance = "0.548668" *)
  input A;
  wire A;
  (* capacitance = "0.511133" *)
  input B;
  wire B;
  (* capacitance = "0.510343" *)
  input C;
  wire C;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  assign _0_ = A & B;
  assign _1_ = _0_ & C;
  assign Y = _1_;
endmodule

module AND4x1_ASAP7_75t_R(A, B, C, D, Y);
  (* capacitance = "0.553061" *)
  input A;
  wire A;
  (* capacitance = "0.510941" *)
  input B;
  wire B;
  (* capacitance = "0.507309" *)
  input C;
  wire C;
  (* capacitance = "0.526481" *)
  input D;
  wire D;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  assign _0_ = A & B;
  assign _1_ = _0_ & C;
  assign _2_ = _1_ & D;
  assign Y = _2_;
endmodule

module AND5x1_ASAP7_75t_R(A, B, C, D, E, Y);
  (* capacitance = "0.481024" *)
  input A;
  wire A;
  (* capacitance = "0.433086" *)
  input B;
  wire B;
  (* capacitance = "0.431762" *)
  input C;
  wire C;
  (* capacitance = "0.431474" *)
  input D;
  wire D;
  (* capacitance = "0.469494" *)
  input E;
  wire E;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  wire _3_;
  assign _0_ = A & B;
  assign _1_ = _0_ & C;
  assign _2_ = _1_ & D;
  assign _3_ = _2_ & E;
  assign Y = _3_;
endmodule

module AO21x1_ASAP7_75t_R(A1, A2, B, Y);
  (* capacitance = "0.514506" *)
  input A1;
  wire A1;
  (* capacitance = "0.528252" *)
  input A2;
  wire A2;
  (* capacitance = "0.529141" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  assign _0_ = A1 & A2;
  assign _1_ = _0_ | B;
  assign Y = _1_;
endmodule

module AO21x2_ASAP7_75t_R(A1, A2, B, Y);
  (* capacitance = "0.514953" *)
  input A1;
  wire A1;
  (* capacitance = "0.529686" *)
  input A2;
  wire A2;
  (* capacitance = "0.530288" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  assign _0_ = A1 & A2;
  assign _1_ = _0_ | B;
  assign Y = _1_;
endmodule

module AOI21x1_ASAP7_75t_R(A1, A2, B, Y);
  (* capacitance = "1.02945" *)
  input A1;
  wire A1;
  (* capacitance = "0.885352" *)
  input A2;
  wire A2;
  (* capacitance = "1.06635" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _00_;
  wire _01_;
  wire _02_;
  wire _03_;
  wire _04_;
  wire _05_;
  wire _06_;
  assign _04_ = _00_ & _01_;
  assign _05_ = _02_ & _03_;
  assign _06_ = _04_ | _05_;
  assign _00_ = ~A1;
  assign _01_ = ~B;
  assign _02_ = ~A2;
  assign _03_ = ~B;
  assign Y = _06_;
endmodule

module BUFx2_ASAP7_75t_R(A, Y);
  (* capacitance = "0.5065" *)
  input A;
  wire A;
  output Y;
  wire Y;
  assign Y = A;
endmodule

module HAxp5_ASAP7_75t_R(A, B, CON, SN);
  (* capacitance = "0.910035" *)
  input A;
  wire A;
  (* capacitance = "0.851438" *)
  input B;
  wire B;
  output CON;
  wire CON;
  output SN;
  wire SN;
  wire _00_;
  wire _01_;
  wire _02_;
  wire _03_;
  wire _04_;
  wire _05_;
  wire _06_;
  wire _07_;
  assign _04_ = A & B;
  assign _05_ = _02_ & _03_;
  assign _06_ = _00_ | _01_;
  assign _07_ = _04_ | _05_;
  assign _00_ = ~A;
  assign _01_ = ~B;
  assign _02_ = ~A;
  assign _03_ = ~B;
  assign CON = _06_;
  assign SN = _07_;
endmodule

module INVx1_ASAP7_75t_R(A, Y);
  (* capacitance = "0.578766" *)
  input A;
  wire A;
  output Y;
  wire Y;
  wire _0_;
  assign _0_ = ~A;
  assign Y = _0_;
endmodule

module NAND2x1_ASAP7_75t_R(A, B, Y);
  (* capacitance = "0.924899" *)
  input A;
  wire A;
  (* capacitance = "0.924444" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  assign _2_ = _0_ | _1_;
  assign _0_ = ~A;
  assign _1_ = ~B;
  assign Y = _2_;
endmodule

module NOR2x1_ASAP7_75t_R(A, B, Y);
  (* capacitance = "0.940205" *)
  input A;
  wire A;
  (* capacitance = "0.955654" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  assign _2_ = _0_ & _1_;
  assign _0_ = ~A;
  assign _1_ = ~B;
  assign Y = _2_;
endmodule

module NOR2x2_ASAP7_75t_R(A, B, Y);
  (* capacitance = "1.81013" *)
  input A;
  wire A;
  (* capacitance = "1.92722" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  assign _2_ = _0_ & _1_;
  assign _0_ = ~A;
  assign _1_ = ~B;
  assign Y = _2_;
endmodule

module OA211x2_ASAP7_75t_R(A1, A2, B, C, Y);
  (* capacitance = "0.452518" *)
  input A1;
  wire A1;
  (* capacitance = "0.481403" *)
  input A2;
  wire A2;
  (* capacitance = "0.364942" *)
  input B;
  wire B;
  (* capacitance = "0.375156" *)
  input C;
  wire C;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  wire _3_;
  wire _4_;
  assign _0_ = A1 & B;
  assign _1_ = _0_ & C;
  assign _2_ = A2 & B;
  assign _3_ = _2_ & C;
  assign _4_ = _1_ | _3_;
  assign Y = _4_;
endmodule

module OA21x2_ASAP7_75t_R(A1, A2, B, Y);
  (* capacitance = "0.513005" *)
  input A1;
  wire A1;
  (* capacitance = "0.542924" *)
  input A2;
  wire A2;
  (* capacitance = "0.531608" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  assign _0_ = A1 & B;
  assign _1_ = A2 & B;
  assign _2_ = _0_ | _1_;
  assign Y = _2_;
endmodule

module OAI21x1_ASAP7_75t_R(A1, A2, B, Y);
  (* capacitance = "1.02824" *)
  input A1;
  wire A1;
  (* capacitance = "0.874367" *)
  input A2;
  wire A2;
  (* capacitance = "1.16756" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  wire _3_;
  wire _4_;
  assign _3_ = _0_ & _1_;
  assign _4_ = _3_ | _2_;
  assign _0_ = ~A1;
  assign _1_ = ~A2;
  assign _2_ = ~B;
  assign Y = _4_;
endmodule

module OR2x2_ASAP7_75t_R(A, B, Y);
  (* capacitance = "0.473034" *)
  input A;
  wire A;
  (* capacitance = "0.486821" *)
  input B;
  wire B;
  output Y;
  wire Y;
  wire _0_;
  assign _0_ = A | B;
  assign Y = _0_;
endmodule

module OR3x1_ASAP7_75t_R(A, B, C, Y);
  (* capacitance = "0.549179" *)
  input A;
  wire A;
  (* capacitance = "0.510903" *)
  input B;
  wire B;
  (* capacitance = "0.511424" *)
  input C;
  wire C;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  assign _0_ = A | B;
  assign _1_ = _0_ | C;
  assign Y = _1_;
endmodule

module OR4x1_ASAP7_75t_R(A, B, C, D, Y);
  (* capacitance = "0.553988" *)
  input A;
  wire A;
  (* capacitance = "0.50988" *)
  input B;
  wire B;
  (* capacitance = "0.505853" *)
  input C;
  wire C;
  (* capacitance = "0.524946" *)
  input D;
  wire D;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  assign _0_ = A | B;
  assign _1_ = _0_ | C;
  assign _2_ = _1_ | D;
  assign Y = _2_;
endmodule

module OR5x1_ASAP7_75t_R(A, B, C, D, E, Y);
  (* capacitance = "0.483058" *)
  input A;
  wire A;
  (* capacitance = "0.434739" *)
  input B;
  wire B;
  (* capacitance = "0.433194" *)
  input C;
  wire C;
  (* capacitance = "0.434474" *)
  input D;
  wire D;
  (* capacitance = "0.47167" *)
  input E;
  wire E;
  output Y;
  wire Y;
  wire _0_;
  wire _1_;
  wire _2_;
  wire _3_;
  assign _0_ = A | B;
  assign _1_ = _0_ | C;
  assign _2_ = _1_ | D;
  assign _3_ = _2_ | E;
  assign Y = _3_;
endmodule

module TIEHIx1_ASAP7_75t_R(H);
  output H;
  wire H;
  assign H = 1'h1;
endmodule

module TIELOx1_ASAP7_75t_R(L);
  output L;
  wire L;
  assign L = 1'h0;
endmodule
