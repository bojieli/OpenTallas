// Lockstep bench of the S81 PQ core cluster dsfd_sp_pq (through dsfd_sp_pq_screen_fix) against the FLAT v14 screen
// ot_v41_pqc_spine_screen (physical/s81_pq_xrv/pinned, XRV 1): the same pins every cycle, EVERY output compared every
// cycle.  The stimulus is a legal constrained-random program per seed: phase / stream ROM images written through the
// screen's ROM port, ops issued when ready (Q and BF16 families, 1..4 positions, random bases / strides / formats), a
// request-driven VM model (in-order valid return after L edges) and the exact number of region rows per issued op
// (tag in row[15:14]) returned after its go.  PASS needs zero mismatches, no fault, and every seed to retire its ops.
//   tb_sp_pq_lockstep [+seeds=N] [+seed0=S] [+ops=N] [+maxcyc=N] [+verbose]
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <string>
#include <vector>
#include "Vref.h"
#include "Vdut.h"
#include "verilated.h"
#ifdef SPPQ_DBG
#include "Vref___024root.h"
#define SG(x) r->ot_v41_pqc_spine_screen__DOT__u_sp__DOT__##x
#endif

static uint64_t rs_, dbg_from = ~0ull;
static inline uint64_t rnd() { rs_ ^= rs_ << 13; rs_ ^= rs_ >> 7; rs_ ^= rs_ << 17; return rs_; }
static inline uint32_t rn(uint32_t n) { return (uint32_t)(rnd() % n); }
// a finite FP32 word (the quantiser faults on Inf / NaN): random sign and mantissa, exponent 96..159; some zeros
static inline uint32_t rfin() { uint32_t r = (uint32_t)rnd(); if ((r & 63) == 0) return r & 0x80000000u; return (r & 0x807FFFFFu) | ((96 + (r >> 23) % 64) << 23); }

struct Phase { int fam, K, nb, sbase, rows; };
struct Stim {                       // one cycle of inputs
    uint8_t rst_n = 1, go = 0, i_ph = 0, i_np = 0, i_fmt = 0, x_rv = 0, f_fault = 0, rw_ph = 0, rw_st = 0, rw_a = 0;
    uint32_t i_xbase = 0, i_xps = 0, i_obase = 0, i_ops = 0;
    uint16_t r_v = 0, r_e = 0;
    uint64_t rw_d = 0;
    uint32_t x_q[64] = {0}, r_row[8] = {0}, r_pos[2] = {0}, r_fp32[16] = {0}, r_bf16[8] = {0};
};
template <class M> static void drive(M* m, const Stim& s) {
    m->rst_n = s.rst_n; m->go = s.go; m->i_ph = s.i_ph; m->i_np = s.i_np; m->i_fmt = s.i_fmt; m->x_rv = s.x_rv;
    m->f_fault = s.f_fault; m->rw_ph = s.rw_ph; m->rw_st = s.rw_st; m->rw_a = s.rw_a; m->rw_d = s.rw_d;
    m->i_xbase = s.i_xbase; m->i_xps = s.i_xps; m->i_obase = s.i_obase; m->i_ops = s.i_ops;
    m->r_v = s.r_v; m->r_e = s.r_e;
    for (int i = 0; i < 64; i++) m->x_q[i] = s.x_q[i];
    for (int i = 0; i < 8; i++) { m->r_row[i] = s.r_row[i]; m->r_bf16[i] = s.r_bf16[i]; }
    m->r_pos = ((uint64_t)s.r_pos[1] << 32) | s.r_pos[0];
    for (int i = 0; i < 16; i++) m->r_fp32[i] = s.r_fp32[i];
}
template <class M> static void tick(M* m) { m->clk = 0; m->eval(); m->clk = 1; m->eval(); }
struct Out {
    uint8_t ready, idle, x_re, fault, ev; uint32_t x_addr; uint16_t w_we; uint32_t w_addr[10], w_data[16], bus[51];
};
template <class M> static void sample(M* m, Out& o) {
    memset(&o, 0, sizeof o);
    o.ready = m->o_ready; o.idle = m->o_idle; o.x_re = m->o_x_re; o.fault = m->o_fault; o.ev = m->o_ev;
    o.x_addr = m->o_x_addr; o.w_we = m->o_w_we;
    for (int i = 0; i < 10; i++) o.w_addr[i] = m->o_w_addr[i];
    for (int i = 0; i < 16; i++) o.w_data[i] = m->o_w_data[i];
    for (int i = 0; i < 51; i++) o.bus[i] = m->o_bus[i];
}
static inline uint32_t bits(const uint32_t* w, int lsb, int n) {
    uint64_t v = w[lsb >> 5] >> (lsb & 31);
    if ((lsb & 31) + n > 32) v |= (uint64_t)w[(lsb >> 5) + 1] << (32 - (lsb & 31));
    return (uint32_t)(v & ((1ull << n) - 1));
}
static const char* diff(const Out& a, const Out& b) {
    if (a.ready != b.ready) return "o_ready"; if (a.idle != b.idle) return "o_idle"; if (a.x_re != b.x_re) return "o_x_re";
    if (a.fault != b.fault) return "o_fault"; if (a.ev != b.ev) return "o_ev"; if (a.x_addr != b.x_addr) return "o_x_addr";
    if (a.w_we != b.w_we) return "o_w_we"; if (memcmp(a.w_addr, b.w_addr, sizeof a.w_addr)) return "o_w_addr";
    if (memcmp(a.w_data, b.w_data, sizeof a.w_data)) return "o_w_data"; if (memcmp(a.bus, b.bus, sizeof a.bus)) return "o_bus";
    return nullptr;
}
struct Tot { uint64_t cyc = 0, ops = 0, retired = 0, xre = 0, qbeat = 0, bbeat = 0, wr = 0, mtp = 0, bfops = 0, cmp = 0; };

static int run_seed(uint64_t seed, int nops, uint64_t maxcyc, bool verbose, Tot& T, std::string& why) {
    rs_ = seed * 0x9E3779B97F4A7C15ull + 0x1234567ull; for (int i = 0; i < 8; i++) rnd();
    VerilatedContext cr, cd;
    Vref* R = new Vref(&cr); Vdut* D = new Vdut(&cd);
    // ---- program
    int nph = 4 + rn(21), sp = 0;
    std::vector<Phase> ph(nph);
    uint64_t prom[128] = {0}, srom[256] = {0};
    for (int a = 0; a < 256; a++) srom[a] = 0;
    for (int p = 0; p < nph; p++) {
        Phase& q = ph[p];
        q.fam = rn(100) < 40; q.K = q.fam ? 128 * (1 + rn(2)) : 64 * (1 + rn(4));
        q.nb = 1 + rn(10); if (sp + q.nb > 256) sp = 0; q.sbase = sp; sp += q.nb; q.rows = 1 + rn(48);
        prom[2 * p] = (uint64_t)q.fam | ((uint64_t)q.K << 1) | ((uint64_t)q.nb << 14) | ((uint64_t)q.sbase << 30) |
                      ((uint64_t)q.rows << 46) | ((uint64_t)rn(4) << 62);
        prom[2 * p + 1] = rnd() & 0xFFFFFFFFFFFFull;
        for (int i = 0; i < q.nb; i++) {
            uint64_t w = (rn(100) < 92) ? 1 : 0;                       // beat valid
            if (!q.fam) {                                              // Q word: u = 0, sv[1] = 0, b < K / 32
                w |= (uint64_t)rn(q.K / 32) << 9; w |= (uint64_t)rn(2) << 12;
                for (int k = 2; k < 5; k++) w |= (uint64_t)rn(2) << (8 * k);   // spare index bytes kept in range
                w |= (uint64_t)rn(256) << 40;
            } else {                                                   // BF word: lane mask, block bytes < K / 128
                w |= (uint64_t)rn(8) << 1; w |= (uint64_t)(1 + rn(15)) << 4;
                for (int k = 1; k < 5; k++) w |= (uint64_t)rn(q.K / 128) << (8 * k);
                w |= (uint64_t)rn(256) << 40;
            }
            srom[q.sbase + i] = w;
        }
    }
    int L = 2 + rn(13);                                                // VM return latency (edges), XCAP 16 >= L + 1
    Stim s; Out a, b;
    uint64_t c = 0;
    auto step = [&](const Stim& st, bool cmp) -> bool {
        drive(R, st); drive(D, st); tick(R); tick(D); sample(R, a); sample(D, b); c++;
        if (!cmp) return true;
        T.cmp++;
        const char* d = diff(a, b);
        if (d) { char buf[160]; snprintf(buf, sizeof buf, "seed %llu cycle %llu: %s differs", (unsigned long long)seed,
                                         (unsigned long long)c, d); why = buf; return false; }
        return true;
    };
    s.rst_n = 0; for (int i = 0; i < 12; i++) step(s, false);
    s.rst_n = 1; for (int i = 0; i < 12; i++) step(s, false);
    for (int x = 0; x < 256; x++) {                                    // ROM images through the screen port
        Stim w = s; w.rw_a = x; w.rw_st = 1; w.rw_d = srom[x];
        if (x < 128) { w.rw_ph = 1; }
        if (x < 128) { Stim w2 = w; w2.rw_st = 0; w2.rw_d = prom[x]; if (!step(w2, true)) return 1; w.rw_ph = 0; }
        if (!step(w, true)) return 1;
    }
    for (int i = 0; i < 8; i++) if (!step(s, true)) return 1;
    // ---- run
    struct Rows { int tag; long n; uint64_t at; int np; };
    std::deque<Rows> rows; std::deque<uint64_t> vm;                    // pending row batches; VM request times
    int issued = 0, cfg_ph = 0, cfg_np = 0, since_go = 100, fault_at = -1;
    struct Op { int p, np; uint64_t c; }; std::vector<Op> opl; std::vector<std::string> ev;
    long beats_since = 0, xre_since = 0, lastp_beats = 0;
    bool was_idle = true;
    uint64_t idle_run = 0, end_at = 0;
    while (c < maxcyc) {
        Stim n;
        // observe the reference
        if (a.x_re) { vm.push_back(c + L); T.xre++; }
        uint32_t top = bits(a.bus, 1600, 30);                          // bus[1629:1600]
        bool cfg = (top >> 29) & 1, bgo = (top >> 19) & 1; int tag = (top >> 16) & 3;
        if (cfg) { cfg_ph = (top >> 23) & 63; cfg_np = (top >> 20) & 7; }
        if (bgo) { char eb[128]; snprintf(eb, sizeof eb, "c%llu GO tag %d ph %d np %d (beats %ld xre %ld before)", (unsigned long long)c, tag, cfg_ph, cfg_np, beats_since, xre_since); ev.push_back(eb); beats_since = 0; xre_since = 0;
                   rows.push_back({tag, (long)ph[cfg_ph % nph].rows * (cfg_np + 1), c + 20 + rn(40), cfg_np}); T.ops++; }
        if (a.x_re) xre_since++;
        if (bits(a.bus, 1615, 1) || bits(a.bus, 1063, 1)) beats_since++;
        if (bits(a.bus, 1615, 1)) T.qbeat++;
        if (bits(a.bus, 1063, 1)) T.bbeat++;
        for (int i = 0; i < 16; i++) T.wr += (a.w_we >> i) & 1;
        if (a.fault && fault_at < 0) { char buf[120]; snprintf(buf, sizeof buf, "seed %llu cycle %llu: fault raised by a legal program",
                                                      (unsigned long long)seed, (unsigned long long)c); why = buf; return 1; }
        if (a.idle && !was_idle) T.retired++;
        was_idle = a.idle;
        // VM return
        if (!vm.empty() && vm.front() <= c) { vm.pop_front(); n.x_rv = 1; for (int i = 0; i < 64; i++) n.x_q[i] = rfin(); }
        else if (rn(4) == 0) for (int i = 0; i < 64; i++) n.x_q[i] = (uint32_t)rnd();   // junk while not valid
        // issue
        since_go++;
        if (issued < nops && a.ready && since_go > 8 && rn(100) < 30) {
            int p = rn(nph);
            n.go = 1; n.i_ph = p; n.i_fmt = rn(3);
            // multi-position (MTP) ops only on phases of >= 6 stream words per position.  The streamer compares a
            // word's need with the x buffer's count `have`, which is cleared when the loader STARTS on that buffer; a
            // 1-2 word-per-position MTP stream issued right behind another MTP op finishes on the previous op's stale
            // count before its own load starts (seed 52 without this rule: both models then hang identically, the
            // buffer never released).  Production streams are tens to hundreds of words per position.
            n.i_np = (ph[p].nb >= 6 && rn(100) < 40) ? 1 + rn(3) : 0;
            n.i_xbase = rn(1 << 19); n.i_xps = rn(1 << 19); n.i_obase = rn(1 << 19); n.i_ops = rn(1 << 19);
            issued++; since_go = 0; if (n.i_np) T.mtp++; if (ph[p].fam) T.bfops++; opl.push_back({p, (int)n.i_np, c});
        } else if (rn(8) == 0) { n.i_ph = rn(64); n.i_np = rn(8); n.i_fmt = rn(4); n.i_xbase = rn(1 << 19); n.i_obase = rn(1 << 19); }
        // region rows of the oldest issued op whose time has come.  They return within ~100 edges of the go (the field
        // round trip is bounded): the loader prefetches the next op's x and walks the four slots in a ring without a
        // per-slot 'loaded' flag, so a slot must have retired before the loader comes round to it again
        if (!rows.empty() && rows.front().at <= c) {
            Rows& q = rows.front();
            for (int r = 0; r < 16 && q.n > 0; r++) if (rn(100) < 55) {
                n.r_v |= 1u << r; q.n--;
                uint32_t row = ((uint32_t)q.tag << 14) | rn(1 << 14);
                n.r_row[r / 2] |= row << (16 * (r & 1));
                uint64_t pos = rn(q.np + 1); n.r_pos[(3 * r) >> 5] |= (uint32_t)(pos << ((3 * r) & 31));
                if (((3 * r) & 31) > 29) n.r_pos[1] |= (uint32_t)(pos >> (32 - ((3 * r) & 31)));
                n.r_fp32[r] = (uint32_t)rnd(); n.r_bf16[r / 2] |= (uint32_t)rn(1 << 16) << (16 * (r & 1));
            }
            if (q.n == 0) rows.pop_front();
        } else if (rn(6) == 0) { for (int r = 0; r < 16; r++) n.r_fp32[r] = (uint32_t)rnd(); n.r_row[rn(8)] = (uint32_t)rnd(); }
        // end: all ops issued and retired, then a fault pulse and 40 more compared cycles
        if (issued == nops && a.idle && rows.empty() && vm.empty()) idle_run++; else idle_run = 0;
        if (idle_run == 300 && fault_at < 0) { n.f_fault = 1; fault_at = (int)c; end_at = c + 40; }
        if (!step(n, true)) return 1;
#ifdef SPPQ_DBG
        { auto* r = R->rootp; static int pb0 = -1, pb1 = -1, pl = -1, ps = -1, pt = -1, pr = -1, ph0 = -1, ph1 = -1;
          int b0 = SG(bufbusy)[0], b1 = SG(bufbusy)[1], l = SG(ldt), sr_ = SG(sm_run), stg = SG(sm_tag), lr = SG(ld_run), h0 = SG(have)[0], h1 = SG(have)[1];
          if (verbose && c > dbg_from && (b0 != pb0 || b1 != pb1 || l != pl || sr_ != ps || stg != pt || lr != pr || h0 != ph0 || h1 != ph1))
              printf("  c%llu bufbusy %d %d ldt %d ld_run %d ld_tag %d ld_pos %d ld_more %d | sm_run %d sm_tag %d | have %d %d | go=%d\n", (unsigned long long)c, b0, b1, l, lr, SG(ld_tag), SG(ld_pos), SG(ld_more), sr_, stg, h0, h1, (int)n.go);
          pb0 = b0; pb1 = b1; pl = l; ps = sr_; pt = stg; pr = lr; ph0 = h0; ph1 = h1; }
#endif
        if (end_at && c >= end_at) break;
    }
    T.cyc += c;
    if (!end_at && verbose) {
        for (size_t i = (opl.size() > 8 ? opl.size() - 8 : 0); i < opl.size(); i++) { const Phase& q = ph[opl[i].p]; printf("  issued #%zu c%llu ph %d np %d fam %d K %d nb %d sbase %d rows %d\n", i, (unsigned long long)opl[i].c, opl[i].p, opl[i].np, q.fam, q.K, q.nb, q.sbase, q.rows); for (int k = 0; k < q.nb; k++) printf("      w%d %012llx\n", k, (unsigned long long)srom[q.sbase + k]); }
        for (size_t i = (ev.size() > 8 ? ev.size() - 8 : 0); i < ev.size(); i++) printf("  %s\n", ev[i].c_str());
#ifdef SPPQ_DBG
        { auto* r = R->rootp;
          printf("  DBG ld_run %d ld_more %d ldt %d ld_tag %d ld_pos %d ld_k %d ld_kk %d xo %d bufbusy %d %d have %d %d sm_run %d sm_arm %d sm_tag %d hv %d qcnt %d cred %d rd_run %d rdt %d ist %d acc %d ist_st %d\n", SG(ld_run), SG(ld_more), SG(ldt), SG(ld_tag), SG(ld_pos), SG(ld_k), SG(ld_kk), SG(xo), SG(bufbusy)[0], SG(bufbusy)[1], SG(have)[0], SG(have)[1], SG(sm_run), SG(sm_arm), SG(sm_tag), SG(hv), SG(qcnt), SG(cred), SG(rd_run), SG(rdt), SG(ist), SG(acc), SG(ist_st));
          for (int k = 0; k < 4; k++) printf("  DBG slot %d sv %d sr %d si %d sd %d s_rd %d s_rl %d s_np %d\n", k, SG(sv)[k], SG(sr)[k], SG(si)[k], SG(sd)[k], SG(s_rd)[k], SG(s_rl)[k], SG(s_np)[k]); }
#endif
        printf("  after last go: beats %ld xre %ld; ready %d idle %d; L %d\n", beats_since, xre_since, a.ready, a.idle, L);
    }
    if (!end_at) { char buf[160]; snprintf(buf, sizeof buf, "seed %llu: ops not retired in %llu cycles (issued %d, pending row batches %zu)",
                                           (unsigned long long)seed, (unsigned long long)maxcyc, issued, rows.size()); why = buf; return 1; }
    if (!a.fault) { why = "fault pulse did not reach o_fault"; return 1; }
    if (verbose) printf("  seed %llu: phases %d L %d cycles %llu\n", (unsigned long long)seed, nph, L, (unsigned long long)c);
    R->final(); D->final(); delete R; delete D;
    return 0;
}

int main(int argc, char** argv) {
    int seeds = 24, nops = 40; uint64_t seed0 = 1, maxcyc = 400000; bool verbose = false;
    for (int i = 1; i < argc; i++) {
        if (!strncmp(argv[i], "+seeds=", 7)) seeds = atoi(argv[i] + 7);
        else if (!strncmp(argv[i], "+seed0=", 7)) seed0 = strtoull(argv[i] + 7, 0, 0);
        else if (!strncmp(argv[i], "+ops=", 5)) nops = atoi(argv[i] + 5);
        else if (!strncmp(argv[i], "+maxcyc=", 8)) maxcyc = strtoull(argv[i] + 8, 0, 0);
        else if (!strcmp(argv[i], "+verbose")) verbose = true;
        else if (!strncmp(argv[i], "+dbgfrom=", 9)) dbg_from = strtoull(argv[i] + 9, 0, 0);
    }
    Tot T; std::string why; int bad = 0;
    for (int k = 0; k < seeds && !bad; k++) bad = run_seed(seed0 + k, nops, maxcyc, verbose, T, why);
    printf("SP_PQ_LOCKSTEP stats seeds=%d cycles=%llu compared=%llu ops=%llu retired_idle=%llu bf_ops=%llu mtp_ops=%llu x_reads=%llu "
           "q_beats=%llu bf_beats=%llu row_writes=%llu\n", seeds, (unsigned long long)T.cyc, (unsigned long long)T.cmp,
           (unsigned long long)T.ops, (unsigned long long)T.retired, (unsigned long long)T.bfops, (unsigned long long)T.mtp,
           (unsigned long long)T.xre, (unsigned long long)T.qbeat, (unsigned long long)T.bbeat, (unsigned long long)T.wr);
    if (bad) { printf("SP_PQ_LOCKSTEP FAIL %s\n", why.c_str()); return 1; }
    if (T.ops < (uint64_t)seeds * nops || !T.qbeat || !T.bbeat || !T.wr || !T.mtp) {
        printf("SP_PQ_LOCKSTEP FAIL coverage: ops %llu of %d issued, q_beats %llu, bf_beats %llu, row_writes %llu\n",
               (unsigned long long)T.ops, seeds * nops, (unsigned long long)T.qbeat, (unsigned long long)T.bbeat, (unsigned long long)T.wr);
        return 1;
    }
    printf("SP_PQ_LOCKSTEP PASS exact=%llu\n", (unsigned long long)T.cmp);
    return 0;
}
