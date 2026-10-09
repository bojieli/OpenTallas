// kv-die 2026-10-09: Verilator harness of ot_qkvd_layer_tb -- one attention layer step of Qwen3-8B (TP4 die share:
// 8 q heads, 2 KV heads, head_dim 128) THROUGH the ROM die <-> KV die link, against the golden
// (tools/hdc_golden.py via tools/qwen_nearhbm_attn_ref.py vectors).  It also drives every other crossing class once
// (TOKEN out to the host, EMBQ -> gateway -> EMBD row back, two HCTL host words) and checks them bit for bit.
//   ./Vtb <vector dir> [stall=0] [hbm_latency=16] [bytes_per_cycle=750] [max_cycles=400000]
// HBM: per-engine in-order request queues, a BPC-byte/cycle token bucket per stack, fixed latency; the rows of the
// new position t = T-1 come back POISONED (0xA5): the K / V crossed on KVN must be merged by the KV-die sequencer.
// stall=1: the ROM-side RES consumer withholds its credits for 300 cycles (back-pressure through both dies).
#include "Vot_qkvd_layer_tb.h"
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
    const int LAYER = 3, TOKEN = 0x1D2C5, EMB_ADDR = 0x0ABCD;
    // ---- SU-face words per class: CTL (ATTN, TOKEN), Q (32), KVN (8), EMBQ (1) ----
    std::deque<Word> tx[4];
    { Word w = mkw(); wset(w, 0, 14, T); wset(w, 16, 6, LAYER); wset(w, 32, 32, 0x5000u); wset(w, 524, 4, 1); tx[0].push_back(w); }
    { Word w = mkw(); wset(w, 0, 18, TOKEN); wset(w, 32, 14, T); wset(w, 524, 4, 2); tx[0].push_back(w); }
    for (int vg = 0; vg < 4; vg++) for (int h = 0; h < 2; h++) {
        int v = vg >> 1, g = vg & 1; Word w = mkw();
        const std::vector<uint8_t>& row = kv[v][2 * (T - 1) + g];
        for (int d = 0; d < 64; d++) wset(w, 8 * d, 8, row[64 * h + d]);
        wset(w, 512, 3, (v << 2) | (g << 1) | h); tx[2].push_back(w); }
    for (int b = 0; b < 32; b++) { Word w = mkw(); for (int i = 0; i < 32; i++) wset(w, 16 * i, 16, q[32 * b + i]); wset(w, 512, 6, b); tx[1].push_back(w); }
    { Word w = mkw(); wset(w, 0, 24, EMB_ADDR); wset(w, 512, 1, 0); tx[3].push_back(w); }
    const int QB = (2 * KVD_ROM_ST + 4 + 8 > 48) ? 2 * KVD_ROM_ST + 4 + 8 : 48;
    int scred[4] = {8, QB, 8, 8};
    // host words, gateway row
    std::deque<Word> hq;
    for (int k = 0; k < 2; k++) { Word w = mkw(); wset(w, 0, 32, 0xC0DE0000u + k); wset(w, 512, 16, 0x7000 + k); hq.push_back(w); }
    std::vector<Word> hsent(hq.begin(), hq.end());
    int hcred = 4, gwcred = 8, tkcredret = 0;
    std::deque<Word> gw; std::vector<Word> gsent;
    int kvwcr_due[8] = {0}; int nkvw = 0; bool kvw_ok = true;

    Vot_qkvd_layer_tb* top = new Vot_qkvd_layer_tb;
    uint64_t cyc = 0;
    auto tick = [&]() { top->clk = 0; top->eval(); top->clk = 1; top->eval(); cyc++; };
    top->rst_n = 0; top->su_v = 0; top->vm_cr = 0; top->kvw_cr = 0; top->emb_req_cr = 0; top->emb_q_v = 0; top->hc_v = 0; top->tok_cr = 0;
    for (int x = 0; x < E; x++) sb(top->rsp_valid, x, 1, 0);
    for (int i = 0; i < 5; i++) tick();
    top->rst_n = 1;
    std::deque<Req> rq[E]; std::deque<Rsp> pend[E];
    double tok[4] = {0, 0, 0, 0}; int rr[4] = {0, 0, 0, 0};
    std::vector<uint32_t> out(NH * HD, 0xDEADBEEF); std::vector<int> got(NH * HD, 0); int nout = 0;
    std::vector<Word> embd, hctl, toks;
    int res_owed = 0, faults = 0, ret12[2] = {0, 0}, gwreq_ret = 0;
    int64_t t_ctl = -1, t_start = -1, a_first = -1, a_last = -1, res_first = -1, res_last = -1, t_emb_req = -1, t_embd_last = -1;
    int poisoned = 0;
    while (cyc < MAXC && !(nout == NH * HD && (int)embd.size() == 65 && (int)hctl.size() == 2 && (int)toks.size() == 1 && nkvw == 4)) {
        int64_t now = (int64_t)cyc;
        // ---- SU face ----
        top->su_v = 0;
        for (int c = 0; c < 4; c++) {
            if (now >= 40 && !tx[c].empty() && scred[c] > 0) {
                put_word(top->su_d, c, tx[c].front()); tx[c].pop_front(); scred[c]--; sb(top->su_v, c, 1, 1);
                if (c == 0 && t_ctl < 0) t_ctl = now;
            }
        }
        // ---- VM face: credits (RES withheld during the stall window) ----
        top->vm_cr = 0;
        if (res_owed > 0 && !(STALL && now >= 400 && now < 700)) { sb(top->vm_cr, 0, 1, 1); res_owed--; }
        if (ret12[0] > 0) { sb(top->vm_cr, 1, 1, 1); ret12[0]--; }
        if (ret12[1] > 0) { sb(top->vm_cr, 2, 1, 1); ret12[1]--; }
        top->emb_req_cr = gwreq_ret > 0; if (gwreq_ret > 0) gwreq_ret--;
        // ---- host words ----
        top->hc_v = 0;
        if (now >= 60 && !hq.empty() && hcred > 0) { put_word(top->hc_d, 0, hq.front()); hq.pop_front(); hcred--; top->hc_v = 1; }
        // ---- gateway row words ----
        top->emb_q_v = 0;
        if (!gw.empty() && gwcred > 0) { put_word(top->emb_q_d, 0, gw.front()); gsent.push_back(gw.front()); gw.pop_front(); gwcred--; top->emb_q_v = 1; }
        top->tok_cr = tkcredret > 0; if (tkcredret > 0) tkcredret--;
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
        for (int c = 0; c < 4; c++) if (gb(top->su_cr, c, 1)) scred[c]++;
        if (top->hc_cr) hcred++;
        if (top->emb_q_cr) gwcred++;
        if (top->a_start_o && t_start < 0) t_start = nowc;
        if (top->a_out_valid_o) { if (a_first < 0) a_first = nowc; a_last = nowc; }
        for (int c = 0; c < 3; c++) if (gb(top->vm_v, c, 1)) {
            Word w = get_word(top->vm_d, c);
            if (c == 0) {
                int g = (int)wget(w, 518, 1), beat = (int)wget(w, 512, 6), bph = HD / 16, h = 4 * g + beat / bph, d0 = (beat % bph) * 16;
                for (int l = 0; l < 16; l++) { int i = h * HD + d0 + l; out[i] = (uint32_t)wget(w, 32 * l, 32); got[i]++; nout++; }
                if (res_first < 0) res_first = nowc; res_last = nowc; res_owed++;
            } else {
                if (c == 1) { embd.push_back(w); t_embd_last = nowc; } else hctl.push_back(w);
                // EMBD / HCTL credits return at once (the consumer is always ready)
            }
        }
        ret12[0] += (int)gb(top->vm_v, 1, 1); ret12[1] += (int)gb(top->vm_v, 2, 1);   // returned on the next edge
        if (top->tok_v) { toks.push_back(get_word(top->tok_d, 0)); tkcredret++; }
        if (top->emb_req_v) {
            Word w = get_word(top->emb_req_d, 0); t_emb_req = nowc;
            if (wget(w, 0, 24) != (uint64_t)EMB_ADDR) { fprintf(stderr, "EMBQ address mismatch\n"); faults |= 64; }
            uint32_t s = 0x9E3779B9u ^ EMB_ADDR;
            for (int k = 0; k < 65; k++) { Word r = mkw(); for (int b = 0; b < 512; b += 32) { s = prng(s); wset(r, b, 32, s); } wset(r, 512, 7, k); wset(r, 519, 1, k == 64); gw.push_back(r); }
            gwreq_ret++;             // returned on the next edge
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
        for (int s = 0; s < 4; s++) {
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
    }
    int mism = 0, first_bad = -1;
    for (int i = 0; i < NH * HD; i++) if (got[i] != 1 || out[i] != gold[i]) { if (first_bad < 0) first_bad = i; mism++; }
    int emb_bad = (int)gsent.size() != 65 || embd.size() != 65;
    for (size_t k = 0; !emb_bad && k < 65; k++) if (embd[k] != gsent[k]) emb_bad = 1;
    int hc_bad = hctl.size() != 2 || hctl[0] != hsent[0] || hctl[1] != hsent[1];
    int tk_bad = toks.size() != 1 || wget(toks[0], 0, 18) != (uint64_t)TOKEN || wget(toks[0], 524, 4) != 2;
    bool exact = mism == 0 && faults == 0 && nout == NH * HD && !emb_bad && !hc_bad && !tk_bad && nkvw == 4 && kvw_ok;
    printf("{\"ctx\": %d, \"R\": %d, \"stall\": %d, \"hbm_latency\": %d, \"bytes_per_cycle\": %d, \"outputs\": %d, "
           "\"mismatches\": %d, \"first_bad\": %d, \"faults\": %d, \"poisoned_rows_merged\": %d, \"kvw_rows\": %d, "
           "\"kvw_ok\": %s, \"embd_ok\": %s, \"hctl_ok\": %s, \"token_ok\": %s, \"exact\": %s, \"cycles\": %llu, "
           "\"marks\": {\"ctl_sent\": %lld, \"attn_start\": %lld, \"attn_out_first\": %lld, \"attn_out_last\": %lld, "
           "\"res_first_at_vm\": %lld, \"res_last_at_vm\": %lld, \"emb_req_at_gw\": %lld, \"embd_last_at_su\": %lld}}\n",
           T, R, STALL, LAT, BPC, nout, mism, first_bad, faults, poisoned, nkvw, kvw_ok ? "true" : "false",
           emb_bad ? "false" : "true", hc_bad ? "false" : "true", tk_bad ? "false" : "true", exact ? "true" : "false",
           (unsigned long long)cyc, (long long)t_ctl, (long long)t_start, (long long)a_first, (long long)a_last,
           (long long)res_first, (long long)res_last, (long long)t_emb_req, (long long)t_embd_last);
    if (mism && first_bad >= 0) fprintf(stderr, "first mismatch at %d: rtl %08x gold %08x\n", first_bad, out[first_bad], gold[first_bad]);
    top->final(); delete top;
    return exact ? 0 : 1;
}
