`timescale 1ps/1fs
// HA4 R5a-LA bench: routed-expert fetch BANDWIDTH and first access on the lookahead stream path
// (ot_hbm_accel_expert_fetch_stream_la), refresh live.  Derived from tb_hbm_accel_expert_first_access
// (R5a): same DRAM checker, same SM-line data pattern and release check; the backing array uses the
// R5a-LA placement (expert e in bank set e mod NSETS, row e div NSETS).  Extra plusargs +id0..+id5
// (router order) and an extra BW line: first/last sector returned at the PHY, RD count.
//   top-6 ids (clk, 1.2 GHz) -> NoC -> ot_hbm_accel_expert_fetch_stream (id CDC, dispatch, 32
//   ot_hbm_accel_expert_stream_pc at CK/2 = 1.024 ns, landing CDC FIFOs, SM staging/release)
//   -> HBM3E behavioural device below.
// DRAM: per-PC bank/timing checker in picoseconds with the 52ce3e9c1 bench constants (Ramulator2
// HBM3 preset as in ot_hdc_hbm_model.sv, JESD238 tREFI 3.9 us / tRFC 350 ns, tRFCpb 200 ns from
// ot_hdc_v41x_idx_hbm.sv, tRREFD 8 ns assumed).  Every command is checked and refresh must never be
// overdue.  RD data returns PHY_CMD + CL + BL8 + RSP + NOC after the RD (PHY_CMD, RSP and NOC are
// ASSUMED path latencies, the same terms the c52 bench charged as REQ_PS/RSP_PS = 15 ns each way).
// Data: the backing array holds, at the stream location of (expert, line-order L, quarter), the
// c52 bench pattern of that SM line's c52 address; every released line is compared with it, so the
// SMs receive exactly the bytes ot_gpu_expert_fetch would deliver.
// Plusargs: +t_route_ps=<router top-6 time>  +notice_lead_ps=<0: no notice>  +mut=<negative control>
// Prints one FIRST line (times from top-6 out) and a verdict.
module tb_hbm_integrated_expert_pq;
  parameter integer REF_MODE = 1;
  parameter integer PHASE = 0;
  parameter integer HPHASE_PS = 0;           // hclk phase against clk
  parameter integer NOC_PS = 5000, PHY_CMD_PS = 5000;
  parameter integer NSETS = 7, LAW = 6, LANDP = 4, ORDER = 0, PICK = 2, REPICK = 1, RESERVE = 1, PULL = 0, TAILPULL = 12, PCPROT = 0, STEER = 0, NWIN = 0;   // ORDER 0: R5a line order; 1: rate-balanced
  integer MUT = 0;                           // +mut=1: corrupt one sector (negative control); 2: tRCD check +1 ns
  localparam integer NSM = 8, NPC = 32, NSECT = 49, NLINE = 392, NIDS = 6, ROW_BASE = 0;
  localparam integer CYC = 1024, CLK = 833;
  localparam longint BURST=1024, TCCDL=2560, CL=12500, RCD=19375, RP=16250, RAS=28125, RTP=5625,
    RRDS=2500, RRDL=3125, FAW=15000, RFC=350000, RFCPB=200000, REFI=3900000, RSP=10000, RREFD=8000;
  // c52 layout (results/rtl/w19_expert_fetch.json layout): lines and w1/w3 lines per SM, offsets
  localparam integer LINES [0:7] = '{10,10,0,0,29,29,29,29};
  localparam integer W13 [0:7]   = '{43, 43, 43, 43, 22, 22, 22, 22};
  localparam integer OFF [0:7]   = '{0, 53, 106, 149, 192, 242, 292, 342};
  localparam integer EXP_LINES = 392;

  reg clk = 0, hclk = 0, rst_n = 0, hrst_n = 0;
  always #416.5 clk = ~clk;
  initial begin #(HPHASE_PS); forever #(CYC/2) hclk = ~hclk; end

  // ---------------- static layout: line order L -> (sm, line); w1/w3 of every SM first ----------------
  integer lut_sm [0:NLINE-1], lut_ln [0:NLINE-1];
  reg [NLINE*16-1:0] cfg_lut; reg [NSM*16-1:0] cfg_lines;
  initial begin
    automatic integer L=0;
    // Actual complete W2 source tails, same row owners as W19. Legacy GU
    // seams are retained inside the final W2 line: no uniform17 assumption.
    for(int m=0;m<8;m++)for(int l=0;l<LINES[m];l++) begin lut_sm[L]=m;lut_ln[L]=l;L++;end
    if (L != 136) begin $display("LAYOUT ERROR %0d", L); $finish; end
    for (int l = 0; l < NLINE; l++) cfg_lut[l*16 +: 16] = {8'(lut_sm[l]), 8'(lut_ln[l])};
    for (int m = 0; m < NSM; m++) cfg_lines[m*16 +: 16] = 16'(LINES[m]);
  end
  function automatic [255:0] pat(input [31:0] s); pat = {8{s ^ 32'hA500_0000}}; endfunction

  // ---------------- DUT ----------------
  reg e_valid = 0; wire e_ready; reg [8:0] e_id = 0; reg notice = 0;
  wire [NPC-1:0] row_v, col_v; wire [NPC*3-1:0] row_op; wire [NPC*5-1:0] row_bank, col_bank, col_col;
  wire [NPC*19-1:0] row_row; reg [NPC-1:0] rd_v = 0; reg [NPC*256-1:0] rd_data = 0;
  wire [NSM-1:0] s_valid; wire [NSM*1024-1:0] s_data; wire fault;
  ot_hbm_accel_expert_fetch_stream_wg #(.WG(1),.ENABLE(1), .REF_MODE(REF_MODE), .PHASE(PHASE), .NSETS(NSETS), .LAW(LAW), .LAND(LANDP), .PICK(PICK), .REPICK(REPICK), .RESERVE(RESERVE), .PULL(PULL), .TAILPULL(TAILPULL), .PCPROT(PCPROT), .STEER(STEER), .NWIN(NWIN),
    .NOTICE_PROT(NSETS >= 8 ? 8'hFF : 8'((1 << NSETS) - 1))) dut (
    .clk(clk), .hclk(hclk), .rst_n(rst_n), .hrst_n(hrst_n), .cfg_lines(cfg_lines), .cfg_lut(cfg_lut),
    .e_valid(e_valid), .e_ready(e_ready), .e_id(e_id), .notice(notice),
    .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row),
    .col_v(col_v), .col_bank(col_bank), .col_col(col_col), .rd_v(rd_v), .rd_data(rd_data),
    .s_valid(s_valid), .s_ready(source_ready), .s_data(s_data), .fault(fault));

  // ---------------- backing array: [pc][bank][row][col] ----------------
  bit [255:0] mem [longint];
  function automatic longint midx(input integer pc, bk, rw, col); midx = ((longint'(pc) * 32 + bk) * 65536 + rw) * 32 + col; endfunction
  integer ids [0:NIDS-1] = '{61, 69, 112, 170, 299, 357};     // c52 bench golden router top-6 (ar_L0)

  // ---------------- DRAM checker (ps) ----------------
  longint now;
  bit     b_open [0:31][0:31]; int b_row [0:31][0:31];
  longint b_act [0:31][0:31], b_pre [0:31][0:31], b_rd [0:31][0:31], b_ref_end [0:31][0:31];
  longint p_last_act [0:31], p_last_rd [0:31], p_last_ref [0:31], p_last_refpb_any [0:31];
  longint p_act_bg [0:31][0:3], p_rd_bg [0:31][0:3], p_faw [0:31][0:3];
  bit [31:0] p_round [0:31];
  longint viol = 0, n_act = 0, n_rd = 0, n_ref = 0, n_ref_set0_window = 0;
  longint rq_due [0:31][$]; bit [255:0] rq_dat [0:31][$];
  integer trace_pc = -1;
  longint pc_rd_first [0:31], pc_rd_last [0:31], pc_act [0:31][$];
  longint t_ret_first = -1, t_ret_last = -1, n_ret = 0, t_rd_first = -1, t_rd_last = -1;
  longint hcyc = 0, t_route = 0, notice_lead = 0, t_first_cmd = -1, ref_block_ps = 0;
  task automatic v(input string what, input integer pc, input integer bk);
    if (viol < 20) $display("VIOLATION t=%0d ps pc=%0d bank=%0d %s", now, pc, bk, what);
    viol++;
  endtask
  always @(posedge hclk) if (hrst_n) begin
    now = $time;
    if (hcyc == 0) for (int p = 0; p < 32; p++) p_last_ref[p] += now;
    for (int p = 0; p < 32; p++) begin
      if (row_v[p]) begin
        automatic int op = row_op[p*3 +: 3], bk = row_bank[p*5 +: 5], rw = row_row[p*19 +: 19], g = bk & 3;
        if (p == trace_pc) $display("T %0d pc=%0d ROW op=%0d bank=%0d row=%0d", (now - t_route) / CYC, p, op, bk, rw);
        case (op)
          1: begin
            n_act++;
            if (t_first_cmd < 0 && now >= t_route) t_first_cmd = now;
            if (b_open[p][bk]) v("ACT to open bank", p, bk);
            if (now < b_pre[p][bk] + RP) v("tRP", p, bk);
            if (now < b_act[p][bk] + RAS + RP) v("tRC", p, bk);
            if (now < p_last_act[p] + RRDS) v("tRRD_S", p, bk);
            if (now < p_act_bg[p][g] + RRDL) v("tRRD_L", p, bk);
            if (now < p_faw[p][0] + FAW) v("tFAW", p, bk);
            if (now < b_ref_end[p][bk]) v("ACT during refresh", p, bk);
            if (now < p_last_refpb_any[p] + RREFD) v("tRREFD", p, bk);
            b_open[p][bk] = 1; b_row[p][bk] = rw; b_act[p][bk] = now;
            p_last_act[p] = now; p_act_bg[p][g] = now;
            p_faw[p][0] = p_faw[p][1]; p_faw[p][1] = p_faw[p][2]; p_faw[p][2] = p_faw[p][3]; p_faw[p][3] = now;
          end
          0: begin
            if (!b_open[p][bk]) v("PRE closed bank", p, bk);
            if (now < b_act[p][bk] + RAS) v("tRAS", p, bk);
            if (now < b_rd[p][bk] + RTP) v("tRTP", p, bk);
            b_open[p][bk] = 0; b_pre[p][bk] = now;
          end
          5: for (int b = 0; b < 32; b++) if (b_open[p][b]) begin
            if (now < b_act[p][b] + RAS) v("tRAS (PREab)", p, b);
            if (now < b_rd[p][b] + RTP) v("tRTP (PREab)", p, b);
            b_open[p][b] = 0; b_pre[p][b] = now;
          end
          4: begin
            n_ref++;
            for (int b = 0; b < 32; b++) begin
              if (b_open[p][b]) v("REFab with open bank", p, b);
              if (now < b_pre[p][b] + RP) v("tRP (REFab)", p, b);
              if (now < b_ref_end[p][b]) v("REFab during refresh", p, b);
              b_ref_end[p][b] = now + RFC;
            end
            if (now - p_last_ref[p] > REFI) v("REFab late", p, 0);
            p_last_ref[p] = now;
          end
          6: begin
            n_ref++;
            if (b_open[p][bk]) v("REFpb to open bank", p, bk);
            if (now < b_pre[p][bk] + RP) v("tRP (REFpb)", p, bk);
            if (now < b_act[p][bk] + RAS + RP) v("tRC (REFpb)", p, bk);
            if (now < b_ref_end[p][bk]) v("REFpb during refresh", p, bk);
            if (now < p_last_act[p] + RREFD) v("tRREFD (REFpb after ACT)", p, bk);
            if (now < p_last_refpb_any[p] + RREFD) v("tRREFD (REFpb after REFpb)", p, bk);
            if (p_round[p][bk]) v("REFpb bank twice in one round", p, bk);
            p_round[p][bk] = 1; if (&p_round[p]) p_round[p] = 0;
            if (now - p_last_ref[p] > REFI / 32) v("REFpb late", p, bk);
            p_last_ref[p] = now; p_last_refpb_any[p] = now;
            b_ref_end[p][bk] = now + RFCPB;
          end
          default: v("unknown row op", p, bk);
        endcase
      end
      if (now - p_last_ref[p] > (REF_MODE ? REFI / 32 : REFI)) begin v("refresh overdue", p, 0); p_last_ref[p] = now; end
      if (col_v[p]) begin
        automatic int bk = col_bank[p*5 +: 5], cl = col_col[p*5 +: 5], g = bk & 3;
        if (p == trace_pc) $display("T %0d pc=%0d RD bank=%0d col=%0d", (now - t_route) / CYC, p, bk, cl);
        n_rd++; if (t_rd_first < 0) t_rd_first = now; t_rd_last = now;
        if (pc_rd_first[p] < 0) pc_rd_first[p] = now; pc_rd_last[p] = now;
        if (!b_open[p][bk]) v("RD closed bank", p, bk);
        if (now < b_act[p][bk] + RCD + (MUT == 2 ? 1000 : 0)) v("tRCD", p, bk);
        if (now < p_last_rd[p] + BURST) v("tCCD_S", p, bk);
        if (now < p_rd_bg[p][g] + TCCDL) v("tCCD_L", p, bk);
        if (now < b_ref_end[p][bk]) v("RD during refresh", p, bk);
        // a set-0 bank under refresh at the router time is the collision R5a removes
        p_last_rd[p] = now; p_rd_bg[p][g] = now; b_rd[p][bk] = now;
        rq_due[p].push_back(now + PHY_CMD_PS + CL + BURST + RSP + NOC_PS);
        rq_dat[p].push_back(mem.exists(midx(p, bk, b_row[p][bk], cl)) ? mem[midx(p, bk, b_row[p][bk], cl)] : '1);
      end
    end
    // returns: one sector per PC per hclk, in RD order
    for (int p = 0; p < 32; p++) begin
      if (rq_due[p].size() != 0 && rq_due[p][0] <= now) begin
        rd_v[p] <= 1; rd_data[p*256 +: 256] <= rq_dat[p].pop_front(); void'(rq_due[p].pop_front());
        if (t_ret_first < 0) t_ret_first = now; t_ret_last = now; n_ret++;
      end else rd_v[p] <= 0;
    end
    // set-0 refresh in progress at the router time (diagnostic)
    hcyc <= hcyc + 1;
  end

  // Six real GU streams are byte-unpacked, never compared with synthetic
  // weights. Inactive SMs and W2 retain the source-pattern transport control.
  reg [1023:0] gu_mem[0:1535];reg [1087:0] expected_sm[0:1727];
  reg [1023:0] w2_mem[0:815];reg [15:0] literal_w2_lut[0:135];
  localparam integer W2OFF[0:7]='{0,10,20,20,20,49,78,107};
  integer cnt[0:7],native_cnt[0:5];longint good=0,bad=0;
  longint t_first[0:5],t_gu[0:5],t_native_first[0:5],t_native_last[0:5],t_done[0:7];
  longint t_ids=-1;
  wire [7:0] source_ready;
  wire [5:0] gb_v,gb_r,gb_done,gb_fault;wire [6*1088-1:0] gb_data;
  for(genvar m=0;m<6;m=m+1) begin : gbox
    wire iv=s_valid[m]&&cnt[m]<256;
    ot_hbm_accel_wg_gearbox #(.ENABLE(1)) u (.clk(clk),.rst_n(rst_n),.start(1'b0),
      .in_valid(iv),.in_ready(gb_r[m]),.in_data(s_data[m*1024+:1024]),
      .out_valid(gb_v[m]),.out_ready(native_ready[m]),.out_data(gb_data[m*1088+:1088]),
      .done(gb_done[m]),.fault(gb_fault[m]));
    assign source_ready[m]=cnt[m]<256?gb_r[m]:1'b1;
  end
  assign source_ready[7:6]=2'b11;
  wire [5:0] native_ready;
  // Service-only scope: deterministic finite consumer. No SM numerical,
  // whole-token or physical-provider transfer from these accepted bytes.
  integer clk_edges=0;
  // Full NC8 production PQ/XMAP SM consumes the actual interleaved GU stream. The fixture's request-tag queue is the same
  // behavioural response bookkeeping as the retained SM bench; no hardware
  // provider/credit/area qualification is inferred from this testbench seat.
  integer selected=0;reg sm_start=0,sm_dv=0,sm_xwe=0;
  reg [6:0] sm_xaddr,sm_xgrp;reg [2047:0] sm_xdata;
  wire sm_busy,sm_dr,sm_req,sm_rv,sm_fault,sm_arrive,sm_released;
  wire [31:0] sm_addr;wire [9:0] sm_tag;wire [7:0] sm_row;wire [255:0] sm_data;
  reg sm_rsp=0;reg [9:0] sm_rsp_tag;reg [1087:0] sm_rsp_data;
  reg sm_release=0;integer req_seq=0,results=0;
  int unsigned pending_tags[$];
  reg [27263:0] xwords[0:23];
  longint start_edge=-1,done_edge=-1;
  reg [31:0] expected_gold[0:71];
  wire sm_start_ready;
  ot_hbm_accel_sm_pq #(.ENABLE(1),.PQ_ENABLE(1),.XMAP(1),.PACK_W2(1),.SUB(4),.LBS(2),.LSB(16),.NC(8),.RMAX(256),.LEV(4),.XD(128),.MAX_OUT(512)) sm (
    .clk(clk),.rst_n(rst_n),.start(sm_start),.start_ready(sm_start_ready),.op_xb(7'd0),.op_pack_w2(1'b0),.op_pack_delta_x(7'd0),.op_rows(9'd12),.op_c(16'd8),.op_g(8'd3),.op_gs(1'b1),.op_fmt(2'd2),
    .busy(sm_busy),.d_valid(sm_dv),.d_ready(sm_dr),.d_base(32'd0),.d_lines(24'd288),
    .req_v(sm_req),.req_ready(1'b1),.req_addr(sm_addr),.req_tag(sm_tag),
    .rsp_v(sm_rsp),.rsp_tag(sm_rsp_tag),.rsp_data(sm_rsp_data),
    .xw_en(sm_xwe),.xw_addr(sm_xaddr),.xw_grp(sm_xgrp),.xw_data(sm_xdata),
    .rv(sm_rv),.rrow(sm_row),.rdata(sm_data),.fault(sm_fault),.arrive(sm_arrive),.release_in(sm_release),.released(sm_released));
  for(genvar m=0;m<6;m=m+1) assign native_ready[m]=(int'(m)==selected)?(pending_tags.size()!=0):1'b1;
  always @(posedge clk) begin
    sm_release<=sm_arrive;sm_rsp<=0;
    if(rst_n) begin
      if(sm_req) begin
        if(sm_addr!=req_seq || req_seq>=288) $fatal(1,"SM request sequence/extent");
        pending_tags.push_back(int'(sm_tag));req_seq++;
      end
      if(gb_v[selected]&&native_ready[selected]) begin
        sm_rsp<=1;sm_rsp_tag<=10'(pending_tags.pop_front());sm_rsp_data<=gb_data[selected*1088+:1088];
      end
      if(sm_rv) begin
        if(sm_row>=12||sm_data[31:0]!==expected_gold[selected*12+int'(sm_row)]||sm_data[255:32]!=0)
          $fatal(1,"ACTUAL SM arithmetic mismatch row=%0d",sm_row);
        results++;
      end
      if(sm_fault) $fatal(1,"ACTUAL SM fault");
    end
  end
  initial begin
    wait(rst_n);
    @(negedge clk);sm_dv=1;
    @(posedge clk);while(!sm_dr)@(posedge clk);
    @(negedge clk);sm_dv=0;
    for(int a=0;a<24;a++)for(int g=0;g<2;g++)begin
      sm_xwe=1;sm_xaddr=7'(a);sm_xgrp=7'(g*4);sm_xdata=xwords[a][g*4*2048+:2048];@(negedge clk);
    end
    sm_xwe=0;@(negedge clk); // exact retained >=1 edge last x beat to start
    while($time<t_route)@(negedge clk);
    sm_start=1;start_edge=clk_edges;@(posedge clk);while(!sm_start_ready)@(posedge clk);@(negedge clk);sm_start=0;
    wait(sm_busy);wait(!sm_busy);@(negedge clk);done_edge=clk_edges;
  end

  always @(posedge clk)begin
   clk_edges<=clk_edges+1;
   if(rst_n)begin
    for(int m=0;m<6;m++)if(gb_v[m]&&native_ready[m])begin
     if(native_cnt[m]>=288||gb_data[m*1088+:1088]!==expected_sm[m*288+native_cnt[m]])
      $fatal(1,"GEARBOX source mismatch");
     if(native_cnt[m]==0)t_native_first[m]=$time;
     native_cnt[m]++;t_native_last[m]=$time;
    end
    if(|gb_fault)$fatal(1,"GEARBOX fault");
    for(int m=0;m<8;m++)if(s_valid[m]&&source_ready[m])begin
     if(m<6&&cnt[m]<256)begin
      if(s_data[m*1024+:1024]!==gu_mem[m*256+cnt[m]])$fatal(1,"GU sector mismatch");
      if(cnt[m]==0)t_first[m]=$time;if(cnt[m]==255)t_gu[m]=$time;
     end else begin
      automatic int ix=(m<6?cnt[m]-256:cnt[m]);
      automatic int k=ix/LINES[m],l=ix%LINES[m];
      if(k>=6||s_data[m*1024+:1024]!==w2_mem[k*136+W2OFF[m]+l])$fatal(1,"W2 released source mismatch");
     end
     good+=4;cnt[m]++;
     if(cnt[m]==(m<6?256:0)+6*LINES[m])t_done[m]=$time;
    end
    if(fault)$fatal(1,"DUT fault");
   end
  end
  // ---------------- stimulus ----------------
  initial begin
    automatic bit fl = 1;
    if (!$value$plusargs("t_route_ps=%d", t_route)) t_route = 8000000;
    if (!$value$plusargs("notice_lead_ps=%d", notice_lead)) notice_lead = 0;
    if (!$value$plusargs("mut=%d", MUT)) MUT = 0;
    if (!$value$plusargs("trace_pc=%d", trace_pc)) trace_pc = -1;
    begin integer t; if ($value$plusargs("id0=%d", t)) ids[0] = t; if ($value$plusargs("id1=%d", t)) ids[1] = t;
      if ($value$plusargs("id2=%d", t)) ids[2] = t; if ($value$plusargs("id3=%d", t)) ids[3] = t;
      if ($value$plusargs("id4=%d", t)) ids[4] = t; if ($value$plusargs("id5=%d", t)) ids[5] = t; end
    begin string dir;if(!$value$plusargs("DIR=%s",dir))$fatal(1,"actual source DIR required");
      $readmemh({dir,"/gu.hex"},gu_mem);$readmemh({dir,"/sm_expected.hex"},expected_sm);
      $readmemh({dir,"/w2.hex"},w2_mem);
      $readmemh({dir,"/gold.hex"},expected_gold);$readmemh({dir,"/xmap.hex"},xwords);
      void'($value$plusargs("sm_slot=%d",selected));if(selected<0||selected>=6)$fatal(1,"SM slot range");
      $readmemh({dir,"/cfg_lut.hex"},literal_w2_lut);
      #1;for(int l=0;l<136;l++)if(literal_w2_lut[l]!==cfg_lut[l*16+:16])$fatal(1,"released W2 cfg_lut binding");
    end
    for (int k = 0; k < NIDS; k++)
      for (int L = 0; L < NLINE; L++) for (int q = 0; q < 4; q++) begin
        automatic int s = 4 * L + q, p = s % NPC, j = s / NPC;
        mem[midx(p, ((ids[k] % NSETS) << 2) | ((j & 3) ^ ((ids[k] & 1) << 1)), ROW_BASE + ids[k] / NSETS, (j >> 2) & 31)] = L<256 ? gu_mem[k*256+L][q*256+:256] : w2_mem[k*136+L-256][q*256+:256];
      end
    if (MUT == 1) begin automatic longint i = midx(7, ((ids[0] % NSETS) << 2) | (1 ^ ((ids[0] & 1) << 1)), ROW_BASE + ids[0] / NSETS, 0); mem[i][13] = ~mem[i][13]; end
    for (int m = 0; m < NSM; m++) begin cnt[m]=0;t_done[m]=-1;if(m<6)begin native_cnt[m]=0;t_first[m]=-1;t_gu[m]=-1;t_native_first[m]=-1;t_native_last[m]=-1;end end
    for (int p = 0; p < 32; p++) begin
      pc_rd_first[p] = -1; pc_rd_last[p] = -1;
      p_last_act[p] = -1000000; p_last_rd[p] = -1000000; p_last_refpb_any[p] = -1000000; p_round[p] = 0;
      begin : ph
        automatic int P = REF_MODE ? 118 : 3808;
        automatic int base = (PHASE + (p * P) / 32) % P;
        p_last_ref[p] = longint'(base + ((base + P + p) % 2)) * CYC;   // + first active edge (below)
      end
      for (int g = 0; g < 4; g++) begin p_act_bg[p][g] = -1000000; p_rd_bg[p][g] = -1000000; p_faw[p][g] = -1000000; end
      for (int b = 0; b < 32; b++) begin
        b_open[p][b] = 0; b_act[p][b] = -1000000; b_pre[p][b] = -1000000; b_rd[p][b] = -1000000; b_ref_end[p][b] = 0;
      end
    end
    // both resets released together on an hclk edge so the RTL refresh phase matches the checker
    @(posedge hclk); #1; hrst_n = 1; rst_n = 1;
  end
  // notice: static schedule (hclk domain), from t_route - lead until the stream has started
  always @(posedge hclk) if (hrst_n) notice <= (notice_lead > 0) && ($time >= t_route - notice_lead) && ($time < t_route + 2000000);
  // ids: top-6 out at t_route (clk), through NOC_PS of wire, then one a cycle
  initial begin
    wait (rst_n);
    while ($time < t_route + NOC_PS) @(posedge clk);
    t_ids = $time;
    for (int k = 0; k < NIDS; k++) begin
      e_valid <= 1; e_id <= 9'(ids[k]);
      @(posedge clk); while (!e_ready) @(posedge clk);
    end
    e_valid <= 0;
  end
  initial begin
    automatic longint w13 = 0, e1 = 0, dn = 0;
    wait (rst_n);
    forever begin
      @(posedge clk);
      begin
        automatic bit all = 1;
        for (int m = 0; m < NSM; m++) if (t_done[m] < 0) all = 0;
        if (all) break;
      end
      if ($time > t_route + 20000000) begin $fatal(1,"FIRST TIMEOUT"); end
    end
    wait(done_edge>=0 && &gb_done);repeat(4)@(posedge clk);
    for(int m=0;m<6;m++) $display("SLOT k=%0d first_line_ps=%0d gu_complete_ps=%0d native_first_ps=%0d native_last_ps=%0d",m,t_first[m]-t_route,t_gu[m]-t_route,t_native_first[m]-t_route,t_native_last[m]-t_route);
    for(int m=0;m<6;m++)if(native_cnt[m]!=288)$fatal(1,"native byte word count");
    $display("BW rd_first_ps=%0d rd_last_ps=%0d ret_first_ps=%0d ret_last_ps=%0d n_ret=%0d",t_rd_first-t_route,t_rd_last-t_route,t_ret_first-t_route,t_ret_last-t_route,n_ret);
    if ($test$plusargs("pcdbg")) for (int p = 0; p < 32; p++)
      $display("PC %0d rd_first=%0d rd_last=%0d span_cyc=%0d", p, pc_rd_first[p] - t_route, pc_rd_last[p] - t_route, (pc_rd_last[p] - pc_rd_first[p]) / CYC + 1);
    $display("FIRST verdict=%s", (bad==0&&viol==0&&good==longint'(NIDS)*NLINE*4) ? "PASS" : "FAIL");
    if(results!=12||req_seq!=288)$fatal(1,"integrated arithmetic extent");
    $display("INTEGRATED_PQ_XMAP_PASS results=%0d cycles=%0d",results,done_edge-start_edge);
    if(viol!=0||bad!=0||good!=longint'(NIDS)*NLINE*4)$fatal(1,"service byte/DRAM failure");
    $finish;
  end
endmodule
