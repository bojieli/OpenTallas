`timescale 1ps/1fs
// Native whole-SU source candidate: independent SRAM programme planes, actual
// 3:4 clocks and actual VM/LG. Physical epoch/skew and closure remain OPEN.
module tb_hbm_su_native_multirate_top;
 parameter integer NE=7116,PE=9489,NW=135184,NS=9,RF_RELAY=8,MUT=0,
                   MLAT=4,ALAT=3,LEAF=1,MUT_LG=0,MUT_BANK=0;
 localparam integer QW=2422,FO=8+23+4*(MLAT-3)+(ALAT-3)+LEAF;
 localparam realtime HALF_Q=1250.0/9.0;
 reg serial_clk=0,stream_clk=0,rst_n=0,bridge_rst_n=0;
 integer half_tick=-1,epoch_half=-1;
 // Both clocks derive from the same exact integer event lattice. Half-q
 // rounding is common, preserving the ratio and coincident12q frame exactly.
 initial forever begin
  #(HALF_Q);half_tick=half_tick+1;
  serial_clk=(half_tick%8)<4;stream_clk=(half_tick%6)<3;
 end
 `include "serial/programme_params.svh"
 `include "stream/programme_params.svh"
 reg [279:0] serial_config[0:SERIAL_WRITES-1],stream_config[0:STREAM_WRITES-1];
 reg serial_cfg_we=0,stream_cfg_we=0,serial_start=0,stream_start=0;
 reg [15:0] serial_cfg_bank=0,stream_cfg_bank=0;
 reg [6:0] serial_cfg_row=0,stream_cfg_row=0;
 reg [255:0] serial_cfg_data=0,stream_cfg_data=0;
 wire serial_busy,serial_valid,serial_done,serial_fault,stream_busy,stream_valid,stream_done,stream_fault;
 wire [15:0] serial_edge,stream_edge;
 wire [9687:0] serial_command;wire [63:0] stream_command;
 ot_hbm_su_programme #(.LINE_BITS(9688),.COLS(SERIAL_COLS),.EDGES(NE),.DICT_BANKS(SERIAL_DICT_BANKS),.MACROS(SERIAL_MACROS)) serial_programme(
  .clk(serial_clk),.clk_macro({SERIAL_MACROS{serial_clk}}),.rst_n(rst_n),
  .cfg_we(serial_cfg_we),.cfg_bank(serial_cfg_bank),.cfg_row(serial_cfg_row),.cfg_data(serial_cfg_data),
  .start(serial_start),.length(16'(NE)),.busy(serial_busy),.valid(serial_valid),.done(serial_done),
  .fault(serial_fault),.edge_index(serial_edge),.command(serial_command));
 ot_hbm_su_programme #(.LINE_BITS(64),.COLS(STREAM_COLS),.INDEX_PACK(STREAM_INDEX_PACK),.EDGES(PE),.DICT_BANKS(STREAM_DICT_BANKS),.MACROS(STREAM_MACROS)) stream_programme(
  .clk(stream_clk),.clk_macro({STREAM_MACROS{stream_clk}}),.rst_n(rst_n),
  .cfg_we(stream_cfg_we),.cfg_bank(stream_cfg_bank),.cfg_row(stream_cfg_row),.cfg_data(stream_cfg_data),
  .start(stream_start),.length(16'(PE)),.busy(stream_busy),.valid(stream_valid),.done(stream_done),
  .fault(stream_fault),.edge_index(stream_edge),.command(stream_command));
 reg [9687:0] line;reg[63:0]cal_line;
 bit mut_data,mut_addr,mut_rf,mut_red,mut_cal,mut_epoch;
 always_comb begin
  line=serial_valid?serial_command:'0;cal_line=stream_valid?stream_command:'0;
  if(mut_addr&&serial_edge==1040)line[QW+680+(1742-2-1200)+:24]=24'd3;
  if(mut_rf&&line[74+9+8])line[74+9+:8]=8'd3;
  if(mut_red&&serial_edge>=1040+176+FO&&serial_edge<1040+176+FO+2)line[0+:74]='0;
  // First read is reserved at stream edge3; remove its bank0 reservation.
  if(mut_cal&&stream_edge==3)cal_line[0]=0;
 end
 wire [6967:0]control;wire[959:0]vmr;wire[1247:0]vmw;wire[215:0]rf;wire[295:0]red;
 for(genvar q=0;q<4;q=q+1)begin:g_split
  assign {control[q*1742+:1742],vmr[q*240+:240],vmw[q*312+:312],rf[q*54+:54],red[q*74+:74]}=line[q*QW+:QW];
 end
 wire[543:0]lg_rq;wire[8991:0]lg_wq;wire[8223:0]lg_rr;wire[31:0]lg_w_done;
 reg[8991:0]preload_wq=0;wire[31:0]preload_done,lg_fault;wire[575:0]bank_status;
 reg preload_mode=1;
 wire[95:0]wslot={32{preload_mode?3'd5:3'd0}};
 ot_hbm_su_native_vm #(.MUT_LG(MUT_LG),.MUT_BANK(MUT_BANK)) native_vm(
  .clk_bank({32{stream_clk}}),.rst_n(rst_n),.lg_rq(lg_rq),.lg_wq(lg_wq),.lg_rr(lg_rr),.lg_w_done(lg_w_done),
  .cal_rd(cal_line[31:0]),.cal_wr(cal_line[63:32]),.rslot_v(32'hffffffff),.wslot_v(32'hffffffff),
  .rslot(64'd0),.wslot(wslot),.preload_wq(preload_wq),.preload_done(preload_done),.lg_fault(lg_fault),.bank_status(bank_status));
 wire[19:0]fault;
 ot_hbm_su_static_top #(.MULTIRATE(1),.RF_RELAY(RF_RELAY),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.MUT(MUT)) dut(
  .pg_clk({16{stream_clk}}),.clk_lane({4096{serial_clk}}),.clk_insert({2048{serial_clk}}),.rst_lane_n({512{rst_n}}),
  .clk_bcast({64{serial_clk}}),.rst_bcast_n({64{rst_n}}),.clk_bank({512{serial_clk}}),.clk_bank_macro({3072{serial_clk}}),
  .clk_rf({256{serial_clk}}),.clk_ctl({16{serial_clk}}),.clk_core({4{serial_clk}}),.clk_red({4{serial_clk}}),
  .clk_side({6{serial_clk}}),.clk_relay({4{serial_clk}}),.rst_n(rst_n),.bridge_rst_n(bridge_rst_n),
  .control(control),.vmr_cmd(vmr),.vmw_cmd(vmw),.rf_rd_cmd(rf),.red_cmd(red),
  .lg_rq(lg_rq),.lg_wq(lg_wq),.lg_rr(lg_rr),.lg_w_done(lg_w_done),.fault(fault));
 wire[127:0]lw[0:3];
 wire[511:0]store_commit;wire[255:0]rf_commit;
 for(genvar q=0;q<4;q=q+1)begin:g_lwq
  for(genvar g=0;g<4;g=g+1)begin:g_lws
   assign lw[q][g*32+:32]=dut.g_q[q].u_quarter.g_slice[g].u_slice.vm_we|dut.g_q[q].u_quarter.g_slice[g].u_slice.kv_we;
   for(genvar b=0;b<32;b=b+1)begin:g_commit
    // The pinned bank samples write_v one edge before w_pin drives actual
    // SRAM write enables. Observe pre-edge w_pin at that real commit edge.
    assign store_commit[q*128+g*32+b]=dut.g_q[q].u_quarter.g_slice[g].u_slice.g_bank[b].u_bank.w_pin;
   end
  end
  for(genvar b=0;b<64;b=b+1)begin:g_rfcommit
   assign rf_commit[q*64+b]=dut.g_q[q].u_quarter.u_core.u_rf.g_bank[b].u_bank.wv_pin;
  end
 end
 wire[31:0]bridge_read_present,bridge_ack_present;
 for(genvar q=0;q<4;q=q+1)begin:g_brq
  for(genvar g=0;g<4;g=g+1)begin:g_brg
   for(genvar h=0;h<2;h=h+1)begin:g_brh
    assign bridge_read_present[q*8+g*2+h]=dut.g_q[q].u_quarter.g_slice[g].u_slice.g_leaf[h].g_multirate.u_bridge.serial_rr[256];
    assign bridge_ack_present[q*8+g*2+h]=dut.g_q[q].u_quarter.g_slice[g].u_slice.g_leaf[h].g_multirate.u_bridge.serial_done;
   end
  end
 end
 integer last_read_issue=-1,last_read_return=-1,last_write_issue=-1,last_lg_ack=-1;
 integer last_bridge_read=-1,last_bridge_ack=-1,last_lane=-1,last_scalar=-1;
 integer bridge_reads=0,bridge_acks=0,last_store_commit=-1,last_rf_commit=-1;
 reg[31:0]seed[0:262143];reg[319:0]expw[0:NW-1];reg[127:0]exps[0:NS-1];reg[31:0]explw[0:NE-1];
 reg pend_v[0:31][0:31],pend_w[0:31][0:31];
 integer errors=0,ew=0,es=0,reads=0,writes=0,scalars=0;
 task fail(input string m);begin if(errors<12)$display("SU_NATIVE_MULTIRATE_TOP ERROR %s",m);errors=errors+1;end endtask
 always @(posedge serial_clk)if(rst_n&&epoch_half>=0&&half_tick>=epoch_half)begin
  integer n;
  n=(half_tick-epoch_half)/8;
  if((half_tick-epoch_half)%8!=0)fail("serial clock phase");
  if(|store_commit)last_store_commit=n;if(|rf_commit)last_rf_commit=n;
  if(n<NE)begin
   if(!serial_valid||serial_edge!==n||serial_fault)fail($sformatf("serial programme edge %0d got %0d valid %b",n,serial_edge,serial_valid));
   for(integer q=0;q<4;q=q+1)if(|lw[q])last_lane=n;
   for(integer q=0;q<4;q=q+1)if($countones(lw[q])!==explw[n][q*8+:8])fail($sformatf("lane writes serial%0d q%0d",n,q));
  end else if(serial_valid||serial_busy)fail("serial programme tail");
  for(integer q=0;q<4;q=q+1)if(dut.red_sv[q])begin
   scalars=scalars+1;last_scalar=n;
   if(es>=NS)fail("extra scalar");
   else if(exps[es][127:96]!==n||exps[es][95:64]!==q||exps[es][63:32]!==dut.red_tag[q*32+:32]||exps[es][31:0]!==dut.red_x[q*32+:32])
    fail($sformatf("scalar serial%0d q%0d got%h want%h",n,q,dut.red_x[q*32+:32],exps[es]));
   es=es+1;
  end
  if(|fault||serial_fault||stream_fault)fail($sformatf("serial%0d fault=%h programmes=%b%b",n,fault,serial_fault,stream_fault));
 end
 always @(posedge stream_clk)if(rst_n&&epoch_half>=0&&half_tick>=epoch_half)begin
  integer p;
  p=(half_tick-epoch_half)/6;
  if((half_tick-epoch_half)%6!=0)fail("stream clock phase");
  if(p<PE)begin
   if(!stream_valid||stream_edge!==p||stream_fault)fail($sformatf("stream programme edge%0d got%0d",p,stream_edge));
  end else if(stream_valid||stream_busy)fail("stream programme tail");
  for(integer b=0;b<32;b=b+1)begin
   if(lg_rq[b*17+16])begin pend_v[(p+10)%32][b]=1;last_read_issue=p;end
   if(lg_wq[b*281+280])begin
    reg[319:0]x;reg[255:0]got,want,mask;
    pend_w[(p+7)%32][b]=1;writes=writes+1;last_write_issue=p;
    if(ew>=NW)fail("extra VM write");
    else begin
     x=expw[ew];ew=ew+1;got=lg_wq[b*281+8+:256];want=x[255:0];
     for(integer k=0;k<8;k=k+1)mask[k*32+:32]={32{x[256+k]}};
     if(x[319:288]!==p||x[287:284]!==b/8||x[283:280]!==b%8)fail($sformatf("write order stream%0d bank%0d expected%h",p,b,x[319:280]));
     if(lg_wq[b*281+264+:16]!==x[279:264]||lg_wq[b*281+:8]!==x[263:256])fail("write sector/mask");
     if((got&mask)!==(want&mask))fail($sformatf("write data stream%0d bank%0d got%h want%h",p,b,got,want));
    end
   end
  end
  if(|lg_fault||bank_status!==0)fail($sformatf("VM fault stream%0d lg=%h bank=%h",p,lg_fault,bank_status));
  // Native LG presents its response after this edge. This checker uses the
  // stream calendar; serial return alignment is independently checked by DUT.
  #1;
  for(integer b=0;b<32;b=b+1)begin
   if(lg_rr[b*257+256]!==pend_v[p%32][b])fail($sformatf("read return stream%0d bank%0d",p,b));
   if(lg_w_done[b]!==pend_w[p%32][b])fail($sformatf("write done stream%0d bank%0d",p,b));
   if(lg_rr[b*257+256])begin reads=reads+1;last_read_return=p;end
   if(lg_w_done[b])last_lg_ack=p;
   pend_v[p%32][b]=0;pend_w[p%32][b]=0;
  end
 end
 always @(posedge serial_clk)if(rst_n&&epoch_half>=0&&half_tick>=epoch_half)begin
  integer n;
  n=(half_tick-epoch_half)/8;
  #1;
  if(|bridge_read_present)begin last_bridge_read=n;bridge_reads=bridge_reads+$countones(bridge_read_present);end
  if(|bridge_ack_present)begin last_bridge_ack=n;bridge_acks=bridge_acks+$countones(bridge_ack_present);end
 end
 initial begin
  string dir;reg[255:0]data;reg[15:0]sec;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  mut_data=$test$plusargs("MUT_DATA");mut_addr=$test$plusargs("MUT_ADDR");mut_rf=$test$plusargs("MUT_RF");
  mut_red=$test$plusargs("MUT_RED");mut_cal=$test$plusargs("MUT_CAL");mut_epoch=$test$plusargs("MUT_EPOCH");
  for(integer t=0;t<32;t=t+1)for(integer b=0;b<32;b=b+1)begin pend_v[t][b]=0;pend_w[t][b]=0;end
  $readmemh({dir,"/serial/config.mem"},serial_config);$readmemh({dir,"/stream/config.mem"},stream_config);
  $readmemh({dir,"/phase/stream_expw.mem"},expw);$readmemh({dir,"/exps.mem"},exps);
  $readmemh({dir,"/explw.mem"},explw);$readmemh({dir,"/arith/seed.mem"},seed);
  if(SERIAL_BITS!=9688||STREAM_BITS!=64)$fatal(1,"programme plane width");
  repeat(4)@(negedge serial_clk);rst_n=1;repeat(2)@(negedge stream_clk);
  for(integer i=0;i<1024;i=i+1)begin
   for(integer q=0;q<4;q=q+1)for(integer p=0;p<8;p=p+1)begin
    sec=16'((q<<13)|((i>>1)<<4)|((i&1)<<3)|p);
    for(integer k=0;k<8;k=k+1)begin
     data[k*32+:32]=seed[(i>>1)*512+q*128+(i&1)*64+p*8+k];
     if(mut_data&&(i>>1)*512+q*128+(i&1)*64+p*8+k==777)data[k*32]=~data[k*32];
    end
    preload_wq[(q*8+p)*281+:281]={1'b1,sec,data,8'hff};
   end
   @(negedge stream_clk);
  end
  preload_wq=0;repeat(16)@(negedge stream_clk);preload_mode=0;
  if(bank_status!==0||lg_fault!==0)$fatal(1,"SU_NATIVE_MULTIRATE_TOP FAIL preload fault");
  @(negedge serial_clk);
  for(integer i=0;i<SERIAL_WRITES;i=i+1)begin
   serial_cfg_we=1;serial_cfg_bank=serial_config[i][279:264];serial_cfg_row=serial_config[i][262:256];serial_cfg_data=serial_config[i][255:0];
   @(negedge serial_clk);
  end
  serial_cfg_we=0;@(negedge stream_clk);
  for(integer i=0;i<STREAM_WRITES;i=i+1)begin
   stream_cfg_we=1;stream_cfg_bank=stream_config[i][279:264];stream_cfg_row=stream_config[i][262:256];stream_cfg_data=stream_config[i][255:0];
   @(negedge stream_clk);
  end
  stream_cfg_we=0;
  epoch_half=24*((half_tick+95)/24);
  // Start each real SRAM producer exactly four of its own edges before E0.
  wait(half_tick==epoch_half-33);serial_start=1;
  wait(half_tick==epoch_half-31);serial_start=0;
  wait(half_tick==epoch_half-25);stream_start=1;
  wait(half_tick==epoch_half-23);stream_start=0;
  // Negative run actually advances bridge counters before E0; ordinary DUT
  // fault/data/cycle checks must reject the resulting phase mismatch.
  if(mut_epoch)bridge_rst_n=1;
  wait(half_tick==epoch_half-1);bridge_rst_n=1;
  wait(half_tick>=epoch_half+8*(NE+40));#2;
  if(ew!=NW||es!=NS||reads!=32768||writes!=NW||bridge_reads!=32768||bridge_acks!=NW)fail($sformatf("counts reads%0d writes%0d/%0d scalars%0d/%0d",reads,writes,NW,es,NS));
  if(serial_fault||stream_fault||(|fault)||(|lg_fault)||bank_status!==0)fail("final faults");
  $display("SU_NATIVE_MULTIRATE_ENDPOINTS {\"last_read_issue_stream\":%0d,\"last_read_return_stream\":%0d,\"last_write_issue_stream\":%0d,\"last_lg_ack_stream\":%0d,\"last_bridge_read_serial\":%0d,\"last_bridge_ack_serial\":%0d,\"last_lane_write_serial\":%0d,\"last_scalar_serial\":%0d,\"last_store_sram_commit_serial\":%0d,\"last_rf_register_commit_serial\":%0d,\"config_serial_transactions\":%0d,\"config_stream_transactions\":%0d,\"serial_prime_edges\":4,\"stream_prime_edges\":4,\"serial_programme_edges\":%0d,\"stream_calendar_edges\":%0d,\"checker_tail_serial_edges\":40}",
   last_read_issue,last_read_return,last_write_issue,last_lg_ack,last_bridge_read,last_bridge_ack,last_lane,last_scalar,last_store_commit,last_rf_commit,SERIAL_WRITES,STREAM_WRITES,NE,PE);
  if(errors)$fatal(1,"SU_NATIVE_MULTIRATE_TOP FAIL errors=%0d",errors);
  $display("SU_NATIVE_MULTIRATE_TOP PASS lanes512 storeSRAM3072 nativeVMbanks32 VM_SRAM96 programmeSRAM%0d serial_edges%0d stream_edges%0d reads%0d writes%0d scalars%0d",SERIAL_MACROS+STREAM_MACROS,NE,PE,reads,writes,scalars);
  $finish;
 end
endmodule
