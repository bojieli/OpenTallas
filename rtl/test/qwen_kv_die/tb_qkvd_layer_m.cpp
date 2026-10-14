// Qwen ROM TP8 track B 2026-10-13: Verilator harness of ot_qkvd_layer_m_tb (the MERGED-die KV sequencer; derived from
// tb_qkvd_layer.cpp).  The harness is the HOST (d_start {token, pos, gen}; a program write and a descriptor write), the
// ROM SEQUENCER on its raw pins (every h_start must name the next stage of 0..37 with the step's token / position; a
// stage answers s_done after 5 cycles, the stage of layer LAYER when the last RES word reached the VM face; the head
// stage hands {next token, logit}), the SU (x3 words, 40 credits = one layer; the kvd score descriptor launches the
// layer) and the VM (RES credits).  The step must end with the done level naming the generation, the token and the
// logit, drained and without a fault; the program write must reach BOTH program copies (pw and the ds field) once.
// kv-die 2026-10-09: Verilator harness of ot_qkvd_layer_tb -- one attention layer step of Qwen3-8B (TP4 die share:
// 8 q heads, 2 KV heads, head_dim 128) THROUGH the ROM die <-> KV die link, against the golden
// (tools/hdc_golden.py via tools/qwen_nearhbm_attn_ref.py vectors).  It also drives every other crossing class once
// (TOKEN out to the host, EMBQ -> gateway -> EMBD row back, two HCTL host words) and checks them bit for bit.
//   ./Vtb <vector dir> [stall=0] [hbm_latency=16] [bytes_per_cycle=750] [max_cycles=400000] [hbmt=0]
// HBM: per-engine in-order request queues, a BPC-byte/cycle token bucket per stack, fixed latency; the rows of the
// new position t = T-1 come back POISONED (0xA5): the K / V crossed on KVN must be merged by the KV-die sequencer.
// stall=1: the ROM-side RES consumer withholds its credits for 300 cycles from the first RES word (back-pressure
// through both dies: the RES words pile up in the ROM end, the link and the KV end).
#include "Vot_qkvd_layer_m_tb.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <string>
#include <vector>

#ifndef KVD_R
#define KVD_R 8
#endif
#ifndef KVD_ROM_ST
#define KVD_ROM_ST 24
#endif
static const int R = KVD_R, HD = 128, NH = 8, W = 528, E = 4 * KVD_R;

static void sbit_words(uint32_t* v, int off, int w, uint64_t x) {
    for (int i = 0; i < w; i++) { int b = off + i; if ((x >> i) & 1) v[b / 32] |= 1u << (b % 32); else v[b / 32] &= ~(1u << (b % 32)); }
}
static uint64_t gbits_words(const uint32_t* v, int off, int w) {
    uint64_t r = 0; for (int i = 0; i < w; i++) if ((v[(off + i) / 32] >> ((off + i) % 32)) & 1) r |= 1ull << i; return r;
}
template <std::size_t N> static uint64_t gb(const VlWide<N>& v, int off, int w) { return gbits_words(v.data(), off, w); }
template <std::size_t N> static void sb(VlWide<N>& v, int off, int w, uint64_t x) { sbit_words(v.data(), off, w, x); }
template <typename T> static uint64_t gb(const T& v, int off, int w) { return (uint64_t(v) >> off) & ((w == 64) ? ~0ull : ((1ull << w) - 1)); }
template <typename T> static void sb(T& v, int off, int w, uint64_t x) { uint64_t m = ((w == 64) ? ~0ull : ((1ull << w) - 1)) << off; v = (T)((uint64_t(v) & ~m) | ((x << off) & m)); }

typedef std::vector<uint32_t> Word;     // 528 bits = 17 x 32 (bit 527 is the top)
static Word mkw() { return Word(17, 0); }
static void wset(Word& w, int off, int n, uint64_t x) { sbit_words(w.data(), off, n, x); }
static uint64_t wget(const Word& w, int off, int n) { return gbits_words(w.data(), off, n); }
template <typename T> static void put_word(T& bus, int slot, const Word& w) { for (int b = 0; b < W; b += 32) sb(bus, slot * W + b, (W - b) < 32 ? W - b : 32, wget(w, b, (W - b) < 32 ? W - b : 32)); }
template <typename T> static Word get_word(const T& bus, int slot) { Word w = mkw(); for (int b = 0; b < W; b += 32) wset(w, b, (W - b) < 32 ? W - b : 32, gb(bus, slot * W + b, (W - b) < 32 ? W - b : 32)); return w; }
static uint32_t prng(uint32_t x) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; return x; }

struct Req { int v, g, t; };
struct Rsp { uint64_t at; int v, g, t; };

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 2) { fprintf(stderr, "usage: Vtb DIR [stall] [lat] [bpc] [maxcyc]\n"); return 2; }
    std::string dir = argv[1];
    int STALL = argc > 2 ? atoi(argv[2]) : 0;
    int LAT = argc > 3 ? atoi(argv[3]) : 16;
    int BPC = argc > 4 ? atoi(argv[4]) : 750;
    // qwen-1010/b 2026-10-10: argv[6] = 1 -> rows timed by the tb's HBMT stacks (timed HBM3E model); the token bucket is off
    int HBMT = argc > 6 ? atoi(argv[6]) : 0;
    // argv[7]: start offset in cycles (the layer starts OFS cycles later: its phase against the HBM refresh schedule)
    int64_t OFS = argc > 7 ? atoll(argv[7]) : 0;
    uint64_t MAXC = argc > 5 ? strtoull(argv[5], 0, 10) : 400000;
    int T = 0;
    { std::ifstream m(dir + "/meta.json"); std::string s((std::istreambuf_iterator<char>(m)), std::istreambuf_iterator<char>());
      size_t p = s.find("\"ctx\":"); T = atoi(s.c_str() + p + 6); }
    std::vector<uint16_t> q;
    { std::ifstream f(dir + "/q.hex"); std::string l; while (f >> l) q.push_back((uint16_t)strtoul(l.c_str(), 0, 16)); }
    std::vector<std::vector<uint8_t>> kv[2];
    { std::ifstream f(dir + "/kv.hex"); std::string l; int n = 0;
      while (f >> l) { std::vector<uint8_t> row(HD); for (int d = 0; d < HD; d++) row[d] = (uint8_t)strtoul(l.substr(2 * (HD - 1 - d), 2).c_str(), 0, 16);
                       kv[n < 2 * T ? 0 : 1].push_back(row); n++; } }
    std::vector<uint32_t> gold;
    { std::ifstream f(dir + "/gold.hex"); std::string l; while (f >> l) gold.push_back((uint32_t)strtoul(l.c_str(), 0, 16)); }
    if ((int)q.size() != NH * HD || (int)kv[0].size() != 2 * T || (int)kv[1].size() != 2 * T || (int)gold.size() != NH * HD) {
        fprintf(stderr, "bad vectors\n"); return 2; }
    const int LAYER = 3, TOKEN = 0x1D2C5, EMB_ROW = 0x0ABC;
    // ---- ROM-side faces: x3 (KVN x 8 then Q x 32, class in x3_tag[10:8]) ----
    std::deque<Word> x3q;
    for (int vg = 0; vg < 4; vg++) for (int h = 0; h < 2; h++) {
        int v = vg >> 1, g = vg & 1; Word w = mkw();
        const std::vector<uint8_t>& row = kv[v][2 * (T - 1) + g];
        for (int d = 0; d < 64; d++) wset(w, 8 * d, 8, row[64 * h + d]);
        wset(w, 512, 11, (2 << 8) | (v << 2) | (g << 1) | h); x3q.push_back(w); }
    for (int b = 0; b < 32; b++) { Word w = mkw(); for (int i = 0; i < 32; i++) wset(w, 16 * i, 16, q[32 * b + i]); wset(w, 512, 11, (1 << 8) | b); x3q.push_back(w); }
    int x3c = 40;
    int kvd_at = -1, pw_seen = 0, pw_bad = 0, pws_seen = 0, dw_seen = 0, dw_bad = 0;
    const uint64_t PW_DATA = 0x0123456789ABCDEFull; const int PW_ADDR = 0x2A5;
    const uint64_t DW_DATA = 0xFEDCBA9876543210ull; const int DW_ADDR = 5;
    const int POS = T - 1, GEN = 2, NS = 38; const uint32_t NVAL = 0x41C80000u;
    // ROM-sequencer model and host
    int sq_stage = -1, sq_wait = -1, sq_next = 0, stage_bad = 0, sq_attn = 0, done_seen = 0, tk_bad = 1;
    bool launch = false;
    int kvwcr_due[8] = {0}; int nkvw = 0; bool kvw_ok = true;

    Vot_qkvd_layer_m_tb* top = new Vot_qkvd_layer_m_tb;
    uint64_t cyc = 0;
    auto tick = [&]() { top->clk = 0; top->eval(); top->clk = 1; top->eval(); cyc++; };
    top->rst_n = 0; top->x3_v = 0; top->sd = 0; top->kvd = 0; top->ar_cr = 0; top->kvw_cr = 0; for (int b = 0; b < 182; b += 32) sb(top->hc, b, (182 - b) < 32 ? 182 - b : 32, 0);
    for (int x = 0; x < E; x++) sb(top->rsp_valid, x, 1, 0);
    for (int i = 0; i < 5; i++) tick();
    top->rst_n = 1;
    std::deque<Req> rq[E]; std::deque<Rsp> pend[E];
    double tok[4] = {0, 0, 0, 0}; int rr[4] = {0, 0, 0, 0};
    std::vector<uint32_t> out(NH * HD, 0xDEADBEEF); std::vector<int> got(NH * HD, 0); int nout = 0;
    int res_owed = 0, faults = 0;
    int64_t t_ctl = -1, t_start = -1, a_first = -1, a_last = -1, res_first = -1, res_last = -1, t_emb_req = -1, t_embd_last = -1;
    int poisoned = 0;
    uint64_t last_progress = 0;      // a run that stops making progress for 20,000 cycles ends (a caught mutant)
    while (cyc < MAXC && !(nout == NH * HD && done_seen && nkvw == 4 && pw_seen >= 1 && pws_seen >= 1 && dw_seen >= 1)) {
        int64_t now = (int64_t)cyc;
        // ---- ROM faces ----
        top->x3_v = 0; top->kvd = 0;
        if (launch) {
            if (!x3q.empty() && x3c > 0) { const Word& w = x3q.front(); for (int bb = 0; bb < 512; bb += 32) sb(top->x3_d, bb, 32, wget(w, bb, 32));
                                           top->x3_tag = (uint32_t)wget(w, 512, 11); x3q.pop_front(); x3c--; top->x3_v = 1; }
            // the score descriptor {v, kindk 1, pos = T - 1, wbase = layer block} starts the layer; the weighted-sum
            // descriptor of the same position follows three cycles later (it launches nothing)
            if (kvd_at < 0) { kvd_at = (int)now; if (t_ctl < 0) t_ctl = now;
                top->kvd = (1ull << 43) | (1ull << 42) | ((uint64_t)(T - 1) << 24) | (uint64_t)(LAYER << 6); }
            else if (now == kvd_at + 3) top->kvd = (1ull << 43) | ((uint64_t)(T - 1) << 24) | (uint64_t)((64 + LAYER) << 6);
        }
        // ---- the host: writes at 20 / 24, the step at 40 + OFS ----
        sb(top->hc, 38, 1, 0); sb(top->hc, 113, 1, 0); sb(top->hc, 181, 1, 0);
        if (now == 20) { sb(top->hc, 39, 32, PW_DATA & 0xFFFFFFFFu); sb(top->hc, 71, 32, PW_DATA >> 32); sb(top->hc, 103, 10, PW_ADDR); sb(top->hc, 113, 1, 1); }
        if (now == 24) { sb(top->hc, 114, 32, DW_DATA & 0xFFFFFFFFu); sb(top->hc, 146, 32, DW_DATA >> 32); sb(top->hc, 178, 3, DW_ADDR); sb(top->hc, 181, 1, 1); }
        if (now == 40 + OFS) { sb(top->hc, 0, 18, POS); sb(top->hc, 18, 18, TOKEN); sb(top->hc, 36, 2, GEN); sb(top->hc, 38, 1, 1); }
        top->ar_cr = 0;
        if (res_owed > 0 && !(STALL && res_first >= 0 && now >= res_first && now < res_first + 300)) { top->ar_cr = 1; res_owed--; }
        top->kvw_cr = kvwcr_due[cyc % 8] > 0; if (kvwcr_due[cyc % 8] > 0) kvwcr_due[cyc % 8]--;
        // ---- HBM responses ----
        for (int x = 0; x < E; x++) {
            if (!pend[x].empty() && pend[x].front().at <= cyc) {
                Rsp r = pend[x].front(); pend[x].pop_front(); sb(top->rsp_valid, x, 1, 1);
                bool newpos = (r.t == T - 1);
                const std::vector<uint8_t>& row = kv[r.v][2 * r.t + r.g];
                for (int d = 0; d < HD; d++) sb(top->rsp_data, (x * HD + d) * 8, 8, newpos ? 0xA5 : row[d]);
                if (newpos) poisoned++;
            } else sb(top->rsp_valid, x, 1, 0);
        }
        tick();
        uint64_t nowc = cyc;
        // ---- outputs of this edge ----
        if (top->x3_cr) x3c++;
        if (top->a_start_o && t_start < 0) t_start = nowc;
        if (top->a_out_valid_o) { if (a_first < 0) a_first = nowc; a_last = nowc; }
        if (top->ar_v) {
            int g = (int)gb(top->ar_d, 518, 1), beat = (int)gb(top->ar_d, 512, 6), bph = HD / 16, h = 4 * g + beat / bph, d0 = (beat % bph) * 16;
            for (int l = 0; l < 16; l++) { int i = h * HD + d0 + l; out[i] = (uint32_t)gb(top->ar_d, 32 * l, 32); got[i]++; nout++; }
            if (res_first < 0) res_first = nowc; res_last = nowc; res_owed++;
        }
        if (gb(top->pw, 74, 1)) { pw_seen++; if ((int)gb(top->pw, 64, 10) != PW_ADDR || (gb(top->pw, 0, 32) | (gb(top->pw, 32, 32) << 32)) != PW_DATA) pw_bad = 1; }
        if (gb(top->ds, 118, 1)) { pws_seen++; if ((int)gb(top->ds, 108, 10) != PW_ADDR || (gb(top->ds, 44, 32) | (gb(top->ds, 76, 32) << 32)) != PW_DATA) pw_bad = 1; }
        if (gb(top->ds, 186, 1)) { dw_seen++; if ((int)gb(top->ds, 183, 3) != DW_ADDR || (gb(top->ds, 119, 32) | (gb(top->ds, 151, 32) << 32)) != DW_DATA) dw_bad = 1; }
        // ---- the ROM sequencer on its raw pins ----
        if (gb(top->ds, 42, 1)) {
            int stg = (int)gb(top->ds, 36, 6);
            if (stg != sq_next || (int)gb(top->ds, 18, 18) != TOKEN || (int)gb(top->ds, 0, 18) != POS) stage_bad = 1;
            sq_stage = stg; sq_next = stg + 1; sb(top->sd, 50, 1, 0);
            if (stg == LAYER + 1) { launch = true; sq_attn = 1; sq_wait = -1; } else sq_wait = 5;
        } else if (sq_attn && nout == NH * HD) { sq_attn = 0; sq_wait = 1; }
        else if (sq_wait > 0) sq_wait--;
        else if (sq_wait == 0) {
            sq_wait = -1; sb(top->sd, 50, 1, 1);
            if (sq_stage == NS - 1) { sb(top->sd, 32, 18, TOKEN ^ 0x155); sb(top->sd, 0, 32, NVAL); }
        }
        if (!done_seen && now > 60 + OFS && gb(top->tk, 92, 1)) {
            done_seen = 1;
            tk_bad = (int)gb(top->tk, 90, 2) != GEN || gb(top->tk, 89, 1) != 1 || gb(top->tk, 88, 1) != 0 ||
                     (int)gb(top->tk, 64, 18) != (TOKEN ^ 0x155) || (uint32_t)gb(top->tk, 32, 32) != NVAL;
        }
        if (top->kvw_v) {
            int vg = top->kvw_vg, v = vg >> 1, g = vg & 1;
            const std::vector<uint8_t>& row = kv[v][2 * (T - 1) + g];
            for (int d = 0; d < HD; d++) if (gb(top->kvw_d, 8 * d, 8) != row[d]) kvw_ok = false;
            if (top->kvw_t != T - 1 || top->kvw_layer != LAYER) kvw_ok = false;
            nkvw++; kvwcr_due[(cyc + 3) % 8]++;
        }
        for (int x = 0; x < E; x++) if (gb(top->req_valid, x, 1)) {
            Req r{(int)gb(top->req_v, x, 1), (int)gb(top->req_g, x, 1), (int)gb(top->req_t, 13 * x, 13)};
            if (r.t >= T || ((r.t % 512) / 128) != x / R) { fprintf(stderr, "bad request t=%d x=%d\n", r.t, x); return 3; }
            rq[x].push_back(r);
        }
        if (HBMT) {
            for (int x = 0; x < E; x++) if (gb(top->hrow_rdy, x, 1)) {
                Req r{(int)gb(top->hrow_v, x, 1), (int)gb(top->hrow_g, x, 1), (int)gb(top->hrow_t, 13 * x, 13)};
                if (rq[x].empty() || rq[x].front().v != r.v || rq[x].front().g != r.g || rq[x].front().t != r.t) {
                    fprintf(stderr, "HBMT row out of order x=%d t=%d\n", x, r.t); faults |= 128;
                } else rq[x].pop_front();
                pend[x].push_back(Rsp{cyc, r.v, r.g, r.t});
            }
            if (top->hrow_fault) faults |= 256;
        }
        for (int s = 0; s < 4 && !HBMT; s++) {
            tok[s] += BPC; if (tok[s] > BPC + HD) tok[s] = BPC + HD;
            for (int k = 0; k < R; k++) {
                int x = s * R + (rr[s] + k) % R;
                if (rq[x].empty() || tok[s] < HD) continue;
                Req r = rq[x].front(); rq[x].pop_front(); tok[s] -= HD;
                pend[x].push_back(Rsp{cyc + (uint64_t)LAT, r.v, r.g, r.t});
            }
            rr[s] = (rr[s] + 1) % R;
        }
        if (top->faults) faults |= top->faults;
        if (top->ar_v || gb(top->ds, 42, 1) || top->kvw_v) last_progress = cyc;
        if (cyc > last_progress + 20000) break;
    }
    int mism = 0, first_bad = -1;
    for (int i = 0; i < NH * HD; i++) if (got[i] != 1 || out[i] != gold[i]) { if (first_bad < 0) first_bad = i; mism++; }
    top->x3_v = 0; top->kvd = 0;
    for (int k = 0; k < 96; k++) {                // late words (a second pw) still count
        tick();
        if (gb(top->pw, 74, 1)) pw_seen++;
        if (gb(top->ds, 118, 1)) pws_seen++;
        if (top->faults) faults |= top->faults;
    }
    int emb_bad = pw_seen != 1 || pws_seen != 1 || pw_bad || dw_seen != 1 || dw_bad;     // (printed as pw_ok)
    int hc_bad = stage_bad || sq_next != NS;      // (printed as step_ok: 38 stages in order with the step's token / position)
    if (!done_seen) tk_bad = 1;
    bool exact = mism == 0 && faults == 0 && nout == NH * HD && !emb_bad && !hc_bad && !tk_bad && nkvw == 4 && kvw_ok;
    printf("{\"ctx\": %d, \"R\": %d, \"hbmt\": %d, \"launch\": %d, \"stall\": %d, \"hbm_latency\": %d, \"bytes_per_cycle\": %d, \"outputs\": %d, "
           "\"mismatches\": %d, \"first_bad\": %d, \"faults\": %d, \"poisoned_rows_merged\": %d, \"kvw_rows\": %d, "
           "\"kvw_ok\": %s, \"pw_ok\": %s, \"step_ok\": %s, \"token_ok\": %s, \"exact\": %s, \"cycles\": %llu, "
           "\"marks\": {\"ctl_sent\": %lld, \"attn_start\": %lld, \"attn_out_first\": %lld, \"attn_out_last\": %lld, "
           "\"res_first_at_vm\": %lld, \"res_last_at_vm\": %lld, \"emb_req_at_gw\": %lld, \"embd_last_at_su\": %lld}}\n",
           T, R, HBMT, 1, STALL, LAT, BPC, nout, mism, first_bad, faults, poisoned, nkvw, kvw_ok ? "true" : "false",
           emb_bad ? "false" : "true", hc_bad ? "false" : "true", tk_bad ? "false" : "true", exact ? "true" : "false",
           (unsigned long long)cyc, (long long)t_ctl, (long long)t_start, (long long)a_first, (long long)a_last,
           (long long)res_first, (long long)res_last, (long long)t_emb_req, (long long)t_embd_last);
    if (mism && first_bad >= 0) fprintf(stderr, "first mismatch at %d: rtl %08x gold %08x\n", first_bad, out[first_bad], gold[first_bad]);
    top->final(); delete top;
    return exact ? 0 : 1;
}
