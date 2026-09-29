// Equivalence gate: runtime composition (seq + G slices + tree cells + argmax
// subtrees) versus the unmodified rtl/hdc/ot_hdc_matvec.sv, every public port
// on every checked cycle.  Stimulus follows the G4/G64 runtime-composition
// gate (tools/qwen_matvec_runtime_emit.py) and adds a per-cycle random operand
// mode.  Compile-time: GROUPS, LOLEVELS, COUNTWIDTH, INT8W=1.
#include "Vref.h"
#include "Vseq.h"
#include "Vslice.h"
#include "Vcella.h"
#include "Vamaxlo.h"
#if HILEVELS > 0
#include "Vamaxhi.h"
#else
using Vamaxhi = Vamaxlo;
#endif
#include "qwen_rt_matvec.hpp"
#include <cstdio>
#include <cstring>
#include <sys/resource.h>
#include <type_traits>

template <class V> static uint64_t getbits(const V& v, size_t pos, int n) {
    if constexpr (std::is_integral_v<V>) {
        return (uint64_t(v) >> pos) & (n >= 64 ? ~0ull : ((1ull << n) - 1));
    } else {
        uint64_t r = 0;
        for (int b = 0; b < n; b++) r |= uint64_t((v[(pos + b) / 32] >> ((pos + b) % 32)) & 1) << b;
        return r;
    }
}
template <class V> static void putword(V& v, size_t word, uint32_t x) {
    if constexpr (std::is_integral_v<V>) {
        v = (V)((uint64_t(v) & ~(0xffffffffull << (32 * word))) | (uint64_t(x) << (32 * word)));
    } else v[word] = x;
}
static uint64_t mix(uint64_t x) {
    x += 0x9e3779b97f4a7c15ull; x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebull; return x ^ (x >> 31);
}

int main(int argc, char** argv) {
    constexpr int G = GROUPS, NW = COUNTWIDTH, AWD = 24;
    bool wrong_edge = argc > 1 && !strcmp(argv[1], "--wrong-edge");
    int threads = 8;
    if (const char* t = getenv("RT_THREADS")) threads = atoi(t);
    RtPool pool(threads);
    VerilatedContext rctx; rctx.randReset(0);
    Vref r(&rctx, "ref");
    VerilatedContext sctx; sctx.randReset(0);
    Vseq c(&sctx, "seq");
    RtMatvec<Vseq, Vslice, Vcella, Vamaxlo, Vamaxhi> mv(c, pool, G, LOLEVELS, [&] { return c.rst_n; });
    mv.set_nw(NW);
    const int LG = mv.LG;
    auto both = [&](auto f) { f(r); f(c); };
    both([](auto& m) {
        m.i_nout = 511; m.i_tiles = 2; m.i_k = 3; m.i_wsrc = 0; m.i_wbase = 100; m.i_ts = 12; m.i_ks = 4;
        m.i_js = 1; m.i_xbase = 11; m.i_xks = 3; m.i_xjs = 1; m.i_xcs = 17; m.i_jsh = 0; m.i_split = 0;
        m.i_wcs = 8; m.i_round = 1; m.i_obase = 20; m.i_ots = 8; m.i_ojs = 1; m.i_mmode = 0; m.i_oen = 1;
        m.i_amax = 1; m.i_rmax = 0; m.i_mbase = 2;
    });
    long cycles = 0, writes = 0, checks = 0; int max_settle = 0;
    const int base_cases = (LG + 1) * 8;
    const int cases = 2 * base_cases;   // second half: random per-cycle operands and fields
    auto settle = [&](int limit) {
        int n = 0;
        for (;; n++) {
            if (n >= limit) { printf("FAIL settle did not converge\n"); exit(4); }
            c.eval(); mv.eval_models();
            if (!mv.propagate()) break;
        }
        max_settle = std::max(max_settle, n + 1);
    };
    auto fail = [&](int test, int tick, const char* port, int g) {
        printf("FAIL case=%d tick=%d port=%s group=%d\n", test, tick, port, g); exit(1);
    };
    for (int test = 0; test < cases; test++) {
        const bool rnd = test >= base_cases;
        const int bt = test % base_cases;
        uint64_t seed = mix(uint64_t(test) * 7919 + G);
        both([&](auto& m) {
            m.i_split = bt % (LG + 1); m.i_wsrc = (bt / (LG + 1)) % 2;
            m.i_nout = (bt % 4 == 0 ? 1 : (bt % 4 == 1 ? 127 : (bt % 4 == 2 ? G * 16 : G * 16 * 8 - 1)));
            m.i_mmode = (bt / (2 * (LG + 1))) % 2; m.i_rmax = bt >= 4 * (LG + 1);
        });
        bool high_count = (NW == 18 && bt >= base_cases - 2);
        int tile_count = high_count ? std::max(20, (151936 + G * 16 * 8 - 1) / (G * 16 * 8)) : 2;
        both([&](auto& m) { m.i_tiles = tile_count; });
        if (high_count) both([](auto& m) { m.i_nout = 151936; m.i_split = 0; m.i_mmode = 0; });
        if (rnd) {
            uint64_t h = mix(seed);
            both([&](auto& m) {
                m.i_k = 1 + h % 5; m.i_jsh = (h >> 8) % 4; m.i_round = (h >> 12) & 1;
                m.i_wbase = (h >> 16) % 4096; m.i_ts = (h >> 28) % 64; m.i_ks = (h >> 34) % 16;
                m.i_js = (h >> 40) % 8; m.i_wcs = (h >> 44) % 32; m.i_xcs = (h >> 50) % 64;
                m.i_ojs = 1 + ((h >> 56) % 3); m.i_mbase = (h >> 58) % 64; m.i_amax = (h >> 63) & 1;
            });
        } else {
            both([](auto& m) { m.i_k = 3; m.i_jsh = 0; m.i_round = 1; m.i_wbase = 100; m.i_ts = 12;
                               m.i_ks = 4; m.i_js = 1; m.i_wcs = 8; m.i_xcs = 17; m.i_ojs = 1; m.i_mbase = 2;
                               m.i_amax = 1; });
        }
        bool high_write = false;
        int limit = high_count ? tile_count * (8 * int(r.i_k) + 2) + 380 : 230;
        for (int tick = 0; tick < limit; tick++) {
            both([&](auto& m) { m.rst_n = tick >= 4; m.go = tick == 5; });
            // operands: shared by reference and slices
            for (int g = 0; g < G; g++) {
                for (int j = 0; j < 4; j++) {
                    uint32_t w = rnd ? uint32_t(mix(seed ^ (uint64_t(tick) << 32) ^ (g * 4 + j)))
                                     : (bt % 4 == 0 ? 0x01010101u : (0x807fff01u ^ ((g * 4 + j) * 0x10001u)));
                    putword(r.wrom_q, g * 4 + j, w); putword(mv.s[g]->wrom_q, j, w);
                }
                for (int j = 0; j < 8; j++) {
                    int jj = g * 8 + j;
                    uint32_t v;
                    if (rnd) {
                        uint64_t h = mix(seed ^ 0x5ca1e ^ (uint64_t(tick) << 32) ^ jj);
                        auto bf = [&](uint64_t b) -> uint32_t {
                            uint32_t e = 100 + (b % 50), m7 = (b >> 8) & 127, sg = (b >> 15) & 1;
                            if ((b >> 20) % 97 == 0) return 0;              // zero
                            if ((b >> 20) % 89 == 1) return 0x7f80;         // inf -> fault path
                            return (sg << 15) | (e << 7) | m7;
                        };
                        v = bf(h) | (bf(h >> 24) << 16);
                    } else v = (jj % 3 == 0 ? 0x3f003f00u : (jj % 3 == 1 ? 0x3f803f80u : 0x40004000u));
                    putword(r.scale_q, jj, v); putword(mv.s[g]->scale_q, j, v);
                }
                for (int j = 0; j < 16; j++) {
                    int jj = g * 16 + j;
                    uint32_t v;
                    if (rnd) {
                        uint64_t h = mix(seed ^ 0x4b56 ^ (uint64_t(tick) << 32) ^ jj);
                        v = uint32_t((h & 0x8000ffff) | ((uint64_t(110 + (h >> 20) % 30)) << 23));
                        if ((h >> 40) % 211 == 0) v = 0;
                    } else v = (bt % 4 == 0 ? 0x3f800000u : ((jj % 2 ? 0xbf800000u : 0x3f000000u)));
                    putword(r.kv_q, jj, v); mv.s[g]->kv_q[j] = v;
                }
                uint32_t x;
                if (rnd) {
                    uint64_t h = mix(seed ^ 0x78 ^ (uint64_t(tick) << 32) ^ g);
                    x = uint32_t((h & 0x807fffff) | ((uint64_t(112 + (h >> 24) % 28)) << 23));
                } else x = (bt % 4 == 0 ? 0x3f800000u : (g % 2 ? 0xbf800000u : 0x3f000000u));
                putword(r.x_q, g, x); mv.s[g]->x_q = x;
            }
            r.clk = 0; c.clk = 0; mv.set_clk(0);
            settle(LG + 8);
            r.eval();
            if (tick % 17 != 13) {
                r.clk = 1; c.clk = 1; mv.set_clk(1);
                c.eval();
                if (wrong_edge) mv.propagate();   // negative control: slices see same-edge values
                mv.eval_edge();
                r.eval();
                settle(LG + 8);
            }
            if (tick > 8) {
#define CK(p) if (uint64_t(c.p) != uint64_t(r.p)) fail(test, tick, #p, -1);
                CK(ready) CK(idle) CK(wrom_re) CK(wrom_addr) CK(scale_re) CK(kv_re) CK(ov) CK(am_idx)
                CK(am_val) CK(am_any) CK(mx_we) CK(mx_addr) CK(mx_mask) CK(progress) CK(fault)
                for (int l = 0; l < 16; l++) if (getbits(c.mx_data, 32 * l, 32) != getbits(r.mx_data, 32 * l, 32)) fail(test, tick, "mx_data", -1);
                for (int g = 0; g < G; g++) {
                    auto& s = *mv.s[g];
                    if (s.scale_gre != getbits(r.scale_gre, g, 1)) fail(test, tick, "scale_gre", g);
                    if (s.scale_addr != getbits(r.scale_addr, g * AWD, AWD)) fail(test, tick, "scale_addr", g);
                    if (s.kv_addr != getbits(r.kv_addr, g * AWD, AWD)) fail(test, tick, "kv_addr", g);
                    if (s.x_re != getbits(r.x_re, g, 1)) fail(test, tick, "x_re", g);
                    if (s.x_addr != getbits(r.x_addr, g * AWD, AWD)) fail(test, tick, "x_addr", g);
                    if (s.o_we != getbits(r.o_we, g, 1)) fail(test, tick, "o_we", g);
                    if (s.o_addr != getbits(r.o_addr, g * AWD, AWD)) fail(test, tick, "o_addr", g);
                    if (s.o_mask != getbits(r.o_mask, g * 16, 16)) fail(test, tick, "o_mask", g);
                    for (int l = 0; l < 16; l++)
                        if (s.o_data[l] != getbits(r.o_data, (g * 16 + l) * 32, 32)) fail(test, tick, "o_data", g);
                    if (s.o_we) {
                        writes++;
                        if (uint64_t(s.o_addr) * 16 >= 65536) high_write = true;
                    }
                }
                checks++;
            }
            if (tick == limit - 1 && high_count && !high_write) { printf("FAIL high-count test never wrote high rows\n"); return 5; }
            if (tick == limit - 1 && (!r.idle || r.progress == 0)) { printf("FAIL no completion case%d\n", test); return 3; }
            cycles++;
        }
    }
    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
    printf("PASS rt matvec composition G%d NW%d cases%d cycles%ld checked%ld group_writes%ld settle%d native_holds%zu RSS_KiB%ld\n",
           G, NW, cases, cycles, checks, writes, max_settle, size_t(mv.LG) * G - mv.addidx.size(), ru.ru_maxrss);
    return 0;
}
