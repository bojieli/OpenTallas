// qwen_hbmacc_rt_w12_vp.cpp: the HA8 host (qwen_hbmacc_rt_w12.cpp, unchanged) for the DSpark VERIFY step on the
// HBM accelerator (die model ot_qwen_hbmacc_rt_die_w12_vp; default-off, built only by
// tools/qwen_hbmacc_rt_verify_w12.py).  The verify differences are those of qwen_rom_rt_w12_vp.cpp against
// qwen_rom_rt_w12.cpp, all host-side:
//   * vector memory of RT_VM_ELEMS elements (default 1,048,576; the p-position layer needs p copies of the live
//     regions), program images up to 1,024 instructions and 64 segment descriptors;
//   * RT_XBASES=b0,b1,..: every stage dumps the X of each position (<stage>_p<j>_die<d>_x.hex);
//   * the final stage prints the per-position argmax records (VERIFY_TOKENS);
// plus --nuse P (the die's window use target: each HBM code word is read P times) and, per stage, the die's
// HBM code-word read count and window-release fault (VPSTAT).
//
// HA8: runtime host of the Qwen3-8B HBM-ACCELERATOR dies (default-off; built only by
// tools/qwen_hbmacc_rt_token_w12.py).  Derived from the pinned qwen_rom_rt_w12.cpp (unchanged) with:
//   * Vdie = ot_qwen_hbmacc_rt_die_w12 (ME_STALL / KV_HBM gating from the HBM prefetch stream, DYN constants
//     for a nonzero position, cycle attribution) and, per die, Vwst = ot_hbmacc_qwen_wstream (the r14 streaming
//     controller of the die's stacks) clocked in its own domain: 1.024 ns (CK/2) against the core's 0.8333 ns,
//     edges interleaved at their true times (unit 1/3 ps); the Gray-coded counts cross through each side's
//     two-flop synchroniser;
//   * --pos / --token (the pinned host runs position 0, token 0 only) and --kv-dir: each layer stage loads that
//     layer's KV window of positions < P (the position oracle's kv_pre/L<n>_die<d>.npy) instead of zeroing it;
//   * --plan: the stream plan (total words, per stage the segment table the die gates on);
//   * --preroll N: the stream runs N controller cycles before the core's first edge (the prefetch a chained run
//     has made when this stage starts).
// Every memory read is still served by the host exactly as in the pinned runtime.
//
//   qwen_hbmacc_rt --stages FILE OUTDIR PRELOAD_X --plan PLAN [--pos P --token T --kv-dir DIR --preroll N --max-cycles N]
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
#include "Vwst.h"
#include "qwen_rt_matvec.hpp"   // RtPool, rt_set
#include "qwen_rt_memory.hpp"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <memory>
#include <sys/resource.h>
#include <string>
#include <type_traits>
#include <algorithm>
#include <atomic>

#ifndef TPD
#define TPD 2
#endif
constexpr int D = TPD, W = 16, H = 4096, TMAX = 8192, KVH = 8 / TPD, HD = 128, X_BASE = 4096;
constexpr int RB = (D > 1) ? ((D > 2) ? 2 : 1) : 1;   // rank bits (ot_rom_tp_seq RB)
constexpr int G = GROUPS, TG = 4, NT = G / TG, CB = CBANKS, SW = SWIDTH, NXC = 1 << SMAXB, NXL = NXC / TG;
constexpr int LT = 2, TCUT = TCUTL, NPT = G >> TCUT, NWS_EXT = (NWSD > 0) ? NWSD - 1 : 0, XVM = XVMD;
constexpr int WPG = W * 8 / 32;                 // code-image u32 words per group

[[noreturn]] static void fatal(const char* m, long a = -1, long b = -1) {
    printf("FATAL %s %ld %ld\n", m, a, b); fflush(stdout); exit(2);
}
template <class A> static inline uint64_t getb(const A& w, size_t pos, int n) {
    if constexpr (std::is_integral_v<A>) {
        return (uint64_t(w) >> pos) & (n >= 64 ? ~0ull : ((1ull << n) - 1));
    } else {
        uint64_t r = 0;
        for (int k = 0; k < n; ) {
            size_t word = (pos + k) / 32, off = (pos + k) % 32;
            int take = std::min(n - k, int(32 - off));
            r |= uint64_t((w[word] >> off) & ((take == 32) ? 0xffffffffu : ((1u << take) - 1))) << k;
            k += take;
        }
        return r;
    }
}
template <class A> static inline void setb(A& w, size_t pos, int n, uint64_t v) {
    if constexpr (std::is_integral_v<A>) {
        uint64_t m = (n >= 64 ? ~0ull : ((1ull << n) - 1)) << pos;
        w = A((uint64_t(w) & ~m) | ((v << pos) & m));
    } else {
        for (int k = 0; k < n; ) {
            size_t word = (pos + k) / 32, off = (pos + k) % 32;
            int take = std::min(n - k, int(32 - off));
            uint32_t mask = (take == 32) ? 0xffffffffu : (((1u << take) - 1) << off);
            w[word] = (w[word] & ~mask) | (uint32_t(v >> k << off) & mask);
            k += take;
        }
    }
}
// 32-bit lane l of a port (integral or wide)
template <class A> static inline uint32_t lane32(const A& w, size_t l) { return uint32_t(getb(w, 32 * l, 32)); }
template <class A> static inline void set32(A& w, size_t l, uint32_t v) { setb(w, 32 * l, 32, v); }
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
    if (m.prog.size() > 1024 * 32 || m.desc.size() > 64) fatal("program/descriptor image exceeds bench memory");
    m.prog.resize(1024 * 32, 0); m.desc.resize(64, 0);
}
struct Stage { std::string name, dir[D]; bool kv_reset; int layer = -1; };
// ---- HA8 stream plan -----------------------------------------------------------------------------
constexpr int NSEG = 8;
struct Seg { uint32_t base = 0, len = 0, sidx = 0, kind = 0; };
struct PlanStage { std::string name; std::vector<Seg> seg; };
static std::vector<uint32_t> load_npy_u32(const std::string& path) {
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) fatal("npy file");
    char magic[6]; uint8_t ver[2]; uint16_t hl16 = 0; uint32_t hl = 0;
    if (fread(magic, 1, 6, f) != 6 || memcmp(magic, "\x93NUMPY", 6) || fread(ver, 1, 2, f) != 2) fatal("npy magic");
    if (ver[0] == 1) { if (fread(&hl16, 2, 1, f) != 1) fatal("npy header"); hl = hl16; }
    else { if (fread(&hl, 4, 1, f) != 1) fatal("npy header"); }
    std::string h(hl, ' ');
    if (fread(&h[0], 1, hl, f) != hl) fatal("npy header body");
    if (h.find("'<u4'") == std::string::npos || h.find("False") == std::string::npos) fatal("npy: need little-endian u4, C order");
    std::vector<uint32_t> v;
    uint32_t buf[65536]; size_t n;
    while ((n = fread(buf, 4, 65536, f)) > 0) v.insert(v.end(), buf, buf + n);
    fclose(f);
    return v;
}

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
        // a Verilated model sees a rising edge only after it has evaluated with clk low: lower the
        // tiles' clock (with pre-edge inputs) before raising it
        if (clk) { set_clk(0); eval(); }
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
    if (argc < 5 || strcmp(argv[1], "--stages")) { fprintf(stderr, "usage: %s --stages FILE OUTDIR PRELOAD --plan F [opts]\n", argv[0]); return 2; }
    const std::string dir = argv[3], preload = argv[4];
    long max_cycles = 400000000L, preroll = 0;
    int POS = 0, TOKEN = 0, NUSE = 1;
    std::string kv_dir, plan_file;
    for (int i = 5; i + 1 < argc; i += 2) {
        std::string k = argv[i];
        if (k == "--pos") POS = atoi(argv[i + 1]);
        else if (k == "--token") TOKEN = atoi(argv[i + 1]);
        else if (k == "--kv-dir") kv_dir = argv[i + 1];
        else if (k == "--plan") plan_file = argv[i + 1];
        else if (k == "--preroll") preroll = atol(argv[i + 1]);
        else if (k == "--max-cycles") max_cycles = atol(argv[i + 1]);
        else if (k == "--nuse") NUSE = atoi(argv[i + 1]);
        else fatal("unknown option");
    }
    if (plan_file.empty()) fatal("--plan is required");
    const size_t VM_ELEMS = getenv("RT_VM_ELEMS") ? size_t(atol(getenv("RT_VM_ELEMS"))) : size_t(1) << 20, KV_ELEMS = 8388608;
    std::vector<size_t> xbases;
    if (const char* xb = getenv("RT_XBASES")) {
        std::string t(xb); size_t p0 = 0;
        while (p0 < t.size()) { size_t q = t.find(',', p0); if (q == std::string::npos) q = t.size(); xbases.push_back(std::stoul(t.substr(p0, q - p0))); p0 = q + 1; }
    }
    int threads = 16;
    if (const char* s = getenv("RT_THREADS")) threads = atoi(s);
    RtPool pool(threads);
    auto t0 = std::chrono::steady_clock::now();
    std::vector<Stage> stages;
    {
        FILE* f = fopen(argv[2], "r");
        if (!f) fatal("stages file");
        char n[256], a[1024]; int k;
        while (fscanf(f, "%255s", n) == 1) {
            Stage st; st.name = n;
            for (int d = 0; d < D; d++) { if (fscanf(f, "%1023s", a) != 1) fatal("stage line"); st.dir[d] = a; }
            if (fscanf(f, "%d", &k) != 1) fatal("stage kv_reset");
            st.kv_reset = k != 0;
            if (st.name.size() >= 2 && st.name[0] == 'L') st.layer = atoi(st.name.c_str() + 1);
            stages.push_back(st);
        }
        fclose(f);
        if (stages.empty()) fatal("no stages");
    }
    // plan: "TOTAL <words>" then per stage "STAGE <name> <nseg> {<base> <len> <sidx> <kind>}*"
    uint32_t total_words = 0;
    std::vector<PlanStage> plan;
    {
        FILE* f = fopen(plan_file.c_str(), "r");
        if (!f) fatal("plan file");
        char tag[64], nm[256];
        if (fscanf(f, "%63s %u", tag, &total_words) != 2 || strcmp(tag, "TOTAL")) fatal("plan TOTAL");
        while (fscanf(f, "%63s %255s", tag, nm) == 2) {
            if (strcmp(tag, "STAGE")) fatal("plan STAGE");
            PlanStage ps; ps.name = nm; int n;
            if (fscanf(f, "%d", &n) != 1 || n > NSEG) fatal("plan nseg");
            for (int i = 0; i < n; i++) { Seg sg; if (fscanf(f, "%u %u %u %u", &sg.base, &sg.len, &sg.sidx, &sg.kind) != 4) fatal("plan seg"); ps.seg.push_back(sg); }
            plan.push_back(ps);
        }
        fclose(f);
        if (plan.size() != stages.size()) fatal("plan stages != stages", long(plan.size()), long(stages.size()));
        for (size_t i = 0; i < plan.size(); i++) if (plan[i].name != stages[i].name) fatal("plan stage name", long(i));
    }
    auto set_plan = [&](Vdie& t, const PlanStage& ps) {
        for (int i = 0; i < NSEG; i++) {
            Seg sg = i < int(ps.seg.size()) ? ps.seg[i] : Seg();
            setb(t.seg_base, 24 * i, 24, sg.base); setb(t.seg_len, 24 * i, 24, sg.len);
            setb(t.seg_sidx, 32 * i, 32, sg.sidx); setb(t.seg_kind, 2 * i, 2, sg.kind);
        }
    };
    auto load_kv = [&](std::vector<uint32_t>& kv, const Stage& st, int d) {
        std::fill(kv.begin(), kv.end(), 0u);
        if (kv_dir.empty() || st.layer < 0) return;
        auto v = load_npy_u32(kv_dir + "/L" + std::to_string(st.layer) + "_die" + std::to_string(d) + ".npy");
        if (v.size() > kv.size()) fatal("kv_pre larger than the KV memory", long(v.size()));
        std::copy(v.begin(), v.end(), kv.begin());
    };
    DieMem mem[D];
    auto x0 = QwenHex::load(preload, 1);
    for (int d = 0; d < D; d++) {
        load_images(mem[d], stages[0].dir[d]);
        mem[d].vm.assign(VM_ELEMS, 0);
        for (size_t i = 0; i < x0.size() && i < VM_ELEMS; i++) mem[d].vm[i] = x0[i];
        mem[d].kv.assign(KV_ELEMS, 0);
        load_kv(mem[d].kv, stages[0], d);
    }
    printf("images loaded in %.1f s\n", std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    VerilatedContext dctx[D], cctx;
    std::unique_ptr<Vdie> die[D];
    std::unique_ptr<Fabric> fab[D];
    for (int d = 0; d < D; d++) {
        dctx[d].randReset(0);
        die[d].reset(new Vdie(&dctx[d], ("die" + std::to_string(d)).c_str()));
        die[d]->tp_token = TOKEN; die[d]->tp_pos = POS; die[d]->h_start = 0;
        set_plan(*die[d], plan[0]);
        die[d]->w_nuse = NUSE;
        fab[d].reset(new Fabric(*die[d], pool));
    }
    // ---- HBM stream models (controller domain) ---------------------------------------------------
    VerilatedContext wctx[D];
    std::unique_ptr<Vwst> wst[D];
    for (int d = 0; d < D; d++) {
        wctx[d].randReset(0);
        wst[d].reset(new Vwst(&wctx[d], ("wst" + std::to_string(d)).c_str()));
        Vwst& w = *wst[d];
        w.clk = 0; w.rst_n = 0; w.go = 0; w.cfg_words = total_words; w.c_gray = 0;
        w.eval();
        for (int k = 0; k < 4; k++) { w.clk = 1; w.eval(); w.clk = 0; w.eval(); }
        w.rst_n = 1; w.eval();
    }
    // time in 1/3 ps: core edge every 2,500 (0.8333 ns), controller edge every 3,072 (1.024 ns)
    const long TE = 2500, TC = 3072;
    long t_core = 0, t_ctl = 0, ctl_cycles = 0;
    auto ctl_edge = [&]() {
        for (int d = 0; d < D; d++) {
            Vwst& w = *wst[d];
            w.c_gray = die[d]->w_c_gray;
            w.go = 1;
            w.clk = 1; w.eval(); w.clk = 0; w.eval();
        }
        ctl_cycles++;
    };
    for (long k = 0; k < preroll; k++) ctl_edge();            // prefetch before this run's first stage
    printf("stream: total_words=%u preroll=%ld ctl_cycles; words_ready_at_start=%u/%u\n", total_words, preroll,
           wst[0]->st_words, D > 1 ? wst[D - 1]->st_words : wst[0]->st_words);
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
        std::remove_reference_t<decltype(coll.in_tag)> itag{};
        for (int d = 0; d < D; d++) {
            iv |= die[d]->c_valid << d; il |= die[d]->c_last << d; im |= die[d]->c_mode << d;
            for (int w = 0; w < 16; w++) idat[d * 16 + w] = die[d]->c_data[w];
            setb(itag, 32 * d, 32, die[d]->c_tag);
        }
        ch |= rt_set(coll.rst_n, die[0]->rt_rst_n);
        ch |= rt_set(coll.in_valid, iv); ch |= rt_set(coll.in_last, il); ch |= rt_set(coll.in_mode, im);
        ch |= rt_set(coll.in_data, idat); ch |= rt_set(coll.in_tag, itag);
        for (int d = 0; d < D; d++) {
            Vdie& t = *die[d];
            ch |= rt_set(t.c_ready, uint8_t((coll.in_ready >> d) & 1));
            ch |= rt_set(t.r_valid, uint8_t((coll.out_valid >> d) & 1));
            ch |= rt_set(t.r_last, uint8_t((coll.out_last >> d) & 1));
            ch |= rt_set(t.r_rank, uint8_t(getb(coll.out_rank, d * RB, RB)));
            ch |= rt_set(t.r_err, uint8_t((coll.out_err >> d) & 1));
            std::remove_reference_t<decltype(t.r_data)> rd;
            for (int w = 0; w < 16; w++) rd[w] = coll.out_data[d * 16 + w];
            ch |= rt_set(t.r_data, rd);
        }
        return ch;
    };
    uint8_t me_en[D];
    for (int d = 0; d < D; d++) me_en[d] = 1;
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
    uint32_t pst[D][13] = {};
    long me_busy[D] = {}, edges = 0, n_me_wr[D] = {}, n_su_wr[D] = {};
    const bool trace = getenv("RT_TRACE") != nullptr;
    const bool itrace = getenv("RT_ITRACE") != nullptr;
    bool itr_me = false, itr_c = false;
    long progress_every = getenv("RT_PROGRESS") ? atol(getenv("RT_PROGRESS")) : 4096;
    bool stage_done = false, next_stage = false;
    // a new stage's done is armed only once every die's sequencer has dropped the previous one
    bool done_armed = true;
    size_t cur = 0; long stage_start = 7, busy0[D] = {};
    auto tstart = std::chrono::steady_clock::now();
    bool live_all[D];
    for (int d = 0; d < D; d++) live_all[d] = true;
    for (long tick = 0;; tick++) {
        for (int d = 0; d < D; d++) die[d]->clk = 0;
        coll.clk = 0;
        settle(live_all);
        {
            uint32_t cyc = die[0]->cyc;
            uint8_t all_done = 1;
            for (int d = 0; d < D; d++) all_done &= die[d]->s_done;
            if (!done_armed) {
                bool any_done = false;
                for (int d = 0; d < D; d++) any_done |= die[d]->s_done;
                if (!any_done) done_armed = true;
                all_done = 0;
            }
            if (cyc > 8 && all_done && !stage_done) {
                stage_done = true;
                uint8_t sf = 0, cf = 0;
                for (int d = 0; d < D; d++) { sf |= die[d]->s_fault << d; cf |= die[d]->core_fault << d; }
                uint8_t lf = coll.fault;
                double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - tstart).count();
                printf("STAGE %s done cycles=%ld start_cyc=%ld end_cyc=%u me_busy=%ld/%ld next_token=%u/%u next_val=%08x/%08x "
                       "seq_fault=%d core_fault=%d coll_fault=%d me_writes=%ld su_writes=%ld wall=%.0fs\n", stages[cur].name.c_str(), long(cyc) - stage_start,
                       stage_start, cyc, me_busy[0] - busy0[0], me_busy[D - 1] - busy0[D - 1], die[0]->seq_ntok, die[D - 1]->seq_ntok,
                       die[0]->seq_nval, die[D - 1]->seq_nval, sf, cf, lf, n_me_wr[0], n_su_wr[0], sec);
                for (int d = 0; d < D; d++) {
                    Vdie& v = *die[d]; Vwst& w = *wst[d];
                    uint32_t s[13] = {v.st_wwait, v.st_kvwait, v.st_mm, v.st_attn, v.st_coll, v.st_su, v.st_other,
                                      w.st_cycles, w.st_rd, w.st_room_block, w.st_desc_gap, w.st_words, v.st_last_w};
                    printf("HBMSTAT %s die%d hbm_wait=%u kv_wait=%u matmul=%u attention=%u collective=%u stream_unit=%u other=%u "
                           "ctl_cycles=%u rd=%u room_block=%u desc_gap=%u words_done=%u last_wread_cyc=%u hbm_fault=%d wst_fault=%d\n",
                           stages[cur].name.c_str(), d, s[0] - pst[d][0], s[1] - pst[d][1], s[2] - pst[d][2], s[3] - pst[d][3],
                           s[4] - pst[d][4], s[5] - pst[d][5], s[6] - pst[d][6], s[7] - pst[d][7], s[8] - pst[d][8],
                           s[9] - pst[d][9], s[10] - pst[d][10], s[11], s[12], int(v.hbm_fault), int(w.fault));
                    for (int k = 0; k < 13; k++) pst[d][k] = s[k];
                }
                for (int d = 0; d < D; d++)
                    printf("VPSTAT %s die%d nuse=%d hbm_code_reads=%u rel_fault=%d\n", stages[cur].name.c_str(), d, NUSE,
                           unsigned(die[d]->st_nreads), int(die[d]->rel_fault));
                for (int d = 0; d < D; d++) {
                    if (xbases.empty()) {
                        FILE* fp = fopen((dir + "/" + stages[cur].name + "_die" + char('0' + d) + "_x.hex").c_str(), "w");
                        for (int i = 0; i < H; i++) fprintf(fp, "%08x\n", mem[d].vm[X_BASE + i]);
                        fclose(fp);
                    } else {
                        for (size_t j = 0; j < xbases.size(); j++) {
                            FILE* fp = fopen((dir + "/" + stages[cur].name + "_p" + std::to_string(j) + "_die" + char('0' + d) + "_x.hex").c_str(), "w");
                            for (int i = 0; i < H; i++) fprintf(fp, "%08x\n", mem[d].vm[xbases[j] + i]);
                            fclose(fp);
                        }
                    }
                }
                fflush(stdout);
                uint8_t hf = 0;
                for (int d = 0; d < D; d++) hf |= (die[d]->hbm_fault | wst[d]->fault | die[d]->rel_fault) << d;
                if (sf || cf || lf || hf) { printf("TOKEN FAULT stage=%s hbm=%d\n", stages[cur].name.c_str(), int(hf)); return 1; }
                if (cur + 1 == stages.size()) {
                    for (int d = 0; d < D; d++) {
                        printf("VERIFY_TOKENS die=%d n=%u", d, unsigned(die[d]->seq_n_tok));
                        for (unsigned j = 0; j < die[d]->seq_n_tok && j < 8; j++)
                            printf(" t%u=%u/%08x", j, unsigned(getb(die[d]->seq_tok_vec, j * COUNTWIDTH, COUNTWIDTH)),
                                   unsigned(getb(die[d]->seq_val_vec, j * 32, 32)));
                        printf("\n");
                    }
                    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
                    printf("QWEN_HBMACC_TOKEN PASS stages=%zu token=%u val=%08x die1_token=%u cycles=%u edges=%ld "
                           "settle_max=%d wall_s=%.1f RSS_KiB=%ld threads=%d ctl_cycles=%ld preroll=%ld\n", stages.size(), die[0]->seq_ntok,
                           die[0]->seq_nval, die[D - 1]->seq_ntok, cyc, edges, max_settle, sec, ru.ru_maxrss, threads, ctl_cycles, preroll);
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
            if (itrace && d == 0) {
                // RT_ITRACE: die 0's instruction fetches, ME busy edges, collective traffic edges (per-stage cycles)
                if (t.prog_re) printf("ITR cyc=%u fetch=%u\n", t.cyc, unsigned((size_t(t.prog_base) + t.prog_addr) & 4095));
                if (bool(t.me_clk_en) != itr_me) { itr_me = t.me_clk_en; printf("ITR cyc=%u me=%d\n", t.cyc, int(itr_me)); }
                if (bool(t.c_valid) != itr_c) { itr_c = t.c_valid; printf("ITR cyc=%u coll=%d\n", t.cyc, int(itr_c)); }
            }
            me_en[d] = t.me_clk_en;
            if (t.wrom_re) fatal("stream-unit weight-ROM read (the simulation core narrows that port)");
            r.prog = t.prog_re;
            if (t.prog_re) {
                size_t a = (size_t(t.prog_base) + t.prog_addr) & 4095;
                for (int w = 0; w < 32; w++) r.prog_q[w] = a < 1024 ? m.prog[a * 32 + w] : 0;
            }
            r.desc = t.desc_re;
            if (t.desc_re) r.desc_q = t.desc_addr < 64 ? m.desc[t.desc_addr] : 0;
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
                if (trace && d == 0) {
                    long nr = 0, nz = 0; uint32_t a0 = 0, v0 = 0;
                    for (int c = 0; c < NXC; c++) if (r.vx[c]) { nr++; if (r.vx_q[c]) { if (!nz) { a0 = getb(t.vx_addr, c * 24, 24); v0 = r.vx_q[c]; } nz++; } }
                    long nrom = 0; for (int i = 0; i < NT; i++) nrom += (fab[d]->t[i]->rom_ce != 0);
                    if (nr || nrom) printf("TRACE cyc=%u xreads=%ld nonzero=%ld first=%u:%08x tiles_rom=%ld tgo=%d\n", t.cyc, nr, nz, a0, v0, nrom, int(t.tgo));
                }
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
                        for (int l = 0; l < W; l++) if ((msk >> l) & 1) vmw[d].push_back({(a << 4) + l, lane32(t.vw_me_data, g * 16 + l)});
                        n_me_wr[d]++;
                        if (trace && d == 0 && n_me_wr[d] <= 40)
                            printf("TRACE cyc=%u me_wr g=%d word=%u mask=%04x d0=%08x\n", t.cyc, g, a, msk, lane32(t.vw_me_data, g * 16));
                    }
            }
            if (t.vw_mx_we)
                for (int l = 0; l < W; l++)
                    if ((t.vw_mx_mask >> l) & 1) vmw[d].push_back({uint32_t((uint64_t(t.vw_mx_addr) << 4) + l), lane32(t.vw_mx_data, l)});
            for (int l = 0; l < SW; l++) {
                if (getb(t.vw_su_we, l, 1)) { vmw[d].push_back({uint32_t(getb(t.vw_su_addr, l * 24, 24)), lane32(t.vw_su_data, l)}); n_su_wr[d]++; }
                if (getb(t.kv_we, l, 1)) kvw[d].push_back({uint32_t(getb(t.kv_waddr, l * 24, 24)), lane32(t.kv_wdata, l)});
            }
            if (t.vw_rd_we) vmw[d].push_back({t.vw_rd_addr, t.vw_rd_data});
            r.svr = t.s_vre;
            if (t.s_vre) for (int l = 0; l < W; l++) { size_t a = (size_t(t.s_vraddr) << 4) + l; r.svr_q[l] = a < VM_ELEMS ? m.vm[a] : 0; }
            if (t.s_vwe) for (int l = 0; l < W; l++) vmw[d].push_back({uint32_t((uint32_t(t.s_vwaddr) << 4) + l), lane32(t.s_vwdata, l)});
        }
        // ---- HBM controller domain: every controller edge up to this core edge (ties: controller first) ----
        t_core += TE;
        while (t_ctl + TC <= t_core) { t_ctl += TC; ctl_edge(); }
        for (int d = 0; d < D; d++) die[d]->w_a_gray = wst[d]->a_gray;
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
            if (r.prog) for (int w = 0; w < 32; w++) set32(t.prog_q, w, r.prog_q[w]);
            if (r.desc) t.desc_q = r.desc_q;
            if (r.svr) for (int l = 0; l < W; l++) set32(t.s_vrq, l, r.svr_q[l]);
            for (int l = 0; l < SW; l++) {
                if (r.cr[l]) { set32(t.crom_q, 2 * l, uint32_t(r.cr_q[l])); set32(t.crom_q, 2 * l + 1, uint32_t(r.cr_q[l] >> 32)); }
                if (r.va[l]) set32(t.va_q, l, r.va_q[l]);
                if (r.vb[l]) set32(t.vb_q, l, r.vb_q[l]);
                if (r.vc[l]) set32(t.vc_q, l, r.vc_q[l]);
            }
            if (me_en[d]) {
                const bool sl = scale_local();
                for (int g = 0; g < NPORT; g++)
                    if (r.sc[g]) {
                        if (sl && g >= NPORT) fatal("scale read beyond the port groups", g);
                        size_t w = sl ? size_t(g) * m.scale_words + r.sc_addr[g] : size_t(r.sc_addr[g]);
                        for (int j = 0; j < 8; j++) set32(t.scale_q, g * 8 + j, m.scales[w * 8 + j]);
                    }
                // x chunk port: XVM extra vector-memory registers, then the spine's capture
                if (XVM == 0) {
                    for (int c = 0; c < NXC; c++) if (r.vx[c]) set32(t.vx_q, c, r.vx_q[c]);
                } else {
                    for (int c = 0; c < NXC; c++) if (r.xpipe_v[XVM - 1][c]) set32(t.vx_q, c, r.xpipe_q[XVM - 1][c]);
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
                    if (r.kvr[i]) for (int k = 0; k < TG * W; k++) set32(x.kv_q, k, r.kv_q[i * TG * W + k]);
                });
            }
        }
        // host stage controller: one-cycle start after an image-bank switch
        for (int d = 0; d < D; d++) die[d]->h_start = 0;
        if (next_stage) {
            next_stage = false; stage_done = false; done_armed = false; cur++;
            for (int d = 0; d < D; d++) {
                load_images(mem[d], stages[cur].dir[d]);
                load_kv(mem[d].kv, stages[cur], d);
                set_plan(*die[d], plan[cur]);
                die[d]->h_start = 1;
                busy0[d] = me_busy[d];
            }
            stage_start = long(die[0]->cyc);
            printf("stage %s loaded: code_words=%zu scale_words=%zu crom_words=%zu\n", stages[cur].name.c_str(),
                   mem[0].code_words, mem[0].scale_words, mem[0].crom_words);
            fflush(stdout);
        }
        bool live[D];
        for (int d = 0; d < D; d++) live[d] = me_en[d];
        settle(live);
        if (tick % progress_every == 0) {
            double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - tstart).count();
            printf("progress tick=%ld cyc=%u pc_base=%u/%u me_busy=%ld/%ld wall=%.0fs passes=%ld\n", tick, die[0]->cyc,
                   die[0]->prog_base, die[D - 1]->prog_base, me_busy[0], me_busy[D - 1], sec, passes);
            fflush(stdout);
        }
    }
}
