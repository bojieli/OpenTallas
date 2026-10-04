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
#include "Vtb_qwen_rt_kv_stream.h"
#include "Vtb_qwen_rt_kv_stream___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include <random>
#include <string>
#include <cstdlib>

static constexpr int NT = 1536, KVB = 131072, KL = 22;
static int NOTICE_CYC = getenv("KVS_NOTICE") ? atoi(getenv("KVS_NOTICE")) : 400;
static Vtb_qwen_rt_kv_stream* top;
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
static auto& hbm() { return top->rootp->tb_qwen_rt_kv_stream__DOT__u_hbm__DOT__mem; }
static auto& slice() { return top->rootp->tb_qwen_rt_kv_stream__DOT__slice; }
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

struct Result { std::string name; bool pass; std::string why; uint64_t fill_cycles, kvok_cycle, drain_cycles; };

static Result run_case(const char* name, int layer, int P, uint32_t seed, int neg, bool notice) {
    if (getenv("KVB_ONLY") && std::string(getenv("KVB_ONLY")) != name) return Result{name, true, "skipped", 0, 0, 0};
    std::mt19937 rng(seed);
    const int T = P >> 4, PL = P & 15;
    const uint32_t lb = uint32_t(layer) * 131072;
    // expected slice image (only words this case writes; everything else stays zero)
    std::vector<uint8_t> exp(size_t(NT) * 128 * 64, 0);
    auto put = [&](Loc L, uint8_t v) { exp[(size_t(L.tile) * 128 + L.local) * 64 + L.byte] = v; };
    // clear slices and this layer's HBM region
    for (int t = 0; t < NT; t++) for (int l = 0; l < 128; l++) for (int k = 0; k < 16; k++) slice()[t][l][k] = 0;
    for (uint32_t s = 0; s < 131072; s++) for (int k = 0; k < 8; k++) hbm()[lb + s][k] = 0;
    // preload history
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
    // token values
    uint8_t kt[2][128], vt[2][128];
    for (int h = 0; h < 2; h++) for (int d = 0; d < 128; d++) {
        kt[h][d] = rand_code(rng); vt[h][d] = rand_code(rng);
        put(k_loc(h, T, d, PL), kt[h][d]);
        put(v_loc(h, P, d / 16, d % 16), vt[h][d]);
    }
    // notice: the next layer's descriptor, posted while the previous layer is retired
    top->pos_hint = P;
    if (notice) { top->nx_layer = layer; for (int i = 0; i < NOTICE_CYC; i++) tick(); }
    // start
    top->pos = P; top->layer = layer; top->start = 1; tick(); top->start = 0;
    top->nx_layer = 255;
    uint64_t t_start = cyc, kvok_at = 0, drain_cycles = 0;
    auto clear_we = [&]() { top->kv_we = 0; };
    // wait like the core: an op only when drained
    auto su_op = [&](bool isv, int h, int d0) {
        uint64_t w0 = cyc;
        while (!top->kv_write_drained) { tick(); if (cyc - w0 > 200000) return false; }
        drain_cycles += cyc - w0;
        clear_we();
        for (int l = 0; l < 64; l++) {
            int d = d0 + l;
            uint32_t e, v;
            if (isv) { e = 2097152 + (uint32_t(h) * 8192 + P) * 128 + d; v = e4m3_f32(vt[h][d]); }
            else { e = ((uint32_t(h) * 512 + T) * 128 + d) * 16 + PL; v = e4m3_f32(kt[h][d]); }
            if (neg == 1 && l == 5) e += isv ? 128 : 16;          // wrong position
            if (neg == 2 && l == 7) v |= 0x00001000;               // not an E4M3 value
            top->kv_we |= 1ull << l;
            for (int b = 0; b < 24; b++) {
                size_t bit = size_t(l) * 24 + b;
                uint32_t& w = top->kv_waddr[bit / 32];
                w = (w & ~(1u << (bit % 32))) | (((e >> b) & 1u) << (bit % 32));
            }
            top->kv_wdata[l] = v;
        }
        tick();
        clear_we();
        return true;
    };
    for (int i = 0; i < 6; i++) tick();
    bool ok = true;
    // V row (op #3): 2 heads x 2 chunks of 64 dims; a few cycles later K (ops #8, #10)
    for (int h = 0; h < 2 && ok; h++) for (int c = 0; c < 2 && ok; c++) ok = su_op(true, h, 64 * c);
    for (int i = 0; i < 40; i++) tick();
    for (int c = 0; c < 2 && ok; c++) for (int h = 0; h < 2 && ok; h++) ok = su_op(false, h, 64 * c);
    // descriptor of the scores op
    top->kvd_v = 1; top->kvd_pos = P; tick(); top->kvd_v = 0;
    uint64_t w0 = cyc;
    while (ok && !top->kv_ok && !top->fault) { tick(); if (cyc - w0 > 400000) ok = false; }
    kvok_at = cyc - t_start;
    w0 = cyc;
    while (ok && !top->kv_write_drained && !top->fault) { tick(); if (cyc - w0 > 400000) ok = false; }
    for (int i = 0; i < 20; i++) tick();
    Result r{name, false, "", top->st_fill_cycles, kvok_at, drain_cycles};
    {
        auto* rt = top->rootp;
        printf("STATS %s notice=%d hbm_act=%ld rd=%ld wr=%ld refpb=%ld violations=%ld max_landing=%ld rsp_tile_stall=%u fill_sectors=%u wr_sectors=%u wr_lat_max=%u\n",
               name, int(notice), (long)rt->tb_qwen_rt_kv_stream__DOT__u_hbm__DOT__n_act, (long)rt->tb_qwen_rt_kv_stream__DOT__u_hbm__DOT__n_rd,
               (long)rt->tb_qwen_rt_kv_stream__DOT__u_hbm__DOT__n_wr, (long)rt->tb_qwen_rt_kv_stream__DOT__u_hbm__DOT__n_ref,
               (long)rt->tb_qwen_rt_kv_stream__DOT__u_hbm__DOT__viol, (long)rt->tb_qwen_rt_kv_stream__DOT__u_hbm__DOT__max_land,
               top->st_rsp_stall, top->st_fill_sectors, top->st_wr_sectors, top->st_wr_lat_max);
    }
    if (neg) {
        r.pass = top->fault != 0;
        r.why = r.pass ? "faulted as required (code " + std::to_string(top->fault_code) + ")" : "no fault";
        return r;
    }
    if (!ok) { r.why = "timeout"; return r; }
    if (top->fault) { r.why = "fault code " + std::to_string(top->fault_code); return r; }
    // slices
    long bad = 0, first = -1;
    for (int t = 0; t < NT; t++)
        for (int l = 0; l < 128; l++)
            for (int b = 0; b < 64; b++)
                if (slice_byte(t, l, b) != exp[(size_t(t) * 128 + l) * 64 + b]) { if (first < 0) first = (long(t) * 128 + l) * 64 + b; bad++; }
    if (bad) { r.why = "slice bytes wrong: " + std::to_string(bad) + " first " + std::to_string(first); return r; }
    // HBM write-back of the token
    for (int h = 0; h < 2; h++) for (int d = 0; d < 128; d++) {
        uint32_t a = (uint32_t(h) << 16) + T * 128 + d;
        if (hbm_byte(lb + a / 2, (a & 1) * 16 + PL) != kt[h][d]) { r.why = "HBM K token lane"; return r; }
        uint32_t av = KVB + (uint32_t(h) << 16) + P * 8 + d / 16;
        if (hbm_byte(lb + av / 2, (av & 1) * 16 + d % 16) != vt[h][d]) { r.why = "HBM V token"; return r; }
    }
    r.pass = true;
    r.why = "all " + std::to_string(size_t(NT) * 128 * 64) + " slice bytes and 512 token HBM codes exact";
    return r;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    top = new Vtb_qwen_rt_kv_stream;
    top->rst_n = 0; top->start = 0; top->kvd_v = 0; top->nx_layer = 255; top->pos_hint = 0;
    for (int i = 0; i < 5; i++) tick();
    top->rst_n = 1; tick();
    std::vector<Result> rs;
    for (int nt = 0; nt < 2; nt++) {
        bool n = nt == 1;
        std::string x = n ? "_notice" : "";
        rs.push_back(run_case(("L0_P255" + x).c_str(), 0, 255, 1, 0, n));
        rs.push_back(run_case(("L1_P0" + x).c_str(), 1, 0, 2, 0, n));
        rs.push_back(run_case(("L0_P256_tile_open" + x).c_str(), 0, 256, 3, 0, n));
        rs.push_back(run_case(("L1_P1023" + x).c_str(), 1, 1023, 4, 0, n));
        rs.push_back(run_case(("L0_P2047" + x).c_str(), 0, 2047, 5, 0, n));
    }
    bool all = true;
    std::string js = "{\"cases\":[";
    for (size_t i = 0; i < rs.size(); i++) {
        auto& r = rs[i];
        printf("%s %s fill_cycles=%lu kv_ok_after=%lu su_drain_wait=%lu : %s\n", r.pass ? "PASS" : "FAIL", r.name.c_str(),
               (unsigned long)r.fill_cycles, (unsigned long)r.kvok_cycle, (unsigned long)r.drain_cycles, r.why.c_str());
        all &= r.pass;
        js += std::string(i ? "," : "") + "{\"name\":\"" + r.name + "\",\"pass\":" + (r.pass ? "true" : "false") +
              ",\"fill_cycles\":" + std::to_string(r.fill_cycles) + ",\"kv_ok_after_start\":" + std::to_string(r.kvok_cycle) +
              ",\"su_drain_wait_cycles\":" + std::to_string(r.drain_cycles) + ",\"detail\":\"" + r.why + "\"}";
    }
    // negative cases: a fresh model each (the fault is sticky)
    for (int neg = 1; neg <= 3; neg++) {
        delete top; top = new Vtb_qwen_rt_kv_stream; cyc = 0;
        top->rst_n = 0; top->nx_layer = 255; for (int i = 0; i < 5; i++) tick(); top->rst_n = 1; tick();
        auto r = run_case(neg == 1 ? "NEG_wrong_position" : neg == 2 ? "NEG_not_e4m3" : "NEG_P2048_beyond_stream_map",
                          0, neg == 3 ? 2048 : 255, 7, neg, false);
        printf("%s %s : %s\n", r.pass ? "PASS" : "FAIL", r.name.c_str(), r.why.c_str());
        all &= r.pass;
        js += ",{\"name\":\"" + r.name + "\",\"pass\":" + (r.pass ? "true" : "false") + ",\"detail\":\"" + r.why + "\"}";
    }
    js += std::string("],\"status\":\"") + (all ? "pass" : "fail") + "\"}";
    printf("%s\n%s\n", all ? "KV_SERVICE_STANDALONE PASS" : "KV_SERVICE_STANDALONE FAIL", js.c_str());
    delete top;
    return all ? 0 : 1;
}
