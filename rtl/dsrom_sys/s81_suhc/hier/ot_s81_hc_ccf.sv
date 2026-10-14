`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_ccf (s81-suhc-hier-1011 comb v2, 2026-10-11): the centre-chain forward root of the HC combine region (hard
// tile, bottom row, S face to ctile_22).  Captures the last forward pad stage (stage FP, from ot_s81_hc_cpad), the
// centre y slice (n_y / n_yacc from the centre pin tile) into the y slice FIFO (YS1 wide, 1R1W SRAM macros behind the
// FWFT capture / output buffer), and drives the centre chain: ch_fv / ch_fd output flops (a POST beat carries the
// popped y slice) and the chain reset relay ch_rst.  The FIFO overflow / underflow fault yfl is an output flop
// (ot_s81_hc_cseq folds it into n_flt).  Register counts identical to the flat comb.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_ccf #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer FIFO_SLICE = 512, KEEP_POP = 1, Y_RELAY = 1, PIN_CAPTURE = 1,
    parameter integer MUT = 0, AMUT = 0, RF = 5, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6
) (
    input  wire                 sk, srs,
    input  wire [FVW-1:0]       fv_i,
    input  wire [FSW-1:0]       fd_i,
    input  wire                 n_yacc,
    input  wire [YS1-1:0]       n_y,
    output wire                 ch_rst,
    output reg  [FVW-1:0]       ch_fv,
    output reg  [FDW-1:0]       ch_fd,
    output reg                  yfl
);
    // Production hard-master defaults match the routed NG256 HIER3 tuple; soft parents pass their tuple.
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
    reg [1:0] rsr;                                                // tile-local reset relay (2 flops at the pin)
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    localparam integer YB = $clog2(YD + FP);
    localparam integer YDC = 1 << YB;
    // Keep the outgoing reset relay at its S-face pin rather than sharing the
    // interior reset driver that fans out to the FIFO and transaction state.
    // Both second-stage flops consume rsr[0], preserving the reset epoch.
    ot_s81_hc_ccf_keep_ff u_reset_pin(.clk(sk),.rst_n(1'b1),.d(rsr[0]),.q(ch_rst));
    // One synthesis-preserved capture per face bit. Distributed local POST copies consume
    // this stage rather than the die port. The matching forward pad gives up one stage,
    // so chain issue, FIFO pop, return and completion keep their production cycle counts.
    wire [FVW-1:0] fv_face;
    wire [FSW-1:0] fd_face;
    generate if(PIN_CAPTURE) begin:g_face_capture
        (* keep="true" *) reg [FVW-1:0] fv_pin;
        (* keep="true" *) reg [FSW-1:0] fd_pin;
        always @(posedge sk or negedge rs_n)
            if(!rs_n) fv_pin<=0; else fv_pin<=fv_i;
        always @(posedge sk) fd_pin<=fd_i;
        assign fv_face=fv_pin; assign fd_face=fd_pin;
    end else begin:g_face_legacy
        assign fv_face=fv_i; assign fd_face=fd_i;
    end endgenerate
    // the POST pop selects the y slice into ch_fd: one kept copy of the pop bit per 128-bit slice of the data field
    // (no 3,600-load select net; textbook high_fanout class 2)
    localparam integer NPS = (FDD + 127) / 128;
    wire [NPS-1:0] pop_s;
    generate if(KEEP_POP) begin:g_pop_keep
        for(genvar k=0;k<NPS;k=k+1) begin:g_k
            ot_s81_hc_ccf_keep_ff u_k(.clk(sk),.rst_n(rs_n),.d(fv_face[S_RD]),.q(pop_s[k]));
        end
    end else begin:g_pop_old
        reg [NPS-1:0] p;
        always @(posedge sk or negedge rs_n) if(!rs_n) p<=0; else p<={NPS{fv_face[S_RD]}};
        assign pop_s=p;
    end endgenerate
    reg [FVW-1:0] fv_p;
    reg [FSW-1:0] fd_p;
    reg           ya;
    reg [YS1-1:0] y1;
    always @(posedge sk or negedge rs_n) if (!rs_n) begin fv_p <= 0; ya <= 1'b0; end else begin fv_p <= fv_face; ya <= n_yacc; end
    always @(posedge sk) begin fd_p <= fd_face; y1 <= n_y; end
    reg [YB:0]    yn1;
    reg [YB-1:0]  yw, yr;
    wire pop = fv_p[S_RD];
    wire [YS1-1:0] yf_head;
    wire           yf_hv, yf_ovf;
    generate if (L1 > 0) begin : g_yf
        if(FIFO_SLICE>0) begin:g_slice
            localparam integer NF=(YS1+FIFO_SLICE-1)/FIFO_SLICE;
            wire [NF-1:0] valid,overflow;
            for(genvar f=0;f<NF;f=f+1) begin:g_f
                localparam integer LO=f*FIFO_SLICE,FW=(YS1-LO<FIFO_SLICE)?YS1-LO:FIFO_SLICE;
                wire [FW-1:0] yd;
                wire yp;
                if(Y_RELAY) begin:g_relay
                    reg [FW-1:0] yd_q;
                    always @(posedge sk) yd_q<=y1[LO+:FW];
                    ot_s81_hc_ccf_keep_ff u_v(.clk(sk),.rst_n(rs_n),.d(ya),.q(yp));
                    assign yd=yd_q;
                end else begin:g_direct
                    assign yd=y1[LO+:FW];assign yp=ya;
                end
                ot_fifo_sram_fwft #(.W(FW),.DEPTH(YDC),.MACRO(0),.ESL(256)) u_yf(
                    .clk(sk),.rst_n(rs_n),.push(yp),.wdata(yd),.pop(pop),
                    .hv(valid[f]),.head(yf_head[LO+:FW]),.ovf(overflow[f]));
            end
            assign yf_hv=&valid;assign yf_ovf=|overflow;
        end else begin:g_full
            ot_fifo_sram_fwft #(.W(YS1), .DEPTH(YDC), .MACRO(0), .ESL(256)) u_yf (.clk(sk), .rst_n(rs_n), .push(ya), .wdata(y1),
                .pop(pop), .hv(yf_hv), .head(yf_head), .ovf(yf_ovf));
        end
    end else begin : g_nyf
        assign yf_head = {YS1{1'b0}}; assign yf_hv = 1'b0; assign yf_ovf = 1'b0;
    end endgenerate
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin ch_fv <= 0; yn1 <= 0; yw <= 0; yr <= 0; yfl <= 1'b0; end
        else begin
            ch_fv <= (L1 > 0) ? fv_p : {FVW{1'b0}};
            if (ya) yw <= yw + 1'b1;
            if (pop) yr <= yr + 1'b1;
            yn1 <= yn1 + ya - pop;
            if (L1 > 0 && ((ya && !pop && yn1 == YDC) || (pop && yn1 == 0) || (pop && !yf_hv) || yf_ovf)) yfl <= 1'b1;
        end
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
module ot_s81_hc_ccf_keep_ff(input wire clk,rst_n,d,output wire q);
    (* keep="true" *) reg q_k;
    always @(posedge clk or negedge rst_n) if(!rst_n) q_k<=1'b0;else q_k<=d;
    assign q=q_k;
endmodule
