`timescale 1ns/1ps
// Verification only: unchanged one-credit WINDOW -> real mux -> KARB -> timed backend.
module tb #(parameter integer MEM_MODE=1);
  localparam integer BASE=262144;
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
    .start_v(start_v),.start_ready(start_ready),.start_user(10'b0),.start_first(21'b0),.start_count(8'd128),
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
  ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.MEM_WORDS(BASE+2176),.MEM_MODE(MEM_MODE),.REFPB(3),.CLK_PS(1000)) mem (
    .clk(clk),.rst_n(rst_n),.req_v(hv),.req_rdy(hrdy),.req_addr(ha),.req_len(hl),.req_tag(ht),.req_we(hwe),
    .req_wdata(hd),.req_wstrb(hm),.wr_done(hwdone),.rsp_v(rv),.rsp_rdy(rrdy),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd));
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
    if(MEM_MODE==0) for(integer n=0;n<2176;n=n+1) mem.mem[BASE+n]=pattern(BASE+n);
    #1.1; rst_n=1;
  end
  always @(negedge clk) if(rst_n) begin
    start_v=(mem.cyc==12300);
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
