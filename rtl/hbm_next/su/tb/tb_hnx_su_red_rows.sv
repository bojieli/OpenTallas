`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HBM-NEXT-UNITS-SUDMA2 2026-10-19: REDUCER / RF ROW CLASS bench (norm-style N-row SU.VOP reductions).
// DUT: the four d4g SU quarter cores ot_hbm_su_static_qcore (RF replica 64 x 4 words, six read classes + the reducer
// ot_hbm_su_reduce_static; RTL unchanged) behind the row stage ot_hnx_su_rowr (one a quarter, REG 1), with the RF write
// relay network of ot_hbm_su_static_top / ot_hnx_su_top (reducer w -> every replica over RF_RELAY registered stages,
// the same always-blocks as the top's g_stages). Minimum component: the row class is control on the red74 / rf54 fields
// only; the slices are represented by their registered lane outputs slice_x and the slice-0 drain bit (bench inputs on
// the compiler's edges), as every other datapath input of the core.
// Vectors: tools/hbm_next/su_red_rows_compile.py (prog.mem row-0-relative {rf54, red74} lines, rc2.mem row codes,
// st2.mem strides, xs.mem lane partials, drn.mem drain bits; --absolute = the unrolled d4g image -> same expectations).
// Checks: every reducer scalar (edge, quarter, tag, value) equals the next expected one; every expected class-1 RF
// broadcast word at rf_bword and every expected class-5 RF sector (masked words) at rf_dsec on its edge; zero qcore and
// rowr faults; all expectations consumed. Golden = hdc_golden FP32 RNE in the compiled order (independent of the DUT).
// RTL mutants (-GMUT, ot_hnx_su_rowr, must FAIL): 1 dst stride dropped, 2 export tag stride dropped, 3 RF read stride
// dropped, 4 a / b stride dropped.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hnx_su_red_rows;
 parameter integer NEMAX=4096,NSMAX=256,NBMAX=256,NDMAX=1024,RF_RELAY=8,MUT=0;
 integer NE=0,NT=0,NS=0,NB=0,ND=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [511:0] prog [0:NEMAX-1];
 reg [31:0] rcm [0:NEMAX-1];
 reg [17:0] stm [0:0];
 reg [511:0] xsm [0:NEMAX-1];
 reg [7:0] drm [0:NEMAX-1];
 reg [127:0] exps [0:NSMAX-1];
 reg [79:0] expb [0:NBMAX-1];
 reg [303:0] expd [0:NDMAX-1];
 reg [511:0] line=0; reg [31:0] rcl=0; reg [511:0] xsl=0; reg [7:0] drl=0;
 wire [511:0] rline; wire [3:0] rfault;
 for(genvar q=0;q<4;q=q+1)begin:g_rx
  ot_hnx_su_rowr #(.REG(1),.MUT(MUT)) u_rr(.clk(clk),.rst_n(rst_n),.line_in(line[q*128+:128]),.rc2(rcl[q*8+:8]),
   .st2(stm[0]),.line_out(rline[q*128+:128]),.fault(rfault[q]));
 end
 wire [3:0] red_sv,red_rf_v,cfault; wire [127:0] red_tag,red_x;
 wire [4*128-1:0] bword; wire [4*36-1:0] bcmd; wire [4*256-1:0] dsec;
 wire [40:0] rly_out [0:3][0:3];
 for(genvar w=0;w<4;w=w+1)begin:g_src             // = ot_hnx_su_top g_src / g_stages (RF_RELAY > 0)
  wire [40:0] head={red_rf_v[w],red_tag[w*32+:8],red_x[w*32+:32]};
  for(genvar d=0;d<4;d=d+1)begin:g_dst
   reg st_v [0:RF_RELAY-1]; reg [39:0] st_d [0:RF_RELAY-1];
   integer k;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)for(k=0;k<RF_RELAY;k=k+1)st_v[k]<=1'b0;
    else begin st_v[0]<=head[40];for(k=1;k<RF_RELAY;k=k+1)st_v[k]<=st_v[k-1]; end
   always @(posedge clk)begin st_d[0]<=head[39:0];for(k=1;k<RF_RELAY;k=k+1)st_d[k]<=st_d[k-1]; end
   assign rly_out[w][d]={st_v[RF_RELAY-1],st_d[RF_RELAY-1]};
  end
 end
 for(genvar q=0;q<4;q=q+1)begin:g_q
  wire [3:0] wv; wire [31:0] wa; wire [127:0] wd;
  for(genvar w=0;w<4;w=w+1)begin:g_w
   assign wv[w]=rly_out[w][q][40]; assign wa[w*8+:8]=rly_out[w][q][39:32]; assign wd[w*32+:32]=rly_out[w][q][31:0];
  end
  ot_hbm_su_static_qcore #(.MUT(0),.COLLPORT(0),.RF_LOCAL(0)) u_core(.clk_rf({64{clk}}),.clk_ctl(clk),.clk_red(clk),
   .rst_n(rst_n),.rf_rd_cmd(rline[q*128+74+:54]),.red_cmd(rline[q*128+:74]),.rf_drain_cmd(drl[q*2+:2]),
   .slice_x(xsl[q*128+:128]),.rf_wv(wv),.rf_wa(wa),.rf_wd(wd),.rf_bword(bword[q*128+:128]),.rf_bcmd(bcmd[q*36+:36]),
   .rf_dsec(dsec[q*256+:256]),.red_sv(red_sv[q]),.red_tag(red_tag[q*32+:32]),.red_x(red_x[q*32+:32]),
   .red_rf_v(red_rf_v[q]),.rr_wv(1'b0),.rr_wa(5'd0),.rr_wd(256'd0),.sfu_x(32'd0),.fault(cfault[q]));
 end
 integer cyc=-1,errors=0,es=0,eb=0,ed=0,scalars=0,i,q,k,first_cmd=-1,last_ev=-1;
 task fail(input string m); begin if(errors<12)$display("SU_RED_ROWS ERROR cyc=%0d %s",cyc,m); errors=errors+1; end endtask
 always @(posedge clk)if(rst_n&&cyc>=0)begin
  for(q=0;q<4;q=q+1)if(red_sv[q])begin
   scalars=scalars+1; last_ev=cyc;
   if(es>=NS)fail("unexpected scalar");
   else begin
    if(exps[es][127:96]!==cyc||exps[es][95:64]!==q||exps[es][63:32]!==red_tag[q*32+:32]||exps[es][31:0]!==red_x[q*32+:32])
     fail($sformatf("scalar q%0d tag %h x %h, want cyc %0d q%0d tag %h x %h",q,red_tag[q*32+:32],red_x[q*32+:32],
      exps[es][127:96],exps[es][95:64],exps[es][63:32],exps[es][31:0]));
    es=es+1;
   end
  end
  while(eb<NB&&expb[eb][79:48]==cyc)begin
   q=expb[eb][47:40]; k=expb[eb][39:32]; last_ev=cyc;
   if(bword[q*128+k*32+:32]!==expb[eb][31:0]) fail($sformatf("bcast q%0d class %0d got %h want %h",q,k,bword[q*128+k*32+:32],expb[eb][31:0]));
   eb=eb+1;
  end
  while(ed<ND&&expd[ed][303:272]==cyc)begin
   reg [255:0] m,got,want; q=expd[ed][271:264];
   for(k=0;k<8;k=k+1)m[k*32+:32]={32{expd[ed][256+k]}};
   got=dsec[q*256+:256]; want=expd[ed][255:0]; last_ev=cyc;
   if((got&m)!==(want&m))fail($sformatf("drain q%0d mask %h got %h want %h",q,expd[ed][263:256],got,want));
   ed=ed+1;
  end
  if(|cfault)fail($sformatf("qcore fault %b",cfault));
  if(|rfault)fail($sformatf("rowr fault %b",rfault));
 end
 initial begin
  string dir;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  if(!$value$plusargs("NE=%d",NE)||!$value$plusargs("NT=%d",NT)||!$value$plusargs("NS=%d",NS)||!$value$plusargs("NB=%d",NB)||
     !$value$plusargs("ND=%d",ND)||NT>NEMAX||NS>NSMAX||NB>NBMAX||ND>NDMAX)$fatal(1,"NE/NT/NS/NB/ND missing or over max");
  $readmemh({dir,"/prog.mem"},prog);$readmemh({dir,"/rc2.mem"},rcm);$readmemh({dir,"/st2.mem"},stm);
  $readmemh({dir,"/xs.mem"},xsm);$readmemh({dir,"/drn.mem"},drm);
  $readmemh({dir,"/exps.mem"},exps);$readmemh({dir,"/expb.mem"},expb);$readmemh({dir,"/expd.mem"},expd);
  repeat(4)@(negedge clk); rst_n=1; repeat(2)@(negedge clk);
  for(i=0;i<NT;i=i+1)begin
   if(i<NE)begin line=prog[i]; rcl=rcm[i]; if(first_cmd<0&&|prog[i])first_cmd=i; end else begin line=0; rcl=0; end
   xsl=xsm[i]; drl=drm[i];
   cyc=i;
   @(negedge clk);
  end
  line=0; rcl=0; xsl=0; drl=0;
  for(i=0;i<24;i=i+1)begin cyc=NT+i; @(negedge clk); end
  if(es!=NS)fail($sformatf("scalars %0d of %0d expected",es,NS));
  if(eb!=NB)fail($sformatf("bcast checks %0d of %0d",eb,NB));
  if(ed!=ND)fail($sformatf("drain checks %0d of %0d",ed,ND));
  if(errors)$fatal(1,"SU_RED_ROWS FAIL errors=%0d scalars=%0d MUT=%0d",errors,scalars,MUT);
  $display("SU_RED_ROWS_EDGES first_cmd=%0d last_event=%0d span=%0d",first_cmd,last_ev,last_ev-first_cmd);
  $display("SU_RED_ROWS PASS quarters=4 scalars=%0d bcast=%0d drains=%0d edges=%0d MUT=%0d",scalars,NB,ND,NE,MUT);
  $finish;
 end
endmodule
