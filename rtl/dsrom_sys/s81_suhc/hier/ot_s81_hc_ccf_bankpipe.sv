`timescale 1ns/1ps
// Source-only CCF successor: seven real leaf roots, exact +2 public edges, II1.
module ot_s81_hc_ccf_bankpipe #(
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
      ot_s81_hc_ccf_bankpipe_bank #(.DEPTH(YDC)) u_b(
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

// Input capture plus the actual north-local fault observer; all public timing stays +2.
module ot_s81_hc_ccf_bankpipe_capture #(parameter FVW=7,FSW=1128,YS=2560,DEPTH=32,POPBIT=2,PINREG=0)(
 input wire clk,srs,input wire[FVW-1:0]fv,input wire[FSW-1:0]fd,input wire yv,input wire[YS-1:0]y,
 input wire[4:0]bank_valid,bank_overflow,
 output reg srs_q,output reg[FVW-1:0]fv_q,output reg[FSW-1:0]fd_q,output reg yv_q,output reg[YS-1:0]y_q,
 output reg yfl);
 always @(posedge clk) begin srs_q<=srs;fv_q<=fv;fd_q<=fd;yv_q<=yv;y_q<=y;end
 // Match S's real reset/control phases; this is the original observer moved, not a prediction.
 reg[3:0]rsr;always @(posedge clk)rsr<={rsr[2:0],srs_q};
 reg pop_mid,ya_mid,pop_p,ya_p;
 // PINREG: bank status captured at the pin; the observer's pop / ya and its reset take one more stage to match
 reg[4:0] bv_q,bo_q;always @(posedge clk)begin bv_q<=bank_valid;bo_q<=bank_overflow;end
 reg pop_p2,ya_p2;
 wire rso=PINREG ? rsr[3] : rsr[2];
 always @(posedge clk or negedge rsr[3])
  if(!rsr[3])begin pop_p2<=0;ya_p2<=0;end
  else begin pop_p2<=pop_p;ya_p2<=ya_p;end
 wire pop_o=PINREG ? pop_p2 : pop_p, ya_o=PINREG ? ya_p2 : ya_p;
 wire[4:0] bv=PINREG ? bv_q : bank_valid, bo=PINREG ? bo_q : bank_overflow;
 always @(posedge clk or negedge rsr[1])
  if(!rsr[1])begin pop_mid<=0;ya_mid<=0;end
  else begin pop_mid<=fv_q[POPBIT];ya_mid<=yv_q;end
 always @(posedge clk or negedge rsr[2])
  if(!rsr[2])begin pop_p<=0;ya_p<=0;end
  else begin pop_p<=pop_mid;ya_p<=ya_mid;end
 localparam integer YB=$clog2(DEPTH);
 reg[YB:0]yn1;
 wire yf_hv=&bv;
 wire yf_ovf=|bo;
 always @(posedge clk or negedge rso)
  if(!rso)begin yn1<=0;yfl<=0;end
  else begin
   yn1<=yn1+ya_o-pop_o;
   if((ya_o && !pop_o && yn1==DEPTH) || (pop_o && yn1==0) || (pop_o && !yf_hv) || yf_ovf) yfl<=1;
  end
endmodule

module ot_s81_hc_ccf_bankpipe_bank #(parameter DEPTH=32)(
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
 ot_fifo_sram_fwft #(.W(512),.DEPTH(DEPTH),.MACRO(0),.ESL(256)) u_fifo(
  .clk(clk),.rst_n(rs_n),.push(push_r),.wdata(d1),.pop(pop_q),.hv(hv),.head(head),.ovf(ovf));
 // Real bank boundary registers, including status. No raw SRAM/mux ETM substitution.
 // These preserve the old stream one extra edge even across reset transitions.
 always @(posedge clk)begin head_o<=head;hv_o<=hv;ovf_o<=ovf;end
endmodule

module ot_s81_hc_ccf_bankpipe_control #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer FIFO_SLICE = 512, KEEP_POP = 1, Y_RELAY = 1,
    parameter integer MUT = 0, AMUT = 0, RF = 5, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6,
    parameter integer PINREG = 0
) (
    input wire sk,srs_pin,
    input wire [FVW-1:0] fv_pin,
    input wire [FSW-1:0] fd_pin,
    input wire n_yacc_pin,
    input wire [YS1-1:0] bank_heads_pin,
        output wire ch_rst,
    output reg [FVW-1:0] ch_fv,
    output reg [FDW-1:0] ch_fd
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
    // PINREG: every input captured at the pin first (uniform +1: the S leaf's internal phases are unchanged)
    reg srs_q, ya_q; reg [FVW-1:0] fv_q; reg [FSW-1:0] fd_q; reg [YS1-1:0] bh_q;
    always @(posedge sk) begin srs_q <= srs_pin; ya_q <= n_yacc_pin; fv_q <= fv_pin; fd_q <= fd_pin; bh_q <= bank_heads_pin; end
    wire srs = PINREG ? srs_q : srs_pin, n_yacc = PINREG ? ya_q : n_yacc_pin;
    wire [FVW-1:0] fv_i = PINREG ? fv_q : fv_pin;
    wire [FSW-1:0] fd_i = PINREG ? fd_q : fd_pin;
    wire [YS1-1:0] bank_heads = PINREG ? bh_q : bank_heads_pin;
    reg [2:0] rsr;                                                // tile-local reset relay (2 flops at the pin)
    always @(posedge sk) rsr <= {rsr[1:0], srs};
    wire rs_n = rsr[2];
    localparam integer YB = $clog2(YD + FP);
    localparam integer YDC = 1 << YB;
    assign ch_rst = rs_n;
    reg [FVW-1:0] fv_mid;
    reg [FSW-1:0] fd_mid;
    reg ya_mid;
    always @(posedge sk or negedge rsr[1])
      if(!rsr[1])begin fv_mid<=0;ya_mid<=0;end
      else begin fv_mid<=fv_i;ya_mid<=n_yacc;end
    always @(posedge sk)fd_mid<=fd_i;
    // the POST pop selects the y slice into ch_fd: one kept copy of the pop bit per 128-bit slice of the data field
    // (no 3,600-load select net; textbook high_fanout class 2)
    localparam integer NPS = (FDD + 127) / 128;
    wire [NPS-1:0] pop_s;
    generate if(KEEP_POP) begin:g_pop_keep
        for(genvar k=0;k<NPS;k=k+1) begin:g_k
            ot_s81_hc_ccf_bankpipe_keep_ff u_k(.clk(sk),.rst_n(rs_n),.d(fv_mid[S_RD]),.q(pop_s[k]));
        end
    end else begin:g_pop_old
        reg [NPS-1:0] p;
        always @(posedge sk or negedge rs_n) if(!rs_n) p<=0; else p<={NPS{fv_mid[S_RD]}};
        assign pop_s=p;
    end endgenerate
    reg [FVW-1:0] fv_p;
    reg [FSW-1:0] fd_p;
    reg           ya;
    always @(posedge sk or negedge rs_n) if (!rs_n) begin fv_p <= 0; ya <= 1'b0; end else begin fv_p <= fv_mid; ya <= ya_mid; end
    always @(posedge sk) fd_p <= fd_mid;
    wire pop = fv_p[S_RD];
    wire [YS1-1:0] yf_head;
    assign yf_head=bank_heads;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) ch_fv <= 0;
        else ch_fv <= (L1 > 0) ? fv_p : {FVW{1'b0}};
    always @(posedge sk) begin
        ch_fd[O_D-1:0] <= fd_p[O_D-1:0];
        begin : dfield
            reg [FDD-1:0] t, ty, tf;
            integer k;
            ty = {FDD{1'b0}}; tf = {FDD{1'b0}};
            ty[YS1-1:0] = yf_head;
            tf[S_RD*512-1:0] = fd_p[O_D +: S_RD * 512];
            for (k = 0; k < FDD; k = k + 1) t[k] = pop_s[k / 128] ? ty[k] : tf[k];
            ch_fd[O_D +: FDD] <= t;
        end
    end
endmodule
// Separate synthesis-preserved local select/valid drivers, <=128 data-bit consumers.
module ot_s81_hc_ccf_bankpipe_keep_ff(input wire clk,rst_n,d,output wire q);
    (* keep="true" *) reg q_k;
    always @(posedge clk or negedge rst_n) if(!rst_n) q_k<=1'b0;else q_k<=d;
    assign q=q_k;
endmodule
