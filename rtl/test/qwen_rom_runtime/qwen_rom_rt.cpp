// Runtime composition of the Qwen3-8B O4 ROM die pair at the W12 design point
// (G = 5,120 lane groups a die, pruned engine, vector stream unit SW = 1,024,
// the matrix engine built as the tile array with wire register stages).
//
// Models (Verilator, each compiled once):
//   Vdie   ot_qwen_rom_rt_die: TP sequencer + ot_qwen_rom_core (the production
//          core with the array spine as its engine; tools/qwen_rom_rt_core_emit.py)
//   Vcoll  ot_rom_oneshot_allreduce (N = 2)
//   Vtile  ot_qwen_rom_tile_logic (KV_LOCAL = 0), G/4 instances a die, strap tile_id
// The host wires the tile fabric exactly as rtl/hdc/ot_qwen_me_array.sv does:
// the spine's instruction broadcast (tgo/tb) to every tile, x line t mod NXL to
// tile t, split-tree level 2 = tile t_out, the node of level lv, position p in
// tile p*2^k + 2^(k-1) - 1 (k = lv - 2) fed through NWS - 1 external wire stages
// (a host shift register), level TCUT to the spine's t_lvl, and the OR of the
// tile faults to fab_fault.  The host never adds a cycle the RTL array does not
// have: the external stages are the array's ot_hdc_delay instances.
//
// Memories are the bench's registered-response arrays (read before write, hold
// when not read): per tile, its code-ROM banks (the image word of the enabled
// bank, pair column lanes) and its global KV words; per die the program,
// descriptors, constants, scale ROM (result-port groups), vector memory (SU and
// the spine's x chunk port, XVM extra registers) and KV writes.  The engine's
// clock gate (ME_IDLE_GATE) gates the fabric and the engine memories.
//
//   qwen_rom_rt --stages FILE OUTDIR PRELOAD_X [max_cycles]
//     FILE lines: <name> <die0 image dir> <die1 image dir> <kv_reset 0|1>
// Compile-time: GROUPS, COUNTWIDTH, SWIDTH, SMAXB, TCUTL, NWSD, XVMD, SMINV, CBANKS.
#include "Vdie.h"
#include "Vcoll.h"
#include "Vtile.h"
#include "qwen_rt_matvec.hpp"   // RtPool, rt_set
#include "qwen_rt_memory.hpp"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <memory>
#include <sys/resource.h>

constexpr int D = 2, W = 16, H = 4096, TMAX = 8192, KVH = 4, HD = 128, X_BASE = 4096;
constexpr int G = GROUPS, TG = 4, NT = G / TG, CB = CBANKS, SW = SWIDTH, NXC = 1 << SMAXB, NXL = NXC / TG;
constexpr int LT = 2, TCUT = TCUTL, NPT = G >> TCUT, NWS_EXT = (NWSD > 0) ? NWSD - 1 : 0, XVM = XVMD;
constexpr int WPG = W * 8 / 32;                 // code-image u32 words per group

[[noreturn]] static void fatal(const char* m, long a = -1, long b = -1) {
    printf("FATAL %s %ld %ld\n", m, a, b); fflush(stdout); exit(2);
}
template <class A> static inline uint64_t getb(const A& w, size_t pos, int n) {
    uint64_t r = 0;
    for (int k = 0; k < n; ) {
        size_t word = (pos + k) / 32, off = (pos + k) % 32;
        int take = std::min(n - k, int(32 - off));
        r |= uint64_t((w[word] >> off) & ((take == 32) ? 0xffffffffu : ((1u << take) - 1))) << k;
        k += take;
    }
    return r;
}
template <class A> static inline void setb(A& w, size_t pos, int n, uint64_t v) {
    for (int k = 0; k < n; ) {
        size_t word = (pos + k) / 32, off = (pos + k) % 32;
        int take = std::min(n - k, int(32 - off));
        uint32_t mask = (take == 32) ? 0xffffffffu : (((1u << take) - 1) << off);
        w[word] = (w[word] & ~mask) | (uint32_t(v >> k << off) & mask);
        k += take;
    }
}
static std::vector<uint64_t> as64(const std::vector<uint32_t>& w) {
    std::vector<uint64_t> r(w.size() / 2);
    for (size_t i = 0; i < r.size(); i++) r[i] = w[2 * i] | (uint64_t(w[2 * i + 1]) << 32);
    return r;
}

struct DieMem {
    std::vector<uint32_t> prog, codes, scales, vm, kv;
    std::vector<uint64_t> desc, crom;
    size_t code_words = 0, scale_words = 0, crom_words = 0;
};
// SCALE_LOCAL (RT_SCALE_LOCAL=1): the stage's port-local scale images
// (tools/qwen_rom_scale_local.py), NPORT images of scale_words words each.
static bool scale_local() { const char* s = getenv("RT_SCALE_LOCAL"); return s && s[0] == '1'; }
constexpr int NPORT = G >> SMINV;
static void load_images(DieMem& m, const std::string& p) {
    m.prog = QwenHex::load(p + "/program.hex", 32);
    m.desc = as64(QwenHex::load(p + "/segments.hex", 2));
    m.codes = QwenHex::load(p + "/matrix_int8.hex", size_t(G) * WPG);
    m.code_words = m.codes.size() / (size_t(G) * WPG);
    if (scale_local()) {
        m.scales = QwenHex::load(p + "/matrix_scale_port.hex", 8);
        m.scale_words = m.scales.size() / 8 / NPORT;
        if (m.scale_words * 8 * NPORT != m.scales.size()) fatal("port-local scale image size");
    } else {
        m.scales = QwenHex::load(p + "/matrix_scale_bf16.hex", 8);
        m.scale_words = m.scales.size() / 8;
    }
    m.crom = as64(QwenHex::load(p + "/crom.hex", 2));
    m.crom_words = m.crom.size();
    if (m.prog.size() > 64 * 32 || m.desc.size() > 8) fatal("program/descriptor image exceeds bench memory");
    m.prog.resize(64 * 32, 0); m.desc.resize(8, 0);
}
struct Stage { std::string name, dir[D]; bool kv_reset; };

// ---- tile fabric of one die -------------------------------------------------------------------
struct Fabric {
    Vdie& die;
    RtPool& pool;
    std::vector<std::unique_ptr<Vtile>> t;
    std::vector<int> hl, hp;                     // hosted node: level (0 none), position
    std::vector<int> host;                       // [lv*NT + p] -> tile hosting node (lv, p)
    struct Line { VlWide<16> a, b; uint8_t va; };
    std::vector<std::vector<Line>> ext;          // per tile: NWS_EXT-stage node input delay
    uint8_t clk = 0; bool clk_known = false;
    Fabric(Vdie& d, RtPool& p) : die(d), pool(p) {
        host.assign((TCUT + 1) * NT, -1);
        for (int i = 0; i < NT; i++) {
            t.emplace_back(new Vtile(pool.ctx(i % pool.size()), "t"));
            t.back()->tile_id = i;
            int L = 0, P = 0;
            for (int k = 1; k <= TCUT - LT && !L; k++)
                if ((i % (1 << k)) == (1 << (k - 1)) - 1 && (i >> k) < (G >> (LT + k))) { L = LT + k; P = i >> k; }
            hl.push_back(L); hp.push_back(P);
            if (L) host[L * NT + P] = i;
            ext.emplace_back(NWS_EXT);
            for (auto& l : ext.back()) { for (auto& x : l.a.m_storage) x = 0; for (auto& x : l.b.m_storage) x = 0; l.va = 0; }
        }
    }
    // output word / valid of split-tree level lv, position p
    const VlWide<16>& word(int lv, int p) const { return lv == LT ? t[p]->t_out : t[host[lv * NT + p]]->n_y; }
    uint8_t valid(int lv, int p) const { return lv == LT ? t[p]->t_vout : t[host[lv * NT + p]]->n_vy; }
    void set_clk(uint8_t c) { clk = c; for (auto& x : t) x->clk = c; }
    void eval() { pool.run(t.size(), [&](size_t i) { t[i]->eval(); }); }
    // rising edge: external wire stages shift with pre-edge values, then every tile evaluates
    void edge() {
        if (NWS_EXT > 0)
            pool.run(t.size(), [&](size_t i) {
                if (!hl[i]) return;
                auto& e = ext[i];
                for (int s = NWS_EXT - 1; s > 0; s--) e[s] = e[s - 1];
                e[0].a = word(hl[i] - 1, 2 * hp[i]); e[0].b = word(hl[i] - 1, 2 * hp[i] + 1);
                e[0].va = valid(hl[i] - 1, 2 * hp[i]);
            });
        set_clk(1);
        eval();
    }
    // die -> tiles, tiles -> tiles, tiles -> die; returns true if any tile input changed
    bool propagate() {
        std::atomic<bool> any{false};
        const uint8_t rst = die.rt_rst_n, go = die.tgo;
        pool.run(t.size(), [&](size_t i) {
            Vtile& x = *t[i];
            bool ch = false;
            ch |= rt_set(x.rst_n, rst); ch |= rt_set(x.ib_go, go); ch |= rt_set(x.ib, die.tb);
            VlWide<4> xl;
            for (int k = 0; k < 4; k++) xl[k] = die.xl_d[(i % NXL) * 4 + k];
            ch |= rt_set(x.xl, xl);
            if (hl[i]) {
                if (NWS_EXT > 0) {
                    auto& e = ext[i][NWS_EXT - 1];
                    ch |= rt_set(x.n_a, e.a); ch |= rt_set(x.n_b, e.b); ch |= rt_set(x.n_va, e.va);
                } else {
                    ch |= rt_set(x.n_a, word(hl[i] - 1, 2 * hp[i])); ch |= rt_set(x.n_b, word(hl[i] - 1, 2 * hp[i] + 1));
                    ch |= rt_set(x.n_va, valid(hl[i] - 1, 2 * hp[i]));
                }
            }
            if (ch) any.store(true, std::memory_order_relaxed);
        });
        bool c2 = false;
        std::remove_reference_t<decltype(die.t_lvl)> tl;
        for (int p = 0; p < NPT; p++) { const auto& w = word(TCUT, p); for (int k = 0; k < 16; k++) tl[p * 16 + k] = w[k]; }
        c2 |= rt_set(die.t_lvl, tl);
        uint8_t f = 0;
        for (auto& x : t) f |= x->fault;
        c2 |= rt_set(die.fab_fault, f);
        return any || c2;
    }
};

int main(int argc, char** argv) {
    if (argc < 5 || strcmp(argv[1], "--stages")) { fprintf(stderr, "usage: %s --stages FILE OUTDIR PRELOAD [max_cycles]\n", argv[0]); return 2; }
    const std::string dir = argv[3], preload = argv[4];
    const long max_cycles = argc > 5 ? atol(argv[5]) : 400000000L;
    const size_t VM_ELEMS = 177808, KV_ELEMS = 8388608;
    int threads = 16;
    if (const char* s = getenv("RT_THREADS")) threads = atoi(s);
    RtPool pool(threads);
    auto t0 = std::chrono::steady_clock::now();
    std::vector<Stage> stages;
    {
        FILE* f = fopen(argv[2], "r");
        if (!f) fatal("stages file");
        char n[256], a[1024], b[1024]; int k;
        while (fscanf(f, "%255s %1023s %1023s %d", n, a, b, &k) == 4) stages.push_back({n, {a, b}, k != 0});
        fclose(f);
        if (stages.empty()) fatal("no stages");
    }
    DieMem mem[D];
    auto x0 = QwenHex::load(preload, 1);
    for (int d = 0; d < D; d++) {
        load_images(mem[d], stages[0].dir[d]);
        mem[d].vm.assign(VM_ELEMS, 0);
        for (size_t i = 0; i < x0.size() && i < VM_ELEMS; i++) mem[d].vm[i] = x0[i];
        mem[d].kv.assign(KV_ELEMS, 0);
    }
    printf("images loaded in %.1f s\n", std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    VerilatedContext dctx[D], cctx;
    std::unique_ptr<Vdie> die[D];
    std::unique_ptr<Fabric> fab[D];
    for (int d = 0; d < D; d++) {
        dctx[d].randReset(0);
        die[d].reset(new Vdie(&dctx[d], d ? "die1" : "die0"));
        die[d]->tp_token = 0; die[d]->tp_pos = 0; die[d]->h_start = 0;
        fab[d].reset(new Fabric(*die[d], pool));
    }
    cctx.randReset(0);
    Vcoll coll(&cctx, "coll");
    printf("models constructed in %.1f s (tiles/die=%d nodes/die=%d)\n",
           std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count(), NT,
           int(std::count_if(fab[0]->hl.begin(), fab[0]->hl.end(), [](int v) { return v > 0; })));
    fflush(stdout);

    auto wire_coll = [&]() -> bool {
        bool ch = false;
        uint8_t iv = 0, il = 0, im = 0;
        std::remove_reference_t<decltype(coll.in_data)> idat;
        uint64_t itag = 0;
        for (int d = 0; d < D; d++) {
            iv |= die[d]->c_valid << d; il |= die[d]->c_last << d; im |= die[d]->c_mode << d;
            for (int w = 0; w < 16; w++) idat[d * 16 + w] = die[d]->c_data[w];
            itag |= uint64_t(die[d]->c_tag) << (32 * d);
        }
        ch |= rt_set(coll.rst_n, die[0]->rt_rst_n);
        ch |= rt_set(coll.in_valid, iv); ch |= rt_set(coll.in_last, il); ch |= rt_set(coll.in_mode, im);
        ch |= rt_set(coll.in_data, idat); ch |= rt_set(coll.in_tag, (std::remove_reference_t<decltype(coll.in_tag)>)itag);
        for (int d = 0; d < D; d++) {
            Vdie& t = *die[d];
            ch |= rt_set(t.c_ready, uint8_t((coll.in_ready >> d) & 1));
            ch |= rt_set(t.r_valid, uint8_t((coll.out_valid >> d) & 1));
            ch |= rt_set(t.r_last, uint8_t((coll.out_last >> d) & 1));
            ch |= rt_set(t.r_rank, uint8_t((coll.out_rank >> d) & 1));
            ch |= rt_set(t.r_err, uint8_t((coll.out_err >> d) & 1));
            std::remove_reference_t<decltype(t.r_data)> rd;
            for (int w = 0; w < 16; w++) rd[w] = coll.out_data[d * 16 + w];
            ch |= rt_set(t.r_data, rd);
        }
        return ch;
    };
    uint8_t me_en[D] = {1, 1};
    int max_settle = 0;
    long passes = 0;
    auto settle = [&](bool fabric_live[D]) {
        for (int n = 0;; n++) {
            if (n > 64) fatal("settle did not converge");
            passes++;
            for (int d = 0; d < D; d++) die[d]->eval();
            coll.eval();
            bool ch = wire_coll();
            for (int d = 0; d < D; d++)
                if (fabric_live[d] && fab[d]->propagate()) { ch = true; fab[d]->eval(); }
            if (!ch) { max_settle = std::max(max_settle, n + 1); return; }
        }
    };
    // registered responses (applied after each edge)
    struct Resp {
        bool prog = false, desc = false, svr = false;
        uint32_t prog_q[32], svr_q[16]; uint64_t desc_q = 0;
        std::vector<uint8_t> cr, va, vb, vc, sc, vx;
        std::vector<uint64_t> cr_q; std::vector<uint32_t> va_q, vb_q, vc_q, sc_addr, vx_q;
        std::vector<std::vector<uint32_t>> xpipe_q; std::vector<std::vector<uint8_t>> xpipe_v;
        // tiles
        std::vector<int> rom_bank; std::vector<uint32_t> rom_addr; std::vector<uint8_t> kvr;
        std::vector<uint32_t> kv_q;
    } rs[D];
    struct Wr { uint32_t a, v; };
    std::vector<Wr> vmw[D], kvw[D];
    for (int d = 0; d < D; d++) {
        auto& r = rs[d];
        r.cr.assign(SW, 0); r.va.assign(SW, 0); r.vb.assign(SW, 0); r.vc.assign(SW, 0);
        r.cr_q.assign(SW, 0); r.va_q.assign(SW, 0); r.vb_q.assign(SW, 0); r.vc_q.assign(SW, 0);
        r.sc.assign(NPORT, 0); r.sc_addr.assign(NPORT, 0); r.vx.assign(NXC, 0); r.vx_q.assign(NXC, 0);
        r.xpipe_q.assign(XVM, std::vector<uint32_t>(NXC, 0)); r.xpipe_v.assign(XVM, std::vector<uint8_t>(NXC, 0));
        r.rom_bank.assign(NT, -1); r.rom_addr.assign(NT, 0); r.kvr.assign(NT, 0); r.kv_q.assign(size_t(G) * W, 0);
    }
    long me_busy[D] = {0, 0}, edges = 0;
    long progress_every = getenv("RT_PROGRESS") ? atol(getenv("RT_PROGRESS")) : 4096;
    bool stage_done = false, next_stage = false;
    size_t cur = 0; long stage_start = 7, busy0[D] = {0, 0};
    auto tstart = std::chrono::steady_clock::now();
    bool live_all[D] = {true, true};
    for (long tick = 0;; tick++) {
        for (int d = 0; d < D; d++) { die[d]->clk = 0; fab[d]->set_clk(0); }
        coll.clk = 0;
        settle(live_all);
        {
            uint32_t cyc = die[0]->cyc;
            uint8_t all_done = die[0]->s_done && die[1]->s_done;
            if (cyc > 8 && all_done && !stage_done) {
                stage_done = true;
                uint8_t sf = die[0]->s_fault | (die[1]->s_fault << 1), cf = die[0]->core_fault | (die[1]->core_fault << 1);
                uint8_t lf = coll.fault;
                double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - tstart).count();
                printf("STAGE %s done cycles=%ld start_cyc=%ld end_cyc=%u me_busy=%ld/%ld next_token=%u/%u next_val=%08x/%08x "
                       "seq_fault=%d core_fault=%d coll_fault=%d wall=%.0fs\n", stages[cur].name.c_str(), long(cyc) - stage_start,
                       stage_start, cyc, me_busy[0] - busy0[0], me_busy[1] - busy0[1], die[0]->seq_ntok, die[1]->seq_ntok,
                       die[0]->seq_nval, die[1]->seq_nval, sf, cf, lf, sec);
                for (int d = 0; d < D; d++) {
                    FILE* fp = fopen((dir + "/" + stages[cur].name + "_die" + char('0' + d) + "_x.hex").c_str(), "w");
                    for (int i = 0; i < H; i++) fprintf(fp, "%08x\n", mem[d].vm[X_BASE + i]);
                    fclose(fp);
                }
                fflush(stdout);
                if (sf || cf || lf) { printf("TOKEN FAULT stage=%s\n", stages[cur].name.c_str()); return 1; }
                if (cur + 1 == stages.size()) {
                    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
                    printf("QWEN_ROM_TOKEN_TP2 PASS stages=%zu token=%u val=%08x die1_token=%u cycles=%u edges=%ld "
                           "settle_max=%d wall_s=%.1f RSS_KiB=%ld threads=%d\n", stages.size(), die[0]->seq_ntok,
                           die[0]->seq_nval, die[1]->seq_ntok, cyc, edges, max_settle, sec, ru.ru_maxrss, threads);
                    return 0;
                }
                next_stage = true;
            }
            if (cyc > max_cycles) { printf("timeout cyc=%u\n", cyc); return 3; }
        }
        // ---- the bench's posedge block: sample requests on pre-edge values -----------------
        for (int d = 0; d < D; d++) {
            Vdie& t = *die[d];
            auto& m = mem[d];
            auto& r = rs[d];
            Fabric& f = *fab[d];
            vmw[d].clear(); kvw[d].clear();
            me_en[d] = t.me_clk_en;
            if (t.wrom_re) fatal("stream-unit weight-ROM read (the simulation core narrows that port)");
            r.prog = t.prog_re;
            if (t.prog_re) {
                size_t a = (size_t(t.prog_base) + t.prog_addr) & 4095;
                for (int w = 0; w < 32; w++) r.prog_q[w] = a < 64 ? m.prog[a * 32 + w] : 0;
            }
            r.desc = t.desc_re;
            if (t.desc_re) r.desc_q = t.desc_addr < 8 ? m.desc[t.desc_addr] : 0;
            // stream unit (SW lanes) and constants
            pool.run(SW, [&](size_t l) {
                r.cr[l] = getb(t.crom_re, l, 1);
                if (r.cr[l]) { uint32_t a = getb(t.crom_addr, l * 24, 24); if (a >= m.crom_words) fatal("constant ROM address", a); r.cr_q[l] = m.crom[a]; }
                r.va[l] = getb(t.va_re, l, 1); if (r.va[l]) { uint32_t a = getb(t.va_addr, l * 24, 24); r.va_q[l] = a < VM_ELEMS ? m.vm[a] : 0; }
                r.vb[l] = getb(t.vb_re, l, 1); if (r.vb[l]) { uint32_t a = getb(t.vb_addr, l * 24, 24); r.vb_q[l] = a < VM_ELEMS ? m.vm[a] : 0; }
                r.vc[l] = getb(t.vc_re, l, 1); if (r.vc[l]) { uint32_t a = getb(t.vc_addr, l * 24, 24); r.vc_q[l] = a < VM_ELEMS ? m.vm[a] : 0; }
            });
            if (me_en[d]) {
                me_busy[d]++;
                // spine: scale ROM (result-port groups) and the x chunk port
                pool.run(NPORT, [&](size_t g) {
                    r.sc[g] = getb(t.scale_gre, g, 1);
                    if (r.sc[g]) { uint32_t a = getb(t.scale_addr, g * 24, 24); if (a >= m.scale_words) fatal("scale ROM address", a, long(g)); r.sc_addr[g] = a; }
                });
                pool.run(NXC, [&](size_t c) {
                    r.vx[c] = getb(t.vx_re, c, 1);
                    if (r.vx[c]) { uint32_t a = getb(t.vx_addr, c * 24, 24); r.vx_q[c] = a < VM_ELEMS ? m.vm[a] : 0; }
                });
                // tiles: code ROM bank and KV
                pool.run(NT, [&](size_t i) {
                    Vtile& x = *f.t[i];
                    int b = -1;
                    for (int k = 0; k < CB; k++) if ((x.rom_ce >> k) & 1) { if (b >= 0) fatal("two ROM banks enabled", long(i)); b = k; }
                    r.rom_bank[i] = b;
                    if (b >= 0) { r.rom_addr[i] = uint32_t(b) * 4096 + x.rom_addr; if (r.rom_addr[i] >= m.code_words) fatal("code ROM address", r.rom_addr[i], long(i)); }
                    r.kvr[i] = x.kv_re;
                    if (x.kv_re)
                        for (int g = 0; g < TG; g++) {
                            size_t a = getb(x.kv_addr, g * 24, 24);
                            for (int j = 0; j < W; j++) r.kv_q[(i * TG + g) * W + j] = (a < KV_ELEMS / W) ? m.kv[a * W + j] : 0;
                        }
                });
                // result writes of the port groups (the core gates vw_me_we with the engine enable)
                for (int g = 0; g < NPORT; g++)
                    if (getb(t.vw_me_we, g, 1)) {
                        uint32_t a = getb(t.vw_me_addr, g * 24, 24); uint32_t msk = getb(t.vw_me_mask, g * 16, 16);
                        for (int l = 0; l < W; l++) if ((msk >> l) & 1) vmw[d].push_back({(a << 4) + l, t.vw_me_data[g * 16 + l]});
                    }
            }
            if (t.vw_mx_we)
                for (int l = 0; l < W; l++)
                    if ((t.vw_mx_mask >> l) & 1) vmw[d].push_back({uint32_t((uint64_t(t.vw_mx_addr) << 4) + l), t.vw_mx_data[l]});
            for (int l = 0; l < SW; l++) {
                if (getb(t.vw_su_we, l, 1)) vmw[d].push_back({uint32_t(getb(t.vw_su_addr, l * 24, 24)), t.vw_su_data[l]});
                if (getb(t.kv_we, l, 1)) kvw[d].push_back({uint32_t(getb(t.kv_waddr, l * 24, 24)), t.kv_wdata[l]});
            }
            if (t.vw_rd_we) vmw[d].push_back({t.vw_rd_addr, t.vw_rd_data});
            r.svr = t.s_vre;
            if (t.s_vre) for (int l = 0; l < W; l++) { size_t a = (size_t(t.s_vraddr) << 4) + l; r.svr_q[l] = a < VM_ELEMS ? m.vm[a] : 0; }
            if (t.s_vwe) for (int l = 0; l < W; l++) vmw[d].push_back({uint32_t((uint32_t(t.s_vwaddr) << 4) + l), t.s_vwdata[l]});
        }
        // ---- rising edge ------------------------------------------------------------------
        for (int d = 0; d < D; d++) die[d]->clk = 1;
        coll.clk = 1;
        for (int d = 0; d < D; d++) die[d]->eval();
        coll.eval();
        for (int d = 0; d < D; d++) if (me_en[d]) fab[d]->edge();
        edges++;
        // ---- commit writes and registered responses ---------------------------------------
        for (int d = 0; d < D; d++) {
            auto& m = mem[d];
            auto& r = rs[d];
            Vdie& t = *die[d];
            Fabric& f = *fab[d];
            for (auto& w : vmw[d]) if (w.a < VM_ELEMS) m.vm[w.a] = w.v;
            for (auto& w : kvw[d]) if (w.a < KV_ELEMS) m.kv[w.a] = w.v;
            if (r.prog) for (int w = 0; w < 32; w++) t.prog_q[w] = r.prog_q[w];
            if (r.desc) t.desc_q = r.desc_q;
            if (r.svr) for (int l = 0; l < W; l++) t.s_vrq[l] = r.svr_q[l];
            for (int l = 0; l < SW; l++) {
                if (r.cr[l]) { t.crom_q[2 * l] = uint32_t(r.cr_q[l]); t.crom_q[2 * l + 1] = uint32_t(r.cr_q[l] >> 32); }
                if (r.va[l]) t.va_q[l] = r.va_q[l];
                if (r.vb[l]) t.vb_q[l] = r.vb_q[l];
                if (r.vc[l]) t.vc_q[l] = r.vc_q[l];
            }
            if (me_en[d]) {
                const bool sl = scale_local();
                for (int g = 0; g < NPORT; g++)
                    if (r.sc[g]) {
                        if (sl && g >= NPORT) fatal("scale read beyond the port groups", g);
                        size_t w = sl ? size_t(g) * m.scale_words + r.sc_addr[g] : size_t(r.sc_addr[g]);
                        for (int j = 0; j < 8; j++) t.scale_q[g * 8 + j] = m.scales[w * 8 + j];
                    }
                // x chunk port: XVM extra vector-memory registers, then the spine's capture
                if (XVM == 0) {
                    for (int c = 0; c < NXC; c++) if (r.vx[c]) t.vx_q[c] = r.vx_q[c];
                } else {
                    for (int c = 0; c < NXC; c++) if (r.xpipe_v[XVM - 1][c]) t.vx_q[c] = r.xpipe_q[XVM - 1][c];
                    for (int s = XVM - 1; s > 0; s--) { r.xpipe_q[s] = r.xpipe_q[s - 1]; r.xpipe_v[s] = r.xpipe_v[s - 1]; }
                    r.xpipe_q[0] = r.vx_q; r.xpipe_v[0] = r.vx;
                }
                pool.run(NT, [&](size_t i) {
                    Vtile& x = *f.t[i];
                    int b = r.rom_bank[i];
                    if (b >= 0) {
                        size_t a = r.rom_addr[i];
                        for (int p = 0; p < 2; p++) {
                            size_t base = size_t(p * CB + b) * 266;
                            for (int w = 0; w < 8; w++)
                                setb(x.rom_rd, base + 32 * w, 32, m.codes[(a * G + i * TG + 2 * p) * WPG + w]);
                            setb(x.rom_rd, base + 256, 10, 0);
                        }
                    }
                    if (r.kvr[i]) for (int k = 0; k < TG * W; k++) x.kv_q[k] = r.kv_q[i * TG * W + k];
                });
            }
        }
        // host stage controller: one-cycle start after an image-bank switch
        for (int d = 0; d < D; d++) die[d]->h_start = 0;
        if (next_stage) {
            next_stage = false; stage_done = false; cur++;
            for (int d = 0; d < D; d++) {
                load_images(mem[d], stages[cur].dir[d]);
                if (stages[cur].kv_reset) std::fill(mem[d].kv.begin(), mem[d].kv.end(), 0u);
                die[d]->h_start = 1;
                busy0[d] = me_busy[d];
            }
            stage_start = long(die[0]->cyc);
            printf("stage %s loaded: code_words=%zu scale_words=%zu crom_words=%zu\n", stages[cur].name.c_str(),
                   mem[0].code_words, mem[0].scale_words, mem[0].crom_words);
            fflush(stdout);
        }
        bool live[D] = {bool(me_en[0]), bool(me_en[1])};
        settle(live);
        if (tick % progress_every == 0) {
            double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - tstart).count();
            printf("progress tick=%ld cyc=%u pc_base=%u/%u me_busy=%ld/%ld wall=%.0fs passes=%ld\n", tick, die[0]->cyc,
                   die[0]->prog_base, die[1]->prog_base, me_busy[0], me_busy[1], sec, passes);
            fflush(stdout);
        }
    }
}
