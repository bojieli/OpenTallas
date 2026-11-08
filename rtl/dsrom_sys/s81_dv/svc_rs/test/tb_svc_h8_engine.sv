`timescale 1ns/1ps
// Exact head decomposition: production attention engine H16 once versus H8 twice.
module tb_svc_h8_engine;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0; integer cyc=0,mut=0,errs=0,ns16=0,ns8=0,np16=0,np8=0;
 wire [1:0] sv,pv; wire [15:0] sr[0:1]; wire [3:0] sm[0:1];
 wire [2047:0] sy16; wire [1023:0] sy8; wire [63:0] sf16; wire [31:0] sf8;
 wire [2047:0] py16; wire [1023:0] py8; wire [63:0] pf16; wire [31:0] pf8;
 wire [7:0] pc[0:1];
 reg [31:0] gold_s[0:3][0:15],gold_p[0:7][0:3][0:15];
 reg gold_sf[0:3][0:15],gold_pf[0:7][0:3][0:15];
 reg [31:0] got_s[0:3][0:15],got_p[0:7][0:3][0:15];
 reg got_sf[0:3][0:15],got_pf[0:7][0:3][0:15];
 function automatic [15:0] qval(input integer h,input integer d);
  qval=16'h3e80+16'(h*17+d);
 endfunction
 function automatic [15:0] pval(input integer r,input integer h);
  pval=16'h3e00+16'(h*19+r*7);
 endfunction
 genvar g;
 generate for(g=0;g<2;g++) begin:eng
  localparam integer H=(g==0)?16:8;
  wire jr,qr,kr,pr; reg jv,qv,kv,pp;
  reg [511:0] qw; reg [1059:0] kw; reg [1023:0] pw;
  wire [H*128-1:0] sy,py; wire [H*4-1:0] sf,pf;
  integer rc,pass,hb,hh,rr;
  always @* begin
   pass=(g==1 && cyc>=1010)?1:0;
   rc=cyc-10-pass*1000; hb=(g==0)?0:pass*8;
   if(mut==1 && g==1) hb=8-hb;
   if(mut==3 && g==1) hb=8-hb;
   jv=(rc==0)&&!(mut==2&&g==1&&pass==1);
   qv=rc>=1&&rc<=H&&!(mut==2&&g==1&&pass==1);
   kv=rc==1&&!(mut==2&&g==1&&pass==1);
   pp=rc==200&&!(mut==2&&g==1&&pass==1);
   qw=0; kw=0; pw=0;
   for(integer d=0;d<32;d++) qw[d*16+:16]=qval(hb+rc-1,d);
   for(integer r=0;r<4;r++) begin
    kw[r*265+:265]={1'b0,8'h7f,{32{8'(8'h20+r)}}};
    for(integer h=0;h<H;h++) pw[16*(r*H+h)+:16]=pval(r,hb+h);
   end
  end
  ot_hdc_v41x_attn_s #(.H(H),.D(32),.TD(32),.NL(4),.TROWS(640),.SRAM_MACRO(0),.PWORDS(2),
   .ILV(1),.REPL(2),.NSTAGE(2),.FPL(4),.FML(6),.NBANKP(0),.TILE_S(1),
   .NARROW(1),.MFAN(1),.TRX(1),.F12(1),.FPLX(5),.SC_CRED(0),.PV_CRED(0)) u (
   .clk(clk),.rst_n(rst_n),.job_v(jv),.job_t(16'd4),.job_ready(jr),
   .q_v(qv),.q_w(qw),.q_ready(qr),.kv_v(kv),.kv_m(4'hf),.kv_w(kw),.kv_ready(kr),
   .sc_v(sv[g]),.sc_row(sr[g]),.sc_m(sm[g]),.sc_y(sy),.sc_f(sf),.sc_cr(1'b0),
   .p_v(pp),.p_w(pw),.p_ready(pr),.pv_v(pv[g]),.pv_c(pc[g]),.pv_y(py),.pv_f(pf),.pv_cr(1'b0),
   .qk_iss(),.pv_iss());
  if(g==0) begin assign sy16=sy;assign sf16=sf;assign py16=py;assign pf16=pf;end
  else begin assign sy8=sy;assign sf8=sf;assign py8=py;assign pf8=pf;end
  always @(posedge clk) if(rst_n) begin
   if(jv&&!jr||qv&&!qr||kv&&!kr||pp&&!pr) begin errs++; $display("REFUSED g%0d cyc%0d",g,cyc);end
  end
 end endgenerate
 always @(posedge clk) begin
  cyc<=cyc+1;
  if(cyc==3) rst_n<=1;
  if(sv[0]) begin ns16++;for(integer r=0;r<4;r++)for(integer h=0;h<16;h++)begin gold_s[r][h]<=sy16[32*(r*16+h)+:32];gold_sf[r][h]<=sf16[r*16+h];end end
  if(pv[0]) begin np16++;for(integer r=0;r<4;r++)for(integer h=0;h<16;h++)begin gold_p[pc[0]][r][h]<=py16[32*(r*16+h)+:32];gold_pf[pc[0]][r][h]<=pf16[r*16+h];end end
  if(sv[1]) begin ns8++; for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)begin got_s[r][h+((cyc>1000)?8:0)]<=sy8[32*(r*8+h)+:32];got_sf[r][h+((cyc>1000)?8:0)]<=sf8[r*8+h];end end
  if(pv[1])begin np8++;for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)begin got_p[pc[1]][r][h+((cyc>1000)?8:0)]<=py8[32*(r*8+h)+:32];got_pf[pc[1]][r][h+((cyc>1000)?8:0)]<=pf8[r*8+h];end end
  if(cyc==1900)begin
   for(integer r=0;r<4;r++)for(integer h=0;h<16;h++)begin
    if(got_s[r][h]!==gold_s[r][h]||got_sf[r][h]!==gold_sf[r][h])errs++;
    for(integer c=0;c<8;c++)if(got_p[c][r][h]!==gold_p[c][r][h]||got_pf[c][r][h]!==gold_pf[c][r][h])errs++;
   end
   $display("H8_ENGINE mut=%0d errs=%0d scores=%0d/%0d pv=%0d/%0d",mut,errs,ns16,ns8,np16,np8);
   if(errs==0&&ns16==1&&ns8==2&&np16==8&&np8==16)$display("H8_ENGINE PASS");else $display("H8_ENGINE FAIL");$finish;end
 end
 initial void'($value$plusargs("mut=%d",mut));
endmodule
