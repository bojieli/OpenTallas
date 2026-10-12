`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA BACK (el1011-hbm-tputx [tputx-mtp] 2026-10-12): the VM -> HBM store stream, the mirror of ot_hgi_dma_front.
// Physical spec: el1011-hbm-tputx.log "[tputx-mtp] PHYSICAL SPEC" (10-12 00:40) + "PHYSICAL SPEC AMENDMENT" (03:05).
// Budget: MTP.VERIFY swapout = DMA.STORE h (20,480 FP32, 80 KiB) + STORE PRE + CTL.FENCE in 248 cycles (>= ~750 B/cycle);
// every older store path writes <= 1 sector a cycle a stack (kport lanes), so this engine writes 4 stacks x 8 lanes.
//
// Takes a DMA STORE move (ot_hgi_dma_mover move word, 227 b) of the shape
//   src VM, dst HBM, element strides 1, FP32 / U32 words on both sides (a raw word copy), VM row base and row stride
//   multiples of 64 words (8 sectors: every row chunk is one VM bank group), n a multiple of 8 words (whole sectors),
//   HBM row base / stride 32 B aligned, destination code 0 (linear) or 1 (STRIPE4, spec 6.4: row o on stack
//   (base[36:35] + o) mod 4 at stack-local base[34:0] + o x stride = a linear row step of stride + 2^SBIT mod 2^37);
// (the DMA unit sends every other move elsewhere; a non-eligible move faults here), and
//   G  window generator (2 registered rungs): rows in windows of up to 4 -- G1 the rows' VM sector / HBM byte address
//      (4 parallel adds from the registered row-step multiples), G2 their bank groups, the window's PAR flag (the rows'
//      bank groups pairwise distinct) and the row range check (a row must stay inside its stack); a 4-entry window queue;
//   H  the head window (registered, popped from the queue): per row the VM sector / HBM sector address of the current
//      chunk, advanced by 8 sectors a chunk -- the issue decision reads registers only;
//   I  issue: a row's 8-sector CHUNK is VM sectors vs .. vs + 7 (one bank group g, lanes 8g .. 8g + 7); a PAR window
//      issues the chunk of all its rows in one cycle (the STRIPE4 h swap: 32 sectors a cycle), else one row's chunk a
//      cycle (round robin over the window's rows).  A chunk issues when each lane it uses has a VM read credit and a
//      landing slot (LQ in flight a lane), the read group is granted and the chunk table has a free entry; each used
//      lane gets the read {v, sector 15} on the VM DMA wide READ group (the mover's VR2 contract).  The issue cycle's
//      lane-0 HBM sector address per bank group goes into a CHUNK TABLE entry (LQ entries, retired in order once every
//      lane it used has read it); each lane's route FIFO keeps only the entry tag (+ the stack for NS > 1);
//   L  each VM lane's response is pin-flopped and lands in its landing FIFO (an ot_sram_1r1w_128x256 macro a lane, LQ
//      of its rows);
//   W  stack lane (s, l) picks, rotating, one of the NG VM lanes l, 8 + l, .. whose landing head is for stack s while it
//      holds an svc write credit, and reads that macro (the pick IS the read: no skid); the macro output is captured
//      (no logic before the flops) while the table gives the chunk address, and the next edge the lane's registered
//      output {v, sector address 32 = table address + lane, data 256}: the svc writes the sector at its address
//      (no request / tag / order: a beat is self-describing, any lane, any order);
//   A  the svc returns a lane credit when it pops a beat (wd_cr) and, per stack, the count of sectors written (wa, posted
//      acknowledgements, pin-flopped); quiet = every sent sector acknowledged (registered port).
// Gate fixes ([tputx-mtp] RELAUNCH 5, 10-12): route FIFO 32 b -> tag (chunk table), skid removed (pick at the read),
// outputs generated per lane (constant slices), resets only on control / pointer / valid state (one relay region a
// lane), quiet registered, issue from the registered head window (no queue mux / add before the route writes).
// Retire: src (source consumed) pulses when every source sector of the move has landed (the posted STORE retires; the VM
// may be overwritten); the engine then takes the next eligible STORE while the writes drain; done pulses once when quiet
// (every accepted move's every write acknowledged: CTL.FENCE / wr_quiet).
// Rate: 32 sectors (1 KiB) a cycle in from the VM, 32 out to the svc (8 a stack).
// MUT (bench): 1 a group-1 lane's sector address + 1 (misplaced sector): must FAIL; 2 src pulses when the last chunk
//   issues, before its sectors landed (the bench then overwrites the VM source): must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_back #(
    parameter integer NS = 4,             // stacks written: 4 = the pre-B2 die view (one engine, central VM); 1 = HBM B2: one
                                          //   instance per cluster on its LOCAL VM slice port, writing its own stack STK only
    parameter integer STK = 0,
    parameter integer NB = 32,            // VM read lanes = the VM banks reached: 32 (pre-B2 central VM read group) or 8 (HBM B2:
                                          //   the LOCAL slice lane group, lane b = local bank b = sector s[2:0]; one chunk a cycle)            // the first stack written (B2: the cluster's stack); a row on a stack outside
                                          //   [STK, STK + NS) faults
    parameter integer NL = 8,
    parameter integer SBIT = 35,          // stack select = HBM byte address [SBIT+1:SBIT]
    parameter [35:0] STACK_BYTES = 36'd22500000000,
    parameter integer LQ = 32,            // landing slots a VM lane (<= 128): sectors in flight a lane
    parameter integer VCR = 32,           // the VM read group's credits a lane (the mover's GLQ)
    parameter integer WCR = 32,           // the svc's write credits a stack lane (its beat buffer)
    parameter integer MUT = 0
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     mv_v,
    output wire                     mv_rdy,
    input  wire [226:0]             mv,
    output reg                      mv_src,      // the move's source consumed (posted retire)
    output reg                      mv_done,     // quiet: every accepted move's every HBM write acknowledged
    output reg                      mv_fault,    // sticky until reset
    output wire                     quiet,       // no move held, nothing in flight (registered state only)
    // VM DMA wide READ group (ot_hgi_vm_die dma_r_up / dma_r_dn): up {c_req, 32 x {v, sector 15}};
    // down {c_gnt, credits 32, 32 x {v, data 256}}
    output wire [NB*16:0]           vr2q,
    input  wire [NB*258:0]          vr2r,
    // svc WRITE stream: per stack x lane {v, sector address 32 (= HBM byte address [36:5]), data 256}
    output reg  [NS*NL*289-1:0]     wd,
    input  wire [NS*NL-1:0]         wd_cr,       // the svc popped a beat of the lane (one credit back)
    input  wire [NS*4-1:0]          wa           // per stack: sectors written this cycle (0..8, posted acknowledgements)
);
    localparam integer NG = NB / 8;             // bank groups of 8 lanes (4 or 1)
    localparam [1:0] GM = 2'(NG - 1);
    localparam integer LW = $clog2(LQ);
    localparam integer NO = NS * NL;            // stack lanes (= NB: each VM lane l of a group feeds stack lane l of a stack)
    // ---------------------------------------------------------------- reset relay: one region a VM lane + control
    // (only control / pointer / valid state is reset; data, route and table entries are not)
    wire [NB:0] rl;
    ot_rst_relay #(.REGIONS(NB + 1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rc = rl[NB];
    // ---------------------------------------------------------------- pin flops (VM group, svc credits / acks)
    reg g_gnt; reg [NB-1:0] vcp; reg [NB-1:0] rr_v; reg [255:0] rr_d [0:NB-1];
    reg [NO-1:0] wcp; reg [NS*4-1:0] wap;
    always @(posedge clk or negedge rc)
        if (!rc) begin g_gnt <= 1'b0; vcp <= '0; wcp <= '0; wap <= '0; end
        else begin g_gnt <= vr2r[NB*258]; vcp <= vr2r[NB*258-1 -: NB]; wcp <= wd_cr; wap <= wa; end
    genvar gb, go_;
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_pin
        always @(posedge clk or negedge rl[gb]) if (!rl[gb]) rr_v[gb] <= 1'b0; else rr_v[gb] <= vr2r[gb*257 + 256];
        always @(posedge clk) rr_d[gb] <= vr2r[gb*257 +: 256];                                       // data: no reset
    end endgenerate
    // ---------------------------------------------------------------- command station + move registers
    reg cv_q; reg [226:0] cm_q;
    reg busy;                                    // a move's source is being read (accept .. src)
    reg dirty;                                   // a move accepted since the last done
    reg [14:0] m_vstr;                           // VM row stride in sectors
    reg [36:0] m_st1, m_st2, m_st3, m_st4;       // HBM row step x 1..4
    reg [17:0] m_rsec;                           // sectors a row
    reg [35:0] m_lim;                            // the last stack-local row start that fits: STACK_BYTES - bytes a row
    reg [19:0] g_left;                           // rows not yet windowed
    reg [31:0] tot_sec, landed;                  // the move's sectors, landed so far
    reg        iss_all;                          // every window of the move issued
    assign mv_rdy = rc && !cv_q && !busy && !mv_fault;
    wire [2:0] sfmt = cm_q[4:2], dfmt = cm_q[97:95];
    wire elig = cm_q[1:0] == 2'd1 && cm_q[94:93] == 2'd0 && cm_q[92:77] == 16'd1 && cm_q[185:170] == 16'd1 &&
                (sfmt == 3'd0 || sfmt == 3'd5) && (dfmt == 3'd0 || dfmt == 3'd5) && cm_q[10:5] == 6'd0 &&
                cm_q[50:45] == 6'd0 && cm_q[208:206] == 3'd0 && cm_q[102:98] == 5'd0 && cm_q[142:138] == 5'd0 &&
                cm_q[137:136] == 2'd0 && cm_q[205:186] != 20'd0 && cm_q[226:206] != 21'd0;
    // ---------------------------------------------------------------- G1 / G2 window generator, window queue
    reg        g1_par, g1_bad;                   // G2 (combinational on the G1 registers): the window's PAR flag / range fault
    reg        g1_v; reg [2:0] g1_k; reg [14:0] g1_vs [0:3]; reg [36:0] g1_a [0:3];
    reg [14:0] gw_vs; reg [36:0] gw_a;           // the next window's first row
    reg [1:0]  wq_h, wq_t; reg [2:0] wq_n;
    reg [2:0]  q_k [0:3]; reg q_par [0:3]; reg [14:0] q_vs [0:3][0:3]; reg [36:0] q_a [0:3][0:3];
    wire       g_take = busy && g_left != 20'd0 && (wq_n + {2'd0, g1_v}) < 3'd4;
    wire       g_k4 = g_left >= 20'd4; wire [1:0] g_k = g_left[1:0];   // this window's rows: 4, else g_left (1..3)
    // ---------------------------------------------------------------- H: the head window, registered
    // (popped from the window queue; per row the VM sector and the HBM sector address of the current chunk, advanced
    // by 8 sectors a chunk: the issue decision and the table / route writes read registers only, no queue mux / add)
    reg        hv; reg [2:0] hk; reg hpar; reg [1:0] h_w; reg [17:0] h_rem;
    reg [14:0] hs_vs [0:3]; reg [31:0] hs_sa [0:3];
    reg [11:0] hs_vn [0:3]; reg [31:0] hs_an [0:3];   // the next chunk's (precomputed: the advance is a mux, no add after go)
    // ---------------------------------------------------------------- issue state
    // per lane: landing occupancy (issued, not yet sent), VM credits
    reg [LW:0] l_cnt [0:NB-1]; reg [5:0] v_cr [0:NB-1];
    reg [NB-1:0] l_ok;                           // the lane takes a sector this cycle
    always @* for (integer b = 0; b < NB; b = b + 1) l_ok[b] = l_cnt[b] < (LW+1)'(LQ) && v_cr[b] != 6'd0;
    // chunk table: one entry an issue cycle {per bank group: the HBM sector address of the chunk's lane 0; the lanes still
    // holding it}; a lane's route FIFO keeps only the entry's tag; the entry retires (in order) once every lane read it
    reg [31:0] ct_a [0:LQ-1][0:NG-1]; reg [NB-1:0] ct_m [0:LQ-1];
    reg [LW-1:0] ct_t, ct_h; reg [LW:0] ct_n;
    reg [LQ-1:0] ct_z; always @* for (integer e = 0; e < LQ; e = e + 1) ct_z[e] = ~|ct_m[e];
    wire       ct_adv = ct_n != '0 && ct_z[ct_h];
    // ---- the head window's chunk: per row its group and lanes
    wire [3:0] c_len = (h_rem >= 18'd8) ? 4'd8 : 4'(h_rem);
    reg  [7:0] c_lm;                             // lanes used within the group
    always @* begin c_lm = 8'd0; for (integer l = 0; l < 8; l = l + 1) if (4'(l) < c_len) c_lm[l] = 1'b1; end
    reg [3:0] grp_ok;                            // bank group g: every used lane takes a sector
    always @* for (integer g = 0; g < 4; g = g + 1) grp_ok[g] = (g < NG) && &(l_ok[(g % NG)*8 +: 8] | ~c_lm);
    reg [1:0] r_g [0:3]; reg [3:0] r_in;         // row j: group of the chunk, row j present in the window
    always @* for (integer j = 0; j < 4; j = j + 1) begin r_g[j] = hs_vs[j][4:3] & GM; r_in[j] = 3'(j) < hk; end
    reg [3:0] r_sel;                             // rows issuing this cycle
    reg       go;
    always @* begin
        r_sel = 4'd0;
        if (hpar) r_sel = r_in; else r_sel[h_w] = 1'b1;
        go = rc && hv && g_gnt && !mv_fault && ct_n < (LW+1)'(LQ);
        for (integer j = 0; j < 4; j = j + 1) if (r_sel[j] && !grp_ok[r_g[j]]) go = 1'b0;
    end
    wire last_row = hpar || (3'(h_w) + 3'd1 == hk);
    wire last_chunk = h_rem <= 18'd8;
    wire w_end = go && last_row && last_chunk;
    wire h_pop = (!hv || w_end) && wq_n != 3'd0;
    // ---- the VM requests, route tags and table entry of this cycle
    reg [NB-1:0] i_lv; reg [14:0] i_sec [0:NB-1]; reg [1:0] i_st [0:NB-1]; reg [31:0] i_ga [0:NG-1];
    always @* begin
        i_lv = '0;
        for (integer b = 0; b < NB; b = b + 1) begin i_sec[b] = 15'd0; i_st[b] = 2'd0; end
        for (integer g = 0; g < NG; g = g + 1) i_ga[g] = 32'd0;
        for (integer j = 0; j < 4; j = j + 1) if (go && r_sel[j]) begin
            for (integer g = 0; g < NG; g = g + 1) if (r_g[j] == 2'(g)) begin
                i_ga[g] = i_ga[g] | hs_sa[j];
                for (integer l = 0; l < 8; l = l + 1) if (c_lm[l]) begin
                    i_lv[g*8 + l] = 1'b1;
                    i_sec[g*8 + l] = {hs_vs[j][14:3], 3'(l)};          // chunk sectors are 8-aligned: no add
                    i_st[g*8 + l] = hs_sa[j][SBIT-5 +: 2];
                end
            end
        end
    end
    reg [NB*16:0] s_vr2q; assign vr2q = s_vr2q;
    // ---------------------------------------------------------------- per lane: route tags, landing macro
    reg [LW-1:0] rt [0:NB-1][0:LQ-1];            // route: the chunk-table tag of each in-flight sector (issue order)
    reg [1:0]  rt_s [0:NB-1][0:LQ-1];            // ... and its stack (NS > 1 only: the picker's stack match)
    reg [LW-1:0] rt_t [0:NB-1], d_t [0:NB-1], d_h [0:NB-1];
    reg [LW:0] d_n [0:NB-1];                     // landed, not yet read from the macro
    reg [NB-1:0] rd_i, rd_v, rd_w;               // macro read issued / its data valid (capture) / output stage
    reg [LW-1:0] tg_q [0:NB-1];                  // the read sector's tag (captured at the read)
    reg [255:0] dq [0:NB-1];                     // macro output capture flops (no logic before them)
    reg [31:0]  ab_q [0:NB-1];                   // the read sector's chunk lane-0 HBM sector address (table read rung)
    wire [255:0] m_rd [0:NB-1];
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_lane
        ot_sram_1r1w_128x256_m1_r2c2 u_q (.clk(clk), .r_ce_in(rd_i[gb]), .r_addr_in(7'(d_h[gb])), .rd_out(m_rd[gb]),
            .w_ce_in(rr_v[gb]), .w_addr_in(7'(d_t[gb])), .wd_in(rr_d[gb]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // ---------------------------------------------------------------- W: stack lane pickers (at the macro read)
    // stack lane (s, l) = index s*8 + l picks, rotating, one VM lane g*8 + l whose landing head is for stack s while it
    // holds an svc write credit; the macro read is the pick (no skid): the data goes from the macro output register
    // straight to the lane's registered output the next edge
    reg [1:0] p_rr [0:NO-1];
    reg [NO-1:0] p_v; reg [1:0] p_g [0:NO-1];
    reg [5:0] w_cr [0:NO-1];
    reg [NO-1:0] pv_q, pv_q2; reg [1:0] pg_q [0:NO-1], pg_q2 [0:NO-1];
    always @* begin
        rd_i = '0;
        for (integer s = 0; s < NS; s = s + 1) for (integer l = 0; l < NL; l = l + 1) begin : pk
            integer o;
            o = s * NL + l;
            p_v[o] = 1'b0; p_g[o] = 2'd0;
            for (integer t = NG - 1; t >= 0; t = t - 1) begin : cand
                reg [1:0] g; integer b;
                g = 2'(p_rr[o] + 2'(t)) & GM; b = g * 8 + l;
                if (d_n[b] != '0 && (NS == 1 || rt_s[b][d_h[b]] == 2'(STK + s)) && w_cr[o] != 6'd0) begin p_v[o] = 1'b1; p_g[o] = g; end
            end
            for (integer g = 0; g < NG; g = g + 1) if (p_v[o] && p_g[o] == 2'(g)) rd_i[g*8 + l] = 1'b1;
        end
    end
    // ---- the read sector's HBM sector address (table lane-0 address, registered, + lane; MUT 1: lane 1 + 1)
    reg [31:0] rd_sa [0:NB-1];
    always @* for (integer b = 0; b < NB; b = b + 1)
        rd_sa[b] = ab_q[b] + 32'(b % 8) + ((MUT == 1 && (b % 8) == 1) ? 32'd1 : 32'd0);
    // ---- registered outputs: generated per stack lane (constant slices)
    generate for (go_ = 0; go_ < NO; go_ = go_ + 1) begin : g_out
        localparam integer L = go_ % NL;
        reg [287:0] od;
        always @* begin
            od = {rd_sa[L], dq[L]};
            for (integer g = 1; g < NG; g = g + 1) if (pg_q2[go_] == 2'(g)) od = {rd_sa[g*8 + L], dq[g*8 + L]};
        end
        always @(posedge clk or negedge rl[go_ % NB]) if (!rl[go_ % NB]) wd[go_*289 + 288] <= 1'b0; else wd[go_*289 + 288] <= pv_q2[go_];
        always @(posedge clk) wd[go_*289 +: 288] <= od;                                               // data: no reset
    end endgenerate
    // ---------------------------------------------------------------- landed count (registered popcount rung)
    reg [5:0] nl_q;
    always @(posedge clk or negedge rc) begin : lc
        reg [5:0] c; c = 6'd0;
        if (!rc) nl_q <= 6'd0;
        else begin for (integer b = 0; b < NB; b = b + 1) c = c + 6'(rr_v[b]); nl_q <= c; end
    end
    // per stack: sectors sent, not yet acknowledged
    reg [15:0] out_n [0:NS-1];
    reg [3:0]  ns_q [0:NS-1];                    // sectors sent a stack this cycle (registered popcount)
    // ---------------------------------------------------------------- sequential
    reg [NB-1:0] all_home;
    always @* for (integer b = 0; b < NB; b = b + 1) all_home[b] = l_cnt[b] == '0 && v_cr[b] == 6'(VCR);
    reg wq_any; always @* begin wq_any = 1'b0; for (integer s = 0; s < NS; s = s + 1) if (out_n[s] != 16'd0 || ns_q[s] != 4'd0) wq_any = 1'b1; end
    wire quiet_c = !cv_q && !busy && &all_home && !wq_any;
    reg  quiet_q; assign quiet = quiet_q;        // registered port: drops on the accepting edge, rises a cycle late
    // ---- per lane (own reset region)
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_ls
        always @(posedge clk or negedge rl[gb]) begin
            if (!rl[gb]) begin
                l_cnt[gb] <= '0; v_cr[gb] <= 6'(VCR); rt_t[gb] <= '0; d_t[gb] <= '0; d_h[gb] <= '0; d_n[gb] <= '0;
                rd_v[gb] <= 1'b0; rd_w[gb] <= 1'b0; s_vr2q[gb*16 + 15] <= 1'b0;
            end else begin
                s_vr2q[gb*16 + 15] <= i_lv[gb];
                if (i_lv[gb]) rt_t[gb] <= rt_t[gb] + 1'b1;
                l_cnt[gb] <= l_cnt[gb] + (LW+1)'(i_lv[gb]) - (LW+1)'(rd_w[gb]);
                v_cr[gb] <= v_cr[gb] - 6'(i_lv[gb]) + 6'(vcp[gb]);
                if (rr_v[gb]) d_t[gb] <= d_t[gb] + 1'b1;
                d_n[gb] <= d_n[gb] + (LW+1)'(rr_v[gb]) - (LW+1)'(rd_i[gb]);
                if (rd_i[gb]) d_h[gb] <= d_h[gb] + 1'b1;
                rd_v[gb] <= rd_i[gb]; rd_w[gb] <= rd_v[gb];
            end
        end
        always @(posedge clk) begin                                                                   // no reset
            s_vr2q[gb*16 +: 15] <= i_sec[gb];
            if (i_lv[gb]) begin rt[gb][rt_t[gb]] <= ct_t; rt_s[gb][rt_t[gb]] <= i_st[gb]; end
            if (rd_i[gb]) tg_q[gb] <= rt[gb][d_h[gb]];
            dq[gb] <= m_rd[gb];
            ab_q[gb] <= ct_a[tg_q[gb]][gb / 8];
        end
    end endgenerate
    generate for (go_ = 0; go_ < NO; go_ = go_ + 1) begin : g_os
        always @(posedge clk or negedge rl[go_ % NB]) begin
            if (!rl[go_ % NB]) begin p_rr[go_] <= 2'd0; w_cr[go_] <= 6'(WCR); pv_q[go_] <= 1'b0; pv_q2[go_] <= 1'b0; end
            else begin
                w_cr[go_] <= w_cr[go_] - 6'(p_v[go_]) + 6'(wcp[go_]);
                if (p_v[go_]) p_rr[go_] <= (p_g[go_] + 2'd1) & GM;
                pv_q[go_] <= p_v[go_]; pv_q2[go_] <= pv_q[go_];
            end
        end
        always @(posedge clk) begin pg_q[go_] <= p_g[go_]; pg_q2[go_] <= pg_q[go_]; end
    end endgenerate
    // ---- chunk table (no reset: an entry is written whole at its issue, read only while live)
    always @(posedge clk) begin
        if (go) for (integer g = 0; g < NG; g = g + 1) ct_a[ct_t][g] <= i_ga[g];
        for (integer e = 0; e < LQ; e = e + 1)
            for (integer b = 0; b < NB; b = b + 1)
                if (go && ct_t == LW'(e)) ct_m[e][b] <= i_lv[b];
                else if (rd_v[b] && tg_q[b] == LW'(e)) ct_m[e][b] <= 1'b0;
    end
    // ---- H, window queue data (no reset: guarded by hv / wq_n)
    always @(posedge clk) begin
        if (h_pop) begin
            hk <= q_k[wq_h]; hpar <= q_par[wq_h];
            for (integer j = 0; j < 4; j = j + 1) begin
                hs_vs[j] <= q_vs[wq_h][j]; hs_sa[j] <= q_a[wq_h][j][36:5];
                hs_vn[j] <= q_vs[wq_h][j][14:3] + 12'd1; hs_an[j] <= q_a[wq_h][j][36:5] + 32'd8;
            end
        end else if (go && last_row && !last_chunk)
            for (integer j = 0; j < 4; j = j + 1) begin
                hs_vs[j] <= {hs_vn[j], 3'd0}; hs_sa[j] <= hs_an[j];
                hs_vn[j] <= hs_vn[j] + 12'd1; hs_an[j] <= hs_an[j] + 32'd8;
            end
        if (g1_v) begin
            q_k[wq_t] <= g1_k; q_par[wq_t] <= g1_par;
            for (integer j = 0; j < 4; j = j + 1) begin q_vs[wq_t][j] <= g1_vs[j]; q_a[wq_t][j] <= g1_a[j]; end
        end
        if (g_take) begin : g1d
            g1_k <= g_k4 ? 3'd4 : {1'b0, g_k};
            g1_vs[0] <= gw_vs; g1_vs[1] <= gw_vs + m_vstr; g1_vs[2] <= gw_vs + (m_vstr << 1); g1_vs[3] <= gw_vs + (m_vstr << 1) + m_vstr;
            g1_a[0] <= gw_a; g1_a[1] <= gw_a + m_st1; g1_a[2] <= gw_a + m_st2; g1_a[3] <= gw_a + m_st3;
            gw_vs <= gw_vs + (m_vstr << 2); gw_a <= gw_a + m_st4;
        end
        if (cv_q) begin : dec                    // the move's decoded registers (no reset: read only while busy)
            reg [36:0] st;
            st = {5'd0, cm_q[169:138]} + ((cm_q[137:135] == 3'd1) ? (37'd1 << SBIT) : 37'd0);
            m_vstr <= cm_q[62:48];
            m_st1 <= st; m_st2 <= st << 1; m_st3 <= (st << 1) + st; m_st4 <= st << 2;
            m_rsec <= 18'(cm_q[226:209]); m_lim <= STACK_BYTES - (36'(cm_q[226:209]) << 5);
            gw_vs <= cm_q[22:8]; gw_a <= cm_q[134:98];
            tot_sec <= 32'd0;
        end
        // the move's sector count, accumulated a window at a time (k rows x sectors a row; complete before iss_all)
        if (g_take) tot_sec <= tot_sec + (g_k4 ? 32'(m_rsec) << 2 : 32'd0) + (!g_k4 && g_k[1] ? 32'(m_rsec) << 1 : 32'd0) + (!g_k4 && g_k[0] ? 32'(m_rsec) : 32'd0);
    end
    // G2: the window's PAR flag / range check (combinational on the G1 registers, written with the queue entry)
    // A row stays inside its stack iff its stack-local start <= STACK_BYTES - row bytes (m_lim, registered at the decode;
    // STACK_BYTES < 2^SBIT, so this also keeps its last byte on the same stack): one compare, no add
    always @* begin : g2
        g1_par = 1'b1; g1_bad = 1'b0;
        for (integer j = 0; j < 4; j = j + 1) if (3'(j) < g1_k) begin
            for (integer j2 = 0; j2 < 4; j2 = j2 + 1) if (j2 > j && 3'(j2) < g1_k && (g1_vs[j][4:3] & GM) == (g1_vs[j2][4:3] & GM)) g1_par = 1'b0;
            if ({{(36 - SBIT){1'b0}}, g1_a[j][SBIT-1:0]} > m_lim || 3'(2'(g1_a[j][SBIT +: 2] - 2'(STK))) >= 3'(NS)) g1_bad = 1'b1;
        end
    end
    always @(posedge clk) if (mv_v && mv_rdy) cm_q <= mv;
    always @(posedge clk) landed <= (cv_q && elig) ? 32'd0 : landed + 32'(nl_q);
    // ---- control (reset region rc)
    always @(posedge clk or negedge rc) begin
        if (!rc) begin
            cv_q <= 1'b0; busy <= 1'b0; dirty <= 1'b0; mv_src <= 1'b0; mv_done <= 1'b0; mv_fault <= 1'b0; quiet_q <= 1'b1;
            g1_v <= 1'b0; g_left <= 20'd0; wq_h <= 2'd0; wq_t <= 2'd0; wq_n <= 3'd0; hv <= 1'b0; h_w <= 2'd0; h_rem <= 18'd0;
            iss_all <= 1'b0; s_vr2q[NB*16] <= 1'b0; ct_t <= '0; ct_h <= '0; ct_n <= '0;
            for (integer s = 0; s < NS; s = s + 1) begin out_n[s] <= 16'd0; ns_q[s] <= 4'd0; end
        end else begin
            mv_src <= 1'b0; mv_done <= 1'b0;
            quiet_q <= quiet_c && !(mv_v && mv_rdy);
            // ---- command station
            if (mv_v && mv_rdy) cv_q <= 1'b1;
            if (cv_q) begin
                cv_q <= 1'b0;
                if (!elig) mv_fault <= 1'b1;
                else begin busy <= 1'b1; dirty <= 1'b1; iss_all <= 1'b0; g_left <= cm_q[205:186]; end
            end
            // ---- G1 / G2
            g1_v <= g_take;
            if (g_take) g_left <= g_left - 20'((g_left >= 20'd4) ? 3'd4 : 3'(g_left));
            if (g1_v) begin if (g1_bad) mv_fault <= 1'b1; wq_t <= wq_t + 2'd1; end
            wq_n <= wq_n + {2'd0, g1_v} - {2'd0, h_pop};
            // ---- H
            if (h_pop) begin hv <= 1'b1; h_w <= 2'd0; h_rem <= m_rsec; wq_h <= wq_h + 2'd1; end
            else if (w_end) hv <= 1'b0;
            else if (go) begin
                if (last_row) begin h_rem <= h_rem - 18'd8; h_w <= 2'd0; end
                else h_w <= h_w + 2'd1;
            end
            if (w_end && g_left == 20'd0 && !g1_v && wq_n == 3'd0) iss_all <= 1'b1;
            // ---- I: the read group request, the chunk table
            s_vr2q[NB*16] <= busy || !(&all_home);
            if (go) ct_t <= ct_t + 1'b1;
            if (ct_adv) ct_h <= ct_h + 1'b1;
            ct_n <= ct_n + (LW+1)'(go) - (LW+1)'(ct_adv);
            // ---- W: sent / acknowledged counts
            for (integer s = 0; s < NS; s = s + 1) begin : ws
                reg [3:0] c; c = 4'd0;
                for (integer l = 0; l < NL; l = l + 1) c = c + 4'(pv_q2[s * NL + l]);
                ns_q[s] <= c;
                out_n[s] <= out_n[s] + 16'(ns_q[s]) - 16'(wap[s*4 +: 4]);
            end
            // ---- source consumed, done
            if (busy && iss_all && ((MUT == 2) || landed == tot_sec)) begin
                busy <= 1'b0; mv_src <= 1'b1;
            end
            if (dirty && quiet_c && !mv_v) begin dirty <= 1'b0; mv_done <= 1'b1; end
        end
    end
`ifndef SYNTHESIS
    reg trc; initial trc = $test$plusargs("DMA_TRACE");
    always @(posedge clk) if (trc && rc && cv_q)
        $display("BACK move sf %0d src %h sst %0d df %0d dst %h dstr %0d m %0d n %0d elig %0d", cm_q[4:2], cm_q[44:5], cm_q[76:45],
                 cm_q[97:95], cm_q[137:98], cm_q[169:138], cm_q[205:186], cm_q[226:206], elig);
`endif
endmodule
`default_nettype wire
