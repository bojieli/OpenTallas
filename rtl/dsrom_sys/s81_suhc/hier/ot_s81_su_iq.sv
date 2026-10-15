`timescale 1ns/1ps
// Native32-head128-dimensional query provider. A compiler reserved head slot
// occurs every TWO cycles. Every arithmetic/memory/control state holder is an
// explicit leaf with its own clock/reset. The parent is wires only.
module ot_s81_su_iq #(
    parameter integer MUT=0
)(
    input wire [3:0] ck_rope,rs_rope,ck_quant,rs_quant,
    input wire ck_delay,rs_delay,ck_weight,rs_weight,ck_wdelay,rs_wdelay,ck_frame,rs_frame,
    input wire start,input wire [511:0] header,
    input wire q_v,input wire [4:0] q_head,
    input wire [2047:0] q_bf16,
    input wire [15:0] weight_proj_bf16,
    input wire [1023:0] cos_t,sin_t,
    output wire f_v,output wire [511:0] f_d,
    output wire done,output wire fault
);
    wire [1023:0] first_half;
    wire [1023:0] rope_half;
    wire [3:0] rv,rf,qv,qf;
    wire [575:0] raw;
    wire d_v,w_v,wd_v,wf;
    wire [15:0] w,wd;
    // First64 values are already BF16 at the actual FIELD boundary. Retain
    // them unchanged while the last64 pass through the exact QR row engines.
    ot_s81_iq_first64 u_first(.clk(ck_delay),.rst_n(rs_delay),.i_v(q_v),
        .i_x(q_bf16[1023:0]),.o_v(d_v),.o_x(first_half));
    genvar r,b;
    generate for(r=0;r<4;r=r+1)begin:g_rope
        ot_s81_iq_rope_row #(.MUT(MUT==1?3:0)) u_rope(
            .clk(ck_rope[r]),.rst_n(rs_rope[r]),.i_v(q_v),
            .i_x(q_bf16[1024+256*r+:256]),.i_cos(cos_t[256*r+:256]),.i_sin(sin_t[256*r+:256]),
            .o_v(rv[r]),.o_y(rope_half[256*r+:256]),.fault(rf[r]));
    end
    for(b=0;b<4;b=b+1)begin:g_quant
        wire [511:0] x;wire v;
        if(b<2)begin:g_first assign x=first_half[512*b+:512];assign v=d_v;end
        else begin:g_tail assign x=rope_half[512*(b-2)+:512];assign v=rv[2*(b-2)];end
        ot_s81_iq_quant u_quant(.clk(ck_quant[b]),.rst_n(rs_quant[b]),.i_v(v),.i_x(x),
            .o_v(qv[b]),.o_raw(raw[144*b+:144]),.fault(qf[b]));
    end endgenerate
    ot_s81_iq_weight #(.MUT(MUT==2)) u_weight(.clk(ck_weight),.rst_n(rs_weight),
        .i_v(q_v),.i_w(weight_proj_bf16),.o_v(w_v),.o_w(w),.fault(wf));
    ot_s81_iq_weight_delay u_wdelay(.clk(ck_wdelay),.rst_n(rs_wdelay),.i_v(w_v),.i_w(w),.o_v(wd_v),.o_w(wd));
    ot_s81_iq_frame u_frame(.clk(ck_frame),.rst_n(rs_frame),.start(start),.header(header),
        .i_qv(q_v),.i_head(q_head),.i_v(qv),.i_raw(raw),.i_wv(wd_v),.i_w(wd),
        .i_fault((|rf)||(|qf)||wf),.o_v(f_v),.o_d(f_d),.done(done),.fault(fault));
endmodule

module ot_s81_iq_rope_row #(parameter integer MUT=0)(
    input wire clk,rst_n,i_v,input wire [255:0] i_x,i_cos,i_sin,
    output wire o_v,output wire [255:0] o_y,output wire fault
);
    reg v;reg [255:0] x,cc,ss;
    always @(posedge clk)begin x<=i_x;cc<=i_cos;ss<=i_sin;end
    always @(posedge clk or negedge rst_n)if(!rst_n)v<=0;else v<=i_v;
    wire [511:0] xf,y;
    wire unused_ready,unused_v2;wire [511:0] unused_d2;
    genvar k;generate for(k=0;k<16;k=k+1)begin:g_fp32
        assign xf[32*k+:32]={x[16*k+:16],16'd0};
        assign o_y[16*k+:16]=y[32*k+16+:16];
    end endgenerate
    // Exact QR datapath factored from ot_s81_su_rxe. Keeping RA/RB out of
    // this leaf avoids elaborating unrelated softplus engines on the IQ path.
    ot_s81_iq_qr16 #(.MUT(MUT)) u_qr(.clk(clk),.rst_n(rst_n),.i_v(v),.i_x(xf),
        .i_cos(cc),.i_sin(ss),.o_v(o_v),.o_y(y),.fault(fault));
    assign unused_ready=1'b0;assign unused_v2=1'b0;assign unused_d2=512'd0;
endmodule

module ot_s81_iq_first64(
    input wire clk,rst_n,i_v,input wire [1023:0] i_x,
    output wire o_v,output wire [1023:0] o_x
);
    wire [14:0] v;
    ot_hdc_vline #(.D(14)) u_v(.clk(clk),.rst_n(rst_n),.v(i_v),.vd(v));
    ot_sram_dline #(.W(1024),.D(14)) u_data(.clk(clk),.rst_n(rst_n),.d(i_x),.q(o_x));
    assign o_v=v[14];
endmodule

module ot_s81_iq_quant(
    input wire clk,rst_n,i_v,input wire [511:0] i_x,
    output reg o_v,output reg [143:0] o_raw,output reg fault
);
    reg v;reg [511:0] x;
    always @(posedge clk)x<=i_x;
    always @(posedge clk or negedge rst_n)if(!rst_n)v<=0;else v<=i_v;
    wire [1023:0] xf;wire qv,qf;wire [255:0] codes;wire [511:0] unused_y;
    wire signed [9:0] e;wire signed [10:0] biased=$signed(e)+11'sd127;
    genvar k;generate for(k=0;k<32;k=k+1)begin:g_x assign xf[32*k+:32]={x[16*k+:16],16'd0};end endgenerate
    ot_dsrom_actquant_f12 #(.MLAT(5),.XSRAM(1)) u_q(.clk(clk),.rst_n(rst_n),.v(v),.fp4(1'b1),.x(xf),
        .vo(qv),.q(codes),.e(e),.y(unused_y),.fault(qf));
    integer j;
    always @(posedge clk)begin
        for(j=0;j<32;j=j+1)o_raw[4*j+:4]<=codes[8*j+:4];
        o_raw[143:128]<={8'd0,biased[7:0]};
    end
    always @(posedge clk or negedge rst_n)if(!rst_n)begin o_v<=0;fault<=0;end
        else begin o_v<=qv;fault<=fault||(qv&&(qf||biased<0||biased>255));end
endmodule

module ot_s81_iq_weight #(parameter integer MUT=0)(
    input wire clk,rst_n,i_v,input wire [15:0] i_w,
    output reg o_v,output reg [15:0] o_w,output reg fault
);
    reg v;reg [15:0] w;
    always @(posedge clk)w<=i_w;
    always @(posedge clk or negedge rst_n)if(!rst_n)v<=0;else v<=i_v;
    wire [31:0] y;wire f;wire [5:0] vv;
    ot_hdc_qmul_lat #(5) u_mul(.clk(clk),.rst_n(rst_n),.v(v),.a({w,16'd0}),
        .b(MUT?32'h3f800000:32'h3c800000),.y(y),.fault(f));
    ot_hdc_vline #(.D(5)) u_v(.clk(clk),.rst_n(rst_n),.v(v),.vd(vv));
    wire [32:0] rounded={1'b0,y}+33'h7fff+{32'd0,y[16]};
    always @(posedge clk)o_w<=rounded[31:16];
    always @(posedge clk or negedge rst_n)if(!rst_n)begin o_v<=0;fault<=0;end
        else begin o_v<=vv[5];fault<=fault||(vv[5]&&f);end
endmodule

module ot_s81_iq_weight_delay(
    input wire clk,rst_n,i_v,input wire [15:0] i_w,
    output wire o_v,output wire [15:0] o_w
);
    ot_hdc_delay #(.W(17),.D(27),.RESET(1)) u_delay(.clk(clk),.rst_n(rst_n),.d({i_v,i_w}),.q({o_v,o_w}));
endmodule

module ot_s81_iq_frame(
    input wire clk,rst_n,start,input wire [511:0] header,
    input wire i_qv,input wire [4:0] i_head,
    input wire [3:0] i_v,input wire [575:0] i_raw,
    input wire i_wv,input wire [15:0] i_w,input wire i_fault,
    output reg o_v,output reg [511:0] o_d,output reg done,output reg fault
);
    localparam integer FIRST_RAW=34,LAST_META=97;
    reg active;reg [7:0] age;reg pending;reg [47:0] meta;
    wire [8:0] step={1'b0,age}+9'd1;
    wire want_input=active&&(step<=62)&&!step[0];
    wire want_raw=active&&(step>=FIRST_RAW)&&(step<=FIRST_RAW+62)&&!step[0];
    wire raw_any=|i_v,raw_all=&i_v;
    wire bad_header=header[511:508]!=4'd4||!header[503]||header[491:480]!=12'd64;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin active<=0;age<=0;pending<=0;done<=0;fault<=0;o_v<=0;o_d<=0;meta<=0;end
        else begin
            o_v<=0;done<=0;
            if(start)begin
                if(active||!i_qv||i_head!=0||bad_header)fault<=1;
                active<=1;age<=0;pending<=0;
                if(!fault&&!active&&!bad_header)begin o_v<=1;o_d<=header;end
            end else if(active)begin
                age<=step[7:0];
                if(i_qv!=want_input||(i_qv&&i_head!=step[5:1]))fault<=1;
                if(raw_any!=want_raw||(raw_any&&(!raw_all||!i_wv))||i_fault)fault<=1;
                if(i_wv!=raw_all)fault<=1;
                if(raw_all)begin
                    if(pending)fault<=1;
                    pending<=1;
                    meta<={i_w,i_raw[144*3+128+:8],i_raw[144*2+128+:8],i_raw[144+128+:8],i_raw[128+:8]};
                    if(!fault)begin
                        o_v<=1;o_d<={i_raw[144*3+:128],i_raw[144*2+:128],i_raw[144+:128],i_raw[0+:128]};
                    end
                end else if(pending)begin
                    pending<=0;if(!fault)begin o_v<=1;o_d<={464'd0,meta};end
                end
                if(step==LAST_META)begin active<=0;done<=1;if(!pending)fault<=1;end
            end else if(i_qv||raw_any||i_wv)fault<=1;
        end
    end
endmodule


// Same per-lane multiply/add/BF16 order and13-cycle latency as the QR arm
// of ot_s81_su_rxe (LMR6,LAR5 plus rounding/output registers).
module ot_s81_iq_qr16 #(parameter integer MUT=0)(
    input wire clk,rst_n,i_v,input wire [511:0] i_x,
    input wire [255:0] i_cos,i_sin,
    output reg o_v,output reg [511:0] o_y,output reg fault
);
    wire [12:0] vv;
    ot_hdc_vline #(.D(12)) u_v(.clk(clk),.rst_n(rst_n),.v(i_v),.vd(vv));
    wire [511:0] sums;wire [15:0] bad;
    reg [511:0] rounded;
    genvar l;
    generate for(l=0;l<16;l=l+1)begin:g_lane
        localparam integer ODD=l%2;
        wire [31:0] pp,qq;wire fp,fq,fa;
        wire [31:0] sn=i_sin[32*(l/2)+:32];
        wire [31:0] signed_sin=(ODD^(MUT==3))?sn:{~sn[31],sn[30:0]};
        ot_hdc_qmul_lat #(6) u_p(.clk(clk),.rst_n(rst_n),.v(i_v),.a(i_x[32*l+:32]),.b(i_cos[32*(l/2)+:32]),.y(pp),.fault(fp));
        ot_hdc_qmul_lat #(6) u_q(.clk(clk),.rst_n(rst_n),.v(i_v),.a(i_x[32*(l^1)+:32]),.b(signed_sin),.y(qq),.fault(fq));
        ot_dsrom_qadd #(.LAT(5)) u_a(.clk(clk),.rst_n(rst_n),.v(vv[6]),.a(pp),.b(qq),.y(sums[32*l+:32]),.fault(fa));
        assign bad[l]=fp||fq||fa;
        wire [32:0] rr={1'b0,sums[32*l+:32]}+33'h7fff+{32'd0,sums[32*l+16]};
        always @(posedge clk)rounded[32*l+:32]<={rr[31:16],16'd0};
    end endgenerate
    always @(posedge clk)o_y<=rounded;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin o_v<=0;fault<=0;end
        else begin o_v<=vv[12];fault<=fault||(|bad);end
endmodule
