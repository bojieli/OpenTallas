`timescale 1ns/1ps
// Canonical SW576: 144 real four-lane SWE engines and six real18-block
// quantizers. A compiled pulse selects descriptor, native RW weight row, or
// one of three G/U passes. Missing operands fault; they never gate issue.
// Clock entries: two3072-bit tap halves,144 SWE leaves,six QBE leaves.
module ot_s81_su_sw576_static #(parameter integer MUT=0) (
    input wire [151:0] ck, input wire rst_n,
    input wire [1:0] issue_kind, // 0 idle,1 descriptor,2 nativeRWweights,3 operands
    input wire [1:0] issue_pass, input wire issue_u,
    input wire [11:0] present, input wire [6143:0] data,
    output wire [11:0] wv, output wire [167:0] wa,
    output wire [191:0] wm, output wire [6143:0] wd,
    output wire fault
);
    reg [3071:0] dl0,dl1,dh0,dh1;
    reg [1:0] k0,k1,p0,p1; reg u0,u1;
    reg [11:0] pr0,pr1;
    always @(posedge ck[0]) begin
        dl0<=data[3071:0];dl1<=dl0;
        p0<=issue_pass;p1<=p0;u0<=issue_u;u1<=u0;pr0<=present;pr1<=pr0;
    end
    always @(posedge ck[0] or negedge rst_n) begin
        if(!rst_n) begin k0<=0;k1<=0;end else begin k0<=issue_kind;k1<=k0;end
    end
    always @(posedge ck[1]) begin dh0<=data[6143:3072];dh1<=dh0;end
    wire [6143:0] pd={dh1,dl1};
    reg [13:0] ob; reg [31:0] lim,weight; reg [2:0] wi;
    reg f;
    always @(posedge ck[0]) begin
        if(k1==1) begin ob<=pd[13:0];lim<=pd[96+:32];wi<=pd[128+:3];end
        if(k1==2) weight<=pd[32*(5+wi)+:32];
    end
    always @(posedge ck[0] or negedge rst_n) begin
        if(!rst_n) f<=0;
        else f<=f | (k1==3 && (pr1!=12'hfff || p1==3)) |
                    ((k1==1 || k1==2) && !pr1[0]) | (k1==1 && pd[128+:3]>6);
    end
    wire [143:0] cv,cf;wire [9215:0] cd;wire [1727:0] ct;
    genvar ch,pass;
    generate for(ch=0;ch<48;ch=ch+1) begin:g_chain
        for(pass=0;pass<3;pass=pass+1) begin:g_pass
            localparam integer E=3*ch+pass;
            wire civ,cif;wire [63:0] cid;wire [11:0] cit;
            if(pass==2) begin:g_end
                assign civ=0;assign cif=0;assign cid=0;assign cit=0;
            end else begin:g_link
                assign civ=cv[E+1];assign cif=cf[E+1];assign cid=cd[64*(E+1)+:64];assign cit=ct[12*(E+1)+:12];
            end
            wire [1:0] pp=(MUT==1)?p1+2'd1:p1;
            ot_s81_su_swe #(.LPE(4),.LM(5),.LA(4)) u_e(
                .clk(ck[2+E]),.rst_in(rst_n),
                .i_gv(k1==3 && !u1 && pp==pass),.i_uv(k1==3 && u1 && pp==pass),
                .i_d(pd[512*(ch/4)+128*(ch%4)+:128]),.i_t({10'd0,pp}),
                .i_w((MUT==2)?32'h3f800000:weight),.i_lim(lim),
                .c_iv(civ),.c_id(cid),.c_it(cit),.c_if(cif),
                .c_ov(cv[E]),.c_od(cd[64*E+:64]),.c_ot(ct[12*E+:12]),.c_of(cf[E]));
        end
    end endgenerate
    wire [5:0] nxv,qfu,qfo;wire [1535:0] nxq;wire [59:0] nxe;
    genvar q,c,j;
    generate for(q=0;q<6;q=q+1) begin:g_quant
        wire [1023:0] x;
        for(c=0;c<8;c=c+1)begin:g_chunk
            for(j=0;j<4;j=j+1)begin:g_word
                assign x[32*(4*c+j)+:32]={cd[64*(3*(8*q+c))+16*j+:16],16'd0};
            end
        end
        localparam integer LO=3*(8*q),HI=3*(8*q+4),PAIR=q^1;
        wire [3:0] cb=q;
        ot_s81_su_qbe #(.QB_NB(18),.NPB(6)) u_q(
            .clk(ck[146+q]),.rst_in(rst_n),.cfg_b(cb),
            .i_vlo(cv[LO]),.i_vhi(cv[HI]),.i_lo(x[511:0]),.i_hi(x[1023:512]),
            .i_tlo(ct[12*LO+:12]),.i_thi(ct[12*HI+:12]),.i_ob(ob),.i_f4(1'b0),
            .nx_i_v(nxv[PAIR]),.nx_i_q(nxq[256*PAIR+:256]),.nx_i_e(nxe[10*PAIR+:10]),
            .nx_o_v(nxv[q]),.nx_o_q(nxq[256*q+:256]),.nx_o_e(nxe[10*q+:10]),
            .o_v(wv[2*q+:2]),.o_a(wa[28*q+:28]),.o_m(wm[32*q+:32]),.o_d(wd[1024*q+:1024]),
            .o_fu(qfu[q]),.o_fo(qfo[q]),.o_alive(),.o_den(),.o_rdy(),.o_rjid());
    end endgenerate
    assign fault=f | (|cf) | (|qfu) | (|qfo);
endmodule
