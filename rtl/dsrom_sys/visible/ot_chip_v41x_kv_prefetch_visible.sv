`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Attention KV prefetch of the adopted V4.1 layer die: the die-side end of the
// core's KV_HBM handshake with the KV in HBM.
//
// ADDRESS LAYOUT.  An attention op (ot_hdc_v41x_att_adapt) reads, in order
// c = 0, 1, ..., n-1 (G words a cycle, c = lc .. lc + G - 1), the KV words
//     A(c) = wbase + t*ts + k*ks,   t = c / k_n, k = c mod k_n,
// with n = tiles * (G >> hg) * k_n (js = 0; the adapter faults otherwise).
// The descriptor (kvd_*) carries exactly those fields.  KV word A of the
// running user lives at U = base + A: stack U mod 4, sectors
//     KV_SBASE + 2 * (U >> 2) + {0, 1}  (a 512-bit word is two 32-byte sectors,
// which the stacks' address map puts on one pseudo-channel), in the KV region
// [KV_SBASE, KV_SBASE + KV_SECTORS) of every stack, disjoint from the index
// keys [0, KV_SBASE) (checked at elaboration by the die); every issued sector
// is checked against the region at run time (fault, never a wrap).
//
// SIZING.  A KV word is 16 elements.  The largest op the attention adapter
// accepts (T <= TROWS rows, head dim D) reads at most NMAX words (q.k: D words
// per row tile, p.v: T rows per dim tile, tiles rounded up to G): 960 words at
// TROWS = 160, D = 32, so STG = 2048 words a slot holds any op (checked at
// elaboration); two slots are 2 x 2048 x 64 B = 256 KiB of staging SRAM.
//
// STAGING.  Two slots of STG words (the op being read, the op being fetched).
// kvd_v claims the free slot and fetches its n words, one request a cycle,
// words to their stacks, the responses landing by tag {generation, slot,
// entry, half}; kv_ok is high while the newest descriptor's slot has all its
// words (and no write has just hit it).  The core reads the head slot in order:
// read c of the head slot returns entry c, and the address it presents is
// checked against the entry's (fault on a mismatch, on a read of a slot that
// is not complete, or on a descriptor with both slots busy / n > STG).  A slot
// is evicted when its n words have been read; nothing is written back (writes
// are written through).
//
// RUNTIME KV WRITES (the stream / vector units' new K and V elements):
// WRITE-THROUGH.  The element writes of a cycle are combined per sector (up to
// CMB = SW + SUN sectors a cycle, 4-byte strobes) into one write queue per
// stack (a K row is one lane in each of HD words: every lane can be its own
// sector), each draining a sector a cycle; all drain before any fetch request, so a later fetch of the same
// sector is queued behind the write in its pseudo-channel and sees the new
// data (the model's same-sector ordering).  COHERENCE: a write whose word falls
// in the address range of a slot not yet read restarts that slot's fetch (new
// generation) once the write has drained and the old generation's responses
// have all returned (an outstanding count per slot: generations never overlap
// in flight, and any stale response is dropped by its generation), and drops
// kv_ok the same cycle; a write into a slot being read faults (the program's
// hazard waits exclude it).
// ---------------------------------------------------------------------------
module ot_chip_v41x_kv_prefetch_visible #(
    parameter integer PUBLICATION=0,
    parameter integer MAX_PENDING=2048,
    parameter integer G        = 4,
    parameter integer W        = 16,
    parameter integer SW       = 8,
    parameter integer SUN      = 16,
    parameter integer AW       = 24,
    parameter integer STG      = 2048,        // words per staging slot
    parameter integer SAW      = 11,          // log2(STG)
    parameter integer KV_SBASE = 1 << 18,     // KV region, sector base on every stack
    parameter integer KV_SECTORS = 1 << 14,   // KV region size per stack (sectors)
    parameter integer TROWS    = 160,         // the attention adapter's rows per job (ot_hdc_v41x_att_adapt)
    parameter integer D        = 32,          // its head dim
    parameter integer HAW      = 28,
    parameter integer TAGW     = 16,
    parameter integer WQD      = 128,          // write-queue sectors per stack
    parameter integer CMB      = SW + SUN     // sectors combined a cycle (every lane a different sector)
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire [AW-1:0]       base,          // the running user's KV word base
    // descriptor / permission
    input  wire                kvd_v,
    input  wire [AW-1:0]       kvd_wbase,
    input  wire [AW-1:0]       kvd_ts,
    input  wire [AW-1:0]       kvd_ks,
    input  wire [AW-1:0]       kvd_js,
    input  wire [15:0]         kvd_tiles,
    input  wire [15:0]         kvd_k,
    input  wire [1:0]          kvd_hg,
    output wire                kv_ok,
    // the core's KV port
    input  wire                re,
    input  wire [G*AW-1:0]     raddr,
    output reg  [G*W*32-1:0]   q,
    input  wire [SW-1:0]       we,
    input  wire [SW*AW-1:0]    waddr,
    input  wire [SW*32-1:0]    wdata,
    input  wire [SUN-1:0]      xwe,
    input  wire [SUN*AW-1:0]   xwaddr,
    input  wire [SUN*32-1:0]   xwdata,
    // one request channel and one response channel per stack (ot_chip_v41x_hbm_karb K side)
    output reg  [3:0]          m_v,
    input  wire [3:0]          m_rdy,
    input wire [3:0] m_wr_done,
    input wire [4*6-1:0] m_wr_done_count,
    output wire write_quiet,
    output reg write_fault=0,write_quarantine=0,
    output reg  [4*HAW-1:0]    m_addr,
    output reg  [4*4-1:0]      m_len,
    output reg  [4*TAGW-1:0]   m_tag,
    output reg  [3:0]          m_we,
    output reg  [4*256-1:0]    m_wdata,
    output reg  [4*32-1:0]     m_wstrb,
    input  wire [3:0]          s_v,
    output wire [3:0]          s_rdy,
    input  wire [4*TAGW-1:0]   s_tag,
    input  wire [4*4-1:0]      s_beat,
    input  wire [4*256-1:0]    s_data,
    // status
    output reg                 fault,
    output reg  [4:0]          fault_code,    // [0] slots / size, [1] read, [2] write into a slot being read,
                                              // [3] queue, [4] a sector outside the KV region
    output reg  [31:0]         st_ops,
    output reg  [31:0]         st_words,
    output reg  [31:0]         st_sectors_written,
    output reg  [31:0]         st_refetches,
    output reg  [31:0]         st_wq_high,
    output reg  [31:0]         st_hold_cycles  // cycles kv_ok was low with a descriptor pending
);
    localparam integer NPW = 2;               // sectors per word
    // The largest op the adapter accepts, in KV WORDS (16 elements each): q.k reads k = D words for each of
    // ceil(T / W) row tiles (rounded up to a multiple of G >> hg <= G), p.v reads k = T rows for each of
    // ceil(D / W) dim tiles (likewise); T <= TROWS.
    localparam integer NMAX_QK = ((TROWS + W - 1) / W + G) * D;
    localparam integer NMAX_PV = ((D + W - 1) / W + G) * TROWS;
    localparam integer NMAX = (NMAX_QK > NMAX_PV) ? NMAX_QK : NMAX_PV;
`ifndef SYNTHESIS
    initial begin
        if (STG < NMAX) $fatal(1, "ot_chip_v41x_kv_prefetch: STG %0d < the largest op, %0d words", STG, NMAX);
        if ((1 << SAW) != STG) $fatal(1, "ot_chip_v41x_kv_prefetch: STG must be 2^SAW");
        if (TAGW < SAW + 3) $fatal(1, "ot_chip_v41x_kv_prefetch: tag too narrow");
    end
`endif
    // -- slots -------------------------------------------------------------------------------
    reg          sv    [0:1];                 // valid
    reg  [1:0]   sgen  [0:1];
    reg  [AW-1:0] swb  [0:1], sts [0:1], sks [0:1], slo [0:1], shi [0:1];
    reg  [15:0]  skn   [0:1];
    reg  [SAW:0] sn    [0:1];                 // words
    reg  [SAW:0] sfi   [0:1];                 // words requested
    reg  [SAW+1:0] sha [0:1];                 // halves arrived
    reg  [SAW:0] src   [0:1];                 // words read
    reg          srst  [0:1];                 // restart pending (a write hit it)
    reg  [SAW+1:0] sout [0:1];                // halves requested and not yet returned (any generation)
    reg  [15:0]  sft [0:1], sfk [0:1];        // fetch counters t, k
    reg  [AW-1:0] sfa  [0:1];                 // A of the next fetch
    reg  [AW-1:0] sft_a [0:1];                // A at k = 0 of the current t
    // staging and the address of every staged word: one memory each, entry {slot, index}
    reg  [511:0] stg   [0:2*STG-1];
    reg  [AW-1:0] sadr [0:2*STG-1];
    reg          head;                        // slot being read
    reg          tail;                        // newest descriptor's slot
    wire         both = sv[0] && sv[1];
    // A restart (new generation) waits until the write queue has drained AND every response of the slot's
    // older generations has returned: generations never overlap in flight, so the 2-bit generation in the
    // tag cannot wrap onto a live one, and a stale response is dropped by its generation.
    wire [1:0]   rs_go;
    wire         complete_t = sv[tail] && !srst[tail] && sfi[tail] == sn[tail] && sha[tail] == {sn[tail], 1'b0};
    // -- runtime writes: combine this cycle's lanes per sector ----------------------------------
    localparam integer NL = SW + SUN;
    reg  [AW-1:0] l_word [0:NL-1];
    reg           l_v    [0:NL-1];
    reg  [3:0]    l_lane [0:NL-1];
    reg  [31:0]   l_data [0:NL-1];
    reg  [AW:0]   c_sec  [0:CMB-1];           // {word, half}
    reg           c_v    [0:CMB-1];
    reg  [255:0]  c_d    [0:CMB-1];
    reg  [31:0]   c_s    [0:CMB-1];
    reg           c_over;
    reg  [1:0]    hit;                        // a write this cycle hits slot s's range
    integer i, j, s;
    reg found;
    always @(*) begin
        for (i = 0; i < SW; i = i + 1) begin
            l_v[i] = we[i]; l_word[i] = base + (waddr[i*AW +: AW] >> 4); l_lane[i] = waddr[i*AW +: 4];
            l_data[i] = wdata[32*i +: 32];
        end
        for (i = 0; i < SUN; i = i + 1) begin
            l_v[SW+i] = xwe[i]; l_word[SW+i] = base + (xwaddr[i*AW +: AW] >> 4); l_lane[SW+i] = xwaddr[i*AW +: 4];
            l_data[SW+i] = xwdata[32*i +: 32];
        end
        c_over = 1'b0; found = 1'b0; hit = 2'b00;
        for (j = 0; j < CMB; j = j + 1) begin c_v[j] = 1'b0; c_sec[j] = '0; c_d[j] = '0; c_s[j] = '0; end
        for (i = 0; i < NL; i = i + 1) if (l_v[i]) begin
            found = 1'b0;
            for (j = 0; j < CMB; j = j + 1)
                if (!found && c_v[j] && c_sec[j] == {l_word[i], l_lane[i][3]}) begin
                    found = 1'b1;
                    c_d[j][32*l_lane[i][2:0] +: 32] = l_data[i]; c_s[j][4*l_lane[i][2:0] +: 4] = 4'hf;
                end
            for (j = 0; j < CMB; j = j + 1)
                if (!found && !c_v[j]) begin
                    found = 1'b1; c_v[j] = 1'b1; c_sec[j] = {l_word[i], l_lane[i][3]};
                    c_d[j][32*l_lane[i][2:0] +: 32] = l_data[i]; c_s[j][4*l_lane[i][2:0] +: 4] = 4'hf;
                end
            if (!found) c_over = 1'b1;
        end
        for (s = 0; s < 2; s = s + 1) begin
            hit[s] = 1'b0;
            for (i = 0; i < NL; i = i + 1)
                if (l_v[i] && sv[s] && src[s] == 0 && l_word[i] >= slo[s] && l_word[i] <= shi[s]) hit[s] = 1'b1;
        end
    end
    assign kv_ok = !(sv[0] || sv[1]) || (complete_t && !hit[tail]);
    assign rs_go[0] = srst[0] && !hit[0] && wq_empty && (!PUBLICATION || pending_empty) && !c_v[0] && sout[0] == 0;
    assign rs_go[1] = srst[1] && !hit[1] && wq_empty && (!PUBLICATION || pending_empty) && !c_v[0] && sout[1] == 0;

    // -- write queues: one per stack (a sector's order is kept within its stack, which is all a same-sector
    //    read-after-write needs); each drains one sector a cycle to its stack ---------------------------
    localparam integer QW = $clog2(WQD);
    reg  [AW:0]  wq_sec [0:4*WQD-1];              // entry {stack, pointer}
    reg  [255:0] wq_d   [0:4*WQD-1];
    reg  [31:0]  wq_s   [0:4*WQD-1];
    reg  [QW-1:0] wq_rp [0:3], wq_wp [0:3];
    reg  [QW:0]  wq_n   [0:3];
    wire         wq_empty = (wq_n[0] == 0) && (wq_n[1] == 0) && (wq_n[2] == 0) && (wq_n[3] == 0);
    wire [HAW-1:0] wq_haddr [0:3];
    wire [3:0]   wq_oor_s;
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_wq
        wire [AW:0] hs = wq_sec[{2'(gq), wq_rp[gq]}];
        assign wq_haddr[gq] = HAW'(KV_SBASE) + HAW'({hs[AW:1] >> 2, 1'b0}) + HAW'(hs[0]);
        assign wq_oor_s[gq] = (wq_haddr[gq] < HAW'(KV_SBASE)) || (wq_haddr[gq] >= HAW'(KV_SBASE) + HAW'(KV_SECTORS));
    end endgenerate
    // -- fetch: the slot to fetch (head first) ---------------------------------------------------------
    wire f_h = sv[head] && !srst[head] && sfi[head] != sn[head];
    wire f_t = sv[!head] && !srst[!head] && sfi[!head] != sn[!head];
    wire fs  = f_h ? head : !head;
    wire f_any = (f_h || f_t) && wq_empty && (!PUBLICATION || pending_empty);
    wire [AW-1:0] fa = base + sfa[fs];
    wire [1:0]    f_stk = fa[1:0];
    wire [HAW-1:0] f_haddr = HAW'(KV_SBASE) + HAW'({fa >> 2, 1'b0});
    wire [TAGW-1:0] f_tag = TAGW'({sgen[fs], fs, sfi[fs][SAW-1:0]});
    // request mux: each stack's write queue first; the fetch once every write has been issued
    integer ms;
    always @(*) begin
        m_v = 4'd0; m_addr = '0; m_len = '0; m_tag = '0; m_we = 4'd0; m_wdata = '0; m_wstrb = '0;
        for (ms = 0; ms < 4; ms = ms + 1)
            if (wq_n[ms] != 0) begin
                m_v[ms] = 1'b1; m_addr[ms*HAW +: HAW] = wq_haddr[ms]; m_len[ms*4 +: 4] = 4'd1; m_we[ms] = 1'b1;
                m_wdata[ms*256 +: 256] = wq_d[{2'(ms), wq_rp[ms]}]; m_wstrb[ms*32 +: 32] = wq_s[{2'(ms), wq_rp[ms]}];
            end
        if (wq_empty && f_any) begin
            m_v[f_stk] = 1'b1; m_addr[f_stk*HAW +: HAW] = f_haddr; m_len[f_stk*4 +: 4] = 4'd2;
            m_tag[f_stk*TAGW +: TAGW] = f_tag;
        end
    end
    wire [3:0] wq_pop;
    assign wq_pop[0] = wq_n[0] != 0 && m_rdy[0];
    assign wq_pop[1] = wq_n[1] != 0 && m_rdy[1];
    assign wq_pop[2] = wq_n[2] != 0 && m_rdy[2];
    assign wq_pop[3] = wq_n[3] != 0 && m_rdy[3];
    // every issued sector must lie in the KV region: an out-of-range address faults, it never wraps
    wire wq_oor = |(wq_pop & wq_oor_s);
    wire f_oor  = (f_haddr < HAW'(KV_SBASE)) || (f_haddr + HAW'(1) >= HAW'(KV_SBASE) + HAW'(KV_SECTORS));
    wire f_go = wq_empty && f_any && m_rdy[f_stk];
    assign s_rdy = 4'hf;

    localparam integer PCW=$clog2(MAX_PENDING+1);
    reg [PCW-1:0] pending[0:3];
    wire pending_empty=pending[0]==0 && pending[1]==0 && pending[2]==0 && pending[3]==0;
    assign write_quiet=wq_empty && !c_v[0] && (!PUBLICATION || (pending_empty && !write_fault && !write_quarantine));
    initial for(integer p=0;p<4;p=p+1)pending[p]=0;
    // Preserve pending ACK debt at warm reset; native journals retain identities.
    always @(posedge clk)begin
     if(!rst_n)begin
      if(PUBLICATION && (!pending_empty || !wq_empty || c_v[0]))write_quarantine<=1;
     end else if(PUBLICATION && !write_fault && !write_quarantine)begin
      for(integer p=0;p<4;p=p+1)begin:pub
       integer accepted,completed,next_count;
       accepted=m_v[p] && m_rdy[p] && m_we[p];
       completed=32'(m_wr_done_count[p*6+:6]);
       next_count=32'(pending[p])+accepted-completed;
       if(m_wr_done[p]!=(completed!=0) || completed>32'(pending[p]) || next_count>MAX_PENDING)begin
        write_fault<=1;write_quarantine<=1;
       end else pending[p]<=PCW'(next_count);
      end
     end
    end

    // -- read service ----------------------------------------------------------------------------------
    reg [AW-1:0] exp_a;
    reg [SAW:0]  rc;
    integer p;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (s = 0; s < 2; s = s + 1) begin
                sv[s] <= 1'b0; sgen[s] <= 2'd0; srst[s] <= 1'b0; sn[s] <= 0; sfi[s] <= 0; sha[s] <= 0; src[s] <= 0;
                sout[s] <= 0;
            end
            head <= 1'b0; tail <= 1'b0; fault <= 1'b0; fault_code <= 5'd0;
            for (s = 0; s < 4; s = s + 1) begin wq_rp[s] <= 0; wq_wp[s] <= 0; wq_n[s] <= 0; end
            st_ops <= 0; st_words <= 0; st_sectors_written <= 0; st_refetches <= 0; st_wq_high <= 0;
            st_hold_cycles <= 0;
        end else begin
            // write queue: push this cycle's combined sectors, pop the head
            begin : wq_upd
                integer k2, q2, np;
                reg [QW-1:0] w [0:3];
                reg [QW+1:0] n2 [0:3];
                reg [1:0] st2;
                np = 0;
                for (q2 = 0; q2 < 4; q2 = q2 + 1) begin w[q2] = wq_wp[q2]; n2[q2] = 0; end
                for (k2 = 0; k2 < CMB; k2 = k2 + 1) if (c_v[k2]) begin
                    st2 = c_sec[k2][2:1];                       // the stack: word[1:0]
                    wq_sec[{st2, w[st2]}] <= c_sec[k2]; wq_d[{st2, w[st2]}] <= c_d[k2]; wq_s[{st2, w[st2]}] <= c_s[k2];
                    w[st2] = w[st2] + 1'b1; n2[st2] = n2[st2] + 1'b1; np = np + 1;
                end
                for (q2 = 0; q2 < 4; q2 = q2 + 1) begin
                    wq_wp[q2] <= w[q2];
                    if (wq_pop[q2]) wq_rp[q2] <= wq_rp[q2] + 1'b1;
                    wq_n[q2] <= wq_n[q2] + (QW+1)'(n2[q2]) - {{QW{1'b0}}, wq_pop[q2]};
                    if (32'(wq_n[q2]) + 32'(n2[q2]) > st_wq_high) st_wq_high <= 32'(wq_n[q2]) + 32'(n2[q2]);
                    if (32'(wq_n[q2]) + 32'(n2[q2]) > WQD) begin fault <= 1'b1; fault_code[3] <= 1'b1; end
                end
                if (c_over) begin fault <= 1'b1; fault_code[3] <= 1'b1; end
                st_sectors_written <= st_sectors_written + 32'($countones(wq_pop));
            end
            if ((sv[0] || sv[1]) && !kv_ok) st_hold_cycles <= st_hold_cycles + 1;
            // coherence: a write into a slot not yet read restarts it; into a slot being read faults
            for (s = 0; s < 2; s = s + 1) begin
                if (hit[s]) begin
                    srst[s] <= 1'b1; st_refetches <= st_refetches + 1;
                end
            end
            begin : wr_into_reading
                integer i2;
                for (s = 0; s < 2; s = s + 1)
                    for (i2 = 0; i2 < NL; i2 = i2 + 1)
                        if (l_v[i2] && sv[s] && src[s] != 0 && l_word[i2] >= slo[s] && l_word[i2] <= shi[s]) begin
                            fault <= 1'b1; fault_code[2] <= 1'b1;
                        end
            end
            // a restart takes effect once the write queue has drained (the rewrites are ahead of the fetch)
            for (s = 0; s < 2; s = s + 1)
                if (rs_go[s]) begin
                    srst[s] <= 1'b0; sgen[s] <= sgen[s] + 1'b1; sfi[s] <= 0; sha[s] <= 0;
                    sft[s] <= 0; sfk[s] <= 0; sfa[s] <= swb[s]; sft_a[s] <= swb[s];
                end
            if (wq_oor || (f_go && f_oor)) begin
                fault <= 1'b1; fault_code[4] <= 1'b1;
`ifndef SYNTHESIS
                $error("ot_chip_v41x_kv_prefetch: KV sector %0d outside [%0d, %0d)",
                       f_haddr, KV_SBASE, KV_SBASE + KV_SECTORS);
`endif
            end
            // fetch issue
            if (f_go) begin
                sfi[fs] <= sfi[fs] + 1'b1;
                st_words <= st_words + 1;
                if (sfk[fs] + 1 == skn[fs]) begin
                    sfk[fs] <= 0; sft[fs] <= sft[fs] + 1'b1;
                    sft_a[fs] <= sft_a[fs] + sts[fs]; sfa[fs] <= sft_a[fs] + sts[fs];
                end else begin
                    sfk[fs] <= sfk[fs] + 1'b1; sfa[fs] <= sfa[fs] + sks[fs];
                end
            end
            // responses
            begin : arrivals
                integer a0, a1, o0, o1, p2;
                reg [TAGW-1:0] t2;
                a0 = 0; a1 = 0; o0 = 0; o1 = 0;
                for (p2 = 0; p2 < 4; p2 = p2 + 1) if (s_v[p2]) begin
                    t2 = s_tag[p2*TAGW +: TAGW];
                    if (t2[SAW]) o1 = o1 + 1; else o0 = o0 + 1;
                    if (sv[t2[SAW]] && t2[SAW+2:SAW+1] == sgen[t2[SAW]] && !srst[t2[SAW]]) begin
                        if (t2[SAW]) a1 = a1 + 1; else a0 = a0 + 1;
                    end
                end
                if (!rs_go[0]) sha[0] <= sha[0] + (SAW+2)'(a0);
                if (!rs_go[1]) sha[1] <= sha[1] + (SAW+2)'(a1);
                // outstanding halves: +2 a word request, -1 a response of the slot, whatever its generation
                sout[0] <= sout[0] + ((f_go && fs == 1'b0) ? (SAW+2)'(2) : '0) - (SAW+2)'(o0);
                sout[1] <= sout[1] + ((f_go && fs == 1'b1) ? (SAW+2)'(2) : '0) - (SAW+2)'(o1);
            end
            // core reads of the head slot
            if (re) begin
                if (!sv[head] || srst[head] || sha[head] != {sn[head], 1'b0}) begin
                    fault <= 1'b1; fault_code[1] <= 1'b1;
                end
                for (p = 0; p < G; p = p + 1)
                    if (src[head] + p < sn[head] && raddr[p*AW +: AW] != sadr[{head, src[head][SAW-1:0] + SAW'(p)}]) begin
                        fault <= 1'b1; fault_code[1] <= 1'b1;
                    end
                if (src[head] + G >= sn[head]) begin
                    sv[head] <= 1'b0; src[head] <= 0; head <= !head;
                end else src[head] <= src[head] + G;
            end
            // descriptor: claim a slot
            if (kvd_v) begin : claim
                reg ns, ret, hn;
                reg [1:0] vn;
                reg [31:0] n32;
                // the slots after this cycle's retire; the new op goes behind the (new) head
                ret = re && sv[head] && (src[head] + G >= sn[head]);
                vn[0] = sv[0] && !(ret && head == 1'b0);
                vn[1] = sv[1] && !(ret && head == 1'b1);
                hn = ret ? !head : head;
                ns = vn[hn] ? !hn : hn;
                n32 = 32'(kvd_tiles) * 32'(G >> kvd_hg) * 32'(kvd_k);
                if ((vn[0] && vn[1]) || sout[ns] != 0 || n32 > STG || n32 == 0 || kvd_js != 0) begin
                    fault <= 1'b1; fault_code[0] <= 1'b1;
                end
                sv[ns] <= 1'b1; tail <= ns; srst[ns] <= 1'b0;
                sgen[ns] <= sgen[ns] + 1'b1;
                swb[ns] <= kvd_wbase; sts[ns] <= kvd_ts; sks[ns] <= kvd_ks; skn[ns] <= kvd_k;
                sn[ns] <= (SAW+1)'(n32); sfi[ns] <= 0; sha[ns] <= 0; src[ns] <= 0;
                sft[ns] <= 0; sfk[ns] <= 0; sfa[ns] <= kvd_wbase; sft_a[ns] <= kvd_wbase;
                slo[ns] <= base + kvd_wbase;
                shi[ns] <= base + kvd_wbase + AW'(32'(kvd_tiles) * 32'(G >> kvd_hg) - 1) * kvd_ts
                           + AW'(32'(kvd_k) - 1) * kvd_ks;
                st_ops <= st_ops + 1;
            end
        end
    end
    // the memories (no reset): staged addresses at fetch, response halves by tag, read data (latency 1):
    // entry c = src + p of the head slot
    integer pr;
    reg [TAGW-1:0] rt;
    always @(posedge clk) begin
        if (f_go) sadr[{fs, sfi[fs][SAW-1:0]}] <= sfa[fs];
        for (pr = 0; pr < 4; pr = pr + 1) begin
            rt = s_tag[pr*TAGW +: TAGW];
            if (s_v[pr] && sv[rt[SAW]] && rt[SAW+2:SAW+1] == sgen[rt[SAW]] && !srst[rt[SAW]])
                stg[{rt[SAW], rt[SAW-1:0]}][256*s_beat[pr*4] +: 256] <= s_data[pr*256 +: 256];
        end
        if (re)
            for (i = 0; i < G; i = i + 1)
                q[i*W*32 +: W*32] <= stg[{head, src[head][SAW-1:0] + SAW'(i)}];
    end
endmodule
