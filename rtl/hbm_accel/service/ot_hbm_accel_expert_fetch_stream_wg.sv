// ADDITIVE Opt4 candidate, not r2 qualification. WG=0 delegates byte-identical
// legacy LA. WG=1 cfg_lines holds W2-only per-SM line counts; cfg_lut maps the
// 136 W2 lines (original W2 permutation). GU 256 lines go to router slot k.
// Full GU consumes 255 source lines plus its pad; gearbox drops pad explicitly.
`timescale 1ps/1fs
// HA4 R5a-LA (HBM accelerator): the routed-expert fetch path of one HBM3E stack at full stack
// bandwidth.  Successor of ot_hbm_accel_expert_fetch_stream (R5a); default-off (ENABLE=0 ties every
// output to zero); nothing pinned instantiates it.  The SM-side contract is R5a's: per-SM staging
// ring, at most LAND sectors landed per SM per cycle with a rotating PC priority, in-order release
// of whole 128-B lines (s_valid/s_ready), lines of the k-th expert of a task in staging slot
// (task * TOPK + k) * lines + line, so every SM releases exactly R5a's byte sequence.
//
// R5a measured 0.395 TB/s of the 1.0 TB/s stack (results/rtl/hbm_accel_ha4_20261004): every expert
// sat in bank set 0, so each (expert, PC) descriptor of 49 sectors re-closed and re-opened the same
// four banks, and the 32-entry landing crossing could not cover the ~40-cycle credit round trip.
// R5a-LA changes five things, none of which touches a byte:
//  1. LAYOUT (load-time placement): expert e sits in bank set e mod NSETS at row ROW_BASE + e div
//     NSETS (NSETS = 7 leaves set 7 empty as the refresh parking set).  Within the set, PC-local
//     sector j -> BG j[1:0] ^ {e[0], 0}, column j[6:2] (the R5a map with a BG swizzle by id parity).
//  2. Sequencers with a one-deep descriptor lookahead (ot_hbm_accel_expert_stream_pc_la): the next
//     expert's banks open while the current expert streams; the switch costs no cycle.
//  3. FETCH ORDER: the dispatcher streams the router's first expert first, then, among the arrived
//     experts, the earliest one whose set (and, once all ids are in, BG swizzle id[0]) differs from
//     the previous one (an expert whose set equals
//     the previous one's is taken only when no other is available and all TOPK ids are in, or the
//     id queue is empty).  Each descriptor carries its router index k as a tag through a per-PC tag
//     queue to the landing crossing, so the slot (hence the release order) is the router order.
//  4. Landing crossings are 2**LAW deep (64): the credit round trip (PHY + CL + response + two
//     synchronisers each way) exceeds 32 cycles.
//  3a. PICK (default 2): PICK 2 keeps the router order except where that would force two same-set
//     experts to be adjacent later (a feasibility test on the remaining sets); PICK 1: after the router's first, the expert taken next is the one whose set has the
//     most unpicked experts left (among sets differing from the previous one), once all TOPK ids are
//     in; the greedy earliest-first order (PICK 0) left same-set pairs for the end.
//  5. REPICK (default 1): a REFpb's bank is latched LEAD (48) cycles before it is due, usually before
//     the later router ids (hence `prot`) arrive; the sequencer moves a pending REFpb off a bank that
//     has become protected onto a closed unprotected one.  Without it one REFpb in each routed
//     window landed on a needed set and stalled that PC for tRFCpb (200 ns).
// `prot` (sets of the task's experts) and `notice` keep refresh off the sets the task needs.
module ot_hbm_accel_expert_fetch_stream_wg #(
  parameter integer WG = 0,
  parameter integer ENABLE = 0, REF_MODE = 1, PHASE = 0,
  parameter integer NSM = 8, NPC = 32, NSECT = 49, IW = 9, ROW_BASE = 0,
  parameter integer DEPTH = 512, LAND = 4, MAXL = 64,
  parameter integer TOPK = 6, NSETS = 7, LAW = 6, PICK = 2, REPICK = 1, RESERVE = 1, PULL = 0, TAILPULL = 12,
  parameter integer PCPROT = 0, STEER = 0, NWIN = 0,
  parameter [7:0]   NOTICE_PROT = 8'h7F
)(
  input  wire               clk, hclk, rst_n, hrst_n,
  input  wire [NSM*16-1:0]  cfg_lines,
  input  wire [NSECT*NPC/4*16-1:0] cfg_lut,
  input  wire               e_valid, output wire e_ready, input wire [IW-1:0] e_id,
  input  wire               notice,
  output wire [NPC-1:0]     row_v, output wire [NPC*3-1:0] row_op, output wire [NPC*5-1:0] row_bank,
  output wire [NPC*19-1:0]  row_row,
  output wire [NPC-1:0]     col_v, output wire [NPC*5-1:0] col_bank, output wire [NPC*5-1:0] col_col,
  input  wire [NPC-1:0]     rd_v, input wire [NPC*256-1:0] rd_data,
  output wire [NSM-1:0]     s_valid, input wire [NSM-1:0] s_ready, output wire [NSM*1024-1:0] s_data,
  output wire               fault
);
  generate if (!WG) begin : legacy
    ot_hbm_accel_expert_fetch_stream_la #(.ENABLE(ENABLE),.REF_MODE(REF_MODE),.PHASE(PHASE),.NSM(NSM),.NPC(NPC),.NSECT(NSECT),.IW(IW),.ROW_BASE(ROW_BASE),.DEPTH(DEPTH),.LAND(LAND),.MAXL(MAXL),.TOPK(TOPK),.NSETS(NSETS),.LAW(LAW),.PICK(PICK),.REPICK(REPICK),.RESERVE(RESERVE),.PULL(PULL),.TAILPULL(TAILPULL),.PCPROT(PCPROT),.STEER(STEER),.NWIN(NWIN),.NOTICE_PROT(NOTICE_PROT)) u (.*);
  end else if (!ENABLE) begin : off
    assign e_ready = 0; assign row_v = 0; assign row_op = 0; assign row_bank = 0; assign row_row = 0;
    assign col_v = 0; assign col_bank = 0; assign col_col = 0; assign s_valid = 0; assign s_data = 0;
    assign fault = 0;
  end else begin : on
    localparam integer NLINE = NSECT * NPC / 4;
    localparam integer SW = $clog2(DEPTH);
    localparam integer MW = (NSM > 1) ? $clog2(NSM) : 1;
    localparam integer PERIOD = REF_MODE ? 118 : 3808;
    localparam integer JW = $clog2(NSECT + 1);
    function automatic [2:0] set_of(input [IW-1:0] id);  set_of = 3'(id % NSETS); endfunction
    function automatic [18:0] row_of(input [IW-1:0] id); row_of = 19'(ROW_BASE) + 19'(id / NSETS); endfunction
    // ---------------- ids: clk -> hclk ----------------
    wire id_full, id_empty; wire [IW-1:0] id_q; wire id_pop;
    ot_hbm_accel_cdc_fifo #(.W(IW), .AW(3)) u_ids (
      .wclk(clk), .wrst_n(rst_n), .we(e_valid), .wdata(e_id), .full(id_full), .rd_freed(),
      .rclk(hclk), .rrst_n(hrst_n), .re(id_pop), .rdata(id_q), .empty(id_empty));
    assign e_ready = !id_full;
    // ---------------- dispatch (hclk): arrival table, fetch order, one descriptor per (expert, PC) --
    reg [IW-1:0] tab [0:7]; reg [2:0] tset [0:7]; reg [3:0] cnt;
    reg [2:0] ord [0:41]; reg [5:0] j0s [0:41]; reg [5:0] ns [0:41]; reg keeps [0:41];
    reg [5:0] oc; reg [7:0] prot; reg plan_started,id_fault,retire_toggle;
    wire [NPC-1:0] tag_room,tq_empty;
    wire task_consumed;
    reg consumed_h1,consumed_h2,ack_h1,ack_h2;
    reg rearm_c1,rearm_c2,rearm_seen;
    always @(posedge hclk or negedge hrst_n)
      if (!hrst_n) begin consumed_h1<=0;consumed_h2<=0;ack_h1<=0;ack_h2<=0;end
      else begin consumed_h1<=task_consumed;consumed_h2<=consumed_h1;ack_h1<=rearm_seen;ack_h2<=ack_h1;end
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin rearm_c1<=0;rearm_c2<=0;end
      else begin rearm_c1<=retire_toggle;rearm_c2<=rearm_c1;end
    reg [5:0] ptr [0:NPC-1];
    wire [NPC-1:0] pc_r, pc_busy, pc_fault, dv; wire [NPC-1:0] all_done_v;
    for (genvar p = 0; p < NPC; p = p + 1) begin : dsp
      assign dv[p] = (6'(ptr[p]) < oc) && tag_room[p] && !id_fault;
      assign all_done_v[p] = (ptr[p] == oc) && !pc_busy[p];
    end
    wire [53:0] held_ids;
    for(genvar k=0;k<6;k=k+1) assign held_ids[k*9+:9]=tab[k];
    wire sched_ready,sched_v,sched_busy,sched_fault,sched_keep,sched_last;
    wire [2:0] sched_k; wire [5:0] sched_j0,sched_n;
    wire sched_start=(cnt==6)&&!plan_started&&!id_fault;
    ot_hbm_accel_wg_dispatch #(.ENABLE(1)) u_schedule (
      .clk(hclk),.rst_n(hrst_n),.task_valid(sched_start),.ids(held_ids),.task_ready(sched_ready),
      .desc_valid(sched_v),.desc_ready(oc<42),.desc_slot(sched_k),.desc_j0(sched_j0),.desc_n(sched_n),
      .desc_keep(sched_keep),.desc_last(sched_last),.busy(sched_busy),.fault(sched_fault));
    wire retire=(cnt==6)&&(oc==42)&&(&all_done_v)&&(&tq_empty)&&(&l_empty)&&consumed_h2;
    assign id_pop=!id_empty&&(cnt<6)&&!retire&&!id_fault&&(ack_h2==retire_toggle);
    reg id_legal;
    always @* begin
      id_legal=(id_q<384);
      if(cnt!=0 && id_q<=tab[cnt-1]) id_legal=0;
    end
    always @(posedge hclk or negedge hrst_n)
      if(!hrst_n) begin cnt<=0;oc<=0;prot<=0;plan_started<=0;id_fault<=0;retire_toggle<=0;
        for(integer p=0;p<NPC;p=p+1) ptr[p]<=0;
      end else begin
        if(retire) begin cnt<=0;oc<=0;prot<=0;plan_started<=0;retire_toggle<=!retire_toggle;
          for(integer p=0;p<NPC;p=p+1) ptr[p]<=0;
        end else begin
          if(id_pop) begin
            if(!id_legal) id_fault<=1;
            else begin tab[cnt[2:0]]<=id_q;tset[cnt[2:0]]<=set_of(id_q);cnt<=cnt+1'b1;
              prot<=prot|(8'b1<<set_of(id_q));end
          end
          if(sched_start&&sched_ready) plan_started<=1;
          if(sched_v&&oc<42) begin ord[oc]<=sched_k;j0s[oc]<=sched_j0;ns[oc]<=sched_n;keeps[oc]<=sched_keep;oc<=oc+1'b1;end
          for(integer p=0;p<NPC;p=p+1) if(dv[p]&&pc_r[p]) ptr[p]<=ptr[p]+1'b1;
        end
      end
    // ---------------- 32 stream sequencers (hclk), tag queues and landing crossings ----------------
    wire [NPC*3-1:0] cred_ret;
    wire [NPC-1:0] l_empty, l_full, l_re; wire [NPC*265-1:0] l_q;
    reg  land_fault;
    for (genvar p = 0; p < NPC; p = p + 1) begin : pc
      wire [2:0] dk = (6'(ptr[p])<oc) ? ord[ptr[p]] : 3'b0;
      wire [5:0] dj0=j0s[ptr[p]], dn=ns[ptr[p]];
      wire [IW-1:0] did = tab[dk];
      ot_hbm_accel_expert_stream_pc_wg #(.ENABLE(1), .REF_MODE(REF_MODE), .PC(p), .CRED(1 << LAW),
        .REF_PHASE((PHASE + (p * PERIOD) / 32) % PERIOD), .NOTICE_PROT(NOTICE_PROT), .REPICK(REPICK), .RESERVE(RESERVE), .PULL(PULL), .TAILPULL(TAILPULL), .STEER(STEER), .NWIN(NWIN)) u (
        .clk(hclk), .rst_n(hrst_n), .desc_v(dv[p]), .desc_r(pc_r[p]),
        .desc_row(row_of(did)), .desc_set(set_of(did)), .desc_bgx(did[0]), .desc_n({5'b0,dn}),.desc_j0({5'b0,dj0}),.desc_keep(keeps[ptr[p]]),
        .go(1'b1), .next_posted(1'b0), .notice(notice), .prot(prot),
        .row_v(row_v[p]), .row_prio(), .row_gnt(1'b1),
        .row_op(row_op[p*3 +: 3]), .row_bank(row_bank[p*5 +: 5]), .row_row(row_row[p*19 +: 19]),
        .col_v(col_v[p]), .col_bank(col_bank[p*5 +: 5]), .col_col(col_col[p*5 +: 5]),
        .cred_ret(cred_ret[p*3 +: 3]), .busy(pc_busy[p]), .ref_fault(pc_fault[p]));
      // At least ceil(CRED/8)+two sequencer seats: 16 tags. Accepted
      // descriptors are retained until ALL of their ordered sector returns.
      reg [5:0] tq [0:15]; reg [4:0] tq_w,tq_r;reg [5:0] rcnt;reg tq_fault;
      wire [2:0] rslot=tq[tq_r[3:0]][5:3];
      wire [5:0] rj0={tq[tq_r[3:0]][2:0],3'b0};
      wire [5:0] rj=rj0+rcnt;
      wire tq_push=dv[p]&&pc_r[p]&&!retire;
      wire tq_pop=rd_v[p]&&(rcnt==(rj0==48?6'd0:6'd7));
      assign tag_room[p]=(tq_w-tq_r)<16;
      assign tq_empty[p]=(tq_w==tq_r);
      always @(posedge hclk or negedge hrst_n)
        if(!hrst_n) begin tq_w<=0;tq_r<=0;rcnt<=0;tq_fault<=0;end
        else begin
          if(tq_push) begin tq[tq_w[3:0]]<={dk,dj0[5:3]};tq_w<=tq_w+1'b1;end
          if(rd_v[p]) rcnt<=tq_pop?0:rcnt+1'b1;
          if(tq_pop) tq_r<=tq_r+1'b1;
          if((tq_push&&!tag_room[p])||(rd_v[p]&&tq_empty[p])) tq_fault<=1;
        end
      ot_hbm_accel_cdc_fifo #(.W(265),.AW(LAW)) u_land (
        .wclk(hclk),.wrst_n(hrst_n),.we(rd_v[p]),.wdata({rslot,rj,rd_data[p*256+:256]}),
        .full(l_full[p]),.rd_freed(cred_ret[p*3+:3]),
        .rclk(clk),.rrst_n(rst_n),.re(l_re[p]),.rdata(l_q[p*265+:265]),.empty(l_empty[p]));
    end
    wire [NPC-1:0] tqf; for (genvar p = 0; p < NPC; p = p + 1) begin : tqfo assign tqf[p] = pc[p].tq_fault; end
    always @(posedge hclk or negedge hrst_n)
      if (!hrst_n) land_fault <= 0; else if (|(rd_v & l_full) || |tqf) land_fault <= 1;
    // ---------------- landing (clk): sector -> (SM, slot, quarter), <= LAND a SM a cycle ----------------
    reg [$clog2(NPC)-1:0] prio;
    reg [3:0] mask [0:NSM-1][0:DEPTH-1];
    reg [255:0] ring [0:NSM-1][0:3][0:DEPTH-1];
    reg [7:0] gu_p [0:NSM-1];reg [2:0] w2_k[0:NSM-1];reg [4:0] w2_p[0:NSM-1];reg [1:0] out_phase[0:NSM-1];
    reg [NPC-1:0] re_c; reg [MW-1:0] l_sm [0:NPC-1]; reg [SW-1:0] l_slot [0:NPC-1]; reg [1:0] l_qt [0:NPC-1];
    integer nland [0:NSM-1];
    always @* begin
      re_c = 0;
      for (integer m = 0; m < NSM; m = m + 1) nland[m] = 0;
      for (integer pp = 0; pp < NPC; pp = pp + 1) begin
        automatic integer p = (prio + pp) % NPC;
        automatic integer s = int'(l_q[p*265+256+:6])*NPC+p;
        automatic integer L = s >> 2;
        automatic bit gu = L<256;
        automatic integer kk = int'(l_q[p*265+262+:3]);
        automatic integer sm = gu ? kk : int'(cfg_lut[(L-256)*16+8+:8]);
        automatic integer ln = gu ? L : int'(cfg_lut[(L-256)*16+:8]);
        l_sm[p] = MW'(sm); l_qt[p] = 2'(s & 3);
        l_slot[p] = SW'(gu ? ln : (256+kk*32+ln));
        if (!l_empty[p] && sm<NSM && ln<(gu?256:32) && nland[sm] < LAND) begin re_c[p] = 1; nland[sm] = nland[sm] + 1; end
      end
    end
    assign l_re = re_c;
    // ---------------- release (clk) ----------------
    wire [NSM-1:0] take;
    for (genvar m = 0; m < NSM; m = m + 1) begin : out
      wire [SW-1:0] cs=out_phase[m]==0?SW'(gu_p[m]):SW'(256+int'(w2_k[m])*32+int'(w2_p[m]));
      assign s_valid[m] = (out_phase[m]==0 || (out_phase[m]==1&&cfg_lines[m*16+:16]!=0)) && &mask[m][cs];
      assign s_data[m*1024 +: 1024] = {ring[m][3][cs], ring[m][2][cs], ring[m][1][cs], ring[m][0][cs]};
      assign take[m] = s_valid[m] && s_ready[m];
    end
    wire [NSM-1:0] drained;
    for(genvar m=0;m<NSM;m=m+1) assign drained[m]=(out_phase[m]==2);
    assign task_consumed=&drained;
    reg ring_fault;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin
        prio <= 0; ring_fault <= 0;
        rearm_seen<=0;
        for (integer m = 0; m < NSM; m = m + 1) begin
          gu_p[m]<=0;w2_k[m]<=0;w2_p[m]<=0;out_phase[m]<=m<TOPK?0:1; for (integer d = 0; d < DEPTH; d = d + 1) mask[m][d] <= 4'd0;
        end
      end else if(rearm_seen!=rearm_c2) begin
        rearm_seen<=rearm_c2;
        for(integer m=0;m<NSM;m=m+1) begin gu_p[m]<=0;w2_k[m]<=0;w2_p[m]<=0;out_phase[m]<=m<TOPK?0:1;end
      end else begin
        prio <= prio + 1'b1;
        for (integer m = 0; m < NSM; m = m + 1) if (take[m]) begin
          automatic integer cs;cs=out_phase[m]==0?int'(gu_p[m]):256+int'(w2_k[m])*32+int'(w2_p[m]);
          mask[m][cs]<=0;
          if(out_phase[m]==0) begin
            if(gu_p[m]==255) out_phase[m]<=1;else gu_p[m]<=gu_p[m]+1'b1;
          end else if(int'(w2_p[m])+1==int'(cfg_lines[m*16+:16])) begin
            w2_p[m]<=0;if(w2_k[m]==5) out_phase[m]<=2;else w2_k[m]<=w2_k[m]+1'b1;
          end else w2_p[m]<=w2_p[m]+1'b1;
        end
        for(integer m=0;m<NSM;m=m+1) if(out_phase[m]==1 && cfg_lines[m*16+:16]==0) begin
          if(w2_k[m]==5) out_phase[m]<=2;else w2_k[m]<=w2_k[m]+1'b1;
        end
        for (integer p = 0; p < NPC; p = p + 1) if (re_c[p]) begin
          if (mask[l_sm[p]][l_slot[p]][l_qt[p]]) ring_fault <= 1;
          ring[l_sm[p]][l_qt[p]][l_slot[p]] <= l_q[p*265 +: 256];
          mask[l_sm[p]][l_slot[p]][l_qt[p]] <= 1'b1;

        end
      end
    reg pf_s1, pf_s2;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin pf_s1 <= 0; pf_s2 <= 0; end else begin pf_s1 <= (|pc_fault) || land_fault || id_fault || sched_fault; pf_s2 <= pf_s1; end
    assign fault = pf_s2 || ring_fault;
  end endgenerate
endmodule
