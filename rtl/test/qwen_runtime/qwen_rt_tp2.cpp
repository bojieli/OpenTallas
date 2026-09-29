// Runtime-composed replay of rtl/test/tb_hdc_qwen_layer0_tp2.sv at full shape, and the
// connected multi-stage (36 layers + lm_head) token run built on the same bench.
//
// Two ot_qwen_rt_die models (TP sequencer + core with the matrix-engine
// sequencer), one ot_rom_oneshot_allreduce model, and per die G matvec slices,
// log2(G)*G split-tree cells and argmax subtrees.  The host plays the bench:
// every memory is a registered-response array with the bench's read-before-
// write order (ME groups ascending, MX, SU, RD, TP), and the finish check,
// dumps and fault check are the bench's.  Output files use the bench's names
// and formats so tools/rtl_hdc_qwen_layer0_tp2.py-style comparison applies.
#include "Vdie.h"
#include "Vcoll.h"
#include "Vslice.h"
#include "Vcella.h"
#include "Vamaxlo.h"
#include "Vamaxhi.h"
#include "qwen_rt_matvec.hpp"
#include "qwen_rt_memory.hpp"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <sys/resource.h>

constexpr int D = 2, W = 16, H = 4096, TMAX = 8192, KVH = 4, HD = 128, X_BASE = 4096;
using MV = RtMatvec<Vdie, Vslice, Vcella, Vamaxlo, Vamaxhi>;

struct DieMem {
    std::vector<uint32_t> prog, codes, scales, vm, kv, t1o, t1d;
    std::vector<uint64_t> desc, crom;
    size_t code_words = 0, scale_words = 0, crom_words = 0;
};

static std::vector<uint64_t> as64(const std::vector<uint32_t>& w) {
    std::vector<uint64_t> r(w.size() / 2);
    for (size_t i = 0; i < r.size(); i++) r[i] = w[2 * i] | (uint64_t(w[2 * i + 1]) << 32);
    return r;
}
[[noreturn]] static void fatal(const char* m, long a = -1, long b = -1) {
    printf("FATAL %s %ld %ld\n", m, a, b); fflush(stdout); exit(2);
}

struct Stage { std::string name, dir[D]; bool kv_reset; };

// Load one die's stage images.  pad_* > 0 reproduce the layer-0 bench's
// memory depths (reads past an image but inside the bench memory return 0);
// otherwise the depth is the image itself.
static void load_images(DieMem& m, const std::string& p, size_t groups, size_t pad_code, size_t pad_scale, size_t pad_crom) {
    const size_t wpg = W * 8 / 32;
    m.prog = QwenHex::load(p + "/program.hex", 32);
    m.desc = as64(QwenHex::load(p + "/segments.hex", 2));
    m.codes = QwenHex::load(p + "/matrix_int8.hex", groups * wpg);
    m.code_words = m.codes.size() / (groups * wpg);
    m.scales = QwenHex::load(p + "/matrix_scale_bf16.hex", 8);
    m.scale_words = m.scales.size() / 8;
    m.crom = as64(QwenHex::load(p + "/crom.hex", 2));
    m.crom_words = m.crom.size();
    if (m.prog.size() > 64 * 32 || m.desc.size() > 8) fatal("program/descriptor image exceeds bench memory");
    m.prog.resize(64 * 32, 0); m.desc.resize(8, 0);
    if (pad_code) {
        if (m.code_words > pad_code || m.scale_words > pad_scale || m.crom_words > pad_crom) fatal("image exceeds bench memory");
        m.code_words = pad_code; m.scale_words = pad_scale; m.crom_words = pad_crom;
    }
    m.codes.resize(m.code_words * groups * wpg, 0);
    m.scales.resize(m.scale_words * 8, 0);
    m.crom.resize(m.crom_words, 0);
}

int main(int argc, char** argv) {
    // layer-0 bench replay:  qwen_rt DIR [max_cycles]
    // connected token:       qwen_rt --stages FILE OUTDIR PRELOAD_X [max_cycles]
    //   FILE lines: <name> <die0 image dir> <die1 image dir> <kv_reset 0|1>
    if (argc < 2) { fprintf(stderr, "usage: %s DIR [max_cycles] | --stages FILE OUTDIR PRELOAD [max_cycles]\n", argv[0]); return 2; }
    const bool token_mode = !strcmp(argv[1], "--stages");
    if (token_mode && argc < 5) { fprintf(stderr, "--stages FILE OUTDIR PRELOAD\n"); return 2; }
    const std::string dir = token_mode ? std::string(argv[3]) : std::string(argv[1]);
    const std::string preload = token_mode ? std::string(argv[4]) : dir + "/vm_x_fp32.hex";
    const long max_cycles = token_mode ? (argc > 5 ? atol(argv[5]) : 400000000L) : (argc > 2 ? atol(argv[2]) : 10000000);
    constexpr int G = GROUPS, WPG = W * 8 / 32;  // code words (u32) per group
    const size_t VM_ELEMS = 177808, KV_ELEMS = 8388608;
    int threads = 16;
    if (const char* t = getenv("RT_THREADS")) threads = atoi(t);
    RtPool pool(threads);
    auto t0 = std::chrono::steady_clock::now();
    std::vector<Stage> stages;
    if (token_mode) {
        FILE* f = fopen(argv[2], "r");
        if (!f) fatal("stages file");
        char n[256], a[1024], b[1024]; int k;
        while (fscanf(f, "%255s %1023s %1023s %d", n, a, b, &k) == 4) stages.push_back({n, {a, b}, k != 0});
        fclose(f);
        if (stages.empty()) fatal("no stages");
    } else {
        stages.push_back({"layer0", {dir + "/die0", dir + "/die1"}, true});
    }
    // bench parameters (tb_hdc_qwen_layer0_tp2 defaults) apply to the replay only
    const size_t PAD_CODE = token_mode ? 0 : 1488, PAD_SCALE = token_mode ? 0 : 50616, PAD_CROM = token_mode ? 0 : 543233;
    DieMem mem[D];
    auto x0 = QwenHex::load(preload, 1);
    for (int d = 0; d < D; d++) {
        auto& m = mem[d];
        load_images(m, stages[0].dir[d], G, PAD_CODE, PAD_SCALE, PAD_CROM);
        m.vm.assign(VM_ELEMS, 0);
        for (size_t i = 0; i < x0.size() && i < VM_ELEMS; i++) m.vm[i] = x0[i];
        m.kv.assign(KV_ELEMS, 0);
        m.t1o.assign(H, 0); m.t1d.assign(H, 0);
        printf("die%d stage %s images: code_words=%zu scale_words=%zu crom_words=%zu\n", d, stages[0].name.c_str(),
               m.code_words, m.scale_words, m.crom_words);
    }
    printf("images loaded in %.1f s\n", std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    fflush(stdout);

    VerilatedContext dctx[D], cctx;
    std::unique_ptr<Vdie> die[D];
    std::unique_ptr<MV> mv[D];
    for (int d = 0; d < D; d++) {
        dctx[d].randReset(0);
        die[d].reset(new Vdie(&dctx[d], d ? "die1" : "die0"));
        die[d]->tp_token = 0; die[d]->tp_pos = 0; die[d]->h_start = 0;
        Vdie* dp = die[d].get();
        mv[d].reset(new MV(*dp, pool, G, std::min(7, [] { int l = 0; while ((1 << l) < G) l++; return l; }()),
                           [dp] { return dp->rt_rst_n; }));
        mv[d]->set_nw(COUNTWIDTH);
    }
    cctx.randReset(0);
    Vcoll coll(&cctx, "coll");
    printf("models constructed in %.1f s\n", std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
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
    int max_settle = 0;
    double t_edge = 0, t_top = 0, t_models = 0, t_prop = 0, t_mem = 0; long passes = 0;
    auto now = [] { return std::chrono::steady_clock::now(); };
    auto dt = [](auto a, auto b) { return std::chrono::duration<double>(b - a).count(); };
    auto settle = [&]() {
        for (int n = 0;; n++) {
            if (n > 64) fatal("settle did not converge");
            passes++;
            auto a = now();
            for (int d = 0; d < D; d++) die[d]->eval();
            coll.eval();
            auto b = now();
            for (int d = 0; d < D; d++) mv[d]->eval_models();
            auto c = now();
            bool ch = wire_coll();
            for (int d = 0; d < D; d++) ch |= mv[d]->propagate();
            auto e = now();
            t_top += dt(a, b); t_models += dt(b, c); t_prop += dt(c, e);
            if (!ch) { max_settle = std::max(max_settle, n + 1); return; }
        }
    };
    auto set_clk = [&](uint8_t c) {
        for (int d = 0; d < D; d++) { die[d]->clk = c; mv[d]->set_clk(c); }
        coll.clk = c;
    };

    // registered bench responses (applied after each edge)
    struct Resp {
        bool prog = false, desc = false, crom = false, code = false, va = false, vb = false, vc = false, svr = false;
        uint32_t prog_q[32]; uint64_t desc_q = 0, crom_q = 0; size_t code_addr = 0;
        uint32_t va_q = 0, vb_q = 0, vc_q = 0, svr_q[16];
        std::vector<uint8_t> sc, kvr, vx;          // per group: scale / kv / x response pending
        std::vector<uint32_t> sc_addr, kv_addr, vx_q, kv_q;
    } rs[D];
    struct Wr { uint32_t a, v; };
    std::vector<Wr> vmw[D], kvw[D], t1ow[D], t1dw[D];
    for (int d = 0; d < D; d++) {
        rs[d].sc.assign(G, 0); rs[d].kvr.assign(G, 0); rs[d].vx.assign(G, 0);
        rs[d].sc_addr.assign(G, 0); rs[d].kv_addr.assign(G, 0); rs[d].vx_q.assign(G, 0); rs[d].kv_q.assign(size_t(G) * W, 0);
    }
    long me_busy[D] = {0, 0}, edges = 0;
    auto dump = [&](int d) {
        std::string p = dir + "/die" + char('0' + d) + "/";
        auto& m = mem[d];
        auto wr = [&](const char* n, auto f, int count) {
            FILE* fp = fopen((p + n).c_str(), "w");
            for (int i = 0; i < count; i++) fprintf(fp, "%08x\n", f(i));
            fclose(fp);
        };
        wr("x_final.hex", [&](int i) { return m.vm[X_BASE + i]; }, H);
        wr("t1_final.hex", [&](int i) { return m.vm[i]; }, H);
        wr("t1_after_o_scale.hex", [&](int i) { return m.t1o[i]; }, H);
        wr("t1_after_down_scale.hex", [&](int i) { return m.t1d[i]; }, H);
        wr("k_pos0.hex", [&](int i) { int h = i / HD, dim = i % HD; long ka = ((long(h) * (TMAX / W)) * HD + dim) * W; return m.kv[ka]; }, KVH * HD);
        wr("v_pos0.hex", [&](int i) { int h = i / HD, dim = i % HD; long va = long(KVH) * TMAX * HD + (long(h) * TMAX) * HD + dim; return m.kv[va]; }, KVH * HD);
    };

    long progress_every = getenv("RT_PROGRESS") ? atol(getenv("RT_PROGRESS")) : 1024;
    bool finished = false, stage_done = false, next_stage = false;
    size_t cur = 0; long stage_start = 7, busy0[D] = {0, 0};
    auto tstart = std::chrono::steady_clock::now();
    for (long tick = 0;; tick++) {
        set_clk(0);
        settle();
        // ---- the bench's posedge block, evaluated on pre-edge values -------------
        {
            uint32_t cyc = die[0]->cyc;
            uint8_t all_done = die[0]->s_done && die[1]->s_done;
            if (!token_mode && cyc > 8 && all_done && !finished) {
                finished = true;
                uint8_t sf = die[0]->s_fault | (die[1]->s_fault << 1), cf = die[0]->core_fault | (die[1]->core_fault << 1);
                uint8_t lf = coll.fault;
                if (sf || cf || lf) { printf("layer0 fault seq=%d core=%d coll=%d\n", sf, cf, lf); return 1; }
                dump(0); dump(1);
                struct rusage ru; getrusage(RUSAGE_SELF, &ru);
                double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - tstart).count();
                printf("QWEN_LAYER0_TP2 PASS dies=2 token=0 pos=0 cycles=%u seq_fault=00 core_fault=00 coll_fault=00\n", cyc);
                printf("RT_STATS groups=%d edges=%ld me_busy_die0=%ld me_busy_die1=%ld core_cycles_die0=%u core_cycles_die1=%u "
                       "link_stalls=%u settle_max=%d wall_s=%.1f RSS_KiB=%ld threads=%d\n",
                       G, edges, me_busy[0], me_busy[1], die[0]->core_cycles, die[1]->core_cycles, coll.link_stalls,
                       max_settle, sec, ru.ru_maxrss, threads);
                return 0;
            }
            if (token_mode && cyc > 8 && all_done && !stage_done) {
                // stage boundary: bench-style fault check, per-stage dump, then
                // the host stage controller selects the next image bank
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
                    printf("QWEN_TOKEN_TP2 PASS stages=%zu token=%u val=%08x die1_token=%u cycles=%u edges=%ld "
                           "settle_max=%d wall_s=%.1f RSS_KiB=%ld threads=%d\n", stages.size(), die[0]->seq_ntok,
                           die[0]->seq_nval, die[1]->seq_ntok, cyc, edges, max_settle, sec, ru.ru_maxrss, threads);
                    return 0;
                }
                next_stage = true;
            }
            if (cyc > max_cycles) { printf("layer0 timeout cyc=%u\n", cyc); return 3; }
        }
        auto tm0 = now();
        for (int d = 0; d < D; d++) {
            Vdie& t = *die[d];
            auto& m = mem[d];
            auto& r = rs[d];
            MV& e = *mv[d];
            vmw[d].clear(); kvw[d].clear(); t1ow[d].clear(); t1dw[d].clear();
            if (e.top.b_active) me_busy[d]++;
            r.prog = t.prog_re;
            if (t.prog_re) {
                size_t a = (size_t(t.prog_base) + t.prog_addr) & 4095;
                for (int w = 0; w < 32; w++) r.prog_q[w] = a < 64 ? m.prog[a * 32 + w] : 0;
            }
            r.desc = t.desc_re;
            if (t.desc_re) r.desc_q = t.desc_addr < 8 ? m.desc[t.desc_addr] : 0;
            if (t.wrom_re) fatal("BF16 weight ROM requested");
            r.code = t.int8_wrom_re;
            if (t.int8_wrom_re) {
                if (t.int8_wrom_addr >= m.code_words) fatal("code ROM address", t.int8_wrom_addr);
                r.code_addr = t.int8_wrom_addr;
            }
            r.crom = t.crom_re;
            if (t.crom_re) {
                if (t.crom_addr >= m.crom_words) fatal("constant ROM address", t.crom_addr);
                r.crom_q = m.crom[t.crom_addr];
            }
            const bool kv_re = t.kv_re;
            pool.run(G, [&](size_t g) {
                auto& s = *e.s[g];
                r.sc[g] = s.scale_gre;
                if (s.scale_gre) {
                    if (s.scale_addr >= m.scale_words) fatal("scale ROM address", s.scale_addr, long(g));
                    r.sc_addr[g] = s.scale_addr;
                }
                r.kvr[g] = kv_re;
                if (kv_re) {
                    size_t a = s.kv_addr;
                    for (int j = 0; j < W; j++) r.kv_q[g * W + j] = (a < KV_ELEMS / W) ? m.kv[a * W + j] : 0;
                }
                r.vx[g] = s.x_re;
                if (s.x_re) r.vx_q[g] = s.x_addr < VM_ELEMS ? m.vm[s.x_addr] : 0;
            });
            for (int g = 0; g < G; g++) {
                auto& s = *e.s[g];
                if (s.o_we)
                    for (int l = 0; l < W; l++)
                        if ((s.o_mask >> l) & 1) vmw[d].push_back({uint32_t((uint64_t(s.o_addr) << 4) + l), s.o_data[l]});
            }
            r.va = t.va_re; if (t.va_re) r.va_q = t.va_addr < VM_ELEMS ? m.vm[t.va_addr] : 0;
            r.vb = t.vb_re; if (t.vb_re) r.vb_q = t.vb_addr < VM_ELEMS ? m.vm[t.vb_addr] : 0;
            r.vc = t.vc_re; if (t.vc_re) r.vc_q = t.vc_addr < VM_ELEMS ? m.vm[t.vc_addr] : 0;
            if (t.kv_we) kvw[d].push_back({t.kv_waddr, t.kv_wdata});
            if (t.vw_mx_we)
                for (int l = 0; l < W; l++)
                    if ((t.vw_mx_mask >> l) & 1) vmw[d].push_back({uint32_t((uint64_t(t.vw_mx_addr) << 4) + l), t.vw_mx_data[l]});
            if (t.vw_su_we) {
                vmw[d].push_back({t.vw_su_addr, t.vw_su_data});
                if (t.vw_su_addr < H && t.prog_base == 21) t1ow[d].push_back({t.vw_su_addr, t.vw_su_data});
                if (t.vw_su_addr < H && t.prog_base == 30) t1dw[d].push_back({t.vw_su_addr, t.vw_su_data});
            }
            if (t.vw_rd_we) vmw[d].push_back({t.vw_rd_addr, t.vw_rd_data});
            r.svr = t.s_vre;
            if (t.s_vre)
                for (int l = 0; l < W; l++) { size_t a = (size_t(t.s_vraddr) << 4) + l; r.svr_q[l] = a < VM_ELEMS ? m.vm[a] : 0; }
            if (t.s_vwe)
                for (int l = 0; l < W; l++) vmw[d].push_back({uint32_t((uint32_t(t.s_vwaddr) << 4) + l), t.s_vwdata[l]});
        }
        t_mem += dt(tm0, now());
        // ---- rising edge: every model sees only pre-edge inputs -------------------
        set_clk(1);
        auto te0 = now();
        for (int d = 0; d < D; d++) die[d]->eval();
        coll.eval();
        auto te1 = now();
        for (int d = 0; d < D; d++) mv[d]->eval_edge();
        t_top += dt(te0, te1); t_edge += dt(te1, now());
        auto tc0 = now();
        edges++;
        // ---- commit bench NBAs: memory writes, registered read responses ---------
        for (int d = 0; d < D; d++) {
            auto& m = mem[d];
            auto& r = rs[d];
            Vdie& t = *die[d];
            MV& e = *mv[d];
            for (auto& w : vmw[d]) if (w.a < VM_ELEMS) m.vm[w.a] = w.v;
            for (auto& w : kvw[d]) { size_t a = w.a; if (a < KV_ELEMS) m.kv[a] = w.v; }
            for (auto& w : t1ow[d]) m.t1o[w.a] = w.v;
            for (auto& w : t1dw[d]) m.t1d[w.a] = w.v;
            if (r.prog) for (int w = 0; w < 32; w++) t.prog_q[w] = r.prog_q[w];
            if (r.desc) t.desc_q = r.desc_q;
            if (r.crom) t.crom_q = r.crom_q;
            if (r.va) t.va_q = r.va_q;
            if (r.vb) t.vb_q = r.vb_q;
            if (r.vc) t.vc_q = r.vc_q;
            if (r.svr) for (int l = 0; l < W; l++) t.s_vrq[l] = r.svr_q[l];
            const bool code = r.code; const size_t ca = r.code_addr;
            pool.run(G, [&](size_t g) {
                auto& s = *e.s[g];
                if (code) for (int j = 0; j < WPG; j++) s.wrom_q[j] = m.codes[(ca * G + g) * WPG + j];
                if (r.sc[g]) for (int j = 0; j < 8; j++) s.scale_q[j] = m.scales[size_t(r.sc_addr[g]) * 8 + j];
                if (r.kvr[g]) for (int j = 0; j < W; j++) s.kv_q[j] = r.kv_q[g * W + j];
                if (r.vx[g]) s.x_q = r.vx_q[g];
            });
        }
        // host stage controller: one-cycle start after an image-bank switch
        for (int d = 0; d < D; d++) die[d]->h_start = 0;
        if (next_stage) {
            next_stage = false; stage_done = false; cur++;
            for (int d = 0; d < D; d++) {
                load_images(mem[d], stages[cur].dir[d], G, 0, 0, 0);
                if (stages[cur].kv_reset) std::fill(mem[d].kv.begin(), mem[d].kv.end(), 0u);
                die[d]->h_start = 1;
                busy0[d] = me_busy[d];
            }
            stage_start = long(die[0]->cyc);
            printf("stage %s loaded: code_words=%zu scale_words=%zu crom_words=%zu\n", stages[cur].name.c_str(),
                   mem[0].code_words, mem[0].scale_words, mem[0].crom_words);
            fflush(stdout);
        }
        t_mem += dt(tc0, now());
        settle();
        if (tick % progress_every == 0) {
            double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - tstart).count();
            printf("progress tick=%ld cyc=%u pc_base=%u/%u me_busy=%ld/%ld wall=%.0fs top=%.1f models=%.1f prop=%.1f mem=%.1f edge=%.1f passes=%ld\n", tick, die[0]->cyc,
                   die[0]->prog_base, die[1]->prog_base, me_busy[0], me_busy[1], sec, t_top, t_models, t_prop, t_mem, t_edge, passes);
            fflush(stdout);
        }
    }
}
