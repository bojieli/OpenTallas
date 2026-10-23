`timescale 1ns/1ps
/*verilator lint_off BLKSEQ*/
/*verilator lint_off WIDTH*/
/*verilator lint_off UNUSED*/
module ot_sram_1r1w_128x256_m1_r2c2_m165 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [6:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [6:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [13:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
    localparam integer WORDS = 128;
    localparam integer BITS = 256;
    localparam integer MUX = 1;
    localparam integer AW = 7;
    localparam integer ROWS = 128;
    localparam integer NSR = 2;
    localparam integer NSC = 2;
    localparam integer PR = 130;
    localparam integer PC = 258;
    localparam integer RA = 7;
    localparam integer CB = 8;
    reg [PC-1:0] arr [0:PR-1];
    integer init_i;
    initial begin
        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};
    end
    function automatic integer phys_row(input integer a);
        integer k, r;
        begin
            r = a / MUX;
            for (k = 0; k < NSR; k = k + 1)
                if (rr_en[k] && rr_addr[k*RA +: RA] == r[RA-1:0]) r = ROWS + k;
            phys_row = r;
        end
    endfunction
    function automatic integer phys_col(input integer b, input integer s);
        integer k, io;
        begin
            io = b;
            for (k = 0; k < NSC; k = k + 1)
                if (cr_en[k] && cr_sel[k*CB +: CB] == b[CB-1:0]) io = BITS + k;
            phys_col = io * MUX + s;
        end
    endfunction
    function automatic cell_read(input integer r, input integer c);
        reg v;
        begin
            v = arr[r][c];
            cell_read = v;
        end
    endfunction
    task automatic cell_write(input integer r, input integer c, input reg v);
        reg old, nv;
        begin
            old = arr[r][c];
            nv = v;
            arr[r][c] = nv;
        end
    endtask
    function automatic [65:0] decode(input integer a);
        integer r0, r1;
        reg [1:0] sel_n;
        begin
            r0 = phys_row(a);
            r1 = r0;
            sel_n = 2'd1;
            decode = {sel_n, r1[31:0], r0[31:0]};
        end
    endfunction
    function automatic [BITS-1:0] word_read(input integer a);
        integer b, s, r0, r1, n;
        reg [BITS-1:0] q;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (n == 0) q[b] = 1'b0;
                else if (n == 1) q[b] = cell_read(r0, phys_col(b, s));
                else q[b] = cell_read(r0, phys_col(b, s)) & cell_read(r1, phys_col(b, s));
            word_read = q;
        end
    endfunction
    task automatic word_write(input integer a, input [BITS-1:0] d, input [BITS-1:0] m);
        integer b, s, r0, r1, n;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (m[b] && n != 0) begin
                    cell_write(r0, phys_col(b, s), d[b]);
                    if (n == 2) cell_write(r1, phys_col(b, s), d[b]);
                end
        end
    endtask
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= word_read(r_addr_in);
        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);
    end
endmodule
/*verilator lint_on BLKSEQ*/
/*verilator lint_on WIDTH*/
/*verilator lint_on UNUSED*/
`timescale 1ns/1ps
`default_nettype none
(* keep_hierarchy *)
module ot_hbm_su_red_pt_sel8_r13_m165 #(parameter integer K=0)(input wire mode, va, vb, input wire [31:0] a, b, output wire [7:0] ia, ib);
 wire agt=(a[31]!=b[31])?!a[31]:(a[31]?(a[30:0]<b[30:0]):(a[30:0]>b[30:0]));
 wire [7:0] a8=a[K*8+:8], b8=b[K*8+:8];
 wire [7:0] mx=(va&&vb)?(agt?a8:b8):(va?a8:b8);
 assign ia=mode?mx:(va?a8:8'd0);
 assign ib=mode?8'd0:(vb?b8:8'd0);
endmodule
(* keep_hierarchy *)
module ot_hbm_su_red_pt_kq_r13_m165 #(parameter integer N=1)(input wire clk, input wire d, (* keep = 1 *) output wire q);
 reg [N-1:0] p;
 always @(posedge clk) p<={p[N-2+(N==1):0],d};
 assign q=p[N-1];
endmodule
(* keep_hierarchy *)
module ot_hbm_su_red_pt_kqr_r13_m165(input wire clk, r0, r1, r2, r3, r4, r5, d, (* keep = 1 *) output wire q);
 reg [5:0] p;
 always @(posedge clk or negedge r0) if(!r0) p[0]<=1'b0; else p[0]<=d;
 always @(posedge clk or negedge r1) if(!r1) p[1]<=1'b0; else p[1]<=p[0];
 always @(posedge clk or negedge r2) if(!r2) p[2]<=1'b0; else p[2]<=p[1];
 always @(posedge clk or negedge r3) if(!r3) p[3]<=1'b0; else p[3]<=p[2];
 always @(posedge clk or negedge r4) if(!r4) p[4]<=1'b0; else p[4]<=p[3];
 always @(posedge clk or negedge r5) if(!r5) p[5]<=1'b0; else p[5]<=p[4];
 assign q=p[5];
endmodule
module ot_hbm_su_red_pretree_node_r13_m165 #(parameter integer LAT=6)(
 input wire clk, rst_n,
 input wire [3:0] mode_in,              
 input wire [3:0] va, input wire [31:0] a,
 input wire [3:0] vb, input wire [31:0] b,
 output wire [3:0] mode_out, output wire [3:0] vy, output wire [31:0] y, output wire err
);
 wire [31:0] ia, ib;
 for(genvar k=0;k<4;k=k+1)begin:g_sel
  ot_hbm_su_red_pt_sel8_r13_m165 #(.K(k)) u_s(.mode(mode_in[k]),.va(va[k]),.vb(vb[k]),.a(a),.b(b),.ia(ia[k*8+:8]),.ib(ib[k*8+:8]));
 end
 wire v=va[0]||vb[0];
 wire [1:0] e; wire vo;
 ot_hdc_fp32_add_n32_m165 #(.LAT(LAT),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(ia),.b(ib),.y(y),.err(e),.valid_out(vo));
 generate if(LAT!=6) begin:g_bad_lat ot_hbm_su_red_pretree_node_r13_requires_LAT6 u_trap(); end endgenerate
 reg [LAT-2:0] md;
 always @(posedge clk) md<={md[LAT-3:0],mode_in[0]};
 for(genvar k=0;k<4;k=k+1)begin:g_cp
  ot_hbm_su_red_pt_kq_r13_m165 #(.N(1)) u_m(.clk(clk),.d(md[LAT-2]),.q(mode_out[k]));
  ot_hbm_su_red_pt_kqr_r13_m165 u_v(.clk(clk),.r0(rst_n),.r1(rst_n),.r2(rst_n),.r3(rst_n),.r4(rst_n),.r5(rst_n),.d(v),.q(vy[k]));
 end
 assign err=vo&&(e!=2'd0);
endmodule
module ot_hbm_su_red_pretree_j_r13_m165 #(parameter integer LAT=6,MUT=0)(
 input wire clk, rst_n,
 input wire [4*67-1:0] slice_t,
 output reg tree_v, output reg [31:0] tree_x, output reg tree_max,
 output reg fault
);
 reg [4*67-1:0] t_p;                    
 always @(posedge clk) t_p<=slice_t;
 wire [31:0] l0_x [0:7];
 for(genvar k=0;k<8;k=k+1) begin:g_leaf
  localparam integer S=k%4, H=k/4;
  assign l0_x[k]=t_p[67*S+33*H+:32];
 end
 wire [3:0] l1_m [0:3]; wire [3:0] l1_v [0:3]; wire [3:0] l1_e; wire [31:0] l1_x [0:3];
 for(genvar i=0;i<4;i=i+1) begin:g_l1
  localparam integer A=(MUT==2&&i<2)?i:2*i, B=(MUT==2&&i<2)?i+2:2*i+1;
  localparam integer BA=67*(A%4)+33*(A/4)+32, BB=67*(B%4)+33*(B/4)+32;
  wire [3:0] m_c, va_c, vb_c;
  for(genvar k=0;k<4;k=k+1)begin:g_pc         
   ot_hbm_su_red_pt_kq_r13_m165 #(.N(1)) u_m(.clk(clk),.d(slice_t[66]),.q(m_c[k]));
   ot_hbm_su_red_pt_kq_r13_m165 #(.N(1)) u_a(.clk(clk),.d(slice_t[BA]),.q(va_c[k]));
   ot_hbm_su_red_pt_kq_r13_m165 #(.N(1)) u_b(.clk(clk),.d(slice_t[BB]),.q(vb_c[k]));
  end
  ot_hbm_su_red_pretree_node_r13_m165 #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(m_c),.va(va_c),.a(l0_x[A]),
   .vb(vb_c),.b(l0_x[B]),.mode_out(l1_m[i]),.vy(l1_v[i]),.y(l1_x[i]),.err(l1_e[i]));
 end
 wire [3:0] l2_m [0:1]; wire [3:0] l2_v [0:1]; wire [1:0] l2_e; wire [31:0] l2_x [0:1];
 for(genvar i=0;i<2;i=i+1) begin:g_l2
  ot_hbm_su_red_pretree_node_r13_m165 #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(l1_m[2*i]),.va(l1_v[2*i]),.a(l1_x[2*i]),
   .vb(l1_v[2*i+1]),.b(l1_x[2*i+1]),.mode_out(l2_m[i]),.vy(l2_v[i]),.y(l2_x[i]),.err(l2_e[i]));
 end
 wire [3:0] l3_m, l3_v; wire l3_e; wire [31:0] l3_x;
 ot_hbm_su_red_pretree_node_r13_m165 #(.LAT(LAT)) u_n3(.clk(clk),.rst_n(rst_n),.mode_in(l2_m[0]),.va(l2_v[0]),.a(l2_x[0]),
  .vb(l2_v[1]),.b(l2_x[1]),.mode_out(l3_m),.vy(l3_v),.y(l3_x),.err(l3_e));
 always @(posedge clk) begin tree_x<=l3_x; tree_max<=l3_m[0]; end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin tree_v<=1'b0; fault<=1'b0; end
  else begin tree_v<=l3_v[0]; if((|l1_e)||(|l2_e)||l3_e) fault<=1'b1; end
endmodule
`default_nettype wire
module ot_hbm_su_reduce_static_r13_m165 #(parameter AW=10)(
 input wire clk,rst_n,cmd_valid,
 input wire [2:0] cmd_op,
 input wire [AW-1:0] cmd_a,cmd_b,cmd_dst,
 input wire [31:0] operand_fp32,cmd_tag,
 output reg scalar_valid, output reg [31:0] scalar_tag,scalar_fp32,
 output reg [15:0] scalar_bf16,output reg fault
);
 reg rst_local;
 reg iv; reg [2:0] iop; reg [AW-1:0] ia,ib,idst; reg [31:0] ix,itag;
 always @(posedge clk) begin
  rst_local <= rst_n;
  iv <= rst_n && cmd_valid;
  iop <= cmd_op; ia <= cmd_a; ib <= cmd_b; idst <= cmd_dst;
  ix <= operand_fp32; itag <= cmd_tag;
 end
 generate if(AW!=10) begin:g_bad_aw
  ot_hbm_su_reduce_static_requires_AW10 invalid_parameter();
 end endgenerate
 reg cv;reg [2:0] co;reg [AW-1:0] ca,cb,cd;reg[31:0] cx,ct;
 always @(posedge clk) begin
  if(!rst_local) cv<=0;else cv<=iv;
  co<=iop;ca<=ia;cb<=ib;cd<=idst;cx<=ix;ct<=itag;
 end
 (* keep = 1 *) reg [7:0] cw_a[0:1],cw_b[0:1];
 for(genvar h=0;h<2;h=h+1)begin:g_word_capture
  for(genvar n=0;n<8;n=n+1)begin:g_word
   always @(posedge clk) begin cw_a[h][n]<=(ia[2:0]==3'(n));cw_b[h][n]<=(ib[2:0]==3'(n));end
  end
 end
 wire [255:0] qa,qb;wire[31:0] qa_word,qb_word;
 for(genvar h=0;h<2;h=h+1)begin:g_word_select
  reg[15:0] aa,bb;integer n;
  always @*begin aa=0;bb=0;for(n=0;n<8;n=n+1)begin aa=aa|({16{cw_a[h][n]}}&qa[n*32+h*16+:16]);bb=bb|({16{cw_b[h][n]}}&qb[n*32+h*16+:16]);end end
  assign qa_word[h*16+:16]=aa;assign qb_word[h*16+:16]=bb;
 end
 reg sv;reg [2:0] so;reg [AW-1:0] sd;reg [31:0] sx,st,av,bv;
 always @(posedge clk) begin
  if(!rst_local) sv<=0;else sv<=cv;
  so<=co;sd<=cd;sx<=cx;st<=ct;
  av<=qa_word;
  bv<=(co==2||co==5)?qb_word:cx;
 end
 reg [5:0] pv;
 reg [2:0] po[0:5]; reg [AW-1:0] pd[0:5];
 reg [31:0] pt[0:5],px[0:5]; wire [31:0] px0_d;
 wire [31:0] add_y; wire [1:0] add_err;wire add_v;
 wire wr=rst_local&&pv[5]&&(po[5]<4||po[5]==5);
 wire [1:0] wsel;                                   
 for(genvar h=0;h<2;h=h+1)begin:g_wsel
  ot_hbm_su_reduce_r13_pipe6_m165 u_p(.clk(clk),.d(so==1||so==2),.q(wsel[h]));
 end
 wire[31:0] wd={wsel[1]?add_y[31:16]:px[5][31:16],wsel[0]?add_y[15:0]:px[5][15:0]};
 wire [2:0] pdw [0:1];                                 
 for(genvar m=0;m<2;m=m+1)begin:g_pdw
  ot_hbm_su_reduce_r13_pd6_m165 u_p(.clk(clk),.d(sd[2:0]),.q(pdw[m]));
 end
 wire[255:0] wm_a=256'hffffffff << (pdw[0]*32);
 wire[255:0] wm_b=256'hffffffff << (pdw[1]*32);
 wire[255:0] wdata={8{wd}};
 ot_sram_1r1w_128x256_m1_r2c2_m165 ma(.clk(clk),.r_ce_in(iv),.r_addr_in(ia[9:3]),.rd_out(qa),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm_a),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_128x256_m1_r2c2_m165 mb(.clk(clk),.r_ce_in(iv),.r_addr_in(ib[9:3]),.rd_out(qb),
 .w_ce_in(wr),.w_addr_in(pd[5][9:3]),.wd_in(wdata),.w_mask_in(wm_b),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 wire rst_add;
 ot_hbm_su_reduce_r13_rcp_m165 u_rcp(.clk(clk),.d(rst_n),.q(rst_add));
 ot_hdc_fp32_add_n32_m165 #(.LAT(6),.DRST(0)) u_add(.clk(clk),.rst_n(rst_add),
 .valid_in(sv && (so==1 || so==2)),.a(av),.b(bv),
 .y(add_y),.err(add_err),.valid_out(add_v));
 wire [31:0] max_y;
 for(genvar h=0;h<2;h=h+1)begin:g_max
  ot_hbm_su_reduce_r13_max16_m165 #(.H(h)) u_m(.a(av),.b(bv),.y(max_y[h*16+:16]));
 end
 wire [31:0] ex=px[5];
 wire [31:0] rounded=ex+32'h00007fff+{31'b0,ex[16]};
 wire [15:0] ex_bf16=(&ex[30:23])?ex[31:16]:rounded[31:16];
 integer i;
 always @(posedge clk) begin
   po[0]<=so;pd[0]<=sd;pt[0]<=st;px[0]<=px0_d;
   for(i=1;i<6;i=i+1) begin po[i]<=po[i-1];pd[i]<=pd[i-1];pt[i]<=pt[i-1];px[i]<=px[i-1];end
 end
 always @(posedge clk) begin
  if(!rst_local) begin pv<=0;scalar_valid<=0;fault<=0; end
  else begin
   scalar_valid<=0;
   pv<={pv[4:0],sv};
   if(iv && (iop>5 || ((iop==0||iop==1||iop==3)&&(&ix[30:23])))) fault<=1;
   if(sv && ((so==3||so==5)&&((&av[30:23])||(&bv[30:23])) || so==4&&(&av[30:23]))) fault<=1;
   if(pv[5]) begin
    if(po[5]==1 || po[5]==2) begin
     if(!add_v || add_err!=0) fault<=1;
    end else if(po[5]==4) scalar_valid<=1;
   end
  end
 end
 wire [4:0] exq;
 for(genvar k=0;k<5;k=k+1)begin:g_exq
  ot_hbm_su_reduce_r13_exq_m165 u_e(.clk(clk),.d(rst_n&&rst_local&&pv[4]&&po[4]==3'd4),.q(exq[k]));
 end
 always @(posedge clk) begin
  if(exq[0]) scalar_tag[15:0]<=pt[5][15:0];
  if(exq[1]) scalar_tag[31:16]<=pt[5][31:16];
  if(exq[2]) scalar_fp32[15:0]<=ex[15:0];
  if(exq[3]) scalar_fp32[31:16]<=ex[31:16];
  if(exq[4]) scalar_bf16<=ex_bf16;
 end
 wire [1:0] psel [0:3];
 for(genvar k=0;k<4;k=k+1)begin:g_psel
  ot_hbm_su_reduce_r13_k2_m165 u_s(.clk(clk),.d({co==3'd3||co==3'd5,co==3'd0}),.q(psel[k]));
  assign px0_d[k*8+:8]=psel[k][0]?sx[k*8+:8]:(psel[k][1]?max_y[k*8+:8]:av[k*8+:8]);
 end
endmodule
(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_pipe6_m165(input wire clk, input wire d, (* keep = 1 *) output wire q);
 reg [5:0] p; always @(posedge clk) p<={p[4:0],d}; assign q=p[5];
endmodule
(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_pd6_m165(input wire clk, input wire [2:0] d, (* keep = 1 *) output wire [2:0] q);
 reg [2:0] p [0:5]; integer i;
 always @(posedge clk) begin p[0]<=d; for(i=1;i<6;i=i+1) p[i]<=p[i-1]; end
 assign q=p[5];
endmodule
(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_exq_m165(input wire clk, d, (* keep = 1 *) output reg q);
 always @(posedge clk) q<=d;
endmodule
(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_rcp_m165(input wire clk, d, (* keep = 1 *) output reg q);
 always @(posedge clk) q<=d;
endmodule
(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_max16_m165 #(parameter integer H=0)(input wire [31:0] a, b, output wire [15:0] y);
 wire agt=(a[31]!=b[31])?!a[31]:(a[31]?(a[30:0]<b[30:0]):(a[30:0]>b[30:0]));
 wire az=(a[30:0]==0), bz=(b[30:0]==0);
 wire [15:0] raw=agt?a[H*16+:16]:b[H*16+:16];
 assign y=(agt?az:bz)?16'b0:raw;
endmodule
(* keep_hierarchy *)
module ot_hbm_su_reduce_r13_k2_m165(input wire clk, input wire [1:0] d, (* keep = 1 *) output reg [1:0] q);
 always @(posedge clk) q<=d;
endmodule
`timescale 1ns/1ps
`default_nettype none
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_kq_m165 #(parameter integer W=1)(input wire clk,input wire [W-1:0] d,(* keep = 1 *) output reg [W-1:0] q);
 always @(posedge clk) q<=d;
endmodule
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_kqr_m165(input wire clk,rst_v,d,(* keep = 1 *) output reg q);
 always @(posedge clk or negedge rst_v) if(!rst_v) q<=1'b0; else q<=d;
endmodule
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_sec_m165 #(parameter integer S=0,MUT=0,COLLPORT=1)(
 input wire clk,
 input wire rst_wv0,rst_wv1,rst_wv2,rst_wv3,rst_rv0,rst_rv1,rst_rv2,rst_rv3,rst_cf,
 input wire [5*32-1:0] rd_oh, input wire [3:0] r5_oh,
 input wire [39:0] rd_ve,rd_key, input wire [7:0] r5_ve,r5_key,
 input wire [3:0] wv, input wire [31:0] wa, input wire [127:0] wd,
 input wire rrv, input wire [4:0] rra, input wire [255:0] rrd,
 output reg [5*32-1:0] raw_o,                   
 output reg [255:0] raw5_o,                     
 output reg conf_o                              
);
 wire [31:0] wa_c; wire [127:0] wd_c; wire [3:0] wv_c; wire [255:0] rrd_c;
 ot_hbm_su_qcore_r13_kq_m165 #(.W(128)) u_wd(.clk(clk),.d(wd),.q(wd_c));
 ot_hbm_su_qcore_r13_kq_m165 #(.W(32)) u_wa(.clk(clk),.d(wa),.q(wa_c));
 for(genvar w=0;w<4;w=w+1)begin:g_wv ot_hbm_su_qcore_r13_kqr_m165 u_wv(.clk(clk),.rst_v(w==0?rst_wv0:w==1?rst_wv1:w==2?rst_wv2:rst_wv3),.d(wv[w]),.q(wv_c[w])); end
 ot_hbm_su_qcore_r13_kq_m165 #(.W(256)) u_rr(.clk(clk),.d(rrd),.q(rrd_c));
 wire [7:0] row_c={wa_c[30+:2],wa_c[22+:2],wa_c[14+:2],wa_c[6+:2]};
 wire [4:0] rra_g [0:3]; wire rrv_g [0:3];
 for(genvar g=0;g<4;g=g+1)begin:g_rw
  ot_hbm_su_qcore_r13_kq_m165 #(.W(5)) u_rw(.clk(clk),.d(rra),.q(rra_g[g]));
  ot_hbm_su_qcore_r13_kqr_m165 u_rv(.clk(clk),.rst_v(g==0?rst_rv0:g==1?rst_rv1:g==2?rst_rv2:rst_rv3),.d(rrv),.q(rrv_g[g]));
 end
 wire [3:0] smatch; wire [11:0] wbk;
 for(genvar w=0;w<4;w=w+1)begin:g_sm assign smatch[w]=wv_c[w]&&wa_c[w*8+3+:3]==3'(S); assign wbk[w*3+:3]=wa_c[w*8+:3]; end
 (* keep = 1 *) reg [31:0] rq[0:4][0:1];
 (* keep = 1 *) reg [3:0] r5q[0:15];
 wire cv[0:4][0:7]; wire c5v[0:7][0:3];
 for(genvar h=0;h<16;h=h+1)begin:g_rq
  if(h<2)begin:g_ncap
   for(genvar c=0;c<5;c=c+1)begin:g_c
    always @(posedge clk) rq[c][h]<=rd_oh[c*32+:32];
   end
  end
  always @(posedge clk) r5q[h]<=r5_oh;
 end
 for(genvar c=0;c<5;c=c+1)begin:g_cv
  for(genvar g=0;g<8;g=g+1)begin:g_g
   ot_hbm_su_qcore_r13_xor_m165 u_v(.a(rd_ve[c*8+g]),.b(rd_key[c*8+g]),.y(cv[c][g]));
  end
 end
 for(genvar g=0;g<8;g=g+1)begin:g_c5v
  for(genvar bp=0;bp<4;bp=bp+1)begin:g_bp
   ot_hbm_su_qcore_r13_xor_m165 u_v(.a(r5_ve[g]),.b(r5_key[g]),.y(c5v[g][bp]));
  end
 end
 wire [1023:0] memf;                                     
 wire [7:0] bconf;
 for(genvar b=0;b<8;b=b+1)begin:g_b
  wire [1:0] cf;
  for(genvar hf=0;hf<2;hf=hf+1)begin:g_h
   wire [3:0] en; wire [15:0] d; wire [63:0] wd16;
   for(genvar w=0;w<4;w=w+1)begin:g_w assign wd16[w*16+:16]=wd_c[w*32+hf*16+:16]; end
   ot_hbm_su_qcore_r13_wb_m165 #(.S(S),.B(b),.COLLPORT(COLLPORT)) u_wb(.sm(smatch),.wbk(wbk),.row(row_c),.wd16(wd16),.rrv(rrv_g[b/2]),.rra(rra_g[b/2]),
    .rrd16(rrd_c[32*((MUT==128)?7-b:b)+hf*16+:16]),.en(en),.d(d),.conf(cf[hf]));
   for(genvar r=0;r<4;r=r+1)begin:g_r
    reg [15:0] q;
    always @(posedge clk) if(en[r]) q<=d;
    assign memf[(r*8+b)*32+hf*16+:16]=q;
   end
  end
  assign bconf[b]=cf[0];
 end
 always @(posedge clk or negedge rst_cf) if(!rst_cf) conf_o<=1'b0; else conf_o<=|bconf;
 wire [1:0] read_word[0:4][0:15]; wire [1:0] read5_word[0:15][0:7];
 for(genvar h=0;h<16;h=h+1)begin:g_read
  for(genvar c=0;c<5;c=c+1)begin:g_c
   reg [1:0] val; integer n;
   always @*begin val=0; for(n=0;n<32;n=n+1) val=val|({2{rq[c][h/8][n]}}&memf[n*32+h*2+:2]); end
   assign read_word[c][h]=val;
   always @(posedge clk) if(cv[c][h/2]) raw_o[c*32+h*2+:2]<=read_word[c][h];
  end
  for(genvar k=0;k<8;k=k+1)begin:g_k
   reg [1:0] val; integer n;
   always @*begin val=0; for(n=0;n<4;n=n+1) val=val|({2{r5q[h][n]}}&memf[(n*8+k)*32+h*2+:2]); end
   assign read5_word[h][k]=val;
   always @(posedge clk) if(c5v[h/2][k/2]) raw5_o[k*32+h*2+:2]<=read5_word[h][k];
  end
 end
endmodule
module ot_hbm_su_static_qcore_r13 #(parameter integer MUT=0,COLLPORT=1,RF_LOCAL=1,PRETREE=0)(
 input wire clk_ctl,rst_n,
 input wire [6*9-1:0] rf_rd_cmd,
 input wire [73:0] red_cmd,
 input wire [1:0] rf_drain_cmd,
 input wire [4*32-1:0] slice_x,
 input wire [3:0] rf_wv, input wire [4*8-1:0] rf_wa, input wire [4*32-1:0] rf_wd,
 output reg [4*32-1:0] rf_bword,
 output reg [4*9-1:0] rf_bcmd,
 output reg [255:0] rf_dsec,
 output wire red_sv, output wire [31:0] red_tag, output wire [31:0] red_x,
 output wire red_rf_v,
 input wire rr_wv,
 input wire [4:0] rr_wa,
 input wire [255:0] rr_wd,
 input wire [31:0] sfu_x,
 input wire [4*67-1:0] slice_t,         
 output reg fault
); /* hier_block moved to its _hw wrappers */
 wire rf_drain_now=rf_drain_cmd[1]&&(rf_drain_cmd[0]||MUT==16);
 reg c5v_p; reg [2:0] c5b_p;
 always @(posedge clk_ctl or negedge rst_n) if(!rst_n) begin c5v_p<=1'b0; c5b_p<=3'd0; end
  else begin c5v_p<=rf_rd_cmd[5*9+8]; c5b_p<=rf_rd_cmd[5*9+:3]; end
 wire [1279:0] rd_all; wire [31:0] r5_all; wire [39:0] rd_ve,rd_key; wire [7:0] r5_ve,r5_key;
 for(genvar c=0;c<5;c=c+1)begin:g_dec
  ot_hbm_su_qcore_r13_dec9_m165 u_d(.a(rf_rd_cmd[c*9+:9]),.y(rd_all[c*256+:256]));
  for(genvar g=0;g<8;g=g+1)begin:g_g
   ot_hbm_su_qcore_r13_kq_m165 #(.W(2)) u_v(.clk(clk_ctl),
    .d({rf_rd_cmd[c*9+8]^rf_rd_cmd[c*9],rf_rd_cmd[c*9]}),.q({rd_ve[c*8+g],rd_key[c*8+g]}));
  end
 end
 ot_hbm_su_qcore_r13_dec6_m165 u_d5(.a(rf_rd_cmd[48+:6]),.y(r5_all));
 for(genvar g=0;g<8;g=g+1)begin:g_v5
  ot_hbm_su_qcore_r13_kq_m165 #(.W(2)) u_v(.clk(clk_ctl),
   .d({rf_rd_cmd[53]^rf_rd_cmd[51],rf_rd_cmd[51]}),.q({r5_ve[g],r5_key[g]}));
 end
 wire [5*32-1:0] raw_s [0:7]; wire [255:0] raw5_s [0:7]; wire [7:0] conf_s;
 for(genvar s=0;s<8;s=s+1)begin:g_sec
  wire [159:0] local_oh; wire [3:0] local_5;
  for(genvar c=0;c<5;c=c+1)begin:g_c
   for(genvar n=0;n<32;n=n+1)begin:g_n
    assign local_oh[c*32+n]=rd_all[c*256+(n/8)*64+s*8+n%8];
   end
  end
  for(genvar n=0;n<4;n=n+1)begin:g_n5 assign local_5[n]=r5_all[n*8+s]; end
  ot_hbm_su_qcore_r13_sec_m165 #(.S(s),.MUT(MUT),.COLLPORT(COLLPORT)) u_s(.clk(clk_ctl),.rst_wv0(rst_n),.rst_wv1(rst_n),.rst_wv2(rst_n),.rst_wv3(rst_n),.rst_rv0(rst_n),.rst_rv1(rst_n),.rst_rv2(rst_n),.rst_rv3(rst_n),.rst_cf(rst_n),.rd_oh(local_oh),.r5_oh(local_5),.rd_ve(rd_ve),.rd_key(rd_key),.r5_ve(r5_ve),.r5_key(r5_key),
   .wv(rf_wv),.wa(rf_wa),.wd(rf_wd),.rrv(rr_wv),.rra(rr_wa),.rrd(rr_wd),.raw_o(raw_s[s]),.raw5_o(raw5_s[s]),.conf_o(conf_s[s]));
 end
 reg [5*32-1:0] raw_or; reg [255:0] raw5_or; integer s2;
 always @*begin
  raw_or=0; raw5_or=0;
  for(s2=0;s2<8;s2=s2+1)begin raw_or=raw_or|raw_s[s2]; raw5_or=raw5_or|raw5_s[s2]; end
 end
 reg [31:0] rd [0:4]; reg [31:0] rd_x [0:4]; reg [255:0] rd5;
 integer c;
 always @(posedge clk_ctl)begin
  for(c=0;c<5;c=c+1) rd_x[c] <= raw_or[c*32+:32];
  for(c=0;c<5;c=c+1) rd[c] <= (MUT==256) ? rd_x[c] : raw_or[c*32+:32];
  rd5 <= raw5_or;
 end
 wire [31:0] rf_word [0:4];
 for(genvar c2=0;c2<5;c2=c2+1)begin:g_rfw assign rf_word[c2]=rd[c2]; end
 always @(posedge clk_ctl)begin
  rf_bword<={rf_word[3],rf_word[2],rf_word[1],rf_word[0]};
  rf_bcmd<=rf_rd_cmd[0+:36];
  rf_dsec<=rd5;
 end
 reg c5_d1,c5_d2;
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)begin c5_d1<=1'b0;c5_d2<=1'b0;end
  else begin c5_d1<=rf_rd_cmd[5*9+8];c5_d2<=c5_d1;end
 wire c5_lead=RF_LOCAL?c5_d2:c5_d1;
 reg drain_p; always @(posedge clk_ctl or negedge rst_n) if(!rst_n) drain_p<=1'b0; else drain_p<=rf_drain_now;
 reg c5_lead_q; always @(posedge clk_ctl or negedge rst_n) if(!rst_n) c5_lead_q<=1'b0; else c5_lead_q<=c5_lead;
 wire dbad=(drain_p&&!c5_lead_q)||(c5v_p&&c5b_p!=3'd0);
 reg rc_v; reg [2:0] rc_op; reg [9:0] rc_a,rc_b,rc_d; reg [31:0] rc_tag,rc_x;
 reg [1:0] e_sl; reg e_os,e_sfu,e_tr; reg [72:8] e_f;
 always @(posedge clk_ctl)begin e_sl<=red_cmd[5:4];e_os<=red_cmd[7];e_sfu<=(COLLPORT!=0)&&red_cmd[6]&&(MUT!=64);e_f<=red_cmd[72:8];
  e_tr<=(PRETREE!=0)&&red_cmd[7]&&red_cmd[5]&&!red_cmd[6];end
 wire pt_v,pt_max,pt_fault; wire [31:0] pt_x;
 if(PRETREE!=0)begin:g_pretree
  wire jv,jm; wire [31:0] jx;
  ot_hbm_su_red_pretree_j_r13_m165 #(.LAT(6),.MUT((MUT==1024)?2:0)) u_ptj(.clk(clk_ctl),.rst_n(rst_n),.slice_t(slice_t),.tree_v(jv),.tree_x(jx),
   .tree_max(jm),.fault(pt_fault));
  if(MUT==512)begin:g_mut_late
   reg lv,lm; reg [31:0] lx; always @(posedge clk_ctl)begin lv<=jv;lm<=jm;lx<=jx;end
   assign pt_v=lv; assign pt_max=lm; assign pt_x=lx;
  end else begin:g_on_time
   assign pt_v=jv; assign pt_max=jm; assign pt_x=jx;
  end
 end else begin:g_no_pretree
  assign pt_v=1'b0; assign pt_max=1'b0; assign pt_x=32'd0; assign pt_fault=1'b0;
 end
 reg e_v;
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)e_v<=1'b0; else e_v<=red_cmd[73];
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)rc_v<=1'b0; else rc_v<=e_v;
 reg pt_bad; always @(posedge clk_ctl or negedge rst_n) if(!rst_n) pt_bad<=1'b0;
  else pt_bad<=e_v&&e_tr&&(!pt_v||(e_f[72:70]==3'd1&&pt_max)||(e_f[72:70]==3'd3&&!pt_max)||
                (e_f[72:70]!=3'd0&&e_f[72:70]!=3'd1&&e_f[72:70]!=3'd3));
 always @(posedge clk_ctl)begin
  rc_op<=e_f[72:70];rc_a<=e_f[69:60];rc_b<=e_f[59:50];rc_d<=e_f[49:40];rc_tag<=e_f[39:8];
  end
 wire [6:0] oh_d={(red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd3,(red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd2,
                  (red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd1,(red_cmd[7]==1'b0)&&red_cmd[5:4]==2'd0,
                  red_cmd[7]&&!((PRETREE!=0)&&red_cmd[5]&&!red_cmd[6])&&!((COLLPORT!=0)&&red_cmd[6]&&(MUT!=64)),
                  red_cmd[7]&&!((PRETREE!=0)&&red_cmd[5]&&!red_cmd[6])&&((COLLPORT!=0)&&red_cmd[6]&&(MUT!=64)),
                  red_cmd[7]&&((PRETREE!=0)&&red_cmd[5]&&!red_cmd[6])};    
 wire [31:0] rcx_d;
 for(genvar y=0;y<4;y=y+1)begin:g_osel
  wire [6:0] oh;
  ot_hbm_su_qcore_r13_kq_m165 #(.W(7)) u_oh(.clk(clk_ctl),.d(oh_d),.q(oh));
  ot_hbm_su_qcore_r13_xsel8_m165 u_x(.oh(oh),.pt(pt_x[y*8+:8]),.sfu(sfu_x[y*8+:8]),.rf(rf_word[4][y*8+:8]),
   .s0(slice_x[0*32+y*8+:8]),.s1(slice_x[1*32+y*8+:8]),.s2(slice_x[2*32+y*8+:8]),.s3(slice_x[3*32+y*8+:8]),.y(rcx_d[y*8+:8]));
 end
 always @(posedge clk_ctl) rc_x<=rcx_d;
 wire red_fault;
 ot_hbm_su_reduce_static_r13_m165 #(.AW(10)) u_red(.clk(clk_ctl),.rst_n(rst_n),.cmd_valid(rc_v),.cmd_op(rc_op),.cmd_a(rc_a),
  .cmd_b(rc_b),.cmd_dst(rc_d),.operand_fp32(rc_x),.cmd_tag(rc_tag),.scalar_valid(red_sv),.scalar_tag(red_tag),
  .scalar_fp32(red_x),.scalar_bf16(),.fault(red_fault));
 assign red_rf_v=red_sv&&(red_tag[8]||MUT==32);
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n)fault<=1'b0; else if((|conf_s)||dbad||red_fault||pt_fault||pt_bad)fault<=1'b1;
endmodule
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_wb_m165 #(parameter integer S=0,B=0,COLLPORT=1)(
 input wire [3:0] sm, input wire [11:0] wbk, input wire [7:0] row, input wire [63:0] wd16,
 input wire rrv, input wire [4:0] rra, input wire [15:0] rrd16,
 output wire [3:0] en, output wire [15:0] d, output wire conf
);
 wire [3:0] hit, sel; wire wvb, multi;
 for(genvar w=0;w<4;w=w+1)begin:g_hit assign hit[w]=sm[w]&&wbk[w*3+:3]==3'(B); end
 ot_hbm_su_qcore_r13_selq_m165 u_q(.hit(hit),.sel(sel),.any(wvb),.multi(multi));
 wire [15:0] wdb=({16{sel[0]}}&wd16[0+:16])|({16{sel[1]}}&wd16[16+:16])|({16{sel[2]}}&wd16[32+:16])|({16{sel[3]}}&wd16[48+:16]);
 wire [1:0] wab=({2{sel[0]}}&row[0+:2])|({2{sel[1]}}&row[2+:2])|({2{sel[2]}}&row[4+:2])|({2{sel[3]}}&row[6+:2]);
 wire rrb=(COLLPORT!=0)&&rrv&&rra[2:0]==3'(S);
 wire bwv=wvb||rrb; wire [1:0] bwa=rrb?rra[4:3]:wab;
 assign d=rrb?rrd16:wdb;
 for(genvar r=0;r<4;r=r+1)begin:g_en assign en[r]=bwv&&bwa==2'(r); end
 assign conf=multi||(rrb&&wvb);
endmodule
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_xsel8_m165(input wire [6:0] oh, input wire [7:0] pt,sfu,rf,s0,s1,s2,s3, output wire [7:0] y);
 assign y=({8{oh[0]}}&pt)|({8{oh[1]}}&sfu)|({8{oh[2]}}&rf)|({8{oh[3]}}&s0)|({8{oh[4]}}&s1)|({8{oh[5]}}&s2)|({8{oh[6]}}&s3);
endmodule
(* keep_hierarchy *)
module ot_hbm_su_qcore_r13_selq_m165(input wire [3:0] hit, output wire [3:0] sel, output wire any, multi);
 assign sel={hit[3],hit[2]&&!hit[3],hit[1]&&!hit[2]&&!hit[3],hit[0]&&!hit[1]&&!hit[2]&&!hit[3]};
 assign any=|hit;
 assign multi=(hit[0]&&(hit[1]||hit[2]||hit[3]))||(hit[1]&&(hit[2]||hit[3]))||(hit[2]&&hit[3]);
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_xor_m165(input wire a,b,output wire y);assign y=a^b;endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec4_m165(input wire[3:0]a,output wire[15:0]y);
 for(genvar i=0;i<16;i=i+1)begin:g assign y[i]=(a==4'(i));end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec5v_m165(input wire[4:0]a,output wire[15:0]y);
 for(genvar i=0;i<16;i=i+1)begin:g assign y[i]=(a=={1'b1,4'(i)});end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec9_m165(input wire[8:0]a,output wire[255:0]y);
 wire[15:0]lo,hi;ot_hbm_su_qcore_r13_dec4_m165 u_l(.a(a[3:0]),.y(lo));ot_hbm_su_qcore_r13_dec5v_m165 u_h(.a(a[8:4]),.y(hi));
 for(genvar i=0;i<256;i=i+1)begin:g assign y[i]=lo[i%16]&hi[i/16];end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec3_m165(input wire[2:0]a,output wire[7:0]y);
 for(genvar i=0;i<8;i=i+1)begin:g assign y[i]=(a==3'(i));end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec3v_m165(input wire[2:0]a,output wire[3:0]y);
 for(genvar i=0;i<4;i=i+1)begin:g assign y[i]=(a=={1'b1,2'(i)});end
endmodule
(* keep_hierarchy *) module ot_hbm_su_qcore_r13_dec6_m165(input wire[5:0]a,output wire[31:0]y);
 wire[7:0]lo;wire[3:0]hi;ot_hbm_su_qcore_r13_dec3_m165 u_l(.a(a[2:0]),.y(lo));ot_hbm_su_qcore_r13_dec3v_m165 u_h(.a(a[5:3]),.y(hi));
 for(genvar i=0;i<32;i=i+1)begin:g assign y[i]=lo[i%8]&hi[i/8];end
endmodule
`default_nettype wire
`timescale 1ns/1ps
module ot_hdc_fp32_add_n32_m165 #(
    parameter integer LAT = 3,
    parameter integer CUTS = -1,
    parameter integer DRST =     1 
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT_A = (CUTS >= 0) ? CUTS % 2       : (LAT >= 5) ? 1 : 0;
    localparam integer CUT_B = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT_C = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 6) ? 1 : 0;
    localparam integer CUT_D = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;      
    generate if (CUTS >= 0 && CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_add_n32_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code;
    for (genvar h=0; h<4; h=h+1) begin:g_bypass_byte
        ot_hdc_fp32_bypass_n32_m165 #(.LO(8*h)) u_b(.a(a),.b(b),.y(bypass_code[8*h+:8]));
    end
    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k__u1_m165 #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k__u1_m165 #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k__u1_m165 #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    localparam integer WA = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] a1 = {valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
                        a_exp, b_exp, a_man, b_man, dab, dba} ;
    wire          a1_swap = !cmp_c;
    wire [WA:0]   a2_in;
    ot_hdc_w11_cut_n32_m165 #(.W(WA + 1), .CUT(CUT_A), .VB(DRST ? -1 : WA - 1), .COPY_MASK((120'b1<<119)|(120'b1111<<8)|120'b1111)) u_ca (.clk(clk), .rst_n(rst_n), .d({a1_swap, a1}), .q(a2_in));
    wire        x_v, x_byp, x_sub, x_as, x_bs, x_swap;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_swap, x_v, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = a2_in;
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);
    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_err <= x_err;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
        s1_small <= x_swap ? small_a : small_b;
    end
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k__u1_m165 #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k__u1_m165 #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer WB = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [WB-1:0] b2_in;
    ot_hdc_w11_cut_n32_m165 #(.W(WB), .CUT(CUT_B), .VB(DRST ? -1 : WB - 1), .COPY_MASK((100'b1<<99)|(100'b1<<55))) u_cb (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(b2_in));
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = b2_in;
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    ot_hdc_lzc32_n32_m165 u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    localparam integer WD = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [WD-1:0] d2_in;
    ot_hdc_w11_cut_n32_m165 #(.W(WD), .CUT(CUT_D), .VB(DRST ? -1 : WD - 1)) u_cd (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(d2_in));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = d2_in;
    wire [5:0] shift_count [0:2];
    wire [26:0] shift_data [0:5];
    assign shift_data[0]=w_dif[26:0];
    for(genvar g=0;g<3;g=g+1)begin:g_shift_count
        if(CUT_D==0)begin:g_uncut
            ot_hdc_lzc32_n32_m165 u_count(.x({dif[26:0] | sentinel,5'b11111}),.n(shift_count[g]));
        end else begin:g_cut
            assign shift_count[g]=lz;
        end
    end
    for(genvar st=0;st<5;st=st+1)begin:g_shift_stage
        for(genvar g=0;g<3;g=g+1)begin:g_group
            ot_hdc_shl27_group_n32_m165 #(.LO(9*g),.SHIFT(1<<st)) u_shift(
                .x(shift_data[st]),.sh(shift_count[g][st]),.y(shift_data[st+1][9*g+:9]));
        end
    end
    wire [26:0] sub_val=shift_data[5];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k__u1_m165 #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k__u1_m165 #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));
    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_err <= w_err; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k__u1_m165 #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer WC = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    wire [WC-1:0] c2_in;
    ot_hdc_w11_cut_n32_m165 #(.W(WC), .CUT(CUT_C), .VB(DRST ? -1 : WC - 1), .COPY_MASK((71'b1<<69)|71'b1)) u_cc (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err, s2_code, s2_exp, rnd_w, rnd_cw}), .q(c2_in));
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = c2_in;
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    generate if (DRST != 0) begin : g_yr
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
            else begin
                valid_out <= u_v;
                if (u_byp) begin y <= u_code; err <= u_err; end
                else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
                else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
                else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
            end
        end
    end else begin : g_yn
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= u_v;
        end
        always @(posedge clk) begin
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end endgenerate
    (* keep = 1 *) reg [6:0] valid_cp;
    always @(posedge clk or negedge rst_n) if(!rst_n) valid_cp<=0; else valid_cp<={7{u_v}};
    (* keep = 1, ot_rst_split = 1 *) wire [7:0] valid_family={valid_cp,valid_out};
endmodule
module ot_hdc_w11_cut_n32_m165 #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1, parameter [W-1:0] COPY_MASK = {W{1'b0}}, parameter integer COPIES = 8) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
    generate if(CUT!=0)begin:g_native_copies
      for(genvar b=0;b<W;b=b+1)begin:g_bit
        if(COPY_MASK[b])begin:g_copy
          (* keep = 1 *) reg [COPIES-2:0] cp;
          if(VB<0 || VB==b)begin:g_reset
            always @(posedge clk or negedge rst_n) if(!rst_n)cp<=0;else cp<={COPIES-1{d[b]}};
          end else begin:g_data
            always @(posedge clk) cp<={COPIES-1{d[b]}};
          end
          (* keep = 1, ot_rst_split = 1 *) wire [COPIES-1:0] family={cp,q[b]};
        end
      end
    end endgenerate
endmodule
(* keep_hierarchy *)
module ot_hdc_fp32_bypass_n32_m165 #(parameter integer LO=0)(
 input wire [31:0] a,b, output wire [7:0] y
);
 wire nf=(a[30:23]==8'hff)||(b[30:23]==8'hff);
 wire az=(a[30:0]==31'd0), bz=(b[30:0]==31'd0);
 assign y=nf?8'd0:(az?(bz?8'd0:b[LO+:8]):a[LO+:8]);
endmodule
(* keep_hierarchy *)
module ot_hdc_lzc32_n32_m165 (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule
(* keep_hierarchy *)
module ot_hdc_shl27_group_n32_m165 #(parameter integer LO=0,SHIFT=1)(
 input wire [26:0] x,input wire sh,output wire [8:0] y
);
 wire [26:0] displaced=x<<SHIFT;
 assign y=sh?displaced[LO+:9]:x[LO+:9];
endmodule
`timescale 1ns/1ps
module ot_hdc_ksadd_k__u1_m165 #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign g[l + 1][i] = g[l][i] | (p[l][i] & g[l][i - (1 << l)]);
                    assign p[l + 1][i] = p[l][i] & p[l][i - (1 << l)];
                end else begin : g_p
                    assign g[l + 1][i] = g[l][i];
                    assign p[l + 1][i] = p[l][i];
                end
            end
        end
    endgenerate
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule
module ot_hdc_inc_k__u1_m165 #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    localparam integer L = $clog2(W + 1);
    (* keep *) wire [W:0] t [0:L];
    assign t[0] = {a, inc};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign t[l + 1][i] = t[l][i] & t[l][i - (1 << l)];
                end else begin : g_p
                    assign t[l + 1][i] = t[l][i];
                end
            end
        end
    endgenerate
    assign y = a ^ t[L][W-1:0];
    assign co = t[L][W];
endmodule
