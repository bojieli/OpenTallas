`timescale 1ns/1ps
`default_nettype none
// CONTROL head leaf of the record-overlap quant cluster (el1013-hbm-quant-split): command relay, descriptors, hazard
// scheduler, read issue, issued-beat queue, gather pop, per-lane retirement.  The former head ot_hgi_qw_ovh had 17.4k
// clock sinks after synthesis trimming (over the 15k rule), so it is two leaves: this one and the DATA head
// ot_hgi_qw_ovd (gather tail, result capture, result-FIFO SRAM and the whole write side).  The lane faces, rq/wq quads
// and first gather stage are in 4 x ot_hgi_qw_lg2; the decoder tiles are children of the wires-only parent.
// Seam control <-> data, a register at both pins, no datapath cycle added (existing register pairs are re-assigned):
//   c_gv  = gv[4]  -> data 'launch'      c_gh = gh[5] -> data gh6 (decode header)
//   c_mw* = the meta-write registers -> data RX, meta written one edge later (read >= 5 edges after: exact)
//   c_wg  = busy && write grant (registered here, the grant pins are on this head's die face) -> data RX: w_fire enable
//   d_wf  = w_fire registered in data -> RX here: resv falls two edges later (conservative: only delays a pop at a
//           result FIFO within 2 of full)
//   d_bad = sticky fault in data -> RX here ('bad'); the fault output rises one cycle later than in the one-head RTL
// Eight compact descriptors stay live until per-lane cumulative output targets retire.
// Continuous read/result pointers and per-beat compact header/output-sector metadata permit
// unrelated records to overlap; earlier live read/write spans serialize all RAW/WAR/WAW hazards.
// cmd[192:129]/[256:193] carry frontend-pipelined A/O span ends in unused SUT words.
// MUT=1 corrupts lane/sector gather; MUT=2 retires without lane completion (negative control).
module ot_hgi_qw_ovc #(
    parameter integer NB = 32,
    parameter integer LQ = 16,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [1408:0] cmd,
    output reg           idle,
    output reg           drained,
    output reg           done,
    output reg           fault,
    // lane-group leaves (4 x ot_hgi_qw_lg2): every output below is a register of this head, every input a leaf register
    output wire [3:0]        l_rst_n,
    output wire [31:0]       l_hit_r, l_hit_p,
    output wire [32*15-1:0]  l_rs,
    output wire [32*4-1:0]   l_sl,
    input  wire [31:0]       l_push, l_rcr, l_done,
    // data head (ot_hgi_qw_ovd)
    output wire              d_rst_n,
    output wire              c_gv,
    output wire [17:0]       c_gh,
    output wire              c_mw_v,
    output wire [5:0]        c_mw_a,
    output wire [14:0]       c_mw_sec,
    output wire [2:0]        c_mw_n,
    output reg               c_wg,        // busy && write grant (the data head's write enable)
    input  wire              d_wf,
    input  wire              d_bad,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer LD = 4;                  // = ot_hgi_qw_rq production default
    localparam integer OD = 64, OW = 6;         // = SRAM words
    localparam integer SW = $clog2(NB), CW = $clog2(LQ + 1), LW = $clog2(LD);
    // ---------------------------------------------------------------- face flops (pure: no logic, reset or enable)
    reg f_rst, f_go, f_rg, f_wg;
    reg [1408:0] f_cmd;
    always @(posedge clk) begin
        f_rst <= rst_n; f_go <= go; f_cmd <= cmd; f_rg <= rg_gnt; f_wg <= wg_gnt;
    end
    wire [6:0] rr_n;                            // 0 control, 1 counters / relays, 2 data head, 3..6 lane-group leaves
    ot_rst_relay #(.REGIONS(7)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    assign l_rst_n = rr_n[6:3]; assign d_rst_n = rr_n[2];
    // ---------------------------------------------------------------- record registers
    wire busy; reg bad, c_done, wf_r;               // bad / wf_r: RX flops of the data head's sticky fault and w_fire pulse
    reg [127:0] hdr;
    reg [19:0] m;
    reg [31:0] rs, ws;
    reg [3:0] nsec_last;
    reg [15:0] beats_row;
    reg b1;
    reg [19:0] r_row; reg [15:0] r_left; reg r_last; reg [14:0] r_sec; reg [31:0] r_nrowbase; reg rd_done;
    reg [19:0] w_row; reg [15:0] w_beat; reg [31:0] w_rowbase;
    
    // command: face flops, then a relay into the centre (the face is ~350 um from the control).  The command words shift
    // unconditionally (no 1,409-flop enable): p_cmd is the command of the f_go cycle whenever p_go is set.
    reg p_go, p_go0; reg [1408:0] p_cmd, p_cmd0;
    wire take = f_go && !p_go0 && !p_go;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin p_go0 <= 0; p_go <= 0; end
        else begin p_go0 <= take; p_go <= p_go0; end
    always @(posedge clk) begin p_cmd0 <= f_cmd; p_cmd <= p_cmd0; end
    // registered status outputs (idle may only lag: it drops two cycles after go and rises a cycle after busy falls)
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin idle <= 1'b1; drained <= 1'b1; done <= 0; fault <= 0; rg_req <= 0; wg_req <= 0; c_wg <= 0; bad <= 0; wf_r <= 0; end
        else begin
            idle <= !take && !p_go0 && !p_go && n_live < 7 && !bad;
            drained <= !busy && !take && !p_go0 && !p_go;
            done <= c_done; fault <= bad; rg_req <= busy; wg_req <= busy; c_wg <= busy && f_wg; bad <= d_bad; wf_r <= d_wf;
        end
    reg rg_ok;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) rg_ok <= 0; else rg_ok <= busy && f_rg;
    // ---------------------------------------------------------------- tiles
    wire [31:0] e1_push = l_push, e1_rcr = l_rcr, e1_done = l_done;   // leaf output registers
    genvar gi;
    // event relays (tile face -> centre): two stages (a corner quad of the 778 x 691 cluster is ~560 um from the centre
    // counters); a later event only returns a credit / count later, so every decision stays conservative and exact.
    reg [31:0] ev_push, ev_rcr, ev_done;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin
            ev_push <= 0; ev_rcr <= 0; ev_done <= 0;
        end else begin
            ev_push <= e1_push; ev_rcr <= e1_rcr; ev_done <= e1_done;
        end
    // ---------------------------------------------------------------- counters (take last cycle's hit vectors)
    reg [CW-1:0] rcr [0:31];
    reg [LW:0] lf_n [0:31], lf_r [0:31];
    reg [31:0] hit_r, hit_p;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) for (integer b = 0; b < 32; b = b + 1) begin rcr[b] <= LQ[CW-1:0]; lf_n[b] <= 0; lf_r[b] <= 0; end
        else for (integer b = 0; b < 32; b = b + 1) begin
            rcr[b] <= rcr[b] + CW'(ev_rcr[b]) - CW'(hit_r[b]);
            lf_n[b] <= lf_n[b] + (LW+1)'(ev_push[b]) - (LW+1)'(hit_p[b]);
            lf_r[b] <= lf_r[b] + (LW+1)'(hit_r[b]) - (LW+1)'(hit_p[b]);
        end
    // issued-beat FIFO, meta FIFO
    reg [4:0] bq_l [0:NB-1]; reg [2:0] bq_n [0:NB-1];
    reg [17:0] bq_hd [0:NB-1]; reg [14:0] bq_dst [0:NB-1];
    reg [SW-1:0] r_tail, r_head; reg [SW:0] r_used;
    reg [OW-1:0] mq_t; reg [OW:0] resv;         // meta FIFO tail (the FIFO itself is in the data head); reserved results
    // ---------------------------------------------------------------- decisions
    // el1011-hbm-fq 10-11 (class 5, ha/hb-d63ee120c od_h -> sec_iss / u_od.r_ce 17 levels): every credit decision is a
    // 32-lane vector AND (one-hot lane window from a register), no 32:1 lane muxes; the write head (sector, count, lane
    // window) is a lookahead register; the result-FIFO SRAM read is issued from a register one edge after w_fire.
    function automatic [31:0] lanes(input [4:0] l0, input [2:0] nn);
        lanes = 0;
        for (integer j = 0; j < 4; j = j + 1) if (j < nn) lanes[5'(l0 + j)] = 1'b1;
    endfunction
    wire [2:0] r_nsec = r_last ? nsec_last[2:0] : 3'd4;
    reg [31:0] r_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1)
        r_ok_l[b] = (rcr[b] > CW'(hit_r[b])) && ((lf_r[b] + (LW+1)'(hit_r[b])) < (LW+1)'(LD));
    wire r_cr_ok = &(~lanes(r_sec[4:0], r_nsec) | r_ok_l);
    wire r_issue = busy && !bad && rg_ok && !rd_done && r_used < NB && r_cr_ok;
    // read head lookahead (el1011-hbm-fq 10-12, qw_h3_ref-f2h CTS SS r_head -> bq mux -> lanes -> l_fire -> mq_sec, 20
    // levels): hh_* = entry r_head of bq, registered.  Both candidates for the next head (r_head, r_head + 1) are read
    // from bq in parallel, with a bypass when r_issue writes that slot this edge (only possible when it is the head:
    // r_used == 0 for r_head, r_used == 1 for r_head + 1); l_fire / p_go only pick between them at the end.  Exact: a
    // live head slot (r_used != 0) is never rewritten (r_issue needs r_used < NB), so hh == bq[r_head] whenever used.
    reg [4:0] hh_l; reg [2:0] hh_n; reg [31:0] hh_ln;
    reg [17:0] hh_hd; reg [14:0] hh_dst;
    wire [4:0] h_l = hh_l; wire [2:0] h_n = hh_n;
    reg [31:0] h_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1) h_ok_l[b] = lf_n[b] > (LW+1)'(hit_p[b]);
    wire h_ok = (r_used != 0) && &(~hh_ln | h_ok_l);
    wire l_fire = busy && h_ok && resv < OD;
    wire [SW-1:0] r_head1 = r_head + 1'b1;
    wire c0_b = r_issue && (r_used == 0), c1_b = r_issue && (r_used == 1);
    wire [4:0] c0_l = c0_b ? r_sec[4:0] : bq_l[r_head];  wire [2:0] c0_n = c0_b ? r_nsec : bq_n[r_head];
    wire [4:0] c1_l = c1_b ? r_sec[4:0] : bq_l[r_head1]; wire [2:0] c1_n = c1_b ? r_nsec : bq_n[r_head1];
    wire [31:0] c0_ln = lanes(c0_l, c0_n), c1_ln = lanes(c1_l, c1_n);
    always @(posedge clk) begin
        // p_go: r_head -> 0 with r_used 0; the next issue writes slot 0 with r_used == 0 and bypasses into hh
        if (l_fire) begin
            hh_l <= c1_l; hh_n <= c1_n; hh_ln <= c1_ln;
            hh_hd <= c1_b ? {hdr[127:118],hdr[71:64]} : bq_hd[r_head1];
            hh_dst <= c1_b ? read_dst : bq_dst[r_head1];
        end else begin
            hh_l <= c0_l; hh_n <= c0_n; hh_ln <= c0_ln;
            hh_hd <= c0_b ? {hdr[127:118],hdr[71:64]} : bq_hd[r_head];
            hh_dst <= c0_b ? read_dst : bq_dst[r_head];
        end
    end
    // ---------------------------------------------------------------- per-lane sectors / slots (registered, then relayed)
    reg [14:0] rs1 [0:31]; reg [3:0] sl1 [0:31];
    always @(posedge clk)
        for (integer b = 0; b < 32; b = b + 1) begin
            rs1[b] <= r_sec + 15'(5'(b - r_sec[4:0]));
            sl1[b] <= 4'(1) << (2'(b - h_l) ^ ((MUT == 1) ? 2'd1 : 2'd0));
        end
    // ---------------------------------------------------------------- gather: registered OR2 tree, launch
    // (el1011-hbm-fq 10-12, qw_h3_ref-f2h CTS SS -382.8: the 4-way OR across a 2 x 2 block of rq tiles into go_h was one
    // stage over ~300 um of 1,024-bit wire.)  Now every stage is one OR2 of two neighbours: gp[k] = the two side-by-side
    // tiles of row k (registered between them), go_h[h] = two adjacent rows, lx = the two halves next to the decoder.
    // +1 edge of gather latency; gv follows (5 deep).
    // el1013 seam rule (register at the pin): each leaf's gp is captured by its own pure head pin flop gpf[k]; the
    // former go_h OR2 is folded into the lx stage (one OR4 of four local registers next to the decoder).  Same latency.
    // (the gpf / lx registers and the decode launch are in the data head; this leaf keeps the valid and header delay
    // lines up to the seam: gv[4] and gh[5] are the TX registers, 'launch' and gh6 the data head's RX registers)
    reg [4:0] gv;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) gv <= 0; else gv <= {gv[3:0], |hit_p};
    reg [17:0] gh [0:5];
    always @(posedge clk) begin
        gh[0] <= hh_hd;
        for (integer i=1; i<6; i=i+1) gh[i] <= gh[i-1];
    end
    assign c_gv = gv[4]; assign c_gh = gh[5];
    // Compact descriptors are admitted independently of output retirement.  A slot remains live
    // until all of its output lanes retire, so dependent spans serialize at the issue scheduler.
    localparam integer RQ=8, TW=9;
    reg [2:0] c_tail, c_issue, c_ret, active_id;
    reg [3:0] n_live, n_pending;
    // Kept local address copies limit each descriptor-bank select to one narrow field.
    (* keep *) reg [2:0] desc_sel [0:11];
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0])
        for(integer i=0;i<12;i=i+1) desc_sel[i]<=0;
    else for(integer i=0;i<12;i=i+1) desc_sel[i]<=load_record ? c_issue+1'b1 : c_issue;
    reg [7:0] live, target_valid;
    reg [17:0] ch [0:RQ-1];
    reg [19:0] cn [0:RQ-1], cm [0:RQ-1];
    reg [31:0] cab [0:RQ-1], cob [0:RQ-1], cars [0:RQ-1], cors [0:RQ-1];
    reg [31:0] caend [0:RQ-1], coend [0:RQ-1];
    wire [14:0] read_dst = w_rowbase[17:3] + 15'({w_beat,2'd0});
    // Each 32-element beat writes four 256-bit VM sectors (partial op6 beat writes two).
    wire [31:0] output_lanes = lanes(read_dst[4:0],r_nsec);
    reg [TW-1:0] issued [0:31], retired [0:31], target [0:RQ-1][0:31];
    wire r_end = r_issue && r_last && (r_row + 1 == m);
    reg hazard;
    always @* begin
        hazard = 0;
        for (integer i=0; i<RQ; i=i+1)
            // issued earlier descriptors are live; pending later descriptors do not constrain this head.
            if (live[i] && (((3'(i)-c_ret)&3'd7) < ((c_issue-c_ret)&3'd7)))
                if ((cab[desc_sel[0]] <= coend[i] && caend[desc_sel[1]] >= cob[i]) ||
                    (cob[desc_sel[2]] <= caend[i] && coend[desc_sel[3]] >= cab[i]) ||
                    (cob[desc_sel[2]] <= coend[i] && coend[desc_sel[3]] >= cob[i])) hazard = 1;
    end
    wire load_record = n_pending != 0 && (rd_done || r_end) && !hazard && !bad;
    assign busy = n_live != 0;
    // Per-quad lane retirement compare, then an eight-quad completion reduction.  The tag rejects
    // stale results when the completion head changes.  TW=9 signed modular differences are
    // safe because NB+OD+LD <256 bounds all outstanding sectors in any one lane.
    reg [7:0] retire_q;
    (* keep *) reg [2:0] target_sel [0:7];
    (* keep *) reg [7:0] tc_valid;
    (* keep *) reg [2:0] tc_id [0:7];
    reg [TW-1:0] tc_value [0:31];
    reg target_ready; reg [2:0] target_ready_id;
    always @(posedge clk or negedge rr_n[1])
        if(!rr_n[1]) begin
            tc_valid<=0;target_ready<=0;target_ready_id<=0;
            for(integer q=0;q<8;q=q+1) begin target_sel[q]<=0;tc_id[q]<=0;end
        end else begin
            target_ready<=r_end;target_ready_id<=active_id;
            for(integer q=0;q<8;q=q+1) begin
                tc_valid[q]<=r_end;tc_id[q]<=active_id;target_sel[q]<=c_ret;
            end
        end
    always @(posedge clk) begin
        for(integer b=0;b<32;b=b+1) tc_value[b]<=issued[b]+TW'(output_lanes[b]);
        for(integer q=0;q<8;q=q+1) if(tc_valid[q])
            for(integer b=0;b<4;b=b+1) target[tc_id[q]][q*4+b]<=tc_value[q*4+b];
    end
    reg [2:0] retire_q_id;
    wire retire_all = &retire_q;
    wire [2:0] retire_all_id = retire_q_id;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin retire_q<=0; retire_q_id<=0; end
        else begin
            retire_q_id <= target_sel[0];
            for (integer q=0;q<8;q=q+1) begin
                retire_q[q] <= target_valid[target_sel[q]] &&
                    ($signed(retired[q*4]+TW'(ev_done[q*4])-target[target_sel[q]][q*4]) >= 0) &&
                    ($signed(retired[q*4+1]+TW'(ev_done[q*4+1])-target[target_sel[q]][q*4+1]) >= 0) &&
                    ($signed(retired[q*4+2]+TW'(ev_done[q*4+2])-target[target_sel[q]][q*4+2]) >= 0) &&
                    ($signed(retired[q*4+3]+TW'(ev_done[q*4+3])-target[target_sel[q]][q*4+3]) >= 0);
            end
        end
    // Explicit signed comparisons avoid unsigned wrap and tolerate later completions on other lanes.
    // The four lane predicates are reduced locally; there is no cross-lane completion arbitration.
    wire retire_record = n_live != 0 && target_valid[c_ret] && ((MUT==2) || (retire_all && retire_all_id == c_ret)) && !bad;
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            c_done<=0; hdr<=0; m<=0; rs<=0; ws<=0;
            nsec_last<=0; beats_row<=0; b1<=0; r_row<=0; r_left<=0; r_last<=0;
            r_sec<=0; r_nrowbase<=0; rd_done<=1;
            r_tail<=0; r_head<=0; r_used<=0; mq_t<=0; resv<=0;
            w_row<=0; w_beat<=0; w_rowbase<=0;
            hit_r<=0; hit_p<=0;
            c_tail<=0; c_issue<=0; c_ret<=0; active_id<=0;
            n_live<=0; n_pending<=0; live<=0; target_valid<=0;
            for(integer b=0;b<32;b=b+1) begin issued[b]<=0; retired[b]<=0; end
        end else begin
            c_done <= retire_record;
            hit_r <= r_issue ? lanes(r_sec[4:0],r_nsec) : 32'd0;
            hit_p <= l_fire ? hh_ln : 32'd0;
            n_live <= n_live + 4'(p_go) - 4'(retire_record);
            n_pending <= n_pending + 4'(p_go) - 4'(load_record);
            if (p_go) begin c_tail<=c_tail+1'b1; live[c_tail]<=1; end
            if (retire_record) begin c_ret<=c_ret+1'b1; live[c_ret]<=0; target_valid[c_ret]<=0; end
            for(integer b=0;b<32;b=b+1) begin
                retired[b] <= retired[b] + TW'(ev_done[b]);
                issued[b] <= issued[b] + TW'(r_issue && output_lanes[b]);
            end
            if (r_issue) begin
                r_tail <= r_tail+1'b1;
                if (r_last) begin
                    r_row<=r_row+1; r_sec<=r_nrowbase[17:3]; r_nrowbase<=r_nrowbase+rs;
                    r_left<=beats_row; r_last<=b1;
                    w_beat<=0; w_rowbase<=w_rowbase+ws;
                    if (r_row+1==m) rd_done<=1;
                end else begin
                    r_sec<=r_sec+15'd4; r_left<=r_left-1'b1; r_last<=r_left==16'd2;
                    w_beat<=w_beat+1'b1;
                end
            end
            if (target_ready) target_valid[target_ready_id]<=1;
            if (load_record) begin
                c_issue<=c_issue+1'b1; active_id<=c_issue;
                hdr<={ch[desc_sel[8]][17:8],46'd0,ch[desc_sel[8]][7:0],64'd0};
                m<=cm[desc_sel[5]]; rs<=cars[desc_sel[6]]; ws<=cors[desc_sel[7]];
                r_sec<=cab[desc_sel[0]][17:3]; r_nrowbase<=cab[desc_sel[0]]+cars[desc_sel[6]];
                w_rowbase<=cob[desc_sel[2]]; w_beat<=0;
                beats_row<=16'((cn[desc_sel[4]]+20'd31)>>5); r_left<=16'((cn[desc_sel[4]]+20'd31)>>5);
                b1<=cn[desc_sel[4]]<=32; r_last<=cn[desc_sel[4]]<=32;
                nsec_last<=cn[desc_sel[4]][4:0]==0 ? 4'd4 : 4'(cn[desc_sel[4]][4:3]);
                r_row<=0; rd_done<=0;
            end
            if (l_fire) begin r_head<=r_head+1'b1; mq_t<=mq_t+1'b1; end
            r_used<=r_used+(SW+1)'(r_issue)-(SW+1)'(l_fire);
            resv<=resv+(OW+1)'(l_fire)-(OW+1)'(wf_r);
        end
    end
    always @(posedge clk) if (p_go) begin
        ch[c_tail]<={p_cmd[128:119],p_cmd[72:65]};
        cn[c_tail]<=p_cmd[433 +:20]; cm[c_tail]<=p_cmd[453 +:20];
        cab[c_tail]<=p_cmd[393 +:32]; cob[c_tail]<=p_cmd[1161 +:32];
        cars[c_tail]<=p_cmd[473 +:32]; cors[c_tail]<=p_cmd[1241 +:32];
        caend[c_tail]<=p_cmd[129 +:32];
        coend[c_tail]<=p_cmd[193 +:32];
    end
    // meta write: registered here one edge after l_fire (TX), registered again in the data head (RX), then written.
    reg mw_v; reg [OW-1:0] mw_a; reg [14:0] mw_sec; reg [2:0] mw_n;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) mw_v <= 0; else mw_v <= l_fire;
    always @(posedge clk) begin mw_a <= mq_t; mw_sec <= hh_dst; mw_n <= h_n; end
    always @(posedge clk) begin
        if (r_issue) begin bq_l[r_tail] <= r_sec[4:0]; bq_n[r_tail] <= r_nsec; bq_hd[r_tail]<={hdr[127:118],hdr[71:64]}; bq_dst[r_tail]<=read_dst; end
    end
    // leaf-facing outputs: stage-1 registers of the former two-stage relays (stage 2 is the leaf pin register)
    generate for (gi = 0; gi < 32; gi = gi + 1) begin : g_lo
        assign l_rs[gi*15 +: 15] = rs1[gi]; assign l_sl[gi*4 +: 4] = sl1[gi];
    end endgenerate
    assign l_hit_r = hit_r; assign l_hit_p = hit_p;
    assign c_mw_v = mw_v; assign c_mw_a = mw_a; assign c_mw_sec = mw_sec; assign c_mw_n = mw_n;
    initial if (NB+OD+LQ+16>=256 || NB < 8 || (NB & (NB - 1)) != 0 || (LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_qw_ovc: NB / LQ");
endmodule
`default_nettype wire
