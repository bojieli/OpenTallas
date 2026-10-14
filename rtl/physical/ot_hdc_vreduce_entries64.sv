`timescale 1ns/1ps
// Structural opt-in prototype: eight regional SQ/chunk leaves and one tail.
// Every child has its own clock input; parent only wires. Relative result latency +3:
// region input capture, region output capture, tail input capture. Original remains reference.
module ot_hdc_vreduce_region8 #(parameter integer AW=24,QLA=3,QLM=3) (
 input wire clk,rst_n,v_in,mx_in,sq_in,last_in,
 input wire [AW-1:0] addr_in,input wire [255:0] x_in,
 output reg v_out,output reg [AW+1:0] tag_out,output reg [31:0] data_out,
 output reg fault_out,output reg busy_out);
 localparam integer SW=8,LA=QLA,LM=QLM,CD=7*LA,NC=1,LC=0,TAG=AW+2;
 reg iv,imx,isq,ilast;reg [AW-1:0] ia;reg [255:0] ix;
 always @(posedge clk or negedge rst_n) if(!rst_n)iv<=0;else iv<=v_in;
 always @(posedge clk)begin imx<=mx_in;isq<=sq_in;ilast<=last_in;ia<=addr_in;ix<=x_in;end
    // -- SQ: every element takes the squaring stage (fixed depth) ------------------
    wire [SW*32-1:0] xsq, xd;
    wire [SW-1:0]    fsq;
    genvar l;
    generate for (l = 0; l < SW; l = l + 1) begin : g_sq
        if (LM == 3) begin : g_fast
          ot_hdc_qmul #(.L(LM)) u_sq (clk, rst_n, iv && isq, ix[32*l +: 32], ix[32*l +: 32], xsq[32*l +: 32], fsq[l]);
        end else begin : g_cut
          wire [1:0] err;
          wire vo;
          ot_hdc_fp32_mul_lat #(.LAT(LM), .DRST(0)) u_sq (.clk(clk), .rst_n(rst_n),
            .valid_in(iv && isq), .a(ix[32*l +: 32]), .b(ix[32*l +: 32]),
            .y(xsq[32*l +: 32]), .err(err), .valid_out(vo));
          assign fsq[l] = vo && (err != 0);
        end
    end endgenerate
    wire [SW*32-1:0] xq;
    wire [TAG-1:0]   tq;
    wire             vq, sqq;
    ot_hdc_delay #(.W(SW*32 + TAG + 1), .D(LM)) u_sqd (.clk(clk), .rst_n(rst_n),
        .d({ix, imx, ilast, ia, isq}), .q({xd, tq, sqq}));
    wire [LM:0] vqs;
    ot_hdc_vline #(.D(LM)) u_vq (.clk(clk), .rst_n(rst_n), .v(iv), .vd(vqs));
    reg  [SW*32-1:0] c_x;
    reg  [TAG-1:0]   c_t;
    reg              c_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) c_v <= 1'b0;
        else c_v <= vqs[LM];
    end
    always @(posedge clk) begin
        c_x <= sqq ? xsq : xd;
        c_t <= tq;
    end
    wire c_mx = c_t[TAG-1];

    // -- CHAIN: chunk k = lanes 8k .. 8k+7, sequential from lane 8k -----------------
    wire [NC*32-1:0] chunk;
    wire [NC*7-1:0]  fch;
    wire [CD:0]      vch;
    ot_hdc_vline #(.D(CD)) u_vch (.clk(clk), .rst_n(rst_n), .v(c_v), .vd(vch));
    wire [CD:0] mxl;
    ot_hdc_vline #(.D(CD)) u_mxl (.clk(clk), .rst_n(rst_n), .v(c_v && c_mx), .vd(mxl));
    genvar k, j;
    generate for (k = 0; k < NC; k = k + 1) begin : g_chunk
        wire [32*8-1:0] acc;                 // acc[j]: after element j joins
        assign acc[31:0] = c_x[32*(8*k) +: 32];
        for (j = 1; j < 8; j = j + 1) begin : g_step
            wire [31:0] xj;
            ot_hdc_delay #(.W(32), .D(LA * (j - 1))) u_xd (.clk(clk), .rst_n(rst_n),
                .d(c_x[32*(8*k + j) +: 32]), .q(xj));
            ot_hdc_vred_leaf_op #(.LA(LA)) u_op (.clk(clk), .rst_n(rst_n), .v(vch[LA * (j - 1)]), .mx(mxl[LA * (j - 1)]),
                .a(acc[32*(j-1) +: 32]), .b(xj), .y(acc[32*j +: 32]), .fault(fch[7*k + j - 1]));
        end
        assign chunk[32*k +: 32] = acc[32*7 +: 32];
    end endgenerate
    wire [TAG-1:0] ct;
    ot_hdc_delay #(.W(TAG), .D(CD)) u_ct (.clk(clk), .rst_n(rst_n), .d(c_t), .q(ct));
    wire cv = vch[CD];


 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin v_out<=0;fault_out<=0;end
  else begin v_out<=cv;fault_out<=(|fsq)||(|fch);end
 end
 always @(posedge clk)begin tag_out<=ct;data_out<=chunk;end
 always @(posedge clk or negedge rst_n) if(!rst_n) busy_out<=0;else busy_out<=iv||(|vqs)||c_v||(|vch)||v_out;
endmodule
module ot_hdc_vreduce_tail64 #(parameter integer AW=24,LV=7,QLA=3)(
 input wire clk,rst_n,input wire [7:0] rv,rb,rf,
 input wire [8*(AW+2)-1:0] rt,input wire [255:0] rd,
 output reg o_we,output reg [AW-1:0] o_addr,output reg [31:0] o_data,
 output reg busy,output reg fault);
 localparam integer SW=64,NC=8,LC=3,LA=QLA,TAG=AW+2;
 reg cv;reg [TAG-1:0] ct;reg [255:0] chunk;reg [7:0] ibusy,ifault,ival;reg [8*TAG-1:0] itags;
 wire phase_fault=(|ival)&&((ival!=8'hff)||(itags!={8{itags[TAG-1:0]}}));
 always @(posedge clk or negedge rst_n)if(!rst_n)begin cv<=0;ibusy<=0;ifault<=0;ival<=0;end else begin cv<=rv[0];ibusy<=rb;ifault<=rf;ival<=rv;end
 always @(posedge clk)begin ct<=rt[TAG-1:0];itags<=rt;chunk<=rd;end
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n && (|rv))begin
  if(rv!==8'hff)$fatal(1,"regional valid phase mismatch");
  if(rt!=={8{rt[TAG-1:0]}})$fatal(1,"regional tag mismatch");
 end
`endif
    // -- TREE: pairwise over the vector's NC chunk sums ----------------------------------
    wire [NC*32-1:0] lvl [0:LC];
    wire [LC:0]      tv;
    wire [TAG-1:0]   tt [0:LC];
    wire [LC:0]      tf;
    wire [LC:0]      tvb;                    // a tree level's adders hold an item
    assign tvb[0] = 1'b0;
    assign lvl[0] = chunk;
    assign tv[0] = cv;
    assign tt[0] = ct;
    assign tf[0] = 1'b0;
    genvar lv, p;
    generate for (lv = 1; lv <= LC; lv = lv + 1) begin : g_tree
        wire [(NC >> lv)-1:0] pf;
        reg  [NC*32-1:0] q;
        wire [LA:0] vd;
        ot_hdc_vline #(.D(LA)) u_vd (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .vd(vd));
        wire [TAG-1:0] td;
        ot_hdc_delay #(.W(TAG), .D(LA)) u_td (.clk(clk), .rst_n(rst_n), .d(tt[lv-1]), .q(td));
        for (p = 0; p < (NC >> lv); p = p + 1) begin : g_pair
            wire [31:0] s;
            ot_hdc_vred_leaf_op #(.LA(LA)) u_op (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .mx(tt[lv-1][TAG-1]),
                .a(lvl[lv-1][32*(2*p) +: 32]), .b(lvl[lv-1][32*(2*p+1) +: 32]), .y(s), .fault(pf[p]));
            always @(posedge clk) q[32*p +: 32] <= s;
        end
        if ((NC >> lv) < NC) begin : g_rest
            always @(posedge clk) q[NC*32-1 : (NC >> lv)*32] <= 0;
        end
        reg rv;
        reg [TAG-1:0] rt;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= vd[LA];
        end
        always @(posedge clk) rt <= td;
        assign lvl[lv] = q;
        assign tv[lv] = rv;
        assign tt[lv] = rt;
        assign tf[lv] = |pf;
        assign tvb[lv] = |vd;
    end endgenerate

    // -- TIME: pair the segment's vector sums --------------------------------------------
    wire [31:0]    sv [0:LV];
    wire [LV:0]    sval;
    wire [TAG-1:0] st [0:LV];
    wire [LV:0]    sf;
    wire [LV:0]    tb;                     // a level's op or pass line holds an item
    assign tb[0] = 1'b0;
    assign sv[0] = lvl[LC][31:0];
    assign sval[0] = tv[LC];
    assign st[0] = tt[LC];
    assign sf[0] = 1'b0;
    genvar t;
    generate for (t = 1; t <= LV; t = t + 1) begin : g_time
        wire [31:0] in_x = sv[t-1];
        wire        in_v = sval[t-1];
        wire [TAG-1:0] in_t = st[t-1];
        wire        in_last = in_t[TAG-2];
        reg  [31:0] held;
        reg         held_v;
        //: pair: held (left) with the new item (right); pass: a LAST item with no
        //: held left sibling (its right sibling is +0); hold: otherwise
        wire pair = in_v && held_v;
        wire pass = in_v && !held_v && in_last;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) held_v <= 1'b0;
            else if (pair) held_v <= 1'b0;
            else if (in_v && !pass) held_v <= 1'b1;
        end
        always @(posedge clk) if (in_v && !held_v && !pass) held <= in_x;
        wire [31:0] s, pd;
        wire f;
        ot_hdc_vred_leaf_op #(.LA(LA)) u_op (.clk(clk), .rst_n(rst_n), .v(pair), .mx(in_t[TAG-1]), .a(held),
                                        .b(in_x), .y(s), .fault(f));
        wire [TAG+2-1:0] od;
        ot_hdc_delay #(.W(TAG + 2 + 32), .D(LA)) u_od (.clk(clk), .rst_n(rst_n),
            .d({in_t, pair, pass, in_x}), .q({od, pd}));
        wire [LA:0] vd;
        ot_hdc_vline #(.D(LA)) u_vd (.clk(clk), .rst_n(rst_n), .v(pair || pass), .vd(vd));
        reg  [31:0] q;
        reg         qv;
        reg  [TAG-1:0] qt;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) qv <= 1'b0;
            else qv <= vd[LA];
        end
        always @(posedge clk) begin
            q <= od[1] ? s : pd;               // od = {tag, pair, pass}
            qt <= od[TAG+1 -: TAG];
        end
        assign sv[t] = q;
        assign sval[t] = qv;
        assign st[t] = qt;
        assign sf[t] = f;
        assign tb[t] = |vd;
    end endgenerate

    // -- result ------------------------------------------------------------------------------
    wire top_last = st[LV][TAG-2];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we <= 1'b0; fault <= 1'b0; end
        else begin
            o_we <= sval[LV] && top_last;
            fault <= phase_fault || (|ifault) || (|tf) || (|sf) || (sval[LV] && !top_last);
        end
    end
    always @(posedge clk) begin
        o_addr <= st[LV][AW-1:0];
        o_data <= sv[LV];
    end
    always @(posedge clk or negedge rst_n) if(!rst_n) busy<=0;else busy<=(|ibusy)||cv||(|tv)||(|tvb)||(|sval)||(|tb)||o_we;
endmodule
module ot_hdc_vreduce_entries64 #(parameter integer AW=24,LV=7,QLA=3,QLM=3)(
 input wire [7:0] ck_region,input wire ck_tail,rst_n,
 input wire v_in,mx_in,sq_in,last_in,input wire [AW-1:0] addr_in,input wire [2047:0] x_in,
 output wire o_we,output wire [AW-1:0] o_addr,output wire [31:0] o_data,output wire busy,fault);
 wire [7:0] rv,rb,rf;wire [8*(AW+2)-1:0] rt;wire [255:0] rd;
 genvar i;generate for(i=0;i<8;i=i+1)begin:g_region
  wire [255:0] xi;
`ifdef OT_VRED_REGION_MUT
  assign xi=x_in[256*i+:256] ^ (i==3 ? 256'h800000 : 256'd0);
`else
  assign xi=x_in[256*i+:256];
`endif
`ifdef OT_VRED_HARD
  ot_hdc_vreduce_region8 u_r(
`else
  ot_hdc_vreduce_region8 #(.AW(AW),.QLA(QLA),.QLM(QLM)) u_r(
`endif
.clk(ck_region[i]),.rst_n(rst_n),.v_in(v_in),.mx_in(mx_in),.sq_in(sq_in),.last_in(last_in),.addr_in(addr_in),.x_in(xi),.v_out(rv[i]),.tag_out(rt[(AW+2)*i+:AW+2]),.data_out(rd[32*i+:32]),.fault_out(rf[i]),.busy_out(rb[i]));
 end endgenerate
 wire tbusy;
`ifdef OT_VRED_HARD
 ot_hdc_vreduce_tail64 u_tail(
`else
 ot_hdc_vreduce_tail64 #(.AW(AW),.LV(LV),.QLA(QLA)) u_tail(
`endif
.clk(ck_tail),.rst_n(rst_n),.rv(rv),.rb(rb),.rf(rf),.rt(rt),.rd(rd),.o_we(o_we),.o_addr(o_addr),.o_data(o_data),.busy(tbusy),.fault(fault));
 assign busy=tbusy;
endmodule

// Same scalar MAX/SUM and reduction association as immutable ot_hdc_vred_op.
// Extra adder cuts use the qualified LAT pipeline; only valid bits carry reset.
module ot_hdc_vred_leaf_op #(parameter integer LA=3)(
 input wire clk,rst_n,v,mx,input wire[31:0] a,b,output wire[31:0]y,output wire fault);
 function automatic[31:0]okey(input[31:0]x);
  okey=x[31]?~x:{1'b1,x[30:0]};
 endfunction
 wire[31:0]ys,ym;wire mxd;
 generate if(LA==3)begin:g_fast
  ot_hdc_qadd u_add(clk,rst_n,v&&!mx,a,b,ys,fault);
 end else begin:g_cut
  wire[1:0]err;wire vo;
  ot_hdc_fp32_add_lat #(.LAT(LA),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(v&&!mx),.a(a),.b(b),.y(ys),.err(err),.valid_out(vo));
  assign fault=vo&&(err!=0);
 end endgenerate
 ot_hdc_delay #(.W(33),.D(LA)) u_m(.clk(clk),.rst_n(rst_n),.d({mx,(okey(a)>=okey(b))?a:b}),.q({mxd,ym}));
 assign y=mxd?ym:ys;
endmodule

// Physical parent boundary: nine scalar independent child entries; no parent registers or gates.
module qfd_su_vred_entries64 #(parameter integer QLA=4,QLM=5)(
 input wire ck_region0,ck_region1,ck_region2,ck_region3,ck_region4,ck_region5,ck_region6,ck_region7,ck_tail,rst_n,
 input wire v_in,mx_in,sq_in,last_in,input wire [23:0]addr_in,input wire [2047:0]x_in,
 output wire o_we,output wire [23:0]o_addr,output wire [31:0]o_data,output wire busy,fault);
 ot_hdc_vreduce_entries64 #(.QLA(QLA),.QLM(QLM)) u_body(
  .ck_region({ck_region7,ck_region6,ck_region5,ck_region4,ck_region3,ck_region2,ck_region1,ck_region0}),
  .ck_tail(ck_tail),.rst_n(rst_n),.v_in(v_in),.mx_in(mx_in),.sq_in(sq_in),.last_in(last_in),.addr_in(addr_in),.x_in(x_in),
  .o_we(o_we),.o_addr(o_addr),.o_data(o_data),.busy(busy),.fault(fault));
endmodule
