// Opt-in candidate: actual same512b SRAM, four128b local elastic mux/capture groups.
// Adds6kept controlFF per bank, no new dataFF or logical edge. No physical view inherited.
`timescale 1ns/1ps
// Source-only CCF successor: seven real leaf roots, exact +2 public edges, II1.
module ot_s81_hc_ccf_bankpipe128 #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer FIFO_SLICE = 512, KEEP_POP = 1, Y_RELAY = 1,
    parameter integer MUT = 0, AMUT = 0, RF = 5, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6,
    // PINREG (HC-COMB 2026-10-16, OWNER RULE 19:50 every leaf registers every input and output at its pin): 1 registers
    // the two remaining unregistered leaf inputs -- the bank status (hv / ovf) at the N capture leaf and the bank heads at
    // the S controller -- with every sibling input of that leaf delayed alike, so the leaf's internal phase relations are
    // unchanged and every public output (data, valid, reset, fault) moves uniformly +3 edges (II 1).  0 = the +2 source.
    parameter integer PINREG = 0
) (
    input wire sk_n,sk_s,srs,
    input wire [4:0] bank_ck,
    input wire [FVW-1:0] fv_i,
    input wire [FSW-1:0] fd_i,
    input wire n_yacc,
    input wire [YS1-1:0] n_y,
    output wire ch_rst,
    output wire [FVW-1:0] ch_fv,
    output wire [FDW-1:0] ch_fd,
    output wire yfl
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer HOP = 2 + RLY;                             // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1) * (HALF ? 2 : 1);    // the centre chain is short by NP - L1 octets
    localparam integer FP = 2 + RF + PAD;                         // forward: send + capture + RF + padding
    localparam integer RP = RT + 2 + PAD;                         // return: relay + send + capture + padding

    localparam integer YB=$clog2(YD+FP),YDC=1<<YB;
    wire psrs,pyacc;
    wire [FVW-1:0] pfv;
    wire [FSW-1:0] pfd;
    wire [YS1-1:0] py;
    wire [YS1-1:0] heads;
    wire [4:0] valid,overflow;
    initial if(NG!=256 || D!=5120 || NCOL!=3 || GS!=8 || S_RD!=2 ||
               FIFO_SLICE!=512 || KEEP_POP!=1 || Y_RELAY!=1 || HALF!=1 || RLY!=2 || RF!=5 || DW!=6)
        $fatal(1,"CCF bankpipe: only measured production shape is supported");
    ot_s81_hc_ccf_bankpipe_capture #(.FVW(FVW),.FSW(FSW),.YS(YS1),.DEPTH(YDC),.POPBIT(S_RD),.PINREG(PINREG)) u_n(
      .clk(sk_n),.srs(srs),.fv(fv_i),.fd(fd_i),.yv(n_yacc),.y(n_y),
      .srs_q(psrs),.fv_q(pfv),.fd_q(pfd),.yv_q(pyacc),.y_q(py),
      .bank_valid(valid),.bank_overflow(overflow),.yfl(yfl));
    for(genvar b=0;b<5;b=b+1) begin:g_bank
      ot_s81_hc_ccf_bankpipe_bank128 #(.DEPTH(YDC)) u_b(
       .clk(bank_ck[b]),.srs(psrs),.pop_i(pfv[S_RD]),.push_i(pyacc),.data_i(py[b*512+:512]),
       .head_o(heads[b*512+:512]),.hv_o(valid[b]),.ovf_o(overflow[b]));
    end
    ot_s81_hc_ccf_bankpipe_control #(
      .NG(NG),
      .D(D),
      .NCOL(NCOL),
      .GS(GS),
      .S_RD(S_RD),
      .S_WR(S_WR),
      .S_RT(S_RT),
      .ML(ML),
      .AL(AL),
      .FIFO_SLICE(FIFO_SLICE),
      .KEEP_POP(KEEP_POP),
      .Y_RELAY(Y_RELAY),
      .MUT(MUT),
      .AMUT(AMUT),
      .RF(RF),
      .RT(RT),
      .RW(RW),
      .YD(YD),
      .HALF(HALF),
      .RLY(RLY),
      .DW(DW),
      .PINREG(PINREG)
    ) u_s(.sk(sk_s),.srs_pin(psrs),.fv_pin(pfv),.fd_pin(pfd),.n_yacc_pin(pyacc),
      .bank_heads_pin(heads),
      .ch_rst(ch_rst),.ch_fv(ch_fv),.ch_fd(ch_fd));
endmodule


module ot_s81_hc_ccf_bankpipe_bank128 #(parameter DEPTH=32)(
 input wire clk,srs,pop_i,push_i,input wire[511:0]data_i,
 output reg[511:0]head_o,output reg hv_o,ovf_o);
 reg[1:0]rsr;always @(posedge clk)rsr<={rsr[0],srs};
 wire rs_n=rsr[1];
 wire pop_q,push_q,push_r;
 ot_s81_hc_ccf_bankpipe_keep_ff u_pop(.clk(clk),.rst_n(rs_n),.d(pop_i),.q(pop_q));
 ot_s81_hc_ccf_bankpipe_keep_ff u_push(.clk(clk),.rst_n(rs_n),.d(push_i),.q(push_q));
 ot_s81_hc_ccf_bankpipe_keep_ff u_push_r(.clk(clk),.rst_n(rs_n),.d(push_q),.q(push_r));
 reg[511:0]d0,d1;
 always @(posedge clk)begin d0<=data_i;d1<=d0;end
 wire[511:0]head;wire hv,ovf;
 ot_fifo_sram_fwft #(.W(512),.DEPTH(DEPTH),.MACRO(0),.ESL(128)) u_fifo(
  .clk(clk),.rst_n(rs_n),.push(push_r),.wdata(d1),.pop(pop_q),.hv(hv),.head(head),.ovf(ovf));
 // Real bank boundary registers, including status. No raw SRAM/mux ETM substitution.
 // These preserve the old stream one extra edge even across reset transitions.
 always @(posedge clk)begin head_o<=head;hv_o<=hv;ovf_o<=ovf;end
endmodule
