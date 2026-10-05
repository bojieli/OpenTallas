`timescale 1ns/1ps
// Verification only: unchanged one-credit WINDOW -> real mux -> KARB -> timed backend.
module tb #(parameter integer MEM_MODE=0);
  localparam integer BASE=262144;
  string control="HEALTHY";
  reg hold_req=0,hold_rsp=0;
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0, start_v=0, stream_go=0, prime_v=0;
  reg [20:0] prime_row=0;
  wire prime_ready;
  wire start_ready, staged_v, busy, done, fault, kv_v;
  wire [4:0] fault_code;
  wire [31:0] refill_cycles, sectors_read;
  wire [7:0] rows_refilled;
  wire [3:0] kv_m,wv,wrdy,wwe,wsv,wsrdy,wwdone;
  wire [16959:0] kv_w;
  wire [119:0] wa,ma;
  wire [15:0] wl,ml,wb,mb;
  wire [63:0] wt,mt,wst,mst;
  wire [1023:0] wd,md,wsd,msd;
  wire [127:0] wm,mm;
  wire [3:0] mv,mrdy,mwe,msv,msrdy,mwdone;
  wire mux_fault;
  ot_chip_v41x_window_attn_source #(.WIN_STACK(2),.STREAM_II1(0),.REFILL_CREDITS(1)) win (
    .clk(clk),.rst_n(rst_n),.retain_qk(1'b0),.retain_pv(1'b0),.retain_complete(1'b0),
    .retain_invalidate(1'b0),.retain_generation(16'b0),
    .region_base_sector(30'(BASE)),.region_sector_count(30'd2176),
    .prime_v(prime_v),.prime_ready(prime_ready),.prime_user(10'b0),.prime_row(prime_row),
    .blk_v(1'b0),.blk_user(10'b0),.blk_row(21'b0),.blk_idx(4'b0),.blk_codes(256'b0),.blk_scale(8'b0),
    .start_v(desc_accept),.start_ready(start_ready),.start_user(10'b0),.start_first(21'b0),.start_count(8'd128),
    .staged_v(staged_v),.stream_go(stream_go),.busy(busy),.done(done),.fault(fault),.fault_code(fault_code),
    .refill_cycles(refill_cycles),.sectors_read(sectors_read),.rows_refilled(rows_refilled),
    .kv_v(kv_v),.kv_ready(1'b1),.kv_m(kv_m),.kv_w(kv_w),
    .m_v(wv),.m_rdy(wrdy),.m_addr(wa),.m_len(wl),.m_tag(wt),.m_we(wwe),.m_wdata(wd),.m_wstrb(wm),
    .m_wr_done(wwdone),.s_v(wsv),.s_rdy(wsrdy),.s_tag(wst),.s_beat(wb),.s_data(wsd));
  ot_chip_v41x_kv_rope_reqmux #(.HAW(30),.TAGW(16)) mux (
    .clk(clk),.rst_n(rst_n),.w_v(wv),.w_rdy(wrdy),.w_addr(wa),.w_len(wl),.w_tag(wt),.w_we(wwe),
    .w_wdata(wd),.w_wstrb(wm),.w_wr_done(wwdone),.w_sv(wsv),.w_srdy(wsrdy),.w_stag(wst),.w_sbeat(wb),.w_sdata(wsd),
    .c_v(4'b0),.c_addr(120'b0),.c_len(16'b0),.c_tag(64'b0),.c_we(4'b0),.c_wdata(1024'b0),.c_wstrb(128'b0),.c_srdy(4'hf),
    .p_v(4'b0),.p_addr(120'b0),.p_len(16'b0),.p_tag(64'b0),.p_we(4'b0),.p_wdata(1024'b0),.p_wstrb(128'b0),.p_srdy(4'hf),
    .m_v(mv),.m_rdy(mrdy),.m_addr(ma),.m_len(ml),.m_tag(mt),.m_we(mwe),.m_wdata(md),.m_wstrb(mm),
    .m_wr_done(mwdone),.s_v(msv),.s_rdy(msrdy),.s_tag(mst),.s_beat(mb),.s_data(msd),.fault(mux_fault));
  assign mrdy[1:0]=2'b11; assign mrdy[3]=1'b1;
  assign msv[1:0]=0; assign msv[3]=0;
  assign mst[31:0]=0; assign mst[63:48]=0;
  assign mb[7:0]=0; assign mb[15:12]=0;
  assign msd[511:0]=0; assign msd[1023:768]=0;
  assign mwdone[1:0]=0; assign mwdone[3]=0;
  wire [31:0] hv,hrdy,hwe,hwdone,rv,rrdy;
  wire [959:0] ha;
  wire [127:0] hl,rb;
  wire [543:0] ht,rt;
  wire [8191:0] hd,rd;
  wire [1023:0] hm;
  ot_chip_v41x_hbm_karb #(.NPC(32),.AW(30),.TAGW(16)) arb (
    .clk(clk),.rst_n(rst_n),.b_v(32'b0),.b_addr(960'b0),.b_len(128'b0),.b_tag(512'b0),.b_we(32'b0),
    .b_wdata(8192'b0),.b_wstrb(1024'b0),.b_rsp_rdy(32'hffffffff),
    .k_v(mv[2]),.k_rdy(mrdy[2]),.k_addr(ma[60+:30]),.k_len(ml[8+:4]),.k_tag(mt[32+:16]),
    .k_we(mwe[2]),.k_wdata(md[512+:256]),.k_wstrb(mm[64+:32]),.k_wr_done(mwdone[2]),
    .k_rsp_v(msv[2]),.k_rsp_rdy(msrdy[2]),.k_rsp_tag(mst[32+:16]),.k_rsp_beat(mb[8+:4]),.k_rsp_data(msd[512+:256]),
    .h_v(hv),.h_rdy(hrdy),.h_addr(ha),.h_len(hl),.h_tag(ht),.h_we(hwe),.h_wdata(hd),.h_wstrb(hm),
    .h_wr_done(hwdone),.r_v(rv),.r_rdy(rrdy),.r_tag(rt),.r_beat(rb),.r_data(rd));
  wire[31:0] raw_hrdy,raw_rv,raw_rrdy;
  assign hrdy=hold_req ? 32'b0 : raw_hrdy;
  assign rv=hold_rsp ? 32'b0 : raw_rv;
  assign raw_rrdy=hold_rsp ? 32'b0 : rrdy;
  ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.MEM_WORDS(BASE+2176),.MEM_MODE(MEM_MODE),.REFPB(3),.CLK_PS(1000)) mem (
    .clk(clk),.rst_n(rst_n),.req_v(hold_req ? 32'b0 : hv),.req_rdy(raw_hrdy),.req_addr(ha),.req_len(hl),.req_tag(ht),.req_we(hwe),
    .req_wdata(hd),.req_wstrb(hm),.wr_done(hwdone),.rsp_v(raw_rv),.rsp_rdy(raw_rrdy),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd));

  wire desc_accept,kv_ok,desc_done,desc_fault;
  wire[15:0] desc_gen;wire[10:0] desc_rows;
  reg issued=0;
  always @(posedge clk)if(rst_n && stream_go)issued<=1;
  ot_chip_v41x_attn_desc_lifecycle #(.AW(30),.NW(21),.L0_ONLY(1)) life(
   .clk(clk),.rst_n(rst_n),.desc_v(start_v && start_ready),.desc_user(10'd0),.desc_pos(21'd127),
   .desc_tiles(21'd4),.desc_k(21'd512),.desc_nout(21'd128),.desc_wbase(30'd0),
   .desc_ts(30'd512),.desc_ks(30'd1),.desc_js(30'd0),.desc_hg(2'd1),.desc_mmode(1'b1),
   .desc_accept(desc_accept),.desc_gen(desc_gen),.desc_rows(desc_rows),
   .stage_v(staged_v),.stage_gen(desc_gen),.stage_rows(11'd128),
   .beat_v(kv_v),.beat_ready(1'b1),.beat_gen(desc_gen),.beat_mask(kv_m),
   .issue_v(stream_go && !issued),.engine_idle(!issued || done),.service_fault(fault || mux_fault || su_fault),
   .wrap_drained(!busy),.issue_ok(kv_ok),.done(desc_done),.fault(desc_fault));
  reg su_go=0;wire su_idle,su_ready,su_fault;
  wire[1023:0] su_re;reg[32767:0] su_q=0;wire[30719:0]su_rd_addr;wire[2047:0]su_rd_src;
  reg[31:0] synthetic_vm[0:65535];integer su_stores=0;
  initial for(integer row=0;row<16;row++)for(integer elem=0;elem<64;elem++)synthetic_vm[56192+row*512+elem]=32'h3f000000;
  wire[255:0] su_vm_we;wire[8191:0] su_vm_data;wire[7679:0] su_vm_addr;
  wire[255:0] su_vi_re;wire[7679:0] su_vi_addr;reg[8191:0]su_vi_q=0;
  ot_hdc_v41x_su_adapt #(.N(256),.M(64),.LV(7),.AW(30),.NW(21),.CLS_DRAIN(0),.BCAST_STAGES(0),.RET_STAGES(0)) su(
   .clk(clk),.rst_n(rst_n),.go(su_go),.ready(su_ready),.idle(su_idle),
   .i_nout(21'd16),.i_nin(21'd64),.i_chase(21'd0),.i_asrc(2'd0),.i_bsrc(2'd1),.i_csrc(2'd0),.i_dsrc(2'd2),
   .i_abase(30'd56192),.i_aso(30'd512),.i_asi(30'd1),.i_aibase(30'd0),.i_aind(2'd0),
   .i_bbase(30'h20000000),.i_bso(30'd0),.i_bsi(30'd1),.i_bhalf(1'b1),
   .i_cbase(30'd0),.i_cso(30'd0),.i_csi(30'd0),.i_cpair(1'b1),
   .i_dbase(30'h20000000),.i_dso(30'd0),.i_dsi(30'd1),
   .i_arnd(1'b0),.i_arelu(1'b0),.i_amin(1'b0),.i_cclip(1'b0),.i_m1(3'd1),.i_m2(2'd0),
   .i_qm(3'd3),.i_ad(3'd1),.i_sfu(3'd0),.i_e1(3'd0),.i_e2(2'd0),.i_rnd(1'b1),
   .i_dst(2'd1),.i_obase(30'd56192),.i_oso(30'd512),.i_osi(30'd1),.i_orow(30'd0),
   .i_red(2'd0),.i_redsq(1'b0),.i_redwhole(1'b0),.i_redtree(1'b0),.i_redrnd(1'b0),
   .i_rbase(30'd0),.i_rso(30'd0),.i_imm1(32'd0),.i_imm2(32'd0),.i_imm3(32'd0),
   .i_m(3'd1),.i_xps(30'd0),.i_ops(30'd0),.vi_re(su_vi_re),.vi_addr(su_vi_addr),.vi_q(su_vi_q),
   .rd_re(su_re),.rd_addr(su_rd_addr),.rd_src(su_rd_src),.rd_q(su_q),.vm_we(su_vm_we),.vm_waddr(su_vm_addr),.vm_wdata(su_vm_data),.fault(su_fault));
  // Synthetic finite operand source, synchronous response. No ready/backpressure fabricated.
  always @(posedge clk)if(rst_n)begin
   for(integer i=0;i<1024;i++)if(su_re[i])begin
    if(su_rd_src[i*2+:2]==0)begin
     if(su_rd_addr[i*30+:30]>=65536)$fatal(1,"SU VM read aperture");
     su_q[i*32+:32]<=synthetic_vm[su_rd_addr[i*30+:30]];
    end else su_q[i*32+:32]<=32'h3f000000;
   end
   for(integer i=0;i<256;i++)if(su_vm_we[i])begin
    if(su_vm_addr[i*30+:30]>=65536)$fatal(1,"SU VM write aperture");
    synthetic_vm[su_vm_addr[i*30+:30]]<=su_vm_data[i*32+:32];su_stores=su_stores+1;
   end
   for(integer i=0;i<256;i++)if(su_vi_re[i])su_vi_q[i*32+:32]<=32'h3f000000;
  end
  wire[63:0]owner_su_retired,owner_req,owner_rsp;
  ot_w17_owner_progress_exports #(.ENABLED(1)) exports(
   .clk(clk),.rst_n(rst_n),.su_retire(su.u_vec.dbg_ret),
   .window_read_accept(wv[2] && wrdy[2] && !wwe[2]),.window_return_accept(wsv[2] && wsrdy[2]),
   .su_retired(owner_su_retired),.window_accepted(owner_req),.window_returned(owner_rsp));
  import "DPI-C" function void owner_progress_init(input int overall);
  import "DPI-C" function int owner_progress_sample(input longint cycle,su_retired,accepted,returned,
   input int rows,desc,win,su_idle,kv_ok,req_v,req_ready,backend_req_v,backend_req_ready,backend_rsp_v,backend_rsp_ready,fault);
  bit old_pc_would_fail=0;
  integer verdict;
  always @(negedge clk)if(rst_n && started>=0)begin
   if(mem.cyc-started>100000)old_pc_would_fail=1;
   verdict=owner_progress_sample(mem.cyc,owner_su_retired,owner_req,owner_rsp,
    win.u_window.st_rows_fetched,life.state,win.u_window.state,su_idle,kv_ok,wv[2],wrdy[2],
    |hv,|(hv&hrdy),|raw_rv,|(raw_rv&raw_rrdy),fault||mux_fault||desc_fault||su_fault);
   if(verdict!=0)begin
    if((control=="HOLD_REQ" && verdict==2 && owner_req==0 && owner_rsp==0) ||
       (control=="HOLD_RSP" && verdict==3 && owner_req==1 && owner_rsp==0) ||
       (control=="OVERALL" && verdict==6 && mem.cyc==12320))begin
     $display("OWNER_PROGRESS_REFUSAL_PASS case=%s reason=%0d cycle=%0d SUret=%0d req=%0d rsp=%0d",control,verdict,mem.cyc,owner_su_retired,owner_req,owner_rsp);
     $finish;
    end else $fatal(1,"unexpected owner watchdog refusal case=%s reason=%0d",control,verdict);
   end
  end

  function automatic [255:0] pattern(input integer addr);
    reg [255:0] p;
    if(MEM_MODE==1) begin
      for(integer n=0;n<8;n=n+1) p[n*32+:32]=((32'(addr)*32'd8+32'(n))*32'h9e3779b1)^32'h5bd1e995;
    end else begin
      p=0;
      for(integer n=0;n<32;n=n+1)
        p[n*8+:8]=((addr-BASE)%17==16) ? 8'(120+n%5) : 8'(1+((addr-BASE)*3+n)%100);
    end
    return p;
  endfunction
  integer c=0, primed=0, started=-1, staged=-1, reads=0, replies=0, beats=0, inflight=0, max_inflight=0;
  integer row,sector,addr; reg [255:0] scale; reg [264:0] expected;
  initial begin
    if(!$value$plusargs("CASE=%s",control))control="HEALTHY";
    if(control!="HEALTHY" && control!="HOLD_REQ" && control!="HOLD_RSP" && control!="OVERALL")$fatal(1,"unknown control");
    owner_progress_init(control=="OVERALL" ? 12320 : 150000);
    if(MEM_MODE==0) for(integer n=0;n<2176;n=n+1) mem.mem[BASE+n]=pattern(BASE+n);
    #1.1; rst_n=1;
  end
  always @(negedge clk) if(rst_n) begin
    start_v=(mem.cyc==12300);
    su_go=start_v;
    hold_req=(control=="HOLD_REQ" && mem.cyc>=12300);
    hold_rsp=(control=="HOLD_RSP" && mem.cyc>=12300);
    prime_v=primed<128; prime_row=21'(primed);
    if(staged>=0) stream_go=1;
  end
  always @(posedge clk) if(rst_n) begin
    c=c+1;
    if(prime_v && prime_ready) primed=primed+1;
    if(start_v && start_ready) started=mem.cyc;
    if(fault || mux_fault) $fatal(1,"source/mux fault code=%0d",fault_code);
    if(wv[2] && wrdy[2]) begin
      if(started<0 || inflight!=0 || wwe[2] || wl[8+:4]!=1 || wt[32+:16]!=(reads%17) || wa[60+:30]!=BASE+reads)
        $fatal(1,"client request identity/order/credit mismatch");
      inflight=inflight+1; reads=reads+1; if(inflight>max_inflight)max_inflight=inflight;
      if(reads<=8) $display("CLIENT_REQUEST cycle=%0d addr=%0h tag=%0h",mem.cyc,wa[60+:30],wt[32+:16]);
    end
    if(wsv[2] && wsrdy[2]) begin
      if(inflight!=1 || wst[32+:16]!=(replies%17) || wb[8+:4]!=0 || wsd[512+:256]!==pattern(BASE+replies))
        $fatal(1,"routed response identity/data mismatch");
      replies=replies+1; inflight=inflight-1;
      if(replies<=8) $display("CLIENT_REPLY cycle=%0d tag=%0h",mem.cyc,wst[32+:16]);
    end
    for(integer p=0;p<32;p=p+1) if(hv[p] && hrdy[p]) begin
      if(reads<=8) $display("BACKEND_REQUEST cycle=%0d pc=%0d addr=%0h tag=%0h",mem.cyc,p,ha[p*30+:30],ht[p*17+:17]);
      if(ht[p*17+16]!=1 || ht[p*17+14+:2]!=0 || hwe[p]) $fatal(1,"backend owner tag or write");
    end
    if(staged_v) begin
      if(staged>=0 || reads!=2176 || replies!=2176 || inflight!=0 || rows_refilled!=128)
        $fatal(1,"publication before all rows committed");
      staged=mem.cyc;
    end
    if(kv_v) begin
      if(staged<0 || kv_m!=15 || beats>=32) $fatal(1,"stream lifecycle/mask");
      for(integer l=0;l<4;l=l+1) begin
        row=beats*4+l; scale=pattern(BASE+17*row+16);
        for(integer g=0;g<16;g=g+1) begin
          expected={1'b0,scale[g*8+:8],pattern(BASE+17*row+g)};
          if(kv_w[(l*16+g)*265+:265]!==expected) $fatal(1,"packed row stream mismatch row=%0d group=%0d",row,g);
        end
      end
      beats=beats+1;
    end
    if(done) begin
      if(control!="HEALTHY" || owner_su_retired!=4 || su_stores!=1024 || !su_idle || !old_pc_would_fail || owner_req!=2176 || owner_rsp!=2176)
        $fatal(1,"owner progress healthy totals or old100k witness");
      if(started!=12300 || staged!=136669 || mem.cyc!=136800 || refill_cycles!=124368)
        $fatal(1,"unchanged credit1 prediction mismatch");
      $display("OWNER_PROGRESS_HEALTHY_PASS SUret=%0d req=%0d rsp=%0d desc=%0d kvok=%0d oldPCwatchdog=%0d",owner_su_retired,owner_req,owner_rsp,life.state,kv_ok,old_pc_would_fail);
      if(beats!=32 || reads!=2176 || replies!=2176 || inflight!=0 || sectors_read!=2176)
        $fatal(1,"terminal totals/drain mismatch");
      for(integer p=0;p<32;p=p+1) begin
        if(mem.st_rd[p]!=68 || mem.q_n[p]!=0 || mem.r_n[p]!=0 || mem.st_wr[p]!=0)
          $fatal(1,"per-PC service totals or drain mismatch pc=%0d",p);
        $display("PC_DRAIN pc=%0d reads=%0d q=%0d r=%0d refreshes=%0d activations=%0d",p,mem.st_rd[p],mem.q_n[p],mem.r_n[p],mem.st_ref[p],mem.st_act[p]);
      end
      $display("CONNECTED_WINDOW_PASS start=%0d staged=%0d done=%0d refill=%0d reads=%0d replies=%0d beats=%0d max_inflight=%0d",started,staged,mem.cyc,refill_cycles,reads,replies,beats,max_inflight);
      $finish;
    end
    if(c%20000==0) $display("PROGRESS cycle=%0d started=%0d primed=%0d staged=%0d reads=%0d replies=%0d beats=%0d src_busy=%0d pfstate=%0d rows=%0d refill=%0d req=%0h ready=%0h backend_req=%0h backend_rsp=%0h rspready=%0h q1=%0d r1=%0d rt1=%0h",mem.cyc,started,primed,staged,reads,replies,beats,busy,win.u_window.state,rows_refilled,refill_cycles,wv,wrdy,hv,rv,rrdy,mem.q_n[1],mem.r_n[1],rt[17+:17]);
    if(c>200000) $fatal(1,"cycle cap reads=%0d replies=%0d staged=%0d beats=%0d",reads,replies,staged,beats);
  end
endmodule
