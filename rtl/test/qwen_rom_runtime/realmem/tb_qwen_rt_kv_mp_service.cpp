// Standalone Verilator bench of the MULTI-POSITION KV service (rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv),
// derived from tb_qwen_rt_kv_service.cpp (unchanged).  Part 1 replays every single-position case of that
// bench unchanged (np = 1; also run with VPMAX = 1).  Part 2 (VPMAX > 1) runs DSpark verify blocks:
// a chain of speculative steps on one persistent HBM layer region -- block writes for P .. P+np-1
// (op-major like the VPOS program, each op only once kv_write_drained is high), slice and HBM checks,
// commit of a+1 positions, and the next step at the committed length over the stale rejected rows --
// plus negative cases for every new fault.  Original description:
//
// with the HBM timing model (rtl/hdc/kv/ot_qwen_hbm_model_ack.sv, WR_ACK = 1).
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
#include "Vtb_qwen_rt_kv_mp_service.h"
#include "Vtb_qwen_rt_kv_mp_service___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include <random>
#include <string>
#include <cstdlib>
#include <array>
#include <algorithm>

static constexpr int NT = 1536, KVB = 131072, KL = 22;
static Vtb_qwen_rt_kv_mp_service* top;
static uint64_t cyc = 0;
static bool dbg = getenv("KVB_DEBUG") != nullptr;
static bool dbg2 = getenv("KVB_DEBUG2") != nullptr;
static void tick() {
    top->clk = 0; top->eval();
    top->clk = 1; top->eval();
    cyc++;
    static unsigned long bp = 0, idle = 0, busy = 0, nv = 0, nr = 0;
    if (dbg2) {
        auto* r = top->rootp;
        nv += __builtin_popcount(r->tb_qwen_rt_kv_mp_service__DOT__h_rsp_v);
        nr += __builtin_popcount(r->tb_qwen_rt_kv_mp_service__DOT__h_rsp_v & r->tb_qwen_rt_kv_mp_service__DOT__h_rsp_rdy);
        if (r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__walk_v) {
            if (r->tb_qwen_rt_kv_mp_service__DOT__h_req_v && !r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__rdy_tgt) bp++;
            else if (!r->tb_qwen_rt_kv_mp_service__DOT__h_req_v) idle++;
            else busy++;
        }
    }
    if (dbg2 && cyc % 500 == 0) {
        printf("D3 bp=%lu idle=%lu busy=%lu rsp_v=%lu taken=%lu\n", bp, idle, busy, nv, nr); bp = idle = busy = nv = nr = 0;
        auto* r = top->rootp;
        unsigned long rd = 0; int qn = 0, rn = 0;
        for (int p = 0; p < 32; p++) { rd += r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_rd[p];
            qn += r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__q_n[p]; rn += r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__r_n[p]; }
        int nv = 0; for (int i = 0; i < 4; i++) nv += __builtin_popcount(r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__r_valid[i]);
        printf("D2 cyc=%lu hbm_rd=%lu qn=%d rn=%d rvalid=%d seg=%d next=%u issued=%u\n", (unsigned long)cyc, rd, qn, rn, nv,
               r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__seg, r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__w_next, top->st_fill_sectors);
    }
    if (dbg && cyc < 400) {
        auto* r = top->rootp;
        printf("DBG v=%08x rdy=%08x rd=%lu lat_max=%lu qn0=%d rn0=%d cyc=%lu act=%d walk=%d seg=%d next=%u end=%u rvalid=%016lx fill_done=%d req_v=%d rdy=%d okn=%d drained=%d fault=%d\n",
               r->tb_qwen_rt_kv_mp_service__DOT__h_rsp_v, r->tb_qwen_rt_kv_mp_service__DOT__h_rsp_rdy, (unsigned long)r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_rd[0], (unsigned long)r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_rd_lat_max, r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__q_n[0], r->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__r_n[0], (unsigned long)cyc, r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__active, r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__walk_v,
               r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__seg, r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__w_next,
               r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__w_end, (unsigned long)r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__r_valid[0],
               r->tb_qwen_rt_kv_mp_service__DOT__u_svc__DOT__fill_done, 0,
               0, top->kv_ok, top->kv_write_drained, top->fault);
    }
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
static auto& hbm() { return top->rootp->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__mem; }
static auto& slice() { return top->rootp->tb_qwen_rt_kv_mp_service__DOT__slice; }
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

static Result run_case(const char* name, int layer, int P, uint32_t seed, int neg) {
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
    if (dbg2) printf("CASE %s start cyc=%lu\n", name, (unsigned long)cyc);
    // start
    top->pos = P; top->layer = layer; top->start = 1; tick(); top->start = 0;
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
        unsigned long hit = 0, conf = 0, act = 0, ref = 0, rd = 0;
        for (int p = 0; p < 32; p++) {
            hit += rt->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_hit[p]; conf += rt->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_conf[p];
            act += rt->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_act[p]; ref += rt->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_ref[p];
            rd += rt->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_rd[p];
        }
        printf("STATS %s hbm_rd=%lu hit=%lu conflict=%lu act=%lu refresh=%lu rd_lat_max_ps=%lu rsp_tile_stall=%u fill_sectors=%u wr_sectors=%u wr_lat_max=%u\n",
               name, rd, hit, conf, act, ref, (unsigned long)rt->tb_qwen_rt_kv_mp_service__DOT__u_hbm__DOT__st_rd_lat_max,
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

// ======================= part 2: DSpark verify blocks (VPMAX > 1) =======================
#ifndef VPMAX_B
#define VPMAX_B 4
#endif
// host model of one layer region: the code of K (h, pos, d) and V (h, pos, d); -1: not committed
struct HostKV {
    std::vector<int16_t> k, v;
    HostKV() : k(size_t(2) * 8192 * 128, -1), v(size_t(2) * 8192 * 128, -1) {}
    int16_t& K(int h, int p, int d) { return k[(size_t(h) * 8192 + p) * 128 + d]; }
    int16_t& V(int h, int p, int d) { return v[(size_t(h) * 8192 + p) * 128 + d]; }
};
static std::vector<uint8_t> bexp;   // expected slice image, persistent across the steps of a chain
static void bput(Loc L, uint8_t c) { bexp[(size_t(L.tile) * 128 + L.local) * 64 + L.byte] = c; }
static void clear_slices() {
    for (int t = 0; t < NT; t++) for (int l = 0; l < 128; l++) for (int k = 0; k < 16; k++) slice()[t][l][k] = 0;
    std::fill(bexp.begin(), bexp.end(), 0);
}
static void set_lane(int l, uint32_t e, uint32_t v) {
    top->kv_we |= 1ull << l;
    for (int b = 0; b < 24; b++) {
        size_t bit = size_t(l) * 24 + b;
        uint32_t& w = top->kv_waddr[bit / 32];
        w = (w & ~(1u << (bit % 32))) | (((e >> b) & 1u) << (bit % 32));
    }
    top->kv_wdata[l] = v;
}
struct StepOut { bool ok; std::string why; uint64_t kvok_after, drain_wait, cycles; uint32_t wr_sectors; };
// neg: 0 none, 3 write outside the block, 4 duplicate K lane write, 9 commit before write-done
static StepOut block_step(const char* name, int layer, int P, int np, uint32_t seed, HostKV& hk, int neg) {
    std::mt19937 rng(seed);
    const int T = P >> 4, PL = P & 15;
    const uint32_t lb = uint32_t(layer) * 131072;
    StepOut o{false, "", 0, 0, 0, 0};
    // 1. what the fill must restore: committed rows only (K tiles 0..T, lanes < P; V rows < P)
    for (int h = 0; h < 2; h++)
        for (int t = 0; t <= T; t++)
            for (int d = 0; d < 128; d++)
                for (int l = 0; l < 16; l++) {
                    int p = t * 16 + l;
                    if (p >= P) continue;
                    if (hk.K(h, p, d) < 0) { o.why = "host model: committed K missing"; return o; }
                    bput(k_loc(h, t, d, l), uint8_t(hk.K(h, p, d)));
                }
    for (int h = 0; h < 2; h++)
        for (int p = 0; p < P; p++)
            for (int q = 0; q < 8; q++)
                for (int l = 0; l < 16; l++) {
                    if (hk.V(h, p, q * 16 + l) < 0) { o.why = "host model: committed V missing"; return o; }
                    bput(v_loc(h, p, q, l), uint8_t(hk.V(h, p, q * 16 + l)));
                }
    // 2. the block's tokens
    std::vector<uint8_t> kt(size_t(np) * 256), vt(size_t(np) * 256);
    for (int j = 0; j < np; j++)
        for (int h = 0; h < 2; h++)
            for (int d = 0; d < 128; d++) {
                uint8_t kc = rand_code(rng), vc = rand_code(rng);
                kt[(j * 2 + h) * 128 + d] = kc; vt[(j * 2 + h) * 128 + d] = vc;
                int pj = P + j;
                bput(k_loc(h, pj >> 4, d, pj & 15), kc);
                bput(v_loc(h, pj, d / 16, d % 16), vc);
                hk.K(h, pj, d) = kc; hk.V(h, pj, d) = vc;
            }
    uint32_t wr0 = top->st_wr_sectors;
    top->pos = P; top->layer = layer; top->npos = np; top->start = 1; tick(); top->start = 0;
    uint64_t t0 = cyc;
    // an op = consecutive 64-lane cycles, issued only once kv_write_drained is high (KV_VEC_WRITE_BRIDGE)
    auto op = [&](const std::vector<std::pair<uint32_t, uint32_t>>& lanes) {
        uint64_t w0 = cyc;
        while (!top->kv_write_drained) { tick(); if (cyc - w0 > 200000 || top->fault) return false; }
        o.drain_wait += cyc - w0;
        for (size_t c = 0; c < lanes.size(); c += 64) {
            top->kv_we = 0;
            for (size_t l = 0; l < 64 && c + l < lanes.size(); l++) set_lane(int(l), lanes[c + l].first, lanes[c + l].second);
            tick();
        }
        top->kv_we = 0;
        return true;
    };
    for (int i = 0; i < 6; i++) tick();
    bool ok = true;
    // op-major, as the VPOS program: V rows of every position, then K lo of every position, then K hi
    for (int j = 0; j < np && ok; j++) {
        std::vector<std::pair<uint32_t, uint32_t>> ln;
        for (int h = 0; h < 2; h++) for (int d = 0; d < 128; d++) {
            uint32_t e = 2097152 + (uint32_t(h) * 8192 + P + j) * 128 + d;
            if (neg == 3 && j == np - 1 && h == 1 && d == 3) e += 128;          // row P+np: outside the block
            ln.push_back({e, e4m3_f32(vt[(j * 2 + h) * 128 + d])});
        }
        ok = op(ln);
    }
    for (int i = 0; i < 40 && ok; i++) tick();
    for (int half = 0; half < 2 && ok; half++)
        for (int j = 0; j < np && ok; j++) {
            std::vector<std::pair<uint32_t, uint32_t>> ln;
            int pj = P + j;
            for (int h = 0; h < 2; h++) for (int d = 64 * half; d < 64 * half + 64; d++) {
                uint32_t e = ((uint32_t(h) * 512 + (pj >> 4)) * 128 + d) * 16 + (pj & 15);
                ln.push_back({e, e4m3_f32(kt[(j * 2 + h) * 128 + d])});
            }
            if (neg == 4 && half == 1 && j == np - 1) ln.push_back(ln.front());   // a lane written twice
            ok = op(ln);
        }
    if (neg == 9) {   // commit while the last K op's write-through is still in flight
        top->commit_v = 1; top->commit_n = 1; tick(); top->commit_v = 0;
    }
    top->kvd_v = 1; top->kvd_pos = P; tick(); top->kvd_v = 0;
    uint64_t w0 = cyc;
    while (ok && !top->kv_ok && !top->fault) { tick(); if (cyc - w0 > 400000) ok = false; }
    o.kvok_after = cyc - t0;
    w0 = cyc;
    while (ok && !top->kv_write_drained && !top->fault) { tick(); if (cyc - w0 > 400000) ok = false; }
    for (int i = 0; i < 20; i++) tick();
    o.cycles = cyc - t0;
    o.wr_sectors = top->st_wr_sectors - wr0;
    if (neg) { o.ok = top->fault != 0 && ((top->fault_code >> neg) & 1); o.why = "fault_code " + std::to_string(top->fault_code); return o; }
    if (!ok) { o.why = "timeout"; return o; }
    if (top->fault) { o.why = "fault code " + std::to_string(top->fault_code); return o; }
    long bad = 0, first = -1;
    for (int t = 0; t < NT; t++)
        for (int l = 0; l < 128; l++)
            for (int b = 0; b < 64; b++)
                if (slice_byte(t, l, b) != bexp[(size_t(t) * 128 + l) * 64 + b]) { if (first < 0) first = (long(t) * 128 + l) * 64 + b; bad++; }
    if (bad) { o.why = std::string(name) + ": slice bytes wrong: " + std::to_string(bad) + " first " + std::to_string(first); return o; }
    // HBM: every committed row (< P) unchanged and every block row written back
    for (int h = 0; h < 2; h++)
        for (int p = 0; p < P + np; p++)
            for (int d = 0; d < 128; d++) {
                uint32_t a = (uint32_t(h) << 16) + (p >> 4) * 128 + d;
                if (hk.K(h, p, d) >= 0 && hbm_byte(lb + a / 2, (a & 1) * 16 + (p & 15)) != uint8_t(hk.K(h, p, d))) {
                    o.why = "HBM K row " + std::to_string(p); return o; }
                uint32_t av = KVB + (uint32_t(h) << 16) + p * 8 + d / 16;
                if (hk.V(h, p, d) >= 0 && hbm_byte(lb + av / 2, (av & 1) * 16 + d % 16) != uint8_t(hk.V(h, p, d))) {
                    o.why = "HBM V row " + std::to_string(p); return o; }
            }
    o.ok = true;
    o.why = "slices exact; HBM rows 0.." + std::to_string(P + np - 1) + " exact";
    return o;
}
static bool do_commit(int P, int n, HostKV& hk, std::string& why) {
    uint64_t w0 = cyc;
    while (!top->kv_write_drained) { tick(); if (cyc - w0 > 400000) { why = "commit: never drained"; return false; } }
    top->commit_v = 1; top->commit_n = n; tick(); top->commit_v = 0; tick();
    if (top->fault) { why = "commit fault " + std::to_string(top->fault_code); return false; }
    if (!top->committed_v || int(top->committed_len) != P + n) { why = "committed_len " + std::to_string(top->committed_len); return false; }
    // rollback in the host model: rows >= P + n are no longer committed (their HBM bytes are stale)
    for (int h = 0; h < 2; h++) for (int p = P + n; p < 8192; p++) for (int d = 0; d < 128; d++) { hk.K(h, p, d) = -1; hk.V(h, p, d) = -1; }
    return true;
}
static void fresh_model() {
    delete top; top = new Vtb_qwen_rt_kv_mp_service; cyc = 0;
    top->npos = 1; top->commit_v = 0; top->commit_n = 0; top->start = 0; top->kvd_v = 0;
    top->rst_n = 0; for (int i = 0; i < 5; i++) tick(); top->rst_n = 1; tick();
}
static void preload_history(int layer, int P0, uint32_t seed, HostKV& hk) {
    std::mt19937 rng(seed);
    const uint32_t lb = uint32_t(layer) * 131072;
    for (uint32_t s = 0; s < 131072; s++) for (int k = 0; k < 8; k++) hbm()[lb + s][k] = 0;
    for (int h = 0; h < 2; h++)
        for (int p = 0; p < P0; p++)
            for (int d = 0; d < 128; d++) {
                uint8_t kc = rand_code(rng), vc = rand_code(rng);
                uint32_t a = (uint32_t(h) << 16) + (p >> 4) * 128 + d;
                hbm_set_byte(lb + a / 2, (a & 1) * 16 + (p & 15), kc);
                uint32_t av = KVB + (uint32_t(h) << 16) + p * 8 + d / 16;
                hbm_set_byte(lb + av / 2, (av & 1) * 16 + d % 16, vc);
                hk.K(h, p, d) = kc; hk.V(h, p, d) = vc;
            }
}
struct Chain { const char* name; int layer; std::vector<std::array<int, 2>> steps; };   // {np, commit_n}
static void block_part(bool& all, std::string& js) {
    bexp.assign(size_t(NT) * 128 * 64, 0);
    const std::vector<std::pair<int, Chain>> chains = {
        // start P, steps {np, commit_n}: rejected drafts, an AR step after a rejection, 16-tile and 512-row crossings
        {250,  {"C0_P250_tile15_16", 0, {{4, 2}, {1, 1}, {4, 1}, {4, 3}, {1, 1}, {4, 4}}}},
        {1021, {"C1_P1021_row1024",  1, {{4, 4}, {4, 1}, {2, 2}, {4, 2}}}},
        {8185, {"C2_P8185_window_end", 0, {{4, 1}, {4, 4}, {2, 2}}}},
    };
    for (auto& [P0, ch] : chains) {
        fresh_model();
        std::fill(bexp.begin(), bexp.end(), 0);
        HostKV hk;
        preload_history(ch.layer, P0, 100 + P0, hk);
        int P = P0; bool ok = true; std::string why = "all steps exact"; std::string trace;
        for (size_t s = 0; s < ch.steps.size() && ok; s++) {
            int np = ch.steps[s][0], n = ch.steps[s][1];
            clear_slices();   // other layers use the slices between two steps of this layer
            auto o = block_step(ch.name, ch.layer, P, np, 1000 + uint32_t(s) * 7 + P, hk, 0);
            trace += (s ? ";" : "") + std::string("P") + std::to_string(P) + "/np" + std::to_string(np) + "/keep" + std::to_string(n) +
                     ":kv_ok@" + std::to_string(o.kvok_after) + ",cyc" + std::to_string(o.cycles) + ",drain_wait" +
                     std::to_string(o.drain_wait) + ",wr" + std::to_string(o.wr_sectors);
            if (!o.ok) { ok = false; why = "step " + std::to_string(s) + ": " + o.why; break; }
            if (!do_commit(P, n, hk, why)) { ok = false; break; }
            P += n;
        }
        printf("%s %s : %s [%s]\n", ok ? "PASS" : "FAIL", ch.name, why.c_str(), trace.c_str());
        all &= ok;
        js += ",{\"name\":\"" + std::string(ch.name) + "\",\"pass\":" + (ok ? "true" : "false") + ",\"steps\":\"" + trace + "\",\"detail\":\"" + why + "\"}";
    }
    // negatives: each new fault
    struct Neg { const char* name; int kind; };
    for (auto ng : {Neg{"NEG_block_write_outside", 3}, Neg{"NEG_duplicate_K_lane", 4}, Neg{"NEG_commit_before_write_done", 9},
                    Neg{"NEG_commit_n_zero", 80}, Neg{"NEG_commit_n_above_np", 81}, Neg{"NEG_start_not_at_committed_len", 10},
                    Neg{"NEG_npos_above_VPMAX", 82}}) {
        fresh_model();
        std::fill(bexp.begin(), bexp.end(), 0);
        HostKV hk;
        preload_history(0, 253, 7, hk);
        bool pass = false; std::string why;
        if (ng.kind == 3 || ng.kind == 4 || ng.kind == 9) {
            auto o = block_step(ng.name, 0, 253, 4, 9, hk, ng.kind);
            pass = o.ok; why = o.why;
        } else if (ng.kind == 82) {
            top->pos = 253; top->layer = 0; top->npos = VPMAX_B + 1; top->start = 1; tick(); top->start = 0; tick();
            pass = top->fault && ((top->fault_code >> 8) & 1); why = "fault_code " + std::to_string(top->fault_code);
        } else {
            auto o = block_step(ng.name, 0, 253, 4, 9, hk, 0);
            if (!o.ok) { why = "setup step failed: " + o.why; }
            else if (ng.kind == 10) {
                std::string w; do_commit(253, 2, hk, w);
                top->pos = 256; top->npos = 4; top->start = 1; tick(); top->start = 0; tick();
                pass = top->fault && ((top->fault_code >> 10) & 1); why = "fault_code " + std::to_string(top->fault_code);
            } else {
                top->commit_v = 1; top->commit_n = ng.kind == 80 ? 0 : 5; tick(); top->commit_v = 0; tick();
                pass = top->fault && ((top->fault_code >> 8) & 1); why = "fault_code " + std::to_string(top->fault_code);
            }
        }
        printf("%s %s : %s\n", pass ? "PASS" : "FAIL", ng.name, why.c_str());
        all &= pass;
        js += ",{\"name\":\"" + std::string(ng.name) + "\",\"pass\":" + (pass ? "true" : "false") + ",\"detail\":\"" + why + "\"}";
    }
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    top = new Vtb_qwen_rt_kv_mp_service;
    top->rst_n = 0; top->start = 0; top->kvd_v = 0; top->npos = 1; top->commit_v = 0; top->commit_n = 0;
    for (int i = 0; i < 5; i++) tick();
    top->rst_n = 1; tick();
    std::vector<Result> rs;
    rs.push_back(run_case("L0_P255", 0, 255, 1, 0));
    rs.push_back(run_case("L1_P0", 1, 0, 2, 0));
    rs.push_back(run_case("L0_P256_tile_open", 0, 256, 3, 0));
    rs.push_back(run_case("L1_P2047", 1, 2047, 4, 0));
    rs.push_back(run_case("L0_P4095", 0, 4095, 5, 0));
    rs.push_back(run_case("L1_P8191", 1, 8191, 6, 0));
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
    for (int neg = 1; neg <= 2; neg++) {
        delete top; top = new Vtb_qwen_rt_kv_mp_service; cyc = 0;
        top->npos = 1; top->commit_v = 0; top->commit_n = 0;
        top->rst_n = 0; for (int i = 0; i < 5; i++) tick(); top->rst_n = 1; tick();
        auto r = run_case(neg == 1 ? "NEG_wrong_position" : "NEG_not_e4m3", 0, 255, 7, neg);
        printf("%s %s : %s\n", r.pass ? "PASS" : "FAIL", r.name.c_str(), r.why.c_str());
        all &= r.pass;
        js += ",{\"name\":\"" + r.name + "\",\"pass\":" + (r.pass ? "true" : "false") + ",\"detail\":\"" + r.why + "\"}";
    }
    if (VPMAX_B > 1) block_part(all, js);
    js += std::string("],\"status\":\"") + (all ? "pass" : "fail") + "\"}";
    printf("%s\n%s\n", all ? "KV_MP_SERVICE_STANDALONE PASS" : "KV_MP_SERVICE_STANDALONE FAIL", js.c_str());
    delete top;
    return all ? 0 : 1;
}
