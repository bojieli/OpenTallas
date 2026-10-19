`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HBM-NEXT-UNITS-SUDMA 2026-10-19: N-row SU.VOP record bench. Fork of tb_hbm_su_static_top (d4g whole static SU, RTL
// unchanged) with the row counter ot_hnx_su_rowx (4 quarters) between the programme line and the SU top.
// Vectors: tools/hbm_next/su_rows_compile.py (prog.mem = row-0-relative lines, rowc.mem = per-edge row codes,
// strides.mem = the record's strides; --absolute = the unrolled d4g image, row codes / strides 0 -> same expectations).
// The bench is only the LG boundary of the four VM slices (sampled read -> VM image +10 edges, write -> done +7, as
// tb_hbm_su_static_top) plus checks: every LG write (edge, quarter, port, sector, mask, masked data) equals the next
// expected write; per-edge lane write counts; zero DUT and rowx faults; all expectations consumed; no reducer scalar.
// Measured: first VM read edge and last VM write edge of the DUT (SU_ROWS_EDGES), the record's cycles(N).
// RTL mutants (-GMUT, ot_hnx_su_rowx): 1 vmr sector stride, 2 control vb stride, 3 vmw sector stride, 4 store-row stride.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hnx_su_rows;
 parameter integer NEMAX=1024,NWMAX=8192,RF_RELAY=8,MUT=0;
 integer NE=0,NW=0;
 localparam integer QW=2422;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg [4*QW-1:0] prog [0:NEMAX-1];
 reg [79:0] rcm [0:NEMAX-1];
 reg [295:0] stm [0:0];
 reg [4*QW-1:0] line=0; reg [79:0] rcl=0;
 reg [31:0] seed [0:262143];
 reg [319:0] expw [0:NWMAX-1];
 reg [31:0] explw [0:NEMAX+1];
 wire [4*QW-1:0] rline; wire [3:0] rfault;
 for(genvar q=0;q<4;q=q+1)begin:g_rx
  ot_hnx_su_rowx #(.REG(1),.MUT(MUT)) u_rx(.clk(clk),.rst_n(rst_n),.line_in(line[q*QW+:QW]),.rc(rcl[q*20+:20]),
   .st(stm[0][294:0]),.line_out(rline[q*QW+:QW]),.fault(rfault[q]));
 end
 wire [4*1742-1:0] control; wire [4*240-1:0] vmr; wire [4*312-1:0] vmw; wire [4*54-1:0] rf; wire [4*74-1:0] red;
 for(genvar q=0;q<4;q=q+1)begin:g_split
  assign {control[q*1742+:1742],vmr[q*240+:240],vmw[q*312+:312],rf[q*54+:54],red[q*74+:74]}=rline[q*QW+:QW];
 end
 wire [4*8*17-1:0] lg_rq; wire [4*8*281-1:0] lg_wq; reg [4*8*257-1:0] lg_rr=0; reg [31:0] lg_w_done=0;
 wire [19:0] fault;
 ot_hbm_su_static_top #(.RF_RELAY(RF_RELAY)) dut(
  .pg_clk({16{clk}}),.clk_lane({4096{clk}}),.clk_insert({2048{clk}}),.rst_lane_n({512{rst_n}}),
  .clk_bcast({64{clk}}),.rst_bcast_n({64{rst_n}}),.clk_bank({512{clk}}),.clk_bank_macro({3072{clk}}),.clk_rf({256{clk}}),.clk_ctl({16{clk}}),
  .clk_core({4{clk}}),.clk_red({4{clk}}),.clk_side({6{clk}}),.clk_relay({4{clk}}),.rst_n(rst_n),
  .control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_rd_cmd(rf),.red_cmd(red),
  .lg_rq(lg_rq),.lg_wq(lg_wq),.lg_rr(lg_rr),.lg_w_done(lg_w_done),.fault(fault));
 wire [127:0] lw [0:3];
 for(genvar q=0;q<4;q=q+1)begin:g_lwq
  for(genvar g=0;g<4;g=g+1)begin:g_lws
   assign lw[q][g*32+:32]=dut.g_q[q].u_quarter.g_slice[g].u_slice.vm_we|dut.g_q[q].u_quarter.g_slice[g].u_slice.kv_we;
  end
 end
 integer stop;
 integer cyc=-1,errors=0,ew=0,reads=0,writes=0,i,q,p,k,first_rd=-1,last_wr=-1;
 reg pend_v [0:31][0:3][0:7]; reg [15:0] pend_s [0:31][0:3][0:7]; reg pend_w [0:31][0:3][0:7];
 task fail(input string m); begin if(errors<12)$display("SU_ROWS ERROR cyc=%0d %s",cyc,m); errors=errors+1; end endtask
 function automatic [255:0] vm_image(input integer qq,input [15:0] s);
  integer row,j,kk; begin
   row=s[12:4]; j=s[3]*8+s[2:0];
   for(kk=0;kk<8;kk=kk+1)vm_image[kk*32+:32]=seed[row*512+qq*128+8*j+kk];
  end
 endfunction
 always @(posedge clk)if(rst_n&&cyc>=0)begin
  for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin
   if(pend_v[cyc%32][q][p])begin
    lg_rr[(q*8+p)*257+:257]<={1'b1,vm_image(q,pend_s[cyc%32][q][p])};
    reads=reads+1;
   end else lg_rr[(q*8+p)*257+:257]<=257'd0;
   lg_w_done[q*8+p]<=pend_w[cyc%32][q][p];
   pend_v[cyc%32][q][p]=0;pend_w[cyc%32][q][p]=0;
  end
  for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin
   if(lg_rq[(q*8+p)*17+16])begin
    pend_v[(cyc+10)%32][q][p]=1;pend_s[(cyc+10)%32][q][p]=lg_rq[(q*8+p)*17+:16];
    if(first_rd<0)first_rd=cyc;
   end
   if(lg_wq[(q*8+p)*281+280])begin
    reg [319:0] x; reg [255:0] got,want,m;
    pend_w[(cyc+7)%32][q][p]=1; writes=writes+1; last_wr=cyc;
    if(ew>=NW)fail("unexpected extra VM write");
    else begin
     x=expw[ew]; ew=ew+1;
     got=lg_wq[(q*8+p)*281+8+:256]; want=x[255:0];
     for(k=0;k<8;k=k+1)m[k*32+:32]={32{x[256+k]}};
     if(x[319:288]!==cyc||x[287:284]!==q||x[283:280]!==p)
      fail($sformatf("write order/edge: got q%0d p%0d at %0d, want q%0d p%0d at %0d",q,p,cyc,x[287:284],x[283:280],x[319:288]));
     if(lg_wq[(q*8+p)*281+264+:16]!==x[279:264]||lg_wq[(q*8+p)*281+:8]!==x[263:256])
      fail($sformatf("write sector/mask got %h want %h",lg_wq[(q*8+p)*281+264+:16],x[279:264]));
     if((got&m)!==(want&m))fail($sformatf("write data q%0d p%0d sec %h got %h want %h",q,p,x[279:264],got,want));
    end
   end
  end
  for(q=0;q<4;q=q+1)if(dut.red_sv[q])fail("unexpected reducer scalar");
  if(cyc<=stop)for(q=0;q<4;q=q+1)if($countones(lw[q])!==explw[cyc][q*8+:8])
   fail($sformatf("lane writes q%0d %0d want %0d",q,$countones(lw[q]),explw[cyc][q*8+:8]));
  if(|fault)fail($sformatf("DUT fault %b",fault));
  if(|rfault)fail($sformatf("rowx fault %b",rfault));
 end
 initial begin
  string dir;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  if(!$value$plusargs("NE=%d",NE)||!$value$plusargs("NW=%d",NW)||NE>NEMAX||NW>NWMAX)$fatal(1,"NE/NW missing or over NEMAX/NWMAX");
  for(i=0;i<32;i=i+1)for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin pend_v[i][q][p]=0;pend_w[i][q][p]=0;pend_s[i][q][p]=0;end
  $readmemh({dir,"/prog.mem"},prog);$readmemh({dir,"/rowc.mem"},rcm);$readmemh({dir,"/strides.mem"},stm);
  $readmemh({dir,"/expw.mem"},expw);$readmemh({dir,"/explw.mem"},explw);$readmemh({dir,"/arith/seed.mem"},seed);
  stop=NE;
  repeat(4)@(negedge clk); rst_n=1; repeat(2)@(negedge clk);
  for(i=0;i<stop;i=i+1)begin
   line=prog[i]; rcl=rcm[i];
   cyc=i;
   @(negedge clk);
  end
  line=0; rcl=0;
  for(i=0;i<40;i=i+1)begin cyc=stop+i; @(negedge clk); end
  if(ew!=NW)fail($sformatf("VM writes %0d of %0d expected",ew,NW));
  if(errors)$fatal(1,"SU_ROWS FAIL errors=%0d reads=%0d writes=%0d MUT=%0d",errors,reads,writes,MUT);
  $display("SU_ROWS_EDGES first_vm_read=%0d last_vm_write=%0d span=%0d",first_rd,last_wr,last_wr-first_rd+1);
  $display("SU_ROWS PASS lanes=512 store_banks=512 SRAMs=3072+8 edges=%0d fill_reads=%0d vm_writes=%0d MUT=%0d",NE,reads,writes,MUT);
  $finish;
 end
endmodule
