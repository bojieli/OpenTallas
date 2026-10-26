`timescale 1ns/1ps
// Full shape SU with native32-bank VM producer. Preload is external bench
// stimulus through bank DMA ports. The measured DUT contains no seed lookup,
// behavioral operand memory, or expected-answer data source. Checks retain
// the original whole-SU edge/mask/data, scalar, lane-write and fault checks.
// cal.mem is compiled from command fields, never observed DUT requests.
module tb_hbm_su_native_composed_top;
 parameter integer NE=7111,NW=135184,NS=9,RF_RELAY=8,MUT=0,MLAT=3,ALAT=3,LEAF=0,MUT_LG=0,MUT_BANK=0;
 localparam integer QW=2422, FO=8+23+4*(MLAT-3)+(ALAT-3)+LEAF;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 `include "programme_params.svh"
 reg [279:0] programme_config[0:PROGRAMME_WRITES-1];
 reg programme_cfg_we=0,programme_start=0;
 reg [15:0] programme_cfg_bank=0;
 reg [6:0] programme_cfg_row=0;
 reg [255:0] programme_cfg_data=0;
 wire programme_busy,programme_valid,programme_done,programme_fault;
 wire [15:0] programme_edge;
 wire [PROGRAMME_BITS-1:0] programme_command;
 ot_hbm_su_programme #(.LINE_BITS(PROGRAMME_BITS),.EDGES(NE),.DICT_BANKS(PROGRAMME_DICT_BANKS),.MACROS(PROGRAMME_MACROS)) programme(
  .clk(clk),.clk_macro({PROGRAMME_MACROS{clk}}),.rst_n(rst_n),.cfg_we(programme_cfg_we),.cfg_bank(programme_cfg_bank),
  .cfg_row(programme_cfg_row),.cfg_data(programme_cfg_data),.start(programme_start),.length(16'(NE)),
  .busy(programme_busy),.valid(programme_valid),.done(programme_done),.fault(programme_fault),
  .edge_index(programme_edge),.command(programme_command));
 reg [4*QW-1:0] line;
 reg [31:0] seed [0:262143];
 reg [319:0] expw [0:NW-1];
 reg [127:0] exps [0:NS-1];
 reg [31:0] explw [0:NE-1];
 wire [4*1742-1:0] control; wire [4*240-1:0] vmr; wire [4*312-1:0] vmw; wire [4*54-1:0] rf; wire [4*74-1:0] red;
 for(genvar q=0;q<4;q=q+1)begin:g_split
  assign {control[q*1742+:1742],vmr[q*240+:240],vmw[q*312+:312],rf[q*54+:54],red[q*74+:74]}=line[q*QW+:QW];
 end
 wire [4*8*17-1:0] lg_rq; wire [4*8*281-1:0] lg_wq; wire [4*8*257-1:0] lg_rr; wire [31:0] lg_w_done;

 reg [63:0] cal_line;
 reg [32*281-1:0] preload_wq=0;
 wire [31:0] preload_done,lg_fault;
 wire [32*18-1:0] bank_status;
 reg preload_mode=1;
 wire [95:0] wslot={32{preload_mode ? 3'd5 : 3'd0}};
 ot_hbm_su_native_vm #(.MUT_LG(MUT_LG),.MUT_BANK(MUT_BANK)) native_vm(
  .clk_bank({32{clk}}),.rst_n(rst_n),.lg_rq(lg_rq),.lg_wq(lg_wq),
  .lg_rr(lg_rr),.lg_w_done(lg_w_done),.cal_rd(cal_line[31:0]),.cal_wr(cal_line[63:32]),
  .rslot_v(32'hffffffff),.wslot_v(32'hffffffff),.rslot(64'd0),.wslot(wslot),
  .preload_wq(preload_wq),.preload_done(preload_done),.lg_fault(lg_fault),.bank_status(bank_status));
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
 bit mut_data,mut_addr,mut_rf,mut_red,mut_cal;
 // Direct DUT-to-DUT command connection. Only explicit negative-test masks
 // alter programme outputs; the positive case is a combinational wire.
 always_comb begin
  line=programme_valid ? programme_command[0+:4*QW] : '0;
  cal_line=programme_valid ? programme_command[4*QW+:64] : '0;
  if(mut_cal && programme_edge==777)cal_line[8]=0;
  if(mut_addr && programme_edge==1040)line[QW+680+(1742-2-1200)+:24]=24'd3;
  if(mut_rf && line[74+9+8])line[74+9+:8]=8'd3;
  if(mut_red && programme_edge>=1040+176+FO && programme_edge<1040+176+FO+2)line[0+:74]='0;
 end
 reg pend_v [0:31][0:3][0:7]; reg [15:0] pend_s [0:31][0:3][0:7]; reg pend_w [0:31][0:3][0:7];
 task fail(input string m); begin if(errors<12)$display("SU_NATIVE_COMPOSED_TOP ERROR cyc=%0d %s",cyc,m); errors=errors+1; end endtask
 always @(posedge clk)if(rst_n&&cyc>=0)begin
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
  if(|lg_fault||bank_status!==0)fail($sformatf("native VM fault lg=%h banks=%h",lg_fault,bank_status));
  if(|fault)fail($sformatf("DUT fault %b",fault));
 end
 always @(posedge clk)if(rst_n&&cyc>=0)begin
  #1;
  for(integer qq=0;qq<4;qq=qq+1)for(integer pp=0;pp<8;pp=pp+1)begin
   if(lg_rr[(qq*8+pp)*257+256]!==pend_v[cyc%32][qq][pp])fail("native read return phase");
   if(lg_w_done[qq*8+pp]!==pend_w[cyc%32][qq][pp])fail("native write done phase");
   if(lg_rr[(qq*8+pp)*257+256])reads=reads+1;
   pend_v[cyc%32][qq][pp]=0;pend_w[cyc%32][qq][pp]=0;
  end
 end
 initial begin
  string dir;
  reg [255:0] predata;
  reg [15:0] presec;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  if(!$value$plusargs("STOP=%d",stop))stop=NE;
  if(stop!=NE)$fatal(1,"native composed proof requires the full compiled timeline");
  mut_data=$test$plusargs("MUT_DATA");mut_addr=$test$plusargs("MUT_ADDR");mut_rf=$test$plusargs("MUT_RF");mut_red=$test$plusargs("MUT_RED");mut_cal=$test$plusargs("MUT_CAL");
  for(i=0;i<32;i=i+1)for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin pend_v[i][q][p]=0;pend_w[i][q][p]=0;pend_s[i][q][p]=0;end
  $readmemh({dir,"/programme/config.mem"},programme_config);
  $readmemh({dir,"/expw.mem"},expw);$readmemh({dir,"/exps.mem"},exps);
  $readmemh({dir,"/explw.mem"},explw);$readmemh({dir,"/arith/seed.mem"},seed);
  repeat(4)@(negedge clk); rst_n=1; repeat(2)@(negedge clk);
  // External initialization: exactly one DMA-sector write per bank/edge.
  // Each 128-word quarter row is16sectors: e={row9,half1}, bank=sector[2:0].
  for(i=0;i<1024;i=i+1)begin
   for(q=0;q<4;q=q+1)for(p=0;p<8;p=p+1)begin
    presec=16'((q<<13)|((i>>1)<<4)|((i&1)<<3)|p);
    for(k=0;k<8;k=k+1)begin
     predata[k*32+:32]=seed[(i>>1)*512+q*128+(i&1)*64+p*8+k];
     if(mut_data&&(i>>1)*512+q*128+(i&1)*64+p*8+k==777)predata[k*32]=~predata[k*32];
    end
    preload_wq[(q*8+p)*281+:281]={1'b1,presec,predata,8'hff};
   end
   @(negedge clk);
  end
  preload_wq=0;repeat(16)@(negedge clk);preload_mode=0;
  if(bank_status!==0||lg_fault!==0)$fatal(1,"native VM preload fault");
  // Host provisioning is outside measured execution. Actual SRAM hardware
  // produces all programme and calendar bits after this configuration phase.
  for(i=0;i<PROGRAMME_WRITES;i=i+1)begin
   programme_cfg_we=1; programme_cfg_bank=programme_config[i][279:264];
   programme_cfg_row=programme_config[i][262:256]; programme_cfg_data=programme_config[i][255:0];
   @(negedge clk);
  end
  programme_cfg_we=0; programme_start=1; @(negedge clk); programme_start=0;
  // Start was sampled before previous negedge: index and dictionary startup.
  @(negedge clk); if(programme_valid)$fatal(1,"programme unexpectedly early");
  @(negedge clk); if(programme_valid)$fatal(1,"programme unexpectedly early");
  @(negedge clk);
  for(i=0;i<stop;i=i+1)begin
   if(!programme_valid || programme_edge!==i || programme_fault)$fatal(1,"programme cycle/index/fault");
   cyc=i;
   @(negedge clk);
  end
  if(stop==NE && (programme_valid || programme_busy || programme_fault))$fatal(1,"programme tail/fault");
  for(i=0;i<40;i=i+1)begin cyc=stop+i; @(negedge clk); end
  if(stop<NE)begin
   // debug run: only expectations due before the stop edge are required
   while(ew<NW&&expw[ew][319:288]<stop)begin fail("missing VM write");ew=ew+1;end
   while(es<NS&&exps[es][127:96]<stop)begin fail("missing scalar");es=es+1;end
   ew=NW;es=NS;
  end
  if(ew!=NW)fail($sformatf("VM writes %0d of %0d expected",ew,NW));
  if(es!=NS)fail($sformatf("scalars %0d of %0d expected",es,NS));
  if(errors)$fatal(1,"SU_NATIVE_COMPOSED_TOP FAIL errors=%0d reads=%0d writes=%0d scalars=%0d",errors,reads,writes,scalars);
  $display("SU_NATIVE_COMPOSED_TOP PASS lanes=512 slices=16 store_banks=512 SRAMs=3072+8+96+%0d native_banks=32 reducers=4 rf_replicas=4 edges=%0d fill_reads=%0d vm_writes=%0d scalars=%0d RF_RELAY=%0d MLAT=%0d",
           PROGRAMME_MACROS,NE,reads,writes,scalars,RF_RELAY,MLAT);
  $finish;
 end
endmodule
