`timescale 1ns/1ps
// Native missing CN/IK arithmetic, composed from the existing physical eight-
// lane KV norm/RoPE engines and QN reduction leaves. Wires-only parent. CN uses
// D=512/E4M3 block16; IK uses D=128/UE8M0 block32. Every state holder has its own
// explicit clock/reset pin. VM descriptor issue/capture/drain are separate
// scheduled clients; this boundary accepts the whole norm row in reserved slots.
// No credits, ready, arbitration, or data-dependent issue.
module ot_s81_su_cn_ik #(
    parameter integer D=512, E4M3=1, LM=5, LA=4, MUT_NO_ROPE=0,
    parameter integer NE=D/8, NH=2, NQ=D/32
)(
    input wire [NE-1:0] ck_norm, rs_norm,
    input wire [NH-1:0] ck_half, rs_half,
    input wire ck_reduce, rs_reduce,
    input wire [NE-1:0] ck_align, rs_align,
    input wire [NQ-1:0] ck_quant, rs_quant,
    input wire go, gain_v, x_v,
    input wire [D*32-1:0] gain, x,
    input wire [31:0] eps,
    input wire [1023:0] cos_t, sin_t,
    output wire [D*16-1:0] y,
    output wire [NQ-1:0] y_v,
    output wire [NQ*144-1:0] raw,
    output wire fault
);
`ifndef SYNTHESIS
    initial if ((D!=512 && D!=128) || NH!=2 || (D==512)!=E4M3)
        $fatal(1,"CN/IK production shape/format mismatch");
`endif
    localparam integer HP=NE/NH;
    localparam integer RP_EXTRA=2+LM+((LA>=5)?LA:LA+1);
    wire [NE-1:0] pv, nv, nf;
    wire [NE*32-1:0] pd;
    wire [D*32-1:0] norm, aligned;
    wire [NE-1:0] av;
    wire rv, rf;
    wire [31:0] rd;
    wire [NH-1:0] hv,hp,hf;
    wire [NH*32-1:0] hd;
    wire [NQ-1:0] qf;
    genvar e,h,q;
    generate for(e=0;e<NE;e=e+1) begin:g_norm
        localparam integer ROTATE=(e>=NE-8);
        wire [127:0] cc,ss,unused_norm;
        wire unused_norm_v;
        if(ROTATE) begin:g_cs
            assign cc=cos_t[128*(e-(NE-8))+:128];
            assign ss=MUT_NO_ROPE?128'd0:sin_t[128*(e-(NE-8))+:128];
        end else begin:g_zero
            assign cc=0;assign ss=0;
        end
        ot_s81_su_kve #(.RP(ROTATE),.LM(LM),.LA(LA)) u_norm(
            .clk(ck_norm[e]),.rst_in(rs_norm[e]),.i_v(gain_v||x_v),
            .i_x(gain_v?gain[256*e+:256]:x[256*e+:256]),
            .i_gk(gain_v),.i_gr(2'd0),.i_gw(2'd0),.i_cos(cc),.i_sin(ss),
            .r_v(rv),.r_d(rd),.p_v(pv[e]),.p_d(pd[32*e+:32]),
            .y_v(nv[e]),.y(norm[256*e+:256]),.norm_v(unused_norm_v),.norm_y(unused_norm),.o_f(nf[e]));
        // Non-RoPE chunks wait exactly the additional RoPE latency. Padding is
        // an owned physical leaf, never flops hidden in this parent.
        ot_s81_su_cn_align #(.DEPTH(ROTATE?0:RP_EXTRA)) u_align(
            .clk(ck_align[e]),.rst_in(rs_align[e]),.i_v(nv[e]),
            .i_d(norm[256*e+:256]),.o_v(av[e]),.o_d(aligned[256*e+:256]));
    end
    for(h=0;h<NH;h=h+1) begin:g_half
        ot_s81_su_qnh #(.NE(HP),.LA(LA)) u_half(
            .clk(ck_half[h]),.rst_in(rs_half[h]),.i_go(go),
            .p_v(pv[HP*h+:HP]),.p_p({HP{1'b0}}),.p_d(pd[32*HP*h+:32*HP]),
            .s_v(hv[h]),.s_p(hp[h]),.s_d(hd[32*h+:32]),.o_f(hf[h]));
    end
    endgenerate
    ot_s81_su_qnr #(.NE(NH),.NV(1),.D(D),.LM(LM),.LA(LA)) u_reduce(
        .clk(ck_reduce),.rst_in(rs_reduce),.i_go(go),.i_eps(eps),
        .p_v(hv),.p_p(hp),.p_d(hd),.p_f(hf),.r_v(rv),.r_d(rd),.o_f(rf));
    generate for(q=0;q<NQ;q=q+1) begin:g_quant
        ot_s81_su_cn_quant #(.E4M3(E4M3)) u_quant(
            .clk(ck_quant[q]),.rst_in(rs_quant[q]),.i_v(av[4*q]),
            .i_x(aligned[1024*q+:1024]),.o_v(y_v[q]),.o_y(y[512*q+:512]),.o_raw(raw[144*q+:144]),.o_fault(qf[q]));
    end endgenerate
    assign fault=(|nf)||(|hf)||rf||(|qf);
endmodule

module ot_s81_su_cn_align #(parameter integer DEPTH=12)(
    input wire clk,rst_in,i_v,input wire [255:0] i_d,
    output wire o_v,output wire [255:0] o_d
);
    ot_hdc_delay #(.W(257),.D(DEPTH),.RESET(1)) u_delay(
        .clk(clk),.rst_n(rst_in),.d({i_v,i_d}),.q({o_v,o_d}));
endmodule

// Registered quantiser boundary. Reuses exact saturating E4M3 and native f12
// UE8M0 arithmetic; the latter is the existing QB FP4 path.
module ot_s81_su_cn_quant #(parameter integer E4M3=1)(
    input wire clk,rst_in,i_v,input wire [1023:0] i_x,
    output reg o_v,output reg [511:0] o_y,output reg [143:0] o_raw,output reg o_fault
);
    reg v;reg [1023:0] x;
    wire qv,qf;wire [511:0] qy;wire [143:0] raw;
    always @(posedge clk) x<=i_x;
    always @(posedge clk or negedge rst_in) if(!rst_in)v<=0;else v<=i_v;
    generate if(E4M3) begin:g_e4m3
        wire [264:0] packed_result;
        ot_hgi_fp4qdq #(.PIPE(1),.PACKED(1)) u_q(.clk(clk),.rst_n(rst_in),.v(v),.x(x),
            .vo(qv),.y(qy),.fault(qf),.packed_word(packed_result),.x4_ext(1024'd0));
        assign raw=packed_result[143:0];
    end else begin:g_e8m0
        wire [255:0] codes;wire signed [9:0] exponent;
        wire [9:0] biased_exponent=exponent+10'sd127;
        ot_dsrom_actquant_f12 #(.MLAT(5)) u_q(.clk(clk),.rst_n(rst_in),.v(v),.x(x),.fp4(1'b1),
            .vo(qv),.q(codes),.e(exponent),.y(qy),.fault(qf));
        genvar k;
        for(k=0;k<32;k=k+1)begin:g_code assign raw[4*k+:4]=codes[8*k+:4];end
        assign raw[143:128]={8'd0,biased_exponent[7:0]};
    end endgenerate
    always @(posedge clk)begin o_y<=qy;o_raw<=raw;end
    always @(posedge clk or negedge rst_in) if(!rst_in)begin o_v<=0;o_fault<=0;end
        else begin o_v<=qv;o_fault<=o_fault||(qv&&qf);end
endmodule

// The production shared-KV successor uses only these new reducers/quant exits;
// it reuses the existing KVE512 bank instead of placing a second norm engine.
module ot_s81_su_ik_reduce(
    input wire [1:0] ck_half,rs_half,input wire ck_reduce,rs_reduce,
    input wire go,input wire [31:0] eps,
    input wire [15:0] p_v,input wire [511:0] p_d,
    output wire r_v,output wire [31:0] r_d,output wire fault
);
    wire [1:0] hv,hp,hf;wire [63:0] hd;wire rf;
    genvar h;
    generate for(h=0;h<2;h=h+1)begin:g_half
        dsfd_su_t_ikh u_half(.ck(ck_half[h]),.rst(rs_half[h]),.i_go(go),
            .p_v(p_v[8*h+:8]),.p_p(8'd0),.p_d(p_d[256*h+:256]),
            .s_v(hv[h]),.s_p(hp[h]),.s_d(hd[32*h+:32]),.o_f(hf[h]));
    end endgenerate
    dsfd_su_t_ikr u_reduce(.ck(ck_reduce),.rst(rs_reduce),
        .i_go(go),.i_eps(eps),.p_v(hv),.p_p(hp),.p_d(hd),.p_f(hf),
        .r_v(r_v),.r_d(r_d),.o_f(rf));
    assign fault=rf||(|hf);
endmodule

module ot_s81_su_cn_write #(parameter integer E4M3=1)(
    input wire clk,rst_in,i_v,input wire [1023:0] i_x,
    input wire [13:0] i_ob,input wire [3:0] i_block,
    output reg o_v,output reg [13:0] o_a,output reg [15:0] o_m,
    output reg [511:0] o_d,output wire o_fault
);
    wire qv,qf;wire [511:0] qy;wire [143:0] raw;
    reg [13:0] address;reg pending;reg [143:0] raw_hold;
    reg overlap;
    always @(posedge clk) if(i_v)address<=i_ob+{10'd0,i_block};
    ot_s81_su_cn_quant #(.E4M3(E4M3)) u_quant(.clk(clk),.rst_in(rst_in),.i_v(i_v),.i_x(i_x),
        .o_v(qv),.o_y(qy),.o_raw(raw),.o_fault(qf));
    // Two fixed writes: QDQ first, then original quant codes/scales. Never
    // re-quantise the QDQ BF16 values; that can change the selected scale.
    always @(posedge clk)begin
        if(qv)raw_hold<=raw;
        o_a<=pending ? address+(E4M3?14'd16:14'd4) : address;
        o_m<=16'hffff;
        o_d<=pending ? {368'd0,raw_hold} : qy;
    end
    always @(posedge clk or negedge rst_in)if(!rst_in)begin o_v<=0;pending<=0;overlap<=0;end
        else begin o_v<=qv||pending;pending<=qv;overlap<=overlap||(qv&&pending);end
    assign o_fault=qf||overlap;
endmodule


module ot_s81_su_cn_norm_write(
    input wire clk,rst_in,i_v,input wire [511:0] i_x,
    input wire [13:0] i_ob,input wire [3:0] i_block,
    output reg o_v,output reg [13:0] o_a,output reg [511:0] o_d
);
    integer i;
    always @(posedge clk)begin
        o_a<=i_ob+{10'd0,i_block};
        o_d<=i_x;
    end
    always @(posedge clk or negedge rst_in)if(!rst_in)o_v<=0;else o_v<=i_v;
endmodule
