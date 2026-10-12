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
//   I  issue: a row's 8-sector CHUNK c is VM sectors vs + 8c .. (one bank group g, lanes 8g .. 8g + 7); a PAR window
//      issues chunk c of all its rows in one cycle (the STRIPE4 h swap: 32 sectors a cycle), else one row's chunk a
//      cycle (round robin over the window's rows).  A chunk issues when each lane it uses has a VM read credit and a
//      landing slot (LQ in flight a lane) and the read group is granted; each used lane gets the read {v, sector 15} on
//      the VM DMA wide READ group (the mover's VR2 contract) and pushes the sector's HBM sector address into its route
//      FIFO (in issue order = the lane's response order);
//   L  each VM lane's response is pin-flopped and lands in its landing FIFO (an ot_sram_1r1w_128x256 macro a lane, LQ
//      of its rows), read (macro output register) into a 3-entry skid on registered occupancy only;
//   W  stack lane (s, l) picks, rotating, one of the 4 VM lanes l, 8 + l, 16 + l, 24 + l whose skid head is for stack s,
//      while it holds an svc write credit, into its registered output {v, sector address 32, data 256}: the svc writes
//      the sector at its address (no request / tag / order: a beat is self-describing, any lane, any order);
//   A  the svc returns a lane credit when it pops a beat (wd_cr) and, per stack, the count of sectors written (wa, posted
//      acknowledgements, pin-flopped); quiet = every sent sector acknowledged.
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
    // ---------------------------------------------------------------- reset relay: a region a bank group + control
    wire [NS:0] rl;
    ot_rst_relay #(.REGIONS(NS + 1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rc = rl[NS];
    // ---------------------------------------------------------------- pin flops (VM group, svc credits / acks)
    reg g_gnt; reg [NB-1:0] vcp; reg [NB-1:0] rr_v; reg [255:0] rr_d [0:NB-1];
    reg [NB-1:0] wcp; reg [NS*4-1:0] wap;
    always @(posedge clk or negedge rc)
        if (!rc) begin g_gnt <= 1'b0; vcp <= '0; rr_v <= '0; wcp <= '0; wap <= '0; end
        else begin
            g_gnt <= vr2r[NB*258]; vcp <= vr2r[NB*258-1 -: NB]; wcp <= NB'(wd_cr); wap <= wa;
            for (integer b = 0; b < NB; b = b + 1) rr_v[b] <= vr2r[b*257 + 256];
        end
    always @(posedge clk) for (integer b = 0; b < NB; b = b + 1) rr_d[b] <= vr2r[b*257 +: 256];   // data: no reset
    // ---------------------------------------------------------------- command station + move registers
    reg cv_q; reg [226:0] cm_q;
    reg busy;                                    // a move's source is being read (accept .. src)
    reg dirty;                                   // a move accepted since the last done
    reg [14:0] m_vs; reg [14:0] m_vstr;          // VM row sector, row stride in sectors
    reg [36:0] m_a, m_st1, m_st2, m_st3, m_st4;  // HBM row byte address, row step x 1..4
    reg [17:0] m_rsec;                           // sectors a row
    reg [24:0] m_rowb;                           // bytes a row
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
    reg        g1_v; reg [2:0] g1_k; reg [14:0] g1_vs [0:3]; reg [36:0] g1_a [0:3];
    reg [14:0] gw_vs; reg [36:0] gw_a;           // the next window's first row
    reg [1:0]  wq_h, wq_t; reg [2:0] wq_n;
    reg [2:0]  q_k [0:3]; reg q_par [0:3]; reg [14:0] q_vs [0:3][0:3]; reg [36:0] q_a [0:3][0:3];
    wire       g_take = busy && g_left != 20'd0 && (wq_n + {2'd0, g1_v}) < 3'd4;
    // ---------------------------------------------------------------- issue state
    reg [14:0] i_c;                              // chunk index (all rows of the window)
    reg [1:0]  i_w;                              // serial: the window row
    reg [17:0] i_rem;                            // sectors of the row from chunk i_c on
    // per lane: landing occupancy (issued, not yet sent), VM credits
    reg [LW:0] l_cnt [0:NB-1]; reg [5:0] v_cr [0:NB-1];
    reg [NB-1:0] l_ok;                           // the lane takes a sector this cycle
    always @* for (integer b = 0; b < NB; b = b + 1) l_ok[b] = l_cnt[b] < (LW+1)'(LQ) && v_cr[b] != 6'd0;
    // ---- the head window's chunk: per row its group and lanes
    wire       h_v = wq_n != 3'd0;
    wire [2:0] h_k = q_k[wq_h]; wire h_par = q_par[wq_h];
    wire [3:0] c_len = (i_rem >= 18'd8) ? 4'd8 : 4'(i_rem);
    reg  [7:0] c_lm;                             // lanes used within the group
    always @* begin c_lm = 8'd0; for (integer l = 0; l < 8; l = l + 1) if (4'(l) < c_len) c_lm[l] = 1'b1; end
    reg [3:0] grp_ok;                            // bank group g: every used lane takes a sector
    always @* for (integer g = 0; g < 4; g = g + 1) grp_ok[g] = (g < NG) && &(l_ok[(g % NG)*8 +: 8] | ~c_lm);
    reg [1:0] r_g [0:3]; reg [3:0] r_in;         // row j: group of chunk i_c, row j present in the window
    always @* for (integer j = 0; j < 4; j = j + 1) begin
        r_g[j] = 2'(q_vs[wq_h][j][4:3] + i_c[1:0]) & GM;
        r_in[j] = 3'(j) < h_k;
    end
    reg [3:0] r_sel;                             // rows issuing this cycle
    reg       go;
    always @* begin
        r_sel = 4'd0;
        if (h_par) r_sel = r_in; else r_sel[i_w] = 1'b1;
        go = rc && h_v && g_gnt && !mv_fault;
        for (integer j = 0; j < 4; j = j + 1) if (r_sel[j] && !grp_ok[r_g[j]]) go = 1'b0;
    end
    wire last_row = h_par || (3'(i_w) + 3'd1 == h_k);
    wire last_chunk = i_rem <= 18'd8;
    wire w_end = go && last_row && last_chunk;
    // ---- the VM requests and route pushes of this cycle (registered into s_vr2q / the route FIFOs)
    reg [NB-1:0] i_lv; reg [14:0] i_sec [0:NB-1]; reg [31:0] i_sa [0:NB-1];
    always @* begin
        i_lv = '0;
        for (integer b = 0; b < NB; b = b + 1) begin i_sec[b] = 15'd0; i_sa[b] = 32'd0; end
        for (integer j = 0; j < 4; j = j + 1) if (go && r_sel[j]) begin : rj
            reg [14:0] s0; reg [36:0] a0;
            s0 = q_vs[wq_h][j] + {i_c[11:0], 3'd0};
            a0 = q_a[wq_h][j] + (37'(i_c) << 8);                   // + 8 c sectors x 32 B
            for (integer l = 0; l < 8; l = l + 1) if (c_lm[l]) begin
                i_lv[r_g[j]*8 + l] = 1'b1;
                i_sec[r_g[j]*8 + l] = s0 + 15'(l);
                i_sa[r_g[j]*8 + l] = a0[36:5] + 32'(l) + ((MUT == 1 && l == 1) ? 32'd1 : 32'd0);
            end
        end
    end
    reg [NB*16:0] s_vr2q; assign vr2q = s_vr2q;
    // ---------------------------------------------------------------- per lane: route FIFO, landing macro, skid
    reg [31:0] rt [0:NB-1][0:LQ-1];              // route: the sector address of each in-flight sector (issue order)
    reg [LW-1:0] rt_t [0:NB-1], d_t [0:NB-1], d_h [0:NB-1];
    reg [LW:0] d_n [0:NB-1];                     // landed, not yet read from the macro
    reg [NB-1:0] rd_i, rd_v;                     // macro read issued / its data valid this cycle
    reg [31:0] rd_sa [0:NB-1];
    wire [255:0] m_rd [0:NB-1];
    reg [287:0] sk [0:NB-1][0:2]; reg [1:0] sk_h [0:NB-1], sk_t [0:NB-1], sk_n [0:NB-1];
    reg [NB-1:0] pop;                            // the lane's skid head goes out this cycle
    always @* for (integer b = 0; b < NB; b = b + 1)
        rd_i[b] = d_n[b] != '0 && ({1'b0, sk_n[b]} + {2'd0, rd_v[b]}) < 3'd3;     // registered occupancy only
    genvar gb;
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_lane
        ot_sram_1r1w_128x256_m1_r2c2 u_q (.clk(clk), .r_ce_in(rd_i[gb]), .r_addr_in(7'(d_h[gb])), .rd_out(m_rd[gb]),
            .w_ce_in(rr_v[gb]), .w_addr_in(7'(d_t[gb])), .wd_in(rr_d[gb]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // ---------------------------------------------------------------- W: stack lane pickers
    reg [1:0] p_rr [0:NB-1];                     // rotating priority a stack lane
    reg [NB-1:0] p_v; reg [1:0] p_g [0:NB-1];   // stack lane (s, l) = index s*8 + l: picks VM lane p_g*8 + l
    reg [5:0] w_cr [0:NB-1];
    always @* begin
        pop = '0;
        for (integer s = 0; s < NS; s = s + 1) for (integer l = 0; l < NL; l = l + 1) begin : pk
            integer o;
            o = s * NL + l;
            p_v[o] = 1'b0; p_g[o] = 2'd0;
            for (integer t = NG - 1; t >= 0; t = t - 1) begin : cand
                reg [1:0] g; integer b;
                g = 2'(p_rr[o] + 2'(t)) & GM; b = g * 8 + l;
                if (sk_n[b] != 2'd0 && sk[b][sk_h[b]][256 + SBIT - 5 +: 2] == 2'(STK + s) && w_cr[o] != 6'd0) begin p_v[o] = 1'b1; p_g[o] = g; end
            end
            if (p_v[o]) pop[p_g[o] * 8 + l] = 1'b1;
        end
    end
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
    assign quiet = !cv_q && !busy && &all_home && !wq_any;
    always @(posedge clk or negedge rc) begin
        if (!rc) begin
            cv_q <= 1'b0; busy <= 1'b0; dirty <= 1'b0; mv_src <= 1'b0; mv_done <= 1'b0; mv_fault <= 1'b0;
            g1_v <= 1'b0; g_left <= 20'd0; wq_h <= 2'd0; wq_t <= 2'd0; wq_n <= 3'd0; i_c <= 15'd0; i_w <= 2'd0;
            iss_all <= 1'b0; tot_sec <= 32'd0; landed <= 32'd0; s_vr2q <= '0; wd <= '0;
            for (integer b = 0; b < NB; b = b + 1) begin
                l_cnt[b] <= '0; v_cr[b] <= 6'(VCR); rt_t[b] <= '0; d_t[b] <= '0; d_h[b] <= '0; d_n[b] <= '0;
                sk_h[b] <= 2'd0; sk_t[b] <= 2'd0; sk_n[b] <= 2'd0; p_rr[b] <= 2'd0; w_cr[b] <= 6'(WCR);
            end
            rd_v <= '0;
            for (integer s = 0; s < NS; s = s + 1) begin out_n[s] <= 16'd0; ns_q[s] <= 4'd0; end
        end else begin
            mv_src <= 1'b0; mv_done <= 1'b0;
            // ---- command station
            if (mv_v && mv_rdy) begin cv_q <= 1'b1; cm_q <= mv; end
            if (cv_q) begin
                cv_q <= 1'b0;
                if (!elig) mv_fault <= 1'b1;
                else begin : dec
                    reg [36:0] st;
                    st = {5'd0, cm_q[169:138]} + ((cm_q[137:135] == 3'd1) ? (37'd1 << SBIT) : 37'd0);
                    busy <= 1'b1; dirty <= 1'b1; iss_all <= 1'b0; landed <= 32'd0;
                    m_vs <= cm_q[22:8]; m_vstr <= cm_q[62:48]; m_a <= cm_q[134:98];
                    m_st1 <= st; m_st2 <= st << 1; m_st3 <= (st << 1) + st; m_st4 <= st << 2;
                    m_rsec <= 18'(cm_q[226:209]); m_rowb <= 25'(cm_q[226:209]) << 5;
                    g_left <= cm_q[205:186]; gw_vs <= cm_q[22:8]; gw_a <= cm_q[134:98];
                    tot_sec <= 32'(cm_q[205:186]) * 32'(cm_q[226:209]);
                    i_rem <= 18'(cm_q[226:209]); i_c <= 15'd0; i_w <= 2'd0;
                end
            end
            // ---- G1: the window's rows
            g1_v <= g_take;
            if (g_take) begin : g1
                reg [2:0] k;
                k = (g_left >= 20'd4) ? 3'd4 : 3'(g_left);
                g1_k <= k;
                g1_vs[0] <= gw_vs; g1_vs[1] <= gw_vs + m_vstr; g1_vs[2] <= gw_vs + (m_vstr << 1); g1_vs[3] <= gw_vs + (m_vstr << 1) + m_vstr;
                g1_a[0] <= gw_a; g1_a[1] <= gw_a + m_st1; g1_a[2] <= gw_a + m_st2; g1_a[3] <= gw_a + m_st3;
                gw_vs <= gw_vs + (m_vstr << 2); gw_a <= gw_a + m_st4;
                g_left <= g_left - 20'(k);
            end
            // ---- G2: groups, PAR, range check -> window queue
            if (g1_v) begin : g2
                reg par, bad; reg [36:0] e; reg [36:0] lo;
                par = 1'b1; bad = 1'b0;
                for (integer j = 0; j < 4; j = j + 1) if (3'(j) < g1_k) begin
                    for (integer j2 = 0; j2 < 4; j2 = j2 + 1) if (j2 > j && 3'(j2) < g1_k && (g1_vs[j][4:3] & GM) == (g1_vs[j2][4:3] & GM)) par = 1'b0;
                    e = g1_a[j] + {12'd0, m_rowb} - 37'd1;
                    lo = {1'b0, {(36 - SBIT){1'b0}}, g1_a[j][SBIT-1:0]} + {12'd0, m_rowb};
                    if (e[SBIT +: 2] != g1_a[j][SBIT +: 2] || lo > {1'b0, STACK_BYTES} ||
                        3'(2'(g1_a[j][SBIT +: 2] - 2'(STK))) >= 3'(NS)) bad = 1'b1;
                end
                if (bad) mv_fault <= 1'b1;
                q_k[wq_t] <= g1_k; q_par[wq_t] <= par;
                for (integer j = 0; j < 4; j = j + 1) begin q_vs[wq_t][j] <= g1_vs[j]; q_a[wq_t][j] <= g1_a[j]; end
                wq_t <= wq_t + 2'd1;
            end
            wq_n <= wq_n + {2'd0, g1_v} - {2'd0, w_end};
            // ---- I: issue
            s_vr2q[NB*16] <= busy || !(&all_home);
            for (integer b = 0; b < NB; b = b + 1) s_vr2q[b*16 +: 16] <= {i_lv[b], i_sec[b]};
            if (go) begin
                if (last_row) begin
                    if (last_chunk) begin i_c <= 15'd0; i_rem <= m_rsec; end
                    else begin i_c <= i_c + 15'd1; i_rem <= i_rem - 18'd8; end
                    i_w <= 2'd0;
                end else i_w <= i_w + 2'd1;
                if (w_end) begin
                    wq_h <= wq_h + 2'd1;
                    if (g_left == 20'd0 && !g1_v && wq_n == 3'd1) iss_all <= 1'b1;
                end
            end
            // ---- per lane
            for (integer b = 0; b < NB; b = b + 1) begin
                if (i_lv[b]) begin rt[b][rt_t[b]] <= i_sa[b]; rt_t[b] <= rt_t[b] + 1'b1; end
                l_cnt[b] <= l_cnt[b] + (LW+1)'(i_lv[b]) - (LW+1)'(pop[b]);
                v_cr[b] <= v_cr[b] - 6'(i_lv[b]) + 6'(vcp[b]);
                if (rr_v[b]) d_t[b] <= d_t[b] + 1'b1;
                d_n[b] <= d_n[b] + (LW+1)'(rr_v[b]) - (LW+1)'(rd_i[b]);
                if (rd_i[b]) begin d_h[b] <= d_h[b] + 1'b1; rd_sa[b] <= rt[b][d_h[b]]; end
                rd_v[b] <= rd_i[b];
                if (rd_v[b]) begin sk[b][sk_t[b]] <= {rd_sa[b], m_rd[b]}; sk_t[b] <= (sk_t[b] == 2'd2) ? 2'd0 : sk_t[b] + 2'd1; end
                if (pop[b]) sk_h[b] <= (sk_h[b] == 2'd2) ? 2'd0 : sk_h[b] + 2'd1;
                sk_n[b] <= sk_n[b] + 2'(rd_v[b]) - 2'(pop[b]);
            end
            // ---- W: stack lane outputs, svc credits, sent / acknowledged counts
            for (integer s = 0; s < NS; s = s + 1) begin : ws
                reg [3:0] c; c = 4'd0;
                for (integer l = 0; l < NL; l = l + 1) begin : wl
                    integer o, b;
                    o = s * NL + l; b = p_g[o] * 8 + l;
                    wd[o*289 +: 289] <= p_v[o] ? {1'b1, sk[b][sk_h[b]]} : 289'd0;
                    w_cr[o] <= w_cr[o] - 6'(p_v[o]) + 6'(wcp[o]);
                    if (p_v[o]) p_rr[o] <= (p_g[o] + 2'd1) & GM;
                    c = c + 4'(p_v[o]);
                end
                ns_q[s] <= c;
                out_n[s] <= out_n[s] + 16'(ns_q[s]) - 16'(wap[s*4 +: 4]);
            end
            // ---- source consumed, done
            if (!(cv_q && elig)) landed <= landed + 32'(nl_q);
            if (busy && iss_all && ((MUT == 2) || landed == tot_sec)) begin
                busy <= 1'b0; mv_src <= 1'b1;
            end
            if (dirty && quiet && !mv_v) begin dirty <= 1'b0; mv_done <= 1'b1; end
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
