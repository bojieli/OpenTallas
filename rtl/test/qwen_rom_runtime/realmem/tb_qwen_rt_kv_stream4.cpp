// Standalone Verilator bench of the 4-STACK KV service (rtl/hdc/kv/ot_qwen_rt_kv_stream4_service.sv +
// rtl/hdc/kv/ot_qwen_hbm_stream4_ack.sv: 4 stacks x 32 PCs, window P < 8192).  Derived from
// tb_qwen_rt_kv_stream.cpp (unchanged); the slice/HBM checks are that bench's.  Cases:
//   ISO   one layer from start (no notice): fill bandwidth (sectors/cycle, TB/s) and exactness;
//   CHAIN two layers A, B at the same P with the straps: A runs, B's descriptor is posted when A
//         retires, kv_free is pulsed ATTN cycles after A's kv_ok, B starts MLP cycles later; B's
//         slices, both layers' token write-backs and the fill exposed after B's start are checked.
// Retained description of the predecessor bench:
// Standalone Verilator bench of the HBM_STREAM KV service (rtl/hdc/kv/ot_qwen_rt_kv_stream_service.sv)
// with the streaming HBM (rtl/hdc/kv/ot_qwen_hbm_stream_ack.sv: ot_hbm_r14_stream_stack WR_EN = 1 at
// HBM CK/2 behind a clock crossing, picosecond DRAM checker, write-done).  Derived from
// tb_qwen_rt_kv_stream.cpp (the fill service's bench, unchanged); the checks are the same, the
// window is limited to P < 2048 (the stream map), and each case runs with or without the
// next-layer NOTICE (nx_layer posted NOTICE_CYC cycles before start).
//
// For each case (layer, position P): random E4M3 KV history is PRELOADED into the HBM model
// (K tiles 0..P/16 with the open tile's lanes >= P mod 16 zero, V positions 0..P-1), the slices
// are cleared, start is pulsed, the token's V row and then its K column are written like the
// stream unit (64 lanes a cycle, each op only once kv_write_drained is high), and then:
//   * every word of every tile slice (1,536 x 128 x 512 bits) must equal the slice image derived
//     independently from the TILE's address map (rtl/hdc/ot_qwen_rom_tile_w12.sv KV_LOCAL = 1:
//     the engine group that reads each K/V word, its tile, and the tile's local-word formula);
//   * the HBM model must hold the token's K and V sectors (write-back with write-done);
//   * kv_ok must rise only after the fill, and no fault.
// Negative cases: a token write at a wrong position, and a non-E4M3 value, must fault.
// Prints PASS/FAIL lines and a JSON summary on the last line.
#include "Vtb_qwen_rt_kv_stream4.h"
#include "Vtb_qwen_rt_kv_stream4___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include <random>
#include <string>
#include <cstdlib>
#include <functional>

static constexpr int NT = 1536, KVB = 131072, KL = 22;
static int NOTICE_CYC = getenv("KVS_NOTICE") ? atoi(getenv("KVS_NOTICE")) : 400;
static Vtb_qwen_rt_kv_stream4* top;
static uint64_t cyc = 0;
static bool dbg = getenv("KVB_DEBUG") != nullptr;
static bool dbg2 = getenv("KVB_DEBUG2") != nullptr;
static void tick() {
    top->clk = 0; top->eval();
    top->clk = 1; top->eval();
    cyc++;
}
// E4M3 code -> FP32 (the tile's e4m3_f32)
static uint32_t e4m3_f32(uint8_t c) {
    uint32_t s = c >> 7, e = (c >> 3) & 15, m = c & 7, fe, fm;
    if (e) { fe = e + 120; fm = m << 20; }
    else if (m & 4) { fe = 120; fm = (m & 3) << 21; }
    else if (m & 2) { fe = 119; fm = (m & 1) << 22; }
    else if (m & 1) { fe = 118; fm = 0; }
    else { fe = 0; fm = 0; }
    return (s << 31) | (fe << 23) | fm;
}
static uint8_t rand_code(std::mt19937& r) {
    for (;;) { uint8_t c = r() & 0xff; if ((c & 0x7f) != 0x7f) return c; }
}
// HBM sector accessors (model memory: 256-bit words as 8 x u32)
static auto& hbm() { return top->rootp->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__mem; }
static auto& slice() { return top->rootp->tb_qwen_rt_kv_stream4__DOT__slice; }
static uint8_t hbm_byte(uint32_t sec, int b) { return (hbm()[sec][b / 4] >> (8 * (b % 4))) & 0xff; }
static void hbm_set_byte(uint32_t sec, int b, uint8_t v) {
    uint32_t& w = hbm()[sec][b / 4];
    w = (w & ~(0xffu << (8 * (b % 4)))) | (uint32_t(v) << (8 * (b % 4)));
}
static uint8_t slice_byte(int t, int l, int b) { return (slice()[t][l][b / 4] >> (8 * (b % 4))) & 0xff; }

// independent map: which (tile, local, byte) holds lane `lane` of KV word a (the tile formula, KV_LOCAL = 1)
struct Loc { int tile, local, byte; };
static Loc k_loc(int h, int t, int d, int lane) {
    // scores op: group g = (t mod 48)*128 + d reads word a = h*65536 + t*128 + d
    int g = (t % 48) * 128 + d, tile = g / 4, gi = g % 4;
    uint32_t a = (uint32_t(h) << 16) + t * 128 + (d & ~3);   // the tile's group-0 address
    int tk = (a & 0xffff) >> 7, lk = (tk / 48) * 2 + int(a >> 16);
    return {tile, lk, (gi * 16 + lane)};
}
static Loc v_loc(int h, int p, int q, int lane) {
    // weighted sum: group g = q*512 + (p mod 512) reads word VB + h*65536 + p*8 + q at k = p/512
    int g = q * 512 + (p % 512), tile = g / 4, gi = g % 4;
    int c0 = (p % 512) & ~3;
    uint32_t a = KVB + (uint32_t(h) << 16) + ((p / 512) * 512 + c0) * 8 + q;   // group-0 address of the tile
    uint32_t w = a - KVB;
    int pv = (w & 0xffff) >> 3, lv = KL + (pv >> 9) * 2 + int(w >> 16);
    return {tile, lv, (gi * 16 + lane)};
}


struct Layer {
    int layer, P;
    std::vector<uint8_t> exp;       // slice image after this layer's fill + token writes
    uint8_t kt[2][128], vt[2][128];
};
// preload one layer's history into HBM and build its expected slice image
static void prep(Layer& L, uint32_t seed) {
    std::mt19937 rng(seed);
    const int P = L.P, T = P >> 4, PL = P & 15;
    const uint32_t lb = uint32_t(L.layer) * 131072;
    L.exp.assign(size_t(NT) * 128 * 64, 0);
    auto put = [&](Loc l, uint8_t v) { L.exp[(size_t(l.tile) * 128 + l.local) * 64 + l.byte] = v; };
    for (uint32_t s = 0; s < 131072; s++) for (int k = 0; k < 8; k++) hbm()[lb + s][k] = 0;
    for (int h = 0; h < 2; h++)
        for (int t = 0; t <= T; t++)
            for (int d = 0; d < 128; d++)
                for (int l = 0; l < 16; l++) {
                    int p = t * 16 + l;
                    if (p >= P) continue;
                    uint8_t c = rand_code(rng);
                    uint32_t a = (uint32_t(h) << 16) + t * 128 + d;
                    hbm_set_byte(lb + a / 2, (a & 1) * 16 + l, c);
                    put(k_loc(h, t, d, l), c);
                }
    for (int h = 0; h < 2; h++)
        for (int p = 0; p < P; p++)
            for (int q = 0; q < 8; q++)
                for (int l = 0; l < 16; l++) {
                    uint8_t c = rand_code(rng);
                    uint32_t a = KVB + (uint32_t(h) << 16) + p * 8 + q;
                    hbm_set_byte(lb + a / 2, (a & 1) * 16 + l, c);
                    put(v_loc(h, p, q, l), c);
                }
    for (int h = 0; h < 2; h++) for (int d = 0; d < 128; d++) {
        L.kt[h][d] = rand_code(rng); L.vt[h][d] = rand_code(rng);
        put(k_loc(h, T, d, PL), L.kt[h][d]);
        put(v_loc(h, P, d / 16, d % 16), L.vt[h][d]);
    }
}
static void clear_slices() { for (int t = 0; t < NT; t++) for (int l = 0; l < 128; l++) for (int k = 0; k < 16; k++) slice()[t][l][k] = 0; }
static uint64_t drain_wait = 0;
// the stream unit's token writes (an op only when kv_write_drained), V row then K column
static bool token_writes(const Layer& L, int neg) {
    const int P = L.P, T = P >> 4, PL = P & 15;
    auto su_op = [&](bool isv, int h, int d0) {
        uint64_t w0 = cyc;
        while (!top->kv_write_drained) { tick(); if (cyc - w0 > 200000) return false; }
        drain_wait += cyc - w0;
        top->kv_we = 0;
        for (int l = 0; l < 64; l++) {
            int d = d0 + l;
            uint32_t e, v;
            if (isv) { e = 2097152 + (uint32_t(h) * 8192 + P) * 128 + d; v = e4m3_f32(L.vt[h][d]); }
            else { e = ((uint32_t(h) * 512 + T) * 128 + d) * 16 + PL; v = e4m3_f32(L.kt[h][d]); }
            if (neg == 1 && l == 5) e += isv ? 128 : 16;
            if (neg == 2 && l == 7) v |= 0x00001000;
            top->kv_we |= 1ull << l;
            for (int b = 0; b < 24; b++) {
                size_t bit = size_t(l) * 24 + b;
                uint32_t& w = top->kv_waddr[bit / 32];
                w = (w & ~(1u << (bit % 32))) | (((e >> b) & 1u) << (bit % 32));
            }
            top->kv_wdata[l] = v;
        }
        tick();
        top->kv_we = 0;
        return true;
    };
    bool ok = true;
    for (int h = 0; h < 2 && ok; h++) for (int c = 0; c < 2 && ok; c++) ok = su_op(true, h, 64 * c);
    for (int i = 0; i < 40; i++) tick();
    for (int c = 0; c < 2 && ok; c++) for (int h = 0; h < 2 && ok; h++) ok = su_op(false, h, 64 * c);
    return ok;
}
static std::string check_slices(const Layer& L) {
    long bad = 0, first = -1;
    for (int t = 0; t < NT; t++)
        for (int l = 0; l < 128; l++)
            for (int b = 0; b < 64; b++)
                if (slice_byte(t, l, b) != L.exp[(size_t(t) * 128 + l) * 64 + b]) { if (first < 0) first = (long(t) * 128 + l) * 64 + b; bad++; }
    return bad ? "slice bytes wrong: " + std::to_string(bad) + " first " + std::to_string(first) : "";
}
static std::string check_hbm_token(const Layer& L) {
    const int P = L.P, T = P >> 4, PL = P & 15;
    const uint32_t lb = uint32_t(L.layer) * 131072;
    for (int h = 0; h < 2; h++) for (int d = 0; d < 128; d++) {
        uint32_t a = (uint32_t(h) << 16) + T * 128 + d;
        if (hbm_byte(lb + a / 2, (a & 1) * 16 + PL) != L.kt[h][d]) return "HBM K token lane (layer " + std::to_string(L.layer) + ")";
        uint32_t av = KVB + (uint32_t(h) << 16) + P * 8 + d / 16;
        if (hbm_byte(lb + av / 2, (av & 1) * 16 + d % 16) != L.vt[h][d]) return "HBM V token (layer " + std::to_string(L.layer) + ")";
    }
    return "";
}
static bool wait_for(const char* what, std::function<bool()> f, uint64_t lim = 400000) {
    uint64_t w0 = cyc;
    while (!f()) { if (top->fault) return false; tick(); if (cyc - w0 > lim) { printf("timeout waiting %s\n", what); return false; } }
    return true;
}
static std::string stats_line(const char* name) {
    auto* rt = top->rootp;
    char b[512];
    snprintf(b, sizeof b, "hbm_act=%ld rd=%ld wr=%ld refpb=%ld violations=%ld max_landing=%ld rsp_tile_stall=%u fill_sectors=%u wr_sectors=%u wr_lat_max=%u",
             (long)rt->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__n_act, (long)rt->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__n_rd,
             (long)rt->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__n_wr, (long)rt->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__n_ref,
             (long)rt->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__viol, (long)rt->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__max_land,
             top->st_rsp_stall, top->st_fill_sectors, top->st_wr_sectors, top->st_wr_lat_max);
    printf("STATS %s %s\n", name, b);
    return b;
}
static void fresh() {
    delete top; top = new Vtb_qwen_rt_kv_stream4; cyc = 0;
    top->rst_n = 0; top->start = 0; top->kvd_v = 0; top->nx_layer = 255; top->pos_hint = 0; top->kv_free = 0;
    top->early_go = 0; top->posted_wb = 0;
    for (int i = 0; i < 5; i++) tick();
    top->rst_n = 1; tick();
}
static std::string js;
static bool all_pass = true;
static void report(const std::string& name, bool pass, const std::string& why, const std::string& kv) {
    printf("%s %s %s : %s\n", pass ? "PASS" : "FAIL", name.c_str(), kv.c_str(), why.c_str());
    all_pass &= pass;
    js += std::string(js.empty() ? "" : ",") + "{\"name\":\"" + name + "\",\"pass\":" + (pass ? "true" : "false") + "," + kv + ",\"detail\":\"" + why + "\"}";
}
// ISO: one layer from start (no notice)
static void iso(const std::string& name, int layer, int P, uint32_t seed, int neg, bool posted) {
    fresh();
    top->posted_wb = posted;
    Layer L{layer, P};
    clear_slices(); prep(L, seed);
    top->pos_hint = P;
    top->pos = P; top->layer = layer; top->start = 1; tick(); top->start = 0;
    uint64_t t0 = cyc;
    for (int i = 0; i < 6; i++) tick();
    drain_wait = 0;
    bool ok = token_writes(L, neg);
    top->kvd_v = 1; top->kvd_pos = P; tick(); top->kvd_v = 0;
    ok = ok && wait_for("kv_ok", [] { return top->kv_ok != 0; });
    uint64_t kvok = cyc - t0;
    ok = ok && wait_for("drain", [] { return top->kv_write_drained && !top->wb_busy; });
    for (int i = 0; i < 20; i++) tick();
    std::string st = stats_line(name.c_str());
    double fc = top->st_fill_cycles, sec = top->st_fill_sectors;
    char kv[400];
    snprintf(kv, sizeof kv, "\"P\":%d,\"fill_cycles\":%u,\"fill_sectors\":%u,\"sectors_per_cycle\":%.2f,\"tb_s_at_1p2ghz\":%.3f,"
             "\"kv_ok_after_start\":%lu,\"su_drain_wait\":%lu,\"violations\":%ld", P, top->st_fill_cycles, top->st_fill_sectors,
             fc ? sec / fc : 0.0, fc ? sec * 32 / (fc * 0.833333) * 1e-3 : 0.0, (unsigned long)kvok, (unsigned long)drain_wait,
             (long)top->rootp->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__viol);
    if (neg) { report(name, top->fault != 0, top->fault ? "faulted as required (code " + std::to_string(top->fault_code) + ")" : "no fault", kv); return; }
    std::string why = !ok ? "timeout" : top->fault ? "fault code " + std::to_string(top->fault_code) : check_slices(L);
    if (why.empty()) why = check_hbm_token(L);
    report(name, why.empty(), why.empty() ? "slices and token HBM codes exact" : why, kv);
}
// CHAIN: A then B (same P) with the straps
static void chain(const std::string& name, int P, uint32_t seed, bool early, bool posted, int attn, int mlp) {
    fresh();
    top->early_go = early; top->posted_wb = posted;
    Layer A{0, P}, B{1, P};
    clear_slices(); prep(A, seed); prep(B, seed + 101);
    top->pos_hint = P; top->nx_layer = 1;
    top->pos = P; top->layer = 0; top->start = 1; tick(); top->start = 0;
    uint64_t tA = cyc;
    for (int i = 0; i < 6; i++) tick();
    drain_wait = 0;
    bool ok = token_writes(A, 0);
    top->kvd_v = 1; top->kvd_pos = P; tick(); top->kvd_v = 0;
    ok = ok && wait_for("kv_ok A", [] { return top->kv_ok != 0; });
    uint64_t kvokA = cyc - tA, fillA = top->st_fill_cycles;
    std::string why = !ok ? "A timeout" : check_slices(A);
    if (why.empty()) {
        for (int i = 0; i < attn; i++) tick();              // QK / softmax / PV / O + all-reduce
        top->kv_free = 1; tick(); top->kv_free = 0;          // the next segment starts
        uint64_t tf = cyc;
        for (int i = 0; i < mlp; i++) tick();               // the MLP
        uint64_t aend = cyc;
        top->nx_layer = 255;
        top->pos = P; top->layer = 1; top->start = 1; tick(); top->start = 0;
        uint64_t tB = cyc;
        for (int i = 0; i < 6; i++) tick();
        ok = token_writes(B, 0);
        top->kvd_v = 1; top->kvd_pos = P; tick(); top->kvd_v = 0;
        ok = ok && wait_for("kv_ok B", [] { return top->kv_ok != 0; });
        uint64_t kvokB = cyc - tB;
        uint32_t exposed = top->st_fill_exposed, fillB = top->st_fill_cycles;
        why = !ok ? "B timeout" : check_slices(B);
        ok = ok && wait_for("drain", [] { return top->kv_write_drained && !top->wb_busy; });
        for (int i = 0; i < 20; i++) tick();
        if (why.empty() && !ok) why = "drain timeout";
        if (why.empty() && top->fault) why = "fault code " + std::to_string(top->fault_code);
        if (why.empty()) why = check_hbm_token(A);
        if (why.empty()) why = check_hbm_token(B);
        stats_line(name.c_str());
        char kv[500];
        snprintf(kv, sizeof kv, "\"P\":%d,\"early_go\":%d,\"posted_wb\":%d,\"attn_cycles\":%d,\"mlp_cycles\":%d,\"A_fill_cycles\":%lu,"
                 "\"A_kv_ok_after_start\":%lu,\"B_fill_cycles\":%u,\"B_fill_exposed_after_start\":%u,\"B_kv_ok_after_start\":%lu,"
                 "\"su_drain_wait\":%lu,\"violations\":%ld", P, int(early), int(posted), attn, mlp, (unsigned long)fillA,
                 (unsigned long)kvokA, fillB, exposed, (unsigned long)kvokB, (unsigned long)drain_wait,
                 (long)top->rootp->tb_qwen_rt_kv_stream4__DOT__u_hbm__DOT__viol);
        (void)tf; (void)aend;
        report(name, why.empty(), why.empty() ? "A and B slices, both token write-backs exact" : why, kv);
        return;
    }
    report(name, false, why, "\"P\":" + std::to_string(P));
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    top = new Vtb_qwen_rt_kv_stream4;
    const char* only = getenv("KVB_ONLY");
    auto want = [&](const char* n) { return !only || std::string(only) == n; };
    if (want("ISO_P255")) iso("ISO_P255", 0, 255, 1, 0, false);
    if (want("ISO_P256_tile_open")) iso("ISO_P256_tile_open", 1, 256, 3, 0, false);
    if (want("ISO_P0")) iso("ISO_P0", 1, 0, 2, 0, false);
    if (want("ISO_P1023")) iso("ISO_P1023", 1, 1023, 4, 0, false);
    if (want("ISO_P4095")) iso("ISO_P4095", 0, 4095, 5, 0, false);
    if (want("ISO_P8191")) iso("ISO_P8191", 1, 8191, 6, 0, false);
    if (want("ISO_P8191_posted")) iso("ISO_P8191_posted", 0, 8191, 7, 0, true);
    if (want("CHAIN_P8191_base")) chain("CHAIN_P8191_base", 8191, 11, false, false, 1200, 3000);
    if (want("CHAIN_P8191_early_posted")) chain("CHAIN_P8191_early_posted", 8191, 12, true, true, 1200, 3000);
    if (want("CHAIN_P4095_early_posted")) chain("CHAIN_P4095_early_posted", 4095, 13, true, true, 600, 3000);
    if (want("CHAIN_P8191_early_short_mlp")) chain("CHAIN_P8191_early_short_mlp", 8191, 14, true, true, 1200, 400);
    if (want("CHAIN_P255_early_posted")) chain("CHAIN_P255_early_posted", 255, 15, true, true, 300, 2500);
    if (want("NEG_wrong_position")) iso("NEG_wrong_position", 0, 255, 7, 1, false);
    if (want("NEG_not_e4m3")) iso("NEG_not_e4m3", 0, 255, 8, 2, false);
    if (want("NEG_P8192_beyond_map")) iso("NEG_P8192_beyond_map", 0, 8192, 9, 3, false);
    printf("%s\n{\"cases\":[%s],\"status\":\"%s\"}\n", all_pass ? "KV_SERVICE4_STANDALONE PASS" : "KV_SERVICE4_STANDALONE FAIL",
           js.c_str(), all_pass ? "pass" : "fail");
    delete top;
    return all_pass ? 0 : 1;
}
