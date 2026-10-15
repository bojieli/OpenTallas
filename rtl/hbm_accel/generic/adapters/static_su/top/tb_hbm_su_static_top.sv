`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Exact full-shape bench of the WHOLE static SU ot_hbm_su_static_top (H-ELEM-B 2026-10-15). Vectors:
// tools/hbm_static/su_top_compile.py (prog.mem = one fixed-edge command line per edge; expw/exps/explw = expected VM
// writes, reducer scalars and lane write counts). The bench is only the LG boundary of the four VM slices (it answers
// every sampled read with the VM image exactly +10 edges later and every sampled write with done +7, as the LG SU station
// does) plus checks; every on-chip operation is the DUT's RTL. No backpressure exists to model.
// Checks: every LG write (edge, quarter, port, sector, mask, masked data) equals the next expected write; every reducer
// scalar (edge, quarter, tag, value); per-edge lane write count per quarter; zero DUT faults; all expectations consumed.
// Bench mutants (same binary, plusargs): +MUT_DATA one fill return bit flipped; +MUT_ADDR quarter-1 A affine term
// corrupted; +MUT_RF RF broadcast command names the wrong word; +MUT_RED first reducer command one edge late.
// RTL mutants (separate builds, -GMUT=): 1 fill phase, 2 drain group, 4 RF broadcast phase, 8 missing relay route.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hbm_su_static_top;
 parameter integer NE=7111,NW=135184,NS=9,RF_RELAY=8,MUT=0,MLAT=3,ALAT=3,LEAF=0;
 localparam integer QW=2422;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [4*QW-1:0] prog [0:NE-1];
 reg [4*QW-1:0] line=0;
 reg [31:0] seed [0:262143];
 reg [319:0] expw [0:NW-1];
 reg [127:0] exps [0:NS-1];
 reg [31:0] explw [0:NE-1];
 wire [4*1742-1:0] control; wire [4*240-1:0] vmr; wire [4*312-1:0] vmw; wire [4*54-1:0] rf; wire [4*74-1:0] red;
 for(genvar q=0;q<4;q=q+1)begin:g_split
  assign {control[q*1742+:1742],vmr[q*240+:240],vmw[q*312+:312],rf[q*54+:54],red[q*74+:74]}=line[q*QW+:QW];
 end
 wire [4*8*17-1:0] lg_rq; wire [4*8*281-1:0] lg_wq; reg [4*8*257-1:0] lg_rr=0; reg [31:0] lg_w_done=0;
 wire [19:0] fault;
 ot_hbm_su_static_top #(.RF_RELAY(RF_RELAY),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.MUT(MUT)) dut(
  .pg_clk({16{clk}}),.clk_lane({4096{clk}}),.clk_insert({2048{clk}}),.rst_lane_n({512{rst_n}}),
  .clk_bcast({64{clk}}),.rst_bcast_n({64{rst_n}}),.clk_bank({512{clk}}),.clk_bank_macro({3072{clk}}),.clk_rf({256{clk}}),.clk_ctl({16{clk}}),
  .clk_core({4{clk}}),.clk_red({4{clk}}),.clk_side({6{clk}}),.clk_relay({4{clk}}),.rst_n(rst_n),
  .control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_rd_cmd(rf),.red_cmd(red),
  .lg_rq(lg_rq),.lg_wq(lg_wq),.lg_rr(lg_rr),.lg_w_done(lg_w_done),.fault(fault));
 // lane write counts per quarter (store element writes)
 wire [127:0] lw [0:3];
 for(genvar q=0;q<4;q=q+1)begin:g_lwq
  for(genvar g=0;g<4;g=g+1)begin:g_lws
   assign lw[q][g*32+:32]=dut.g_q[q].u_quarter.g_slice[g].u_slice.vm_we|dut.g_q[q].u_quarter.g_slice[g].u_slice.kv_we;
  end
 end
 integer stop=NE;
 integer cyc=-1,errors=0,ew=0,es=0,reads=0,writes=0,scalars=0,i,q,p,k;
 bit mut_data,mut_addr,mut_rf,mut_red;
 reg pend_v [0:31][0:3][0:7]; reg [15:0] pend_s [0:31][0:3][0:7]; reg pend_w [0:31][0:3][0:7];
 task fail(input string m); begin if(errors<12)$display("SU_TOP ERROR cyc=%0d %s",cyc,m); errors=errors+1; end endtask
 function automatic [255:0] vm_image(input integer qq,input [15:0] s);
  integer row,j,kk; begin
   row=s[12:4]; j=s[3]*8+s[2:0];
   for(kk=0;kk<8;kk=kk+1)vm_image[kk*32+:32]=seed[row*512+qq*128+8*j+kk];
  end
 endfunction
 always @(posedge clk)if(rst_n&&cyc>=0)begin
  // ---- LG boundary: returns scheduled for this edge (registered: held this edge .. next)
  for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin
   if(pend_v[cyc%32][q][p])begin
    lg_rr[(q*8+p)*257+:257]<={1'b1,vm_image(q,pend_s[cyc%32][q][p])^((mut_data&&reads==777)?256'h10000:256'h0)};
    reads=reads+1;
   end else lg_rr[(q*8+p)*257+:257]<=257'd0;
   lg_w_done[q*8+p]<=pend_w[cyc%32][q][p];
   pend_v[cyc%32][q][p]=0;pend_w[cyc%32][q][p]=0;
  end
  for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin
   if(lg_rq[(q*8+p)*17+16])begin pend_v[(cyc+10)%32][q][p]=1;pend_s[(cyc+10)%32][q][p]=lg_rq[(q*8+p)*17+:16]; end
   if(lg_wq[(q*8+p)*281+280])begin
    reg [319:0] x; reg [255:0] got,want,m;
    pend_w[(cyc+7)%32][q][p]=1; writes=writes+1;
    if(ew>=NW)fail("unexpected extra VM write");
    else begin
     x=expw[ew]; ew=ew+1;
     got=lg_wq[(q*8+p)*281+8+:256]; want=x[255:0];
     for(k=0;k<8;k=k+1)m[k*32+:32]={32{x[256+k]}};
     if(x[319:288]!==cyc||x[287:284]!==q||x[283:280]!==p)
      fail($sformatf("write order/edge: got q%0d p%0d at %0d, want q%0d p%0d at %0d",q,p,cyc,x[287:284],x[283:280],x[319:288]));
     if(lg_wq[(q*8+p)*281+264+:16]!==x[279:264]||lg_wq[(q*8+p)*281+:8]!==x[263:256])fail("write sector/mask");
     if((got&m)!==(want&m))fail($sformatf("write data q%0d p%0d sec %h got %h want %h",q,p,x[279:264],got,want));
    end
   end
  end
  // ---- reducer scalars
  for(q=0;q<4;q=q+1)if(dut.red_sv[q])begin
   scalars=scalars+1;
   if(es>=NS)fail("unexpected scalar");
   else begin
    if(exps[es][127:96]!==cyc||exps[es][95:64]!==q||exps[es][63:32]!==dut.red_tag[q*32+:32]||exps[es][31:0]!==dut.red_x[q*32+:32])
     fail($sformatf("scalar q%0d tag %h got %h want edge %0d q%0d tag %h val %h",q,dut.red_tag[q*32+:32],dut.red_x[q*32+:32],
          exps[es][127:96],exps[es][95:64],exps[es][63:32],exps[es][31:0]));
    es=es+1;
   end
  end
  // ---- lane write counts
  if(cyc<stop)for(q=0;q<4;q=q+1)if($countones(lw[q])!==explw[cyc][q*8+:8])
   fail($sformatf("lane writes q%0d %0d want %0d",q,$countones(lw[q]),explw[cyc][q*8+:8]));
  if(|fault)fail($sformatf("DUT fault %b",fault));
 end
 initial begin
  string dir;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  if(!$value$plusargs("STOP=%d",stop))stop=NE;
  mut_data=$test$plusargs("MUT_DATA");mut_addr=$test$plusargs("MUT_ADDR");mut_rf=$test$plusargs("MUT_RF");mut_red=$test$plusargs("MUT_RED");
  for(i=0;i<32;i=i+1)for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin pend_v[i][q][p]=0;pend_w[i][q][p]=0;pend_s[i][q][p]=0;end
  $readmemh({dir,"/prog.mem"},prog);$readmemh({dir,"/expw.mem"},expw);$readmemh({dir,"/exps.mem"},exps);
  $readmemh({dir,"/explw.mem"},explw);$readmemh({dir,"/arith/seed.mem"},seed);
  repeat(4)@(negedge clk); rst_n=1; repeat(2)@(negedge clk);
  for(i=0;i<stop;i=i+1)begin
   line=prog[i];
   // quarter-1 A affine term bit 0 (control field ld_c, stream A term 0) corrupted at an op's load edge
   if(mut_addr&&i==1040)line[QW+680+(1742-2-1200)+:24]=24'd3;
   if(mut_rf&&line[0*QW+74+9+8])line[0*QW+74+9+:8]=8'd3;
   if(mut_red&&i>=1040+176+31&&i<1040+176+31+2)line[0+:74]=prog[i-1][0+:74];
   cyc=i;
   @(negedge clk);
  end
  line=0;
  for(i=0;i<40;i=i+1)begin cyc=stop+i; @(negedge clk); end
  if(stop<NE)begin
   // debug run: only expectations due before the stop edge are required
   while(ew<NW&&expw[ew][319:288]<stop)begin fail("missing VM write");ew=ew+1;end
   while(es<NS&&exps[es][127:96]<stop)begin fail("missing scalar");es=es+1;end
   ew=NW;es=NS;
  end
  if(ew!=NW)fail($sformatf("VM writes %0d of %0d expected",ew,NW));
  if(es!=NS)fail($sformatf("scalars %0d of %0d expected",es,NS));
  if(errors)$fatal(1,"SU_TOP FAIL errors=%0d reads=%0d writes=%0d scalars=%0d",errors,reads,writes,scalars);
  $display("SU_TOP PASS lanes=512 slices=16 store_banks=512 SRAMs=3072+8 reducers=4 rf_replicas=4 edges=%0d fill_reads=%0d vm_writes=%0d scalars=%0d RF_RELAY=%0d MLAT=%0d",
           NE,reads,writes,scalars,RF_RELAY,MLAT);
  $finish;
 end
endmodule
