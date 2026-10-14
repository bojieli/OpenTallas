`timescale 1ps/1fs
// hgi-takeover 2026-10-10: ot_hgi_dma_front against an svc-stream MODEL per the hgi-takeover.log interface spec (per
// stack: requests {tag, nsec, addr}; 8 lanes, lane l = idx % 8 in order, credit 4 a lane, random lane latencies and
// gaps) and a VM wide-port model.  Every LOAD's VM destination words are compared with an independent decode of the
// HBM model (BF16 << 16, E4M3 exact / NaN -> 0x7FC00000, INT8 exact, FP32 / U32 the word); no other VM word may change.
// Reports cycles and destination bytes a cycle.  +MUT via parameter MUT (1 BF16 lane mirror, 2 early tag free): FAIL.
// hgi-1010/c: INDEXED ROW STREAM loads (ix_cmd + id list with random gaps; ids >= 2^16, duplicates, multi-run rows, rows on
// every stack): row e of VM must equal the decode of HBM row abase + id_e x dyn_mul; MUT 3 (high partial product dropped)
// and MUT 4 (destination pointer advancing every other row) must FAIL.
module tb_hgi_dma_front_qwen_vm4_9b;
    parameter integer PHASE=61;
    parameter integer SOURCE_CAP=16,REQ_IDLE=0;
    parameter integer MUT = 0;
    parameter integer LD = 16;     // front lane buffer = svc initial credit
    parameter integer HOPS = 3;    // registered die-wire stages each way (data svc -> front, credit front -> svc)
    parameter integer NL = 8;      // svc data lanes a stack (lane l = idx % NL)
    parameter integer NB = 32;     // VM wide lanes (banks)
    parameter integer PCX4 = 0;
    parameter integer XP = 0;      // hbm-fq/dma 10-11: the textbook rebuild (registered X1 request vectors, X2 split, count rungs)
    parameter integer XS = 0;      // el1011-hbm-dmafs 10-12: 1 = the two-level split ot_hgi_dma_front_xsw (core + 4 slices)
    parameter integer XQ = 0;      // hbm-fq/mvf 10-11: X2 select rung + conversion rung + pin output register (needs XP)
    parameter integer AP = 0;      // hgi-1010 b: the weight aperture (VM words >= 2^18, 2 slots of 32,768): 281-b lanes, random
                                   //   per-bank wl_rdy stops (no lane may carry a sector 5+ edges into a stop), slot loads
    localparam integer VMW = AP ? 327680 : 262144, LWW = 280 + AP;    // HBM supply a stack in sectors per 4 cycles (99 = 3.80 TB/s a die at 1.2 GHz); 0 = unlimited
    localparam integer NS = 4, NIN = NS * NL, BW = $clog2(NB);
    localparam integer SBIT = 35; localparam longint SB = 22500000000;   // 1 MiB stacks in the bench
    reg [3:0] cclk=0;
    for(genvar q=0;q<4;q++)begin:clocks
      initial begin #(PHASE+q*17);forever #416.666625 cclk[q]=~cclk[q];end
    end
    wire clk=cclk[0];reg vmclk=0;always #555.5555 vmclk=~vmclk;reg rst_n=0;
    reg mv_v = 0; reg [226:0] mv = 0; wire mv_rdy, mv_done, mv_fault;
    reg ix_v = 0; reg [175:0] ix_cmd = 0; wire ix_rdy; reg id_v = 0; reg [31:0] id = 0; wire id_rdy;
    wire [NS*51-1:0] dq; reg [NS-1:0] dq_rdy = 0; reg [NIN*270-1:0] dd_m = 0; wire [NIN*270-1:0] dd; wire [NIN-1:0] dd_cr;
    wire [NB*LWW-1:0] wl; reg [NB-1:0] wl_done = 0; reg [NB-1:0] wl_rdy = '1; integer rlow [0:NB-1];
    wire [8*281-1:0] producer_packet;wire [7:0] producer_issue,vm_bad;wire leasebusy;
    wire [31:0] producer_credit,producer_done,qfault,native_done;wire [3:0] drained,lfault;wire [7:0] rfault;wire [32*281-1:0] native_dq;wire [31:0] dma_valid;
    for(genvar b=0;b<32;b++)assign dma_valid[b]=native_dq[b*281+280];
    ot_hgi_dma_front_xsw7b #(.SOURCE_CAP(SOURCE_CAP),.REQ_IDLE(REQ_IDLE),.QID(0),.NL(8),.LD(16),.SBIT(SBIT),.STACK_BYTES(36'(SB)),.MUT(MUT))dut(
      .clk(clk),.lane_clk({8{clk}}),.slice_clk(clk),.rst_n(rst_n),.mv_v(mv_v),.mv_rdy(mv_rdy),.mv(mv),.mv_done(mv_done),.mv_fault(mv_fault),
      .ix_v(ix_v),.ix_rdy(ix_rdy),.ix_cmd(ix_cmd),.id_v(id_v),.id_rdy(id_rdy),.id(id),.dq(dq),.dq_rdy(dq_rdy),.dd(dd),.dd_cr(dd_cr),
      .lease_grant(1'b1),.lease_busy(leasebusy),.wl_credit(producer_credit[7:0]),.wl_done(producer_done[7:0]),.issue_v(producer_issue),.vm_packet(producer_packet),.vm_bad(vm_bad));
    ot_hgi_dma_vm_transport9 tr(.source_clk(cclk),.vm_clk(vmclk),.rst_n(rst_n),.lease_grant(4'hf),.producer_busy({3'd0,leasebusy}),
      .issue_v({24'd0,producer_issue}),.source_packet({{24*281{1'b0}},producer_packet}),.source_credit(producer_credit),.source_done(producer_done),.queue_fault(qfault),.drained(drained),.lease_fault(lfault),
      .dma_q(native_dq),.dma_done(native_done),.router_fault(rfault));
    // ---- memories
    // HBM byte at address a: a full 64-bit mix (every address bit reaches every data bit; hgi-1010/c: the old hash
    // (a * K + (a >> 7) * K2) >> 3 ignored address bits >= 11, so a high-address error went unseen)
    function automatic [7:0] hb(input longint a);
        longint x;
        begin x = a ^ (a >> 31); x = x * 64'h9E3779B97F4A7C15; x = x ^ (x >> 29); x = x * 64'hBF58476D1CE4E5B9; hb = 8'(x >> 40); end
    endfunction
    reg [31:0] vm [0:VMW-1];
    bit trace_on=0;integer trace_start=0;integer tf[0:15],tl[0:15];
    task automatic hit(input integer stage);
      if(trace_on)begin if(tf[stage]<0)tf[stage]=cyc-trace_start;tl[stage]=cyc-trace_start;end
    endtask
    task automatic begin_trace;
      trace_on=1;trace_start=cyc;for(integer s=0;s<16;s++)begin tf[s]=-1;tl[s]=-1;end
    endtask
    task automatic print_trace;
      for(integer s=0;s<16;s++)$display("LATENCY stage=%0d first=%0d last=%0d",s,tf[s],tl[s]);
    endtask
    always @(posedge clk)if(rst_n&&trace_on)begin
      for(integer b=0;b<4;b++)if(dq[b*51+50]&&dq_rdy[b])hit(0);
      for(integer b=0;b<32;b++)if(dd[b*270+269])hit(1);
      if(dut.core.rqv_w!=0 && dut.core.lane_epoch!=dut.core.ack_epoch)hit(2);
      if(dut.core.u_ctrl.bsel_v!=0)hit(3);
      if(producer_issue!=0)hit(4);
      for(integer b=0;b<8;b++)if(producer_packet[b*281+280])hit(5);
      if(producer_done[7:0]!=0)hit(12);
      if(dut.core.u_ctrl.wdq!=0)hit(13);
      if(dut.core.u_ctrl.ndq!=0)hit(14);
    end
    for(genvar b=0;b<8;b++)begin:latency_bank
      always @(posedge vmclk)if(rst_n&&trace_on)begin
        if(tr.dstbank[b].f.src[0].q.load_head)hit(6);
        if(tr.dstbank[b].f.r.take!=0)hit(7);
        if(tr.dstbank[b].f.r.done_q!=0)hit(11);
      end
      for(genvar q=0;q<4;q++)begin:dest
        always @(posedge vmclk)if(rst_n&&trace_on)begin
          if(native_dq[(q*8+b)*281+280])hit(8);
          if(vehicle.quad[q].vm.g_bank[b].u_bank.dma_v)hit(9);
          if(native_done[q*8+b])hit(10);
        end
      end
    end
    // Observational throughput counters: no changes to grants, credits or fixture stimuli.
    longint prof_active=0,prof_hbm_req=0,prof_hbm_beats=0,prof_issue=0,prof_fmt=0,prof_credit=0,prof_done=0;
    longint prof_hbm_queued_lane=0,prof_hbm_wait_credit=0,prof_hbm_starved_cycles=0,prof_hbm_dq_stall=0;
    longint prof_pending=0,prof_cap_candidates=0,prof_conflict_candidates=0,prof_epoch_wait=0;
    longint prof_no_pick=0,prof_pure_cap=0,prof_req_fire=0,prof_req_bubble=0,prof_req_ft_full=0;
    longint prof_phase[0:3];initial for(integer p=0;p<4;p++)prof_phase[p]=0;
    integer prof_min_credit=SOURCE_CAP,prof_max_capacity=0,prof_max_outstanding=0;
    always @(posedge clk)if(rst_n)begin
      bit pending,offered;pending=0;offered=0;
      for(integer i=0;i<32;i++)if(lt[i]>lh[i])begin offered=1;prof_hbm_queued_lane++;if(cr[i]==0)prof_hbm_wait_credit++;end
      if(leasebusy&&!dut.core.u_ctrl.r_done&&!offered)prof_hbm_starved_cycles++;
      for(integer h=0;h<4;h++)if(dq[h*51+50]&&!dq_rdy[h])prof_hbm_dq_stall++;
      if(leasebusy)prof_active++;
      for(integer s=0;s<4;s++)if(dq[s*51+50]&&dq_rdy[s])prof_hbm_req++;
      for(integer b=0;b<32;b++)if(dd[b*270+269])prof_hbm_beats++;
      for(integer b=0;b<8;b++)begin
        if(producer_issue[b])prof_issue++;
        if(producer_packet[b*281+280])prof_fmt++;
        if(producer_credit[b])prof_credit++;
        if(producer_done[b])prof_done++;
        if(dut.core.u_ctrl.out_credit[b]<prof_min_credit)prof_min_credit=dut.core.u_ctrl.out_credit[b];
        if(tr.src[0].capacity[b]>prof_max_capacity)prof_max_capacity=tr.src[0].capacity[b];
        if(tr.src[0].outstanding[b]>prof_max_outstanding)prof_max_outstanding=tr.src[0].outstanding[b];
      end
      if(dut.core.u_ctrl.busy&&!dut.core.u_ctrl.r_done)begin
        prof_phase[dut.core.u_ctrl.req_phase]++;
        if(dut.core.u_ctrl.req_phase==2)prof_req_bubble++;
        if(dut.core.u_ctrl.ft==16)prof_req_ft_full++;
      end
      if(dut.core.u_ctrl.req_fire)prof_req_fire++;
      for(integer c=0;c<16;c++)begin
        if(dut.core.u_ctrl.rqv_q[c*8+:8]!=0)begin
          if(dut.core.u_ctrl.epoch_q[c]!=dut.core.u_ctrl.seen_epoch[c])begin
            pending=1;prof_pending++;
            if((dut.core.u_ctrl.rqv_q[c*8+:8]&~dut.core.u_ctrl.credit_available)!=0)prof_cap_candidates++;
          end else prof_epoch_wait++;
        end
        if(dut.core.u_ctrl.eligible[c]&&!dut.core.u_ctrl.packet_pick[c])prof_conflict_candidates++;
      end
      if(pending&&dut.core.u_ctrl.packet_pick==0)prof_no_pick++;
      if(pending&&dut.core.u_ctrl.eligible==0)prof_pure_cap++;
    end
    longint prof_qfull[0:7],prof_loadhead[0:7],prof_router_grant[0:7],prof_router_pending[0:7],prof_router_idle[0:7],prof_ticket_full[0:7];
    integer prof_max_q[0:7],prof_max_head[0:7],prof_max_ticket[0:7];
    for(genvar b=0;b<8;b++)begin:profile_bank
      initial begin prof_qfull[b]=0;prof_loadhead[b]=0;prof_router_grant[b]=0;prof_router_pending[b]=0;prof_router_idle[b]=0;prof_ticket_full[b]=0;prof_max_q[b]=0;prof_max_head[b]=0;prof_max_ticket[b]=0;end
      always @(posedge clk)if(rst_n)begin
        integer used;used=int'(5'(tr.dstbank[b].f.src[0].q.wp-tr.dstbank[b].f.src[0].q.ungray(tr.dstbank[b].f.src[0].q.rg2)));
        if(used>prof_max_q[b])prof_max_q[b]=used;
        if(tr.dstbank[b].f.src[0].q.full)prof_qfull[b]++;
      end
      always @(posedge vmclk)if(rst_n)begin
        integer heads;heads=$countones(tr.dstbank[b].f.src[0].q.head_v);
        if(heads>prof_max_head[b])prof_max_head[b]=heads;
        if(tr.dstbank[b].f.src[0].q.load_head)prof_loadhead[b]++;
        prof_router_grant[b]+=$countones(tr.dstbank[b].f.r.grant_v);
        if(tr.dstbank[b].f.r.src_v!=0)prof_router_pending[b]++;
        if(tr.dstbank[b].f.r.src_v!=0&&tr.dstbank[b].f.r.take==0)prof_router_idle[b]++;
        for(integer d=0;d<4;d++)begin
          if(tr.dstbank[b].f.r.tn[d]>prof_max_ticket[b])prof_max_ticket[b]=tr.dstbank[b].f.r.tn[d];
          if(tr.dstbank[b].f.r.tn[d]==16)prof_ticket_full[b]++;
        end
      end
    end
    task automatic print_profile;
      $display("PROFILE src_active=%0d hbm_req=%0d hbm_beats=%0d issue=%0d fmt=%0d credit=%0d done=%0d pending_candidates=%0d cap_candidates=%0d conflict_candidates=%0d epoch_wait=%0d no_pick=%0d pure_cap=%0d req_fire=%0d req_bubble=%0d req_ft_full=%0d phases=%0d/%0d/%0d/%0d min_credit=%0d max_capacity=%0d max_outstanding=%0d",prof_active,prof_hbm_req,prof_hbm_beats,prof_issue,prof_fmt,prof_credit,prof_done,prof_pending,prof_cap_candidates,prof_conflict_candidates,prof_epoch_wait,prof_no_pick,prof_pure_cap,prof_req_fire,prof_req_bubble,prof_req_ft_full,prof_phase[0],prof_phase[1],prof_phase[2],prof_phase[3],prof_min_credit,prof_max_capacity,prof_max_outstanding);
      $display("PROFILEHBM raw_offer_ceiling_srcB_per_source_cycle=256 PCX4=%0d scheduled_sectors=%0d queued_lane_cycles=%0d lane_credit_blocked=%0d no_scheduled_data_cycles=%0d dq_stall=%0d",PCX4,sched,prof_hbm_queued_lane,prof_hbm_wait_credit,prof_hbm_starved_cycles,prof_hbm_dq_stall);
      for(integer b=0;b<8;b++)$display("PROFILEBANK b=%0d queue_full=%0d loadhead=%0d router_grants=%0d router_pending=%0d router_idle=%0d ticket_full=%0d max_queue=%0d max_head=%0d max_ticket=%0d",b,prof_qfull[b],prof_loadhead[b],prof_router_grant[b],prof_router_pending[b],prof_router_idle[b],prof_ticket_full[b],prof_max_q[b],prof_max_head[b],prof_max_ticket[b]);
    endtask
    // Actual native B2/SECDED vehicle pinned to 64fced1f9. No behavioral VM writer.
    wire [32*16-1:0] su_rq;wire [32*257-1:0] su_rr;
    wire [32*280-1:0] su_wq;wire [31:0] su_rc,su_wc,su_done,vehicle_fault;
    wire [32*18-1:0] bank_status;
    ot_hbm_b2_su_vm4 #(.MUT(0)) vehicle(.cclk(cclk),.vclk(vmclk),.rst_n(rst_n),.permit(4'hf),.mirror(4'b0),
      .crq(su_rq),.crq_credit(su_rc),.crr(su_rr),.cwq(su_wq),.cwq_credit(su_wc),.cwq_done(su_done),
      .peer_rq(544'b0),.peer_rq_credit(),.peer_rr(),.peer_wq(8992'b0),.peer_wq_credit(),.peer_wq_done(),
      .dma_q(native_dq),.dma_done(native_done),.fault(vehicle_fault),.bank_status(bank_status));
    reg [3:0] stgo=0,drgo=0;wire [3:0] stdn,drdn,su_ov;
    reg [23:0] su_lo=0,su_hi=65535;
    reg [3:0] st_seen=0,dr_seen=0;integer read_mode=0;
    integer read_count[0:3];integer contention=0;integer scratch_checks=0;
    function automatic [255:0] seed(input integer q,input integer sec);
      for(integer w=0;w<8;w++)seed[w*32+:32]=32'hA5A5_0000+(q<<16)+sec*8+w;
    endfunction
    for(genvar q=0;q<4;q++)begin:su
      wire [7:0] sv,drv;wire [103:0] ss,ds;wire [2047:0] sd;
      reg [7:0] drvalid=0;reg [2047:0] drdata=0;reg [63:0] drm=0;
      ot_hgi_su_ctlw_native_h #(.LWB(16),.LQ(10),.LQSRAM(1)) ctl(
        .clk(cclk[q]),.clk_p0(cclk[q]),.clk_p1(cclk[q]),.clk_p2(cclk[q]),.clk_p3(cclk[q]),.rst_n(rst_n),
        .wst_go_i(stgo[q]),.wdr_go_i(drgo[q]),.lo_i({120'b0,su_lo}),.hi_i({120'b0,su_hi}),.lb_i(102'b0),.rv_i(6'b1),.dsec_i(126'b0),
        .d_lo_i({24'b0,su_lo}),.d_hi_i({24'b0,su_hi}),.d_lb_i({17'b0,17'(su_lo)}),.d_rv_i(2'b01),.d_dsec_i(42'b0),.d_os_i(1'b0),.sl_i(2'(q)),
        .wst_go_o(),.wdr_go_o(),.d_os_o(),.lo_o(),.hi_o(),.lb_o(),.rv_o(),.dsec_o(),.d_lo_o(),.d_hi_o(),.d_lb_o(),.d_rv_o(),.d_dsec_o(),
        .wst_dn_i(1'b1),.wdr_dn_i(1'b1),.ovf_i(1'b0),
        .wrq(su_rq[q*128+:128]),.wrq_cr(su_rc[q*8+:8]),.wrr(su_rr[q*2056+:2056]),
        .wwq(su_wq[q*2240+:2240]),.wwq_cr(su_wc[q*8+:8]),.wwq_done(su_done[q*8+:8]),
        .lsw_v(sv),.lsw_sec(ss),.lsw_d(sd),.ldc_v(),.ldc_sec(),.ldr_v(drv),.ldr_sec(ds),
        .ldr_d(drdata),.ldr_dm(drm),.ldr_rv(drvalid),.wst_dn(stdn[q]),.wdr_dn(drdn[q]),.ovf(su_ov[q]));
      initial read_count[q]=0;
      always @(posedge cclk[q])if(rst_n)begin
        if(stgo[q])st_seen[q]<=0;else if(!stdn[q])st_seen[q]<=1;
        if(drgo[q])dr_seen[q]<=0;else if(!drdn[q])dr_seen[q]<=1;
        drvalid<=drv;
        for(integer b=0;b<8;b++)begin
          drdata[b*256+:256]<=seed(q,int'(ds[b*13+:13]));drm[b*8+:8]<=8'hff;
          if(sv[b])begin
            integer sec;sec=int'(ss[b*13+:13]);
            if(sec%8!=b)$fatal(1,"FATAL actual SU bank/sector q%0d b%0d sec%0d",q,b,sec);
            read_count[q]=read_count[q]+1;
            if(read_mode==1)begin
              if(sd[b*256+:256]!==seed(q,sec))$fatal(1,"FATAL actual contention SU read q%0d sec%0d",q,sec);
              scratch_checks=scratch_checks+1;
            end else if(read_mode==2)
              for(integer w=0;w<8;w++)vm[(q<<16)+sec*8+w]=sd[b*256+w*32+:32];
          end
        end
      end
      for(genvar b=0;b<8;b++)begin:observe
        always @(posedge vmclk)if(rst_n && vehicle.quad[q].vm.g_bank[b].u_bank.dma_v && vehicle.quad[q].vm.g_bank[b].u_bank.wqn[0]!=0)contention=contention+1;
      end
    end
    always @(posedge vmclk)if(rst_n)begin
      if(qfault||rfault||lfault||vehicle_fault||bank_status||su_ov)
        $fatal(1,"FATAL actual native hardware queue%h router%h lease%h vehicle%h status%h su%h",qfault,rfault,lfault,vehicle_fault,bank_status,su_ov);
    end
    task automatic su_run(input integer mode,input integer first,input integer last,input bit wr,input bit rd);
      integer start;
      begin
        su_lo=24'(first);su_hi=24'(last);read_mode=mode;
        for(integer q=0;q<4;q++)read_count[q]=0;
        @(negedge clk);stgo=rd?4'hf:0;drgo=wr?4'hf:0;
        repeat(2)@(negedge clk);stgo=0;drgo=0;start=cyc;
        while((wr && (dr_seen!=4'hf||drdn!=4'hf)) || (rd && (st_seen!=4'hf||stdn!=4'hf||read_count[0]!=(last-first+1)/8||read_count[1]!=(last-first+1)/8||read_count[2]!=(last-first+1)/8||read_count[3]!=(last-first+1)/8)))begin
          @(negedge clk);if(cyc-start>100000)$fatal(1,"FATAL actual SU timeout mode%0d seen%h/%h done%h/%h count%0d/%0d/%0d/%0d",mode,st_seen,dr_seen,stdn,drdn,read_count[0],read_count[1],read_count[2],read_count[3]);
        end
      end
    endtask
    // ---- svc model: per stack a request queue; per lane a beat queue in idx order; credit 4 a lane
    integer rq_n [0:NS-1]; reg [49:0] rq [0:NS-1][0:63]; integer rq_h [0:NS-1];
    integer cr [0:NIN-1]; integer nxt [0:NS-1];               // next idx of the head request to schedule
    reg [269:0] lb [0:NIN-1][0:1023]; integer lh [0:NIN-1]; integer lt [0:NIN-1];
    // die-wire stages: data and credits each cross HOPS registers
    reg [NIN*270-1:0] dpipe [0:7]; reg [NIN-1:0] cpipe [0:7]; wire [NIN-1:0] cr_in;
    always @(posedge clk) begin dpipe[0] <= dd_m; cpipe[0] <= dd_cr; for (integer h = 1; h < 8; h = h + 1) begin dpipe[h] <= dpipe[h-1]; cpipe[h] <= cpipe[h-1]; end end
    assign dd = (HOPS == 0) ? dd_m : dpipe[HOPS-1];
    assign cr_in = (HOPS == 0) ? dd_cr : cpipe[HOPS-1];
    initial for (integer i = 0; i < NIN; i = i + 1) begin cr[i] = LD; lh[i] = 0; lt[i] = 0; end
    initial for (integer p = 0; p < NB; p = p + 1) rlow[p] = 0;
    integer tok [0:NS-1]; longint sched = 0;
    initial for (integer s = 0; s < NS; s = s + 1) begin tok[s] = 0; rq_n[s] = 0; rq_h[s] = 0; nxt[s] = 0; end
    always @(posedge clk) if (rst_n) begin
        dd_m <= 0;
        for (integer s = 0; s < NS; s = s + 1) begin
            dq_rdy[s] <= full || ($urandom % 4) != 0;
            if (dq[s*51 + 50] && dq_rdy[s]) begin rq[s][(rq_h[s] + rq_n[s]) % 64] = dq[s*51 +: 50]; rq_n[s] = rq_n[s] + 1; end
            // schedule up to 8 sectors of the head request into the lane queues (the svc reading its PCs)
            if (PCX4 != 0) tok[s] = (tok[s] + PCX4 > 4 * PCX4) ? 4 * PCX4 : tok[s] + PCX4;   // token bucket, 4 x sectors
            for (integer k = 0; k < NL && rq_n[s] > 0 && (PCX4 == 0 || tok[s] >= 4) && lt[s * NL + (nxt[s] % NL)] - lh[s * NL + (nxt[s] % NL)] < 512; k = k + 1) begin : sch
                reg [49:0] r; reg [255:0] sd; longint a; integer l;
                r = rq[s][rq_h[s] % 64];
                a = longint'(r[36:0]) + 32 * nxt[s];
                for (integer b = 0; b < 32; b = b + 1) sd[8*b +: 8] = hb(a + b);
                l = s * NL + (nxt[s] % NL); if (PCX4 != 0) tok[s] = tok[s] - 4; sched = sched + 1;
                lb[l][lt[l] % 1024] = {1'b1, 1'b0, r[49:46], 8'(nxt[s]), sd}; lt[l] = lt[l] + 1;
                nxt[s] = nxt[s] + 1;
                if (nxt[s] == int'(r[45:37])) begin nxt[s] = 0; rq_h[s] = rq_h[s] + 1; rq_n[s] = rq_n[s] - 1; end
            end
        end
        for (integer i = 0; i < NIN; i = i + 1) begin
            if (cr_in[i]) cr[i] = cr[i] + 1;
            if (lt[i] > lh[i] && cr[i] > 0 && (full || ($urandom % 5) != 0)) begin dd_m[i*270 +: 270] <= lb[i][lh[i] % 1024]; lh[i] = lh[i] + 1; cr[i] = cr[i] - 1; end
        end
    end
    // ---- reference decode
    // binary32 bits of an exactly representable normal / zero double (Verilator's $shortrealtobits is not reliable)
    function automatic [31:0] f32(input real v);
        reg [63:0] d;
        begin
            d = $realtobits(v);
            f32 = (d[62:0] == 63'd0) ? {d[63], 31'd0} : {d[63], 8'(d[62:52] - 11'd1023 + 11'd127), d[51:29]};
        end
    endfunction
    function automatic [31:0] e4(input [7:0] c);
        real v; integer e, m; reg [31:0] r;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 15 && m == 7) e4 = 32'h7FC00000;
            else begin
                v = (e == 0) ? (m / 8.0) * (2.0 ** -6) : (1.0 + m / 8.0) * (2.0 ** (e - 7));
                r = f32(v); r[31] = c[7];
                if (v == 0.0) r = {c[7], 31'd0};
                e4 = r;
            end
        end
    endfunction
    function automatic [31:0] i8(input [7:0] c); i8 = f32(real'($signed(c))); if (c == 0) i8 = 0; endfunction
    integer full = 0; initial full = $test$plusargs("FULL");     // +FULL: the svc model at its full rate (no gaps)
    integer errs = 0, cyc = 0, tbytes = 0, tcyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    task automatic load(input [2:0] f, input longint sbase, input longint sstr, input integer dbase, input integer dstr,
                        input integer m, input integer n);
        integer es, t0, o, i, e0, dma_cycles;bit dma_ok; longint a; reg [31:0] want;
        begin
            es = (f == 0 || f == 5) ? 4 : (f == 1) ? 2 : 1; e0 = errs;
            su_run(0,0,65535,1,0);
            mv = 0; mv[1:0] = 0; mv[4:2] = f; mv[44:5] = 40'(sbase); mv[76:45] = 32'(sstr); mv[92:77] = 1;
            mv[94:93] = 1; mv[97:95] = 0; mv[137:98] = 40'(dbase); mv[169:138] = 32'(dstr); mv[185:170] = 1;
            mv[205:186] = 20'(m); mv[226:206] = 21'(n);
            @(negedge clk); mv_v = 1; t0 = cyc; while (!mv_rdy) begin @(negedge clk); if (cyc - t0 > 50000) $fatal(1, "FATAL front never ready (previous load stuck)"); end @(negedge clk); mv_v = 0; t0 = cyc;begin_trace();
            fork
              begin
                while(!(|dma_valid))@(negedge clk);
                su_run(1,65472,65535,1,1);
              end
              begin
                while (!mv_done && !mv_fault && cyc - t0 < 50000) @(negedge clk);
                dma_cycles=cyc-t0;dma_ok=mv_done;hit(15);trace_on=0;
              end
            join
            if (!dma_ok) begin $display("FAIL load f %0d m %0d n %0d: done %0d fault %0d", f, m, n, mv_done, mv_fault); errs = errs + 1; end
            else begin
                tcyc = tcyc + dma_cycles;
                su_run(2,0,65535,0,1); tbytes = tbytes + m * n * 4;
                for (o = 0; o < m; o = o + 1) for (i = 0; i < n; i = i + 1) begin
                    a = sbase + o * sstr + i * es;
                    case (f)
                        1: want = {hb(a + 1), hb(a), 16'd0};
                        2: want = e4(hb(a));
                        4: want = i8(hb(a));
                        default: want = {hb(a + 3), hb(a + 2), hb(a + 1), hb(a)};
                    endcase
                    if (vm[dbase + o * dstr + i] !== want) begin
                        if (errs < 8) $display("FAIL f %0d row %0d elem %0d: vm %h want %h", f, o, i, vm[dbase + o * dstr + i], want);
                        errs = errs + 1;
                    end
                end
                begin : untouched
                    integer w, o2, hit, bad; bad = 0;
                    for (w = 0; w < VMW; w = w + 1) begin
                        hit = 0;
                        for (o2 = 0; o2 < m; o2 = o2 + 1) if (w >= dbase + o2 * dstr && w < dbase + o2 * dstr + n) hit = 1;
                        if (!hit && vm[w] !== 32'hA5A5_0000 + w) bad = bad + 1;
                    end
                    if (bad != 0) begin $display("FAIL f %0d: %0d words outside the destination changed", f, bad); errs = errs + 1; end
                end
                print_trace();print_profile();
                if (errs != e0) $display("  load f %0d: %0d errors", f, errs - e0);
                $display("LOAD f %0d m %0d n %0d: %0d cycles, %0.1f destination B / cycle, %0.1f source B / cycle = %0.1f %% of 3.80 TB/s at 1.2 GHz (3,166.7 B / cycle)",
                         f, m, n, dma_cycles, (m * n * 4.0) / dma_cycles, (m * n * es * 1.0) / dma_cycles, 100.0 * (m * n * es * 1.0) / dma_cycles / 3166.7);
            end
        end
    endtask
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        load(3'd4, 64'd4294967296, 64'd0, 0, 0, 1, 4096); // dispatch0
        load(3'd0, 64'd8594136608, 64'd0, 12544, 0, 1, 128); // dispatch3
        load(3'd1, 64'd17186160640, 64'd0, 156672, 0, 1, 1536); // dispatch7
        load(3'd1, 64'd17190358016, 64'd0, 156672, 0, 1, 4096); // dispatch26
        load(3'd1, 64'd17215532032, 64'd0, 156672, 0, 1, 6144); // dispatch30
        load(3'd1, 64'd17228127232, 64'd0, 156672, 0, 1, 4096); // dispatch35
        load(3'd1, 64'd17234444288, 64'd0, 156672, 0, 1, 1536); // dispatch39
        load(3'd1, 64'd17238641664, 64'd0, 156672, 0, 1, 4096); // dispatch58
        load(3'd1, 64'd17263815680, 64'd0, 156672, 0, 1, 6144); // dispatch62
        load(3'd1, 64'd17276410880, 64'd0, 156672, 0, 1, 4096); // dispatch67
        load(3'd1, 64'd17282727936, 64'd0, 156672, 0, 1, 1536); // dispatch71
        load(3'd1, 64'd17286925312, 64'd0, 156672, 0, 1, 4096); // dispatch90
        load(3'd1, 64'd17312099328, 64'd0, 156672, 0, 1, 6144); // dispatch94
        load(3'd1, 64'd17324694528, 64'd0, 156672, 0, 1, 4096); // dispatch99
        load(3'd1, 64'd17331011584, 64'd0, 156672, 0, 1, 1536); // dispatch103
        load(3'd1, 64'd17335208960, 64'd0, 156672, 0, 1, 4096); // dispatch122
        load(3'd1, 64'd17360382976, 64'd0, 156672, 0, 1, 6144); // dispatch126
        load(3'd1, 64'd17372978176, 64'd0, 156672, 0, 1, 4096); // dispatch131
        load(3'd1, 64'd17379295232, 64'd0, 156672, 0, 1, 1536); // dispatch135
        load(3'd1, 64'd17383492608, 64'd0, 156672, 0, 1, 4096); // dispatch154
        load(3'd1, 64'd17408666624, 64'd0, 156672, 0, 1, 6144); // dispatch158
        load(3'd1, 64'd17421261824, 64'd0, 156672, 0, 1, 4096); // dispatch163
        load(3'd1, 64'd17427578880, 64'd0, 156672, 0, 1, 1536); // dispatch167
        load(3'd1, 64'd17431776256, 64'd0, 156672, 0, 1, 4096); // dispatch186
        load(3'd1, 64'd17456950272, 64'd0, 156672, 0, 1, 6144); // dispatch190
        load(3'd1, 64'd17469545472, 64'd0, 156672, 0, 1, 4096); // dispatch195
        load(3'd1, 64'd17475862528, 64'd0, 156672, 0, 1, 1536); // dispatch199
        load(3'd1, 64'd17480059904, 64'd0, 156672, 0, 1, 4096); // dispatch218
        load(3'd1, 64'd17505233920, 64'd0, 156672, 0, 1, 6144); // dispatch222
        load(3'd1, 64'd17517829120, 64'd0, 156672, 0, 1, 4096); // dispatch227
        load(3'd1, 64'd17524146176, 64'd0, 156672, 0, 1, 1536); // dispatch231
        load(3'd1, 64'd17528343552, 64'd0, 156672, 0, 1, 4096); // dispatch250
        load(3'd1, 64'd17553517568, 64'd0, 156672, 0, 1, 6144); // dispatch254
        load(3'd1, 64'd17566112768, 64'd0, 156672, 0, 1, 4096); // dispatch259
        load(3'd1, 64'd17572429824, 64'd0, 156672, 0, 1, 1536); // dispatch263
        load(3'd1, 64'd17576627200, 64'd0, 156672, 0, 1, 4096); // dispatch282
        load(3'd1, 64'd17601801216, 64'd0, 156672, 0, 1, 6144); // dispatch286
        load(3'd1, 64'd17614396416, 64'd0, 156672, 0, 1, 4096); // dispatch291
        load(3'd1, 64'd17620713472, 64'd0, 156672, 0, 1, 1536); // dispatch295
        load(3'd1, 64'd17624910848, 64'd0, 156672, 0, 1, 4096); // dispatch314
        load(3'd1, 64'd17650084864, 64'd0, 156672, 0, 1, 6144); // dispatch318
        load(3'd1, 64'd17662680064, 64'd0, 156672, 0, 1, 4096); // dispatch323
        load(3'd1, 64'd17668997120, 64'd0, 156672, 0, 1, 1536); // dispatch327
        load(3'd1, 64'd17673194496, 64'd0, 156672, 0, 1, 4096); // dispatch346
        load(3'd1, 64'd17698368512, 64'd0, 156672, 0, 1, 6144); // dispatch350
        load(3'd1, 64'd17710963712, 64'd0, 156672, 0, 1, 4096); // dispatch355
        load(3'd1, 64'd17717280768, 64'd0, 156672, 0, 1, 1536); // dispatch359
        load(3'd1, 64'd17721478144, 64'd0, 156672, 0, 1, 4096); // dispatch378
        load(3'd1, 64'd17746652160, 64'd0, 156672, 0, 1, 6144); // dispatch382
        load(3'd1, 64'd17759247360, 64'd0, 156672, 0, 1, 4096); // dispatch387
        load(3'd1, 64'd17765564416, 64'd0, 156672, 0, 1, 1536); // dispatch391
        load(3'd1, 64'd17769761792, 64'd0, 156672, 0, 1, 4096); // dispatch410
        load(3'd1, 64'd17794935808, 64'd0, 156672, 0, 1, 6144); // dispatch414
        load(3'd1, 64'd17807531008, 64'd0, 156672, 0, 1, 4096); // dispatch419
        load(3'd1, 64'd17813848064, 64'd0, 156672, 0, 1, 1536); // dispatch423
        load(3'd1, 64'd17818045440, 64'd0, 156672, 0, 1, 4096); // dispatch442
        load(3'd1, 64'd17843219456, 64'd0, 156672, 0, 1, 6144); // dispatch446
        load(3'd1, 64'd17855814656, 64'd0, 156672, 0, 1, 4096); // dispatch451
        load(3'd1, 64'd17862131712, 64'd0, 156672, 0, 1, 1536); // dispatch455
        load(3'd1, 64'd17866329088, 64'd0, 156672, 0, 1, 4096); // dispatch474
        load(3'd1, 64'd17891503104, 64'd0, 156672, 0, 1, 6144); // dispatch478
        load(3'd1, 64'd17904098304, 64'd0, 156672, 0, 1, 4096); // dispatch483
        load(3'd1, 64'd17910415360, 64'd0, 156672, 0, 1, 1536); // dispatch487
        load(3'd1, 64'd17914612736, 64'd0, 156672, 0, 1, 4096); // dispatch506
        load(3'd1, 64'd17939786752, 64'd0, 156672, 0, 1, 6144); // dispatch510
        load(3'd1, 64'd17952381952, 64'd0, 156672, 0, 1, 4096); // dispatch515
        load(3'd1, 64'd17958699008, 64'd0, 156672, 0, 1, 1536); // dispatch519
        load(3'd1, 64'd17962896384, 64'd0, 156672, 0, 1, 4096); // dispatch538
        load(3'd1, 64'd17988070400, 64'd0, 156672, 0, 1, 6144); // dispatch542
        load(3'd1, 64'd18000665600, 64'd0, 156672, 0, 1, 4096); // dispatch547
        load(3'd1, 64'd18006982656, 64'd0, 156672, 0, 1, 1536); // dispatch551
        load(3'd1, 64'd18011180032, 64'd0, 156672, 0, 1, 4096); // dispatch570
        load(3'd1, 64'd18036354048, 64'd0, 156672, 0, 1, 6144); // dispatch574
        load(3'd1, 64'd18048949248, 64'd0, 156672, 0, 1, 4096); // dispatch579
        load(3'd1, 64'd18055266304, 64'd0, 156672, 0, 1, 1536); // dispatch583
        load(3'd1, 64'd18059463680, 64'd0, 156672, 0, 1, 4096); // dispatch602
        load(3'd1, 64'd18084637696, 64'd0, 156672, 0, 1, 6144); // dispatch606
        load(3'd1, 64'd18097232896, 64'd0, 156672, 0, 1, 4096); // dispatch611
        load(3'd1, 64'd18103549952, 64'd0, 156672, 0, 1, 1536); // dispatch615
        load(3'd1, 64'd18107747328, 64'd0, 156672, 0, 1, 4096); // dispatch634
        load(3'd1, 64'd18132921344, 64'd0, 156672, 0, 1, 6144); // dispatch638
        load(3'd1, 64'd18145516544, 64'd0, 156672, 0, 1, 4096); // dispatch643
        load(3'd1, 64'd18151833600, 64'd0, 156672, 0, 1, 1536); // dispatch647
        load(3'd1, 64'd18156030976, 64'd0, 156672, 0, 1, 4096); // dispatch666
        load(3'd1, 64'd18181204992, 64'd0, 156672, 0, 1, 6144); // dispatch670
        load(3'd1, 64'd18193800192, 64'd0, 156672, 0, 1, 4096); // dispatch675
        load(3'd1, 64'd18200117248, 64'd0, 156672, 0, 1, 1536); // dispatch679
        load(3'd1, 64'd18204314624, 64'd0, 156672, 0, 1, 4096); // dispatch698
        load(3'd1, 64'd18229488640, 64'd0, 156672, 0, 1, 6144); // dispatch702
        load(3'd1, 64'd18242083840, 64'd0, 156672, 0, 1, 4096); // dispatch707
        load(3'd1, 64'd18248400896, 64'd0, 156672, 0, 1, 1536); // dispatch711
        load(3'd1, 64'd18252598272, 64'd0, 156672, 0, 1, 4096); // dispatch730
        load(3'd1, 64'd18277772288, 64'd0, 156672, 0, 1, 6144); // dispatch734
        load(3'd1, 64'd18290367488, 64'd0, 156672, 0, 1, 4096); // dispatch739
        load(3'd1, 64'd18296684544, 64'd0, 156672, 0, 1, 1536); // dispatch743
        load(3'd1, 64'd18300881920, 64'd0, 156672, 0, 1, 4096); // dispatch762
        load(3'd1, 64'd18326055936, 64'd0, 156672, 0, 1, 6144); // dispatch766
        load(3'd1, 64'd18338651136, 64'd0, 156672, 0, 1, 4096); // dispatch771
        load(3'd1, 64'd18344968192, 64'd0, 156672, 0, 1, 1536); // dispatch775
        load(3'd1, 64'd18349165568, 64'd0, 156672, 0, 1, 4096); // dispatch794
        load(3'd1, 64'd18374339584, 64'd0, 156672, 0, 1, 6144); // dispatch798
        load(3'd1, 64'd18386934784, 64'd0, 156672, 0, 1, 4096); // dispatch803
        load(3'd1, 64'd18393251840, 64'd0, 156672, 0, 1, 1536); // dispatch807
        load(3'd1, 64'd18397449216, 64'd0, 156672, 0, 1, 4096); // dispatch826
        load(3'd1, 64'd18422623232, 64'd0, 156672, 0, 1, 6144); // dispatch830
        load(3'd1, 64'd18435218432, 64'd0, 156672, 0, 1, 4096); // dispatch835
        load(3'd1, 64'd18441535488, 64'd0, 156672, 0, 1, 1536); // dispatch839
        load(3'd1, 64'd18445732864, 64'd0, 156672, 0, 1, 4096); // dispatch858
        load(3'd1, 64'd18470906880, 64'd0, 156672, 0, 1, 6144); // dispatch862
        load(3'd1, 64'd18483502080, 64'd0, 156672, 0, 1, 4096); // dispatch867
        load(3'd1, 64'd18489819136, 64'd0, 156672, 0, 1, 1536); // dispatch871
        load(3'd1, 64'd18494016512, 64'd0, 156672, 0, 1, 4096); // dispatch890
        load(3'd1, 64'd18519190528, 64'd0, 156672, 0, 1, 6144); // dispatch894
        load(3'd1, 64'd18531785728, 64'd0, 156672, 0, 1, 4096); // dispatch899
        load(3'd1, 64'd18538102784, 64'd0, 156672, 0, 1, 1536); // dispatch903
        load(3'd1, 64'd18542300160, 64'd0, 156672, 0, 1, 4096); // dispatch922
        load(3'd1, 64'd18567474176, 64'd0, 156672, 0, 1, 6144); // dispatch926
        load(3'd1, 64'd18580069376, 64'd0, 156672, 0, 1, 4096); // dispatch931
        load(3'd1, 64'd18586386432, 64'd0, 156672, 0, 1, 1536); // dispatch935
        load(3'd1, 64'd18590583808, 64'd0, 156672, 0, 1, 4096); // dispatch954
        load(3'd1, 64'd18615757824, 64'd0, 156672, 0, 1, 6144); // dispatch958
        load(3'd1, 64'd18628353024, 64'd0, 156672, 0, 1, 4096); // dispatch963
        load(3'd1, 64'd18634670080, 64'd0, 156672, 0, 1, 1536); // dispatch967
        load(3'd1, 64'd18638867456, 64'd0, 156672, 0, 1, 4096); // dispatch986
        load(3'd1, 64'd18664041472, 64'd0, 156672, 0, 1, 6144); // dispatch990
        load(3'd1, 64'd18676636672, 64'd0, 156672, 0, 1, 4096); // dispatch995
        load(3'd1, 64'd18682953728, 64'd0, 156672, 0, 1, 1536); // dispatch999
        load(3'd1, 64'd18687151104, 64'd0, 156672, 0, 1, 4096); // dispatch1018
        load(3'd1, 64'd18712325120, 64'd0, 156672, 0, 1, 6144); // dispatch1022
        load(3'd1, 64'd18724920320, 64'd0, 156672, 0, 1, 4096); // dispatch1027
        load(3'd1, 64'd18731237376, 64'd0, 156672, 0, 1, 1536); // dispatch1031
        load(3'd1, 64'd18735434752, 64'd0, 156672, 0, 1, 4096); // dispatch1050
        load(3'd1, 64'd18760608768, 64'd0, 156672, 0, 1, 6144); // dispatch1054
        load(3'd1, 64'd18773203968, 64'd0, 156672, 0, 1, 4096); // dispatch1059
        load(3'd1, 64'd18779521024, 64'd0, 156672, 0, 1, 1536); // dispatch1063
        load(3'd1, 64'd18783718400, 64'd0, 156672, 0, 1, 4096); // dispatch1082
        load(3'd1, 64'd18808892416, 64'd0, 156672, 0, 1, 6144); // dispatch1086
        load(3'd1, 64'd18821487616, 64'd0, 156672, 0, 1, 4096); // dispatch1091
        load(3'd1, 64'd18827804672, 64'd0, 156672, 0, 1, 1536); // dispatch1095
        load(3'd1, 64'd18832002048, 64'd0, 156672, 0, 1, 4096); // dispatch1114
        load(3'd1, 64'd18857176064, 64'd0, 156672, 0, 1, 6144); // dispatch1118
        load(3'd1, 64'd18869771264, 64'd0, 156672, 0, 1, 4096); // dispatch1123
        load(3'd1, 64'd18876088320, 64'd0, 156672, 0, 1, 1536); // dispatch1127
        load(3'd1, 64'd18880285696, 64'd0, 156672, 0, 1, 4096); // dispatch1146
        load(3'd1, 64'd18905459712, 64'd0, 156672, 0, 1, 6144); // dispatch1150
        load(3'd1, 64'd18918054912, 64'd0, 156672, 0, 1, 4096); // dispatch1155
        load(3'd1, 64'd13040484352, 64'd0, 80640, 0, 1, 37984); // dispatch1158
        if (errs != 0) $fatal(1,"FATAL QWEN_LOAD errors=%0d",errs);
        if(contention==0||scratch_checks!=147*32)$fatal(1,"FATAL actual contention missing cycles%0d scratch%0d",contention,scratch_checks);
        $display("ACTUAL_VM4 phase=%0d contention=%0d SU_scratch_sectors=%0d",PHASE,contention,scratch_checks);
        $display("PASS QWEN_VM4_LOAD records=147 bytes=%0d cycles=%0d price=15674.320143998 ratio=%0.9f",tbytes,tcyc,tcyc/15674.320143998484);
        if($test$plusargs("CHECK_PRICE") && tcyc>1.10*15674.320143998484)
          $fatal(1,"FATAL QWEN_VM4_PRICE cycles=%0d immutable_price=15674.320143998 bound=1.10 ratio=%0.9f",tcyc,tcyc/15674.320143998484);
        $finish;
    end
endmodule
