`timescale 1ns/1ps
// KV-MU7 10-20: zero-delay FUNCTIONAL models of the 42 ASAP7 75t_R cells the native32 prompt netlist
// qkd_hr_core_prompt_mu4p3_n32 uses (function = the official asap7sc7p5t_*_RVT_TT_201020 / SEQ_220101 models'
// "Function" sections; no timing, no notifier).  Bench-only: lets Verilator simulate the mapped leaf.
module INVxp67_ASAP7_75t_R(input A,output Y);assign Y=~A;endmodule
module TIEHIx1_ASAP7_75t_R(output H);assign H=1'b1;endmodule
module TIELOx1_ASAP7_75t_R(output L);assign L=1'b0;endmodule
module AND2x2_ASAP7_75t_R(input A,B,output Y);assign Y=A&B;endmodule
module AND3x1_ASAP7_75t_R(input A,B,C,output Y);assign Y=A&B&C;endmodule
module AND4x1_ASAP7_75t_R(input A,B,C,D,output Y);assign Y=A&B&C&D;endmodule
module AND5x1_ASAP7_75t_R(input A,B,C,D,E,output Y);assign Y=A&B&C&D&E;endmodule
module OR2x2_ASAP7_75t_R(input A,B,output Y);assign Y=A|B;endmodule
module OR3x1_ASAP7_75t_R(input A,B,C,output Y);assign Y=A|B|C;endmodule
module OR4x1_ASAP7_75t_R(input A,B,C,D,output Y);assign Y=A|B|C|D;endmodule
module OR5x1_ASAP7_75t_R(input A,B,C,D,E,output Y);assign Y=A|B|C|D|E;endmodule
module NAND2x1_ASAP7_75t_R(input A,B,output Y);assign Y=~(A&B);endmodule
module NAND3x1_ASAP7_75t_R(input A,B,C,output Y);assign Y=~(A&B&C);endmodule
module NOR2x1_ASAP7_75t_R(input A,B,output Y);assign Y=~(A|B);endmodule
module NOR3x1_ASAP7_75t_R(input A,B,C,output Y);assign Y=~(A|B|C);endmodule
module XOR2x2_ASAP7_75t_R(input A,B,output Y);assign Y=A^B;endmodule
module XNOR2x2_ASAP7_75t_R(input A,B,output Y);assign Y=~(A^B);endmodule
module MAJx2_ASAP7_75t_R(input A,B,C,output Y);assign Y=(A&B)|(A&C)|(B&C);endmodule
module AO21x1_ASAP7_75t_R(input A1,A2,B,output Y);assign Y=(A1&A2)|B;endmodule
module AO211x2_ASAP7_75t_R(input A1,A2,B,C,output Y);assign Y=(A1&A2)|B|C;endmodule
module AO22x1_ASAP7_75t_R(input A1,A2,B1,B2,output Y);assign Y=(A1&A2)|(B1&B2);endmodule
module AO22x2_ASAP7_75t_R(input A1,A2,B1,B2,output Y);assign Y=(A1&A2)|(B1&B2);endmodule
module AO221x1_ASAP7_75t_R(input A1,A2,B1,B2,C,output Y);assign Y=(A1&A2)|(B1&B2)|C;endmodule
module AO222x2_ASAP7_75t_R(input A1,A2,B1,B2,C1,C2,output Y);assign Y=(A1&A2)|(B1&B2)|(C1&C2);endmodule
module AO31x2_ASAP7_75t_R(input A1,A2,A3,B,output Y);assign Y=(A1&A2&A3)|B;endmodule
module AO32x1_ASAP7_75t_R(input A1,A2,A3,B1,B2,output Y);assign Y=(A1&A2&A3)|(B1&B2);endmodule
module AO33x2_ASAP7_75t_R(input A1,A2,A3,B1,B2,B3,output Y);assign Y=(A1&A2&A3)|(B1&B2&B3);endmodule
module AOI21x1_ASAP7_75t_R(input A1,A2,B,output Y);assign Y=~((A1&A2)|B);endmodule
module AOI211x1_ASAP7_75t_R(input A1,A2,B,C,output Y);assign Y=~((A1&A2)|B|C);endmodule
module AOI22x1_ASAP7_75t_R(input A1,A2,B1,B2,output Y);assign Y=~((A1&A2)|(B1&B2));endmodule
module AOI221x1_ASAP7_75t_R(input A1,A2,B1,B2,C,output Y);assign Y=~((A1&A2)|(B1&B2)|C);endmodule
module OA21x2_ASAP7_75t_R(input A1,A2,B,output Y);assign Y=(A1|A2)&B;endmodule
module OA211x2_ASAP7_75t_R(input A1,A2,B,C,output Y);assign Y=(A1|A2)&B&C;endmodule
module OA22x2_ASAP7_75t_R(input A1,A2,B1,B2,output Y);assign Y=(A1|A2)&(B1|B2);endmodule
module OA221x2_ASAP7_75t_R(input A1,A2,B1,B2,C,output Y);assign Y=(A1|A2)&(B1|B2)&C;endmodule
module OA222x2_ASAP7_75t_R(input A1,A2,B1,B2,C1,C2,output Y);assign Y=(A1|A2)&(B1|B2)&(C1|C2);endmodule
module OA31x2_ASAP7_75t_R(input A1,A2,A3,B1,output Y);assign Y=(A1|A2|A3)&B1;endmodule
module OA33x2_ASAP7_75t_R(input A1,A2,A3,B1,B2,B3,output Y);assign Y=(A1|A2|A3)&(B1|B2|B3);endmodule
module OAI21x1_ASAP7_75t_R(input A1,A2,B,output Y);assign Y=~((A1|A2)&B);endmodule
module OAI22x1_ASAP7_75t_R(input A1,A2,B1,B2,output Y);assign Y=~((A1|A2)&(B1|B2));endmodule
module DFFHQNx1_ASAP7_75t_R(input CLK,D,output QN);reg q=1'b0;always @(posedge CLK)q<=D;assign QN=~q;endmodule
// asynchronous active-low RESETN (Q=0) and SETN (Q=1); RESETN wins when both are low (bench never drives both)
module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output QN);reg q=1'b0;
 always @(posedge CLK or negedge RESETN or negedge SETN)if(!RESETN)q<=1'b0;else if(!SETN)q<=1'b1;else q<=D;
 assign QN=~q;endmodule
