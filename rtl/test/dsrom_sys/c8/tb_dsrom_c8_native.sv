`timescale 1ps/1ps
module tb_dsrom_c8_native;
 reg clk=0;always #417 clk=~clk;
 reg rst_n=0;integer cycle=0;
 reg sel_v=0,nw_we=0;reg [29:0] nw_addr=0;reg [1023:0] nw_data=0;
 reg [46:0] identity={16'd7,10'd2,21'd100};
 wire vm_re;wire [14:0] vm_addr;reg [511:0] vm_q;
 wire [3:0] cv,cr,ce,cwd,csv,csr;wire [119:0] ca;wire [15:0] cl,cb;wire [63:0] ct,cst;wire [1023:0] cd,csd;wire [127:0] cw;
 wire own_visible,own_pending;wire [46:0] own_id;wire [20:0] own_gid;wire sf;wire [5:0] sfc;
 wire [3:0] mv,mr,me,mwd,sv,sr;wire [119:0] ma;wire [15:0] ml,sb;wire [63:0] mt,st;wire [1023:0] md,sd;wire [127:0] mw;
 wire [3:0] wready,wwdone;
 reg readback=0,reading_mode=0;reg [3:0] read_done=0;integer read_index=0;
 wire [3:0] port_v=reading_mode?(readback?4'b1000:4'd0):cv;
 wire [119:0] port_addr=readback?{30'(16+9*31+read_index),90'd0}:ca;
 wire [3:0] quiet,qfault,quarantine;
 wire [127:0] vv;wire [128*47-1:0] vi;wire [128*30-1:0] va;wire [255:0] vw;
 integer accepted=0,visible=0,read_count=0;reg [2303:0] expected;
 reg second=0;
 // Actual retained full K512 service, including its original row encoder and
 // full ID table. Only publication completion/visibility logic is selected.
 ot_chip_v41x_ckv_die_service_c8 #(.C8_PUBLICATION(1),.DIE_ID(3),.K(512),.NSLOT(64),.CKV_BASE(16),.CKV_SECTORS(1008)) service(
  .clk(clk),.rst_n(rst_n),.sel_v(sel_v),.sel_vmword(15'd0),.nw_we(nw_we),.nw_addr(nw_addr),.nw_data(nw_data),
  .vm_re(vm_re),.vm_raddr(vm_addr),.vm_rq(vm_q),.vm_busy(),
  .c_v(cv),.c_rdy(reading_mode?4'd0:cr),.c_addr(ca),.c_len(cl),.c_tag(ct),.c_we(ce),.c_wdata(cd),.c_wstrb(cw),.c_wr_done(cwd),
  .c_sv(reading_mode?4'd0:csv),.c_srdy(csr),.c_stag(cst),.c_sbeat(cb),.c_sdata(csd),
  .ag_tx_valid(),.ag_tx_ready(1'b0),.ag_tx_rank(),.ag_tx_gid(),.ag_tx_row(),
  .ag_rx_valid(3'd0),.ag_rx_rank(30'd0),.ag_rx_gid(63'd0),.ag_rx_row(6912'd0),
  .job_v(1'b0),.job_ready(),.kv_v(),.kv_ready(1'b0),.kv_m(),.kv_w(),.job_done(),
  .fault(sf),.fault_code(sfc),.rows_ready(),.st_rows_local(),.st_rows_remote(),.st_cycles_to_ready(),
  .position_identity(identity),.own_visible_v(own_visible),.own_visible_identity(own_id),.own_visible_gid(own_gid),.own_pending(own_pending));
 always @(posedge clk) if(vm_re) for(integer i=0;i<16;i=i+1) vm_q[i*32+:32]<=32'(vm_addr*16+i);
 ot_chip_v41x_kv_rope_reqmux_c8 #(.C8_PUBLICATION(1),.HAW(30),.TAGW(16)) mux(
  .clk(clk),.rst_n(rst_n),.w_v(4'd0),.w_rdy(wready),.w_addr(120'd0),.w_len(16'd0),.w_tag(64'd0),.w_we(4'd0),.w_wdata(1024'd0),.w_wstrb(128'd0),.w_wr_done(wwdone),.w_sv(),.w_srdy(4'hf),.w_stag(),.w_sbeat(),.w_sdata(),
  .c_v(port_v),.c_rdy(cr),.c_addr(port_addr),.c_len(readback?16'h1000:cl),.c_tag(readback?{16'(16'h3000+read_index),48'd0}:ct),.c_we(readback?4'd0:ce),.c_wdata(cd),.c_wstrb(cw),.c_wr_done(cwd),.c_sv(csv),.c_srdy(readback?4'hf:csr),.c_stag(cst),.c_sbeat(cb),.c_sdata(csd),
  .p_v(4'd0),.p_rdy(),.p_addr(120'd0),.p_len(16'd0),.p_tag(64'd0),.p_we(4'd0),.p_wdata(1024'd0),.p_wstrb(128'd0),.p_wr_done(),.p_sv(),.p_srdy(4'hf),.p_stag(),.p_sbeat(),.p_sdata(),
  .m_v(mv),.m_rdy(mr),.m_addr(ma),.m_len(ml),.m_tag(mt),.m_we(me),.m_wdata(md),.m_wstrb(mw),.m_wr_done(mwd),
  .s_v(sv),.s_rdy(sr),.s_tag(st),.s_beat(sb),.s_data(sd),.fault(),.rope_grants(),.rope_wait_cycles());
 genvar g;
 generate for(g=0;g<4;g=g+1) begin:stack
  wire [31:0] hv,hr,he,hwd,rv,rr;wire [959:0] ha;wire [127:0] hl,rb;wire [543:0] ht,rt;wire [8191:0] hd,rd;wire [1023:0] hw;
  wire [63:0] kinds;wire [959:0] da;wire [543:0] dt;
  for(genvar p=0;p<32;p=p+1) begin:kind assign kinds[p*2+:2]=ht[p*17+16]?{1'b1,ht[p*17+14]}:2'b00;end
  ot_chip_v41x_hbm_karb #(.NPC(32),.AW(30),.TAGW(16)) arb(
   .clk(clk),.rst_n(rst_n),.b_v(32'd0),.b_rdy(),.b_addr(960'd0),.b_len(128'd0),.b_tag(512'd0),.b_we(32'd0),.b_wdata(8192'd0),.b_wstrb(1024'd0),.b_wr_done(),.b_rsp_v(),.b_rsp_rdy(32'hffffffff),.b_rsp_tag(),.b_rsp_beat(),.b_rsp_data(),
   .k_v(mv[g]),.k_rdy(mr[g]),.k_addr(ma[g*30+:30]),.k_len(ml[g*4+:4]),.k_tag(mt[g*16+:16]),.k_we(me[g]),.k_wdata(md[g*256+:256]),.k_wstrb(mw[g*32+:32]),.k_wr_done(mwd[g]),.k_rsp_v(sv[g]),.k_rsp_rdy(sr[g]),.k_rsp_tag(st[g*16+:16]),.k_rsp_beat(sb[g*4+:4]),.k_rsp_data(sd[g*256+:256]),
   .h_v(hv),.h_rdy(hr),.h_addr(ha),.h_len(hl),.h_tag(ht),.h_we(he),.h_wdata(hd),.h_wstrb(hw),.h_wr_done(hwd),.r_v(rv),.r_rdy(rr),.r_tag(rt),.r_beat(rb),.r_data(rd),.k_grants(),.b_grants(),.contended());
  ot_hdc_v41x_idx_hbm_c8 #(.NPC(32),.AW(30),.DW(256),.TAGW(17),.LENW(4),.BEATW(4),.MEM_WORDS(1024),.QD(64),.REFPB(3),.MEM_MODE(0)) backend(
   .clk(clk),.rst_n(rst_n),.req_v(hv),.req_rdy(hr),.req_addr(ha),.req_len(hl),.req_tag(ht),.req_we(he),.req_wdata(hd),.req_wstrb(hw),.wr_done(hwd),.wr_done_addr(da),.wr_done_tag(dt),.rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd));
  initial for(integer a=0;a<1024;a=a+1) backend.mem[a]=0;
  ot_dsrom_c8_write_journal #(.NPC(32),.DEPTH(64),.AW(30)) journal(
   .clk(clk),.rst_n(rst_n),.accepted_write(hv&hr&he),.backend_wr_done(hwd),.accepted_addr(ha),.accepted_tag(ht),.backend_done_addr(da),.backend_done_tag(dt),.accepted_writer(kinds),.accepted_identity(identity),
   .visible_v(vv[g*32+:32]),.visible_identity(vi[g*32*47+:32*47]),.visible_addr(va[g*32*30+:32*30]),.visible_writer(vw[g*64+:64]),.quiet(quiet[g]),.debt(),.quarantine(quarantine[g]),.fault(qfault[g]));
 end endgenerate
 always @(posedge clk) if(rst_n) begin
  cycle<=cycle+1;
  if(sf)$fatal(1,"actual service fault code=%h",sfc);
  if(cv[3]&&ce[3]&&mv[3]&&mr[3]&&!cr[3])
   $fatal(1,"backend accepted C write without caller grant");
  if(ce[3]&&cv[3]&&cr[3]) accepted<=accepted+1;
  for(integer p=0;p<128;p=p+1) if(vv[p]) begin
   if(vi[p*47+:47]!=={16'd7,10'd2,21'd100}||vw[p*2+:2]!==2'b11||va[p*30+:30]!==30'(16+9*31+visible))$fatal(1,"wrong visible identity/address/writer");
   visible<=visible+1;
  end
  if(own_visible) begin
   if(accepted!=9||visible+$countones(vv)!=9||own_id!==identity||own_gid!=511)$fatal(1,"own publication before actual nine ACKs");
  end
  if(|qfault || |quarantine)$fatal(1,"unexpected journal quarantine");
 end
 task edge_step;begin @(posedge clk);@(negedge clk);end endtask
 initial begin
  repeat(8)edge_step();rst_n=1;repeat(8)edge_step();
  sel_v=1;edge_step();sel_v=0;
  for(integer b=0;b<16;b=b+1) begin
   // Actual golden qdq_fp4_e4m3(ones): scale 0.171875, code 6,
   // BF16 output 1.03125. Arbitrary unquantized 1.0 is not encoder input.
   nw_we=1;nw_addr=30'(511*512+b*32);
   for(integer i=0;i<32;i=i+1) nw_data[i*32+:32]=32'h3f840000;
   edge_step();
  end
  nw_we=0;
  while(!own_visible && cycle<100000)edge_step();
  if(!own_visible)begin
   $display("BLOCKED id_done=%b count=%0d enc_done=%b enc_busy=%b got=%h go=%b wr_act=%b wr_pending=%b wr_k=%0d cv=%h cr=%h cwd=%h accepted=%0d visible=%0d",service.id_done,service.id_count,service.enc_done,service.enc_busy,service.nw_got,service.go,service.wr_act,service.wr_pending,service.wr_k,cv,cr,cwd,accepted,visible);
   $fatal(1,"actual C writer failed to publish nine visible sectors");
  end
  expected=service.new_row;reading_mode=1;
  // Read through the actual mux/arb/backend AFTER visible completion. No mem
  // peeking is admitted as completion or as the readback value.
  for(integer k=0;k<9;k=k+1) begin
   read_index=k;readback=1;
   while(!cr[3])edge_step();edge_step();readback=0;
   while(!(csv[3] && cst[3*16+:16]==16'(16'h3000+k)))edge_step();
   if(csd[3*256+:256]!==expected[k*256+:256])$fatal(1,"native readback mismatch sector %0d",k);
   read_count=read_count+1;edge_step();
  end
  $display("PASS C8_ACTUAL_CWRITER own_sectors=%0d visible_ACKs=%0d native_readback=%0d K512=1 stacks4_NPC32=1 early_memory_not_receipt=1 cycle=%0d",accepted,visible,read_count,cycle);
  $finish;
 end
endmodule
