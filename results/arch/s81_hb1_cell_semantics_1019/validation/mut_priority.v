// SIMULATION ONLY: exact frozen Liberty binary functions; no SDF/timing.
// Uninitialized state remains X in a four-state simulator.
`timescale 1ns/1ps
module AND2x2_ASAP7_75t_R(Y, A, B);
  output Y;
  input A;
  input B;
  assign Y = (A & B);
endmodule
module AND3x1_ASAP7_75t_R(Y, A, B, C);
  output Y;
  input A;
  input B;
  input C;
  assign Y = (A & B & C);
endmodule
module AND4x1_ASAP7_75t_R(Y, A, B, C, D);
  output Y;
  input A;
  input B;
  input C;
  input D;
  assign Y = (A & B & C & D);
endmodule
module AND5x1_ASAP7_75t_R(Y, A, B, C, D, E);
  output Y;
  input A;
  input B;
  input C;
  input D;
  input E;
  assign Y = (A & B & C & D & E);
endmodule
module AO21x1_ASAP7_75t_R(Y, A1, A2, B);
  output Y;
  input A1;
  input A2;
  input B;
  assign Y = (A1 & A2) | (B);
endmodule
module AO221x1_ASAP7_75t_R(Y, A1, A2, B1, B2, C);
  output Y;
  input A1;
  input A2;
  input B1;
  input B2;
  input C;
  assign Y = (A1 & A2) | (B1 & B2) | (C);
endmodule
module AO222x2_ASAP7_75t_R(Y, A1, A2, B1, B2, C1, C2);
  output Y;
  input A1;
  input A2;
  input B1;
  input B2;
  input C1;
  input C2;
  assign Y = (A1 & A2) | (B1 & B2) | (C1 & C2);
endmodule
module AO22x1_ASAP7_75t_R(Y, A1, A2, B1, B2);
  output Y;
  input A1;
  input A2;
  input B1;
  input B2;
  assign Y = (A1 & A2) | (B1 & B2);
endmodule
module AO31x2_ASAP7_75t_R(Y, A1, A2, A3, B);
  output Y;
  input A1;
  input A2;
  input A3;
  input B;
  assign Y = (A1 & A2 & A3) | (B);
endmodule
module AO32x1_ASAP7_75t_R(Y, A1, A2, A3, B1, B2);
  output Y;
  input A1;
  input A2;
  input A3;
  input B1;
  input B2;
  assign Y = (A1 & A2 & A3) | (B1 & B2);
endmodule
module AOI211x1_ASAP7_75t_R(Y, A1, A2, B, C);
  output Y;
  input A1;
  input A2;
  input B;
  input C;
  assign Y = (~A1 & ~B & ~C) | (~A2 & ~B & ~C);
endmodule
module AOI21x1_ASAP7_75t_R(Y, A1, A2, B);
  output Y;
  input A1;
  input A2;
  input B;
  assign Y = (~A1 & ~B) | (~A2 & ~B);
endmodule
module AOI221x1_ASAP7_75t_R(Y, A1, A2, B1, B2, C);
  output Y;
  input A1;
  input A2;
  input B1;
  input B2;
  input C;
  assign Y = (~A1 & ~B1 & ~C) | (~A1 & ~B2 & ~C) | (~A2 & ~B1 & ~C) | (~A2 & ~B2 & ~C);
endmodule
module BUFx12f_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = A;
endmodule
module BUFx2_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = A;
endmodule
module BUFx3_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = A;
endmodule
module BUFx4f_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = A;
endmodule
module BUFx5_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = A;
endmodule
module BUFx6f_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = A;
endmodule
module BUFx8_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = A;
endmodule
module DFFASRHQNx1_ASAP7_75t_R(QN, D, RESETN, SETN, CLK);
  output reg QN;
  input D;
  input RESETN;
  input SETN;
  input CLK;
  reg previous_CLK;
  always @(CLK or RESETN or SETN) begin
    if (!RESETN) QN <= 1'b1;
    else if (!SETN) QN <= 1'b0;
    else if ((CLK === 1'b1) && (previous_CLK === 1'b0)) QN <= ~D;
    previous_CLK = CLK;
  end
endmodule
module DFFHQNx1_ASAP7_75t_R(QN, D, CLK);
  output reg QN;
  input D;
  input CLK;
  always @(posedge CLK) QN <= ~D;
endmodule
module INVx1_ASAP7_75t_R(Y, A);
  output Y;
  input A;
  assign Y = ~A;
endmodule
module MAJx2_ASAP7_75t_R(Y, A, B, C);
  output Y;
  input A;
  input B;
  input C;
  assign Y = (A & B) | (A & C) | (B & C);
endmodule
module NAND2x1_ASAP7_75t_R(Y, A, B);
  output Y;
  input A;
  input B;
  assign Y = (~A) | (~B);
endmodule
module NAND3x1_ASAP7_75t_R(Y, A, B, C);
  output Y;
  input A;
  input B;
  input C;
  assign Y = (~A) | (~B) | (~C);
endmodule
module NOR2x1_ASAP7_75t_R(Y, A, B);
  output Y;
  input A;
  input B;
  assign Y = (~A & ~B);
endmodule
module OA211x2_ASAP7_75t_R(Y, A1, A2, B, C);
  output Y;
  input A1;
  input A2;
  input B;
  input C;
  assign Y = (A1 & B & C) | (A2 & B & C);
endmodule
module OA21x2_ASAP7_75t_R(Y, A1, A2, B);
  output Y;
  input A1;
  input A2;
  input B;
  assign Y = (A1 & B) | (A2 & B);
endmodule
module OA222x2_ASAP7_75t_R(Y, A1, A2, B1, B2, C1, C2);
  output Y;
  input A1;
  input A2;
  input B1;
  input B2;
  input C1;
  input C2;
  assign Y = (A1 & B1 & C1) | (A1 & B1 & C2) | (A1 & B2 & C1) | (A1 & B2 & C2) | (A2 & B1 & C1) | (A2 & B1 & C2) | (A2 & B2 & C1) | (A2 & B2 & C2);
endmodule
module OA22x2_ASAP7_75t_R(Y, A1, A2, B1, B2);
  output Y;
  input A1;
  input A2;
  input B1;
  input B2;
  assign Y = (A1 & B1) | (A1 & B2) | (A2 & B1) | (A2 & B2);
endmodule
module OA31x2_ASAP7_75t_R(Y, A1, A2, A3, B1);
  output Y;
  input A1;
  input A2;
  input A3;
  input B1;
  assign Y = (A1 & B1) | (A2 & B1) | (A3 & B1);
endmodule
module OAI21x1_ASAP7_75t_R(Y, A1, A2, B);
  output Y;
  input A1;
  input A2;
  input B;
  assign Y = (~A1 & ~A2) | (~B);
endmodule
module OAI22x1_ASAP7_75t_R(Y, A1, A2, B1, B2);
  output Y;
  input A1;
  input A2;
  input B1;
  input B2;
  assign Y = (~A1 & ~A2) | (~B1 & ~B2);
endmodule
module OR2x2_ASAP7_75t_R(Y, A, B);
  output Y;
  input A;
  input B;
  assign Y = (A) | (B);
endmodule
module OR3x1_ASAP7_75t_R(Y, A, B, C);
  output Y;
  input A;
  input B;
  input C;
  assign Y = (A) | (B) | (C);
endmodule
module OR4x1_ASAP7_75t_R(Y, A, B, C, D);
  output Y;
  input A;
  input B;
  input C;
  input D;
  assign Y = (A) | (B) | (C) | (D);
endmodule
module TIEHIx1_ASAP7_75t_R(H);
  output H;
  assign H = 1'b1;
endmodule
module TIELOx1_ASAP7_75t_R(L);
  output L;
  assign L = 1'b0;
endmodule
module XNOR2x2_ASAP7_75t_R(Y, A, B);
  output Y;
  input A;
  input B;
  assign Y = (A & B) | (~A & ~B);
endmodule
module XOR2x2_ASAP7_75t_R(Y, A, B);
  output Y;
  input A;
  input B;
  assign Y = (A & ~B) | (~A & B);
endmodule
