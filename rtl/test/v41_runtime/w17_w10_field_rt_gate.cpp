// Experimental companion: FAST/PP/BP default off; no adoption or clock claim.
// W17 runtime-composition equivalence gate of an experimental FAST/PP runtime baseline (tools/w17_w10_field_rt_gate.py).
//
// Reference: Vflat = ot_v41_fieldtop_w17w10 (spine + vector memory + ot_v41_field_w17w10: NP element pairs, return tree,
//            R region roots; the via-programmed ROM model and the configuration ROM read from image files).
// Candidate: Vcut  = ot_v41_fieldtop_w17w10 with RT_CUT (the field removed, its wires exposed), plus
//            Vpq / Vpb   ot_v41_pair_w17w10 (FP8/FP4-only, BF16-capable) compiled ONCE each with V41_RT (ROM words and
//                        configuration words served by this host through DPI), instantiated per pair,
//            Vretn       ot_v41_retn_w17w10, instantiated per return-tree node inside a region,
//            Vroot       ot_v41_ret_root, instantiated per region,
//            wired by this host exactly as ot_v41_field_w17w10 wires them.
//
// Clock discipline: every model evaluates its rising edge with the inputs present before the edge; only
// then does the host copy producer outputs to consumer inputs (no model ever sees a value registered on
// the same edge); then every model evaluates clk = 0 to settle.  Every cut is register -> register.
// --wrong-edge (negative control): models are evaluated one after another and each one's outputs are
// copied to its consumers immediately, so consumers see same-edge values.  It must fail.
//
// Compared on every cycle: every public port of ot_v41_fieldtop_w17w10 (ready, idle, o_we, o_addr, o_data, fault,
// phase_cycles).  The candidate's vector-memory writes and per-op phase cycles are printed for the golden
// check.   Usage: gate DIR OPS [--wrong-edge] [--no-ref]
// Compile-time: NP, NR (regions), NBF, PHW, VAW.
#include "Vflat.h"
#include "Vcut.h"
#include "Vpq.h"
#include "Vpb.h"
#include "Vretn.h"
#include "Vroot.h"
#include "svdpi.h"
#include "qwen_rt_matvec.hpp"   // RtPool
#include <array>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <sys/resource.h>

constexpr int CW = 25;
struct PairMem {
    std::vector<std::array<uint32_t, 9>> rom[2];
    std::vector<uint64_t> cfg;
};
static std::vector<PairMem> g_mem;
static PairMem* g_reg = nullptr;
static std::unordered_map<const void*, std::pair<PairMem*, int>> g_romscope;
static std::unordered_map<const void*, PairMem*> g_cfgscope;

extern "C" void v41rt_rom_register(const char* inst) {
    if (!g_reg) { printf("FATAL rom register outside construction\n"); exit(3); }
    if (getenv("RT_ROMDBG")) printf("ROMREG %p inst=[%s] scope=%s\n", (void*)g_reg, inst ? inst : "(null)", svGetNameFromScope(svGetScope()));
    // Verilator passes the string parameter space-padded (" b"): the second macro's suffix is its last character
    g_romscope[svGetScope()] = {g_reg, (inst && inst[0] && inst[strlen(inst) - 1] == 'b') ? 1 : 0};
}
extern "C" void v41rt_rom_read(int addr, svBitVecVal* q) {
    auto it = g_romscope.find(svGetScope());
    if (it == g_romscope.end()) { printf("FATAL rom scope\n"); exit(3); }
    const char* mutant = getenv("W17_PP_MUTANT");
    int bank = it->second.second;
    if (mutant && !strcmp(mutant, "bank")) bank ^= 1;
    if (mutant && !strcmp(mutant, "parity")) addr ^= 1;
    const auto& v = it->second.first->rom[bank];
    for (int k = 0; k < 9; k++) q[k] = (size_t(addr) < v.size()) ? v[addr][k] : 0;
}
extern "C" void v41rt_cfg_register() {
    if (!g_reg) { printf("FATAL cfg register outside construction\n"); exit(3); }
    g_cfgscope[svGetScope()] = g_reg;
}
extern "C" long long v41rt_cfg_read(int addr) {
    auto it = g_cfgscope.find(svGetScope());
    if (it == g_cfgscope.end()) { printf("FATAL cfg scope\n"); exit(3); }
    const auto& c = it->second->cfg;
    return (size_t(addr) < c.size()) ? (long long)c[addr] : 0;
}

// ---- bit helpers over Verilator port types --------------------------------------------------------------
template <class V> static uint64_t getb(const V& v, size_t pos, int n) {
    if constexpr (std::is_integral_v<V>) {
        return (uint64_t(v) >> pos) & (n >= 64 ? ~0ull : ((1ull << n) - 1));
    } else {
        uint64_t r = 0;
        for (int b = 0; b < n; b++) r |= uint64_t((v[(pos + b) / 32] >> ((pos + b) % 32)) & 1) << b;
        return r;
    }
}
template <class V> static void setb(V& v, size_t pos, int n, uint64_t x) {
    if constexpr (std::is_integral_v<V>) {
        uint64_t m = (n >= 64 ? ~0ull : ((1ull << n) - 1)) << pos;
        v = (V)((uint64_t(v) & ~m) | ((x << pos) & m));
    } else {
        for (int b = 0; b < n; b++) {
            uint32_t& w = v[(pos + b) / 32];
            uint32_t bit = 1u << ((pos + b) % 32);
            w = ((x >> b) & 1) ? (w | bit) : (w & ~bit);
        }
    }
}
template <class A, class B> static bool same(const A& a, const B& b) {
    if constexpr (std::is_integral_v<A>) return uint64_t(a) == uint64_t(b);
    else { for (size_t i = 0; i < sizeof(a) / 4; i++) if (a[i] != b[i]) return false; return true; }
}
static std::vector<std::string> split(const std::string& s) {
    std::istringstream is(s); std::vector<std::string> r; std::string t;
    while (is >> t) r.push_back(t);
    return r;
}
static void load_words(PairMem& m, const std::string& dir, int p) {
    for (int mb = 0; mb < 2; mb++) {
        std::ifstream f(dir + "/e" + std::to_string(p) + (mb ? "b" : "") + ".words.hex");
        std::string line;
        while (std::getline(f, line)) {
            auto t = split(line);
            if (t.size() != 2) continue;
            size_t a = std::stoul(t[0], nullptr, 16);
            if (m.rom[mb].size() <= a) m.rom[mb].resize(a + 1, std::array<uint32_t, 9>{});
            const std::string& h = t[1];
            std::array<uint32_t, 9> w{};
            for (int k = 0; k < 9; k++) {
                int end = int(h.size()) - 8 * k;
                if (end <= 0) break;
                int beg = std::max(0, end - 8);
                w[k] = uint32_t(std::stoul(h.substr(beg, end - beg), nullptr, 16));
            }
            m.rom[mb][a] = w;
        }
    }
    std::ifstream f(dir + "/e" + std::to_string(p) + ".cfg.hex");
    std::string line;
    while (std::getline(f, line)) if (!line.empty()) m.cfg.push_back(std::stoull(line, nullptr, 16));
}

// ---- the composed field ------------------------------------------------------------------------------------
struct Node { uint8_t v, e; uint32_t t, d; };
constexpr bool is_bf(int p) {
    for (int i = 0; i < NBF; i++) if ((i * NP) / NBF == p) return true;
    return false;
}
struct Field {
    static constexpr int NL = 2 * NP;
    static constexpr int LR = __builtin_ctz(NR), L = __builtin_ctz(NL), LS = L - LR;
    RtPool& pool;
    Vcut& top;
    std::vector<std::unique_ptr<Vpq>> pq;
    std::vector<std::unique_ptr<Vpb>> pb;
    std::vector<int> kind, idx;                                    // per pair: 0 pq / 1 pb, index
    std::vector<std::vector<std::unique_ptr<Vretn>>> nodes;       // [level][position]
    std::vector<std::unique_ptr<Vroot>> roots;
    size_t nmodels() const { return size_t(NP) + nn + roots.size(); }
    size_t nn = 0;
    std::vector<std::pair<int, int>> nlist;                        // flattened (level, position)
    Field(Vcut& t, RtPool& p, const std::string& dir) : pool(p), top(t) {
        g_mem.resize(NP);
        for (int g = 0; g < NP; g++) load_words(g_mem[g], dir, g);
        for (int g = 0; g < NP; g++) {
            g_reg = &g_mem[g];
            std::string nm = "p" + std::to_string(g);
            if (is_bf(g)) { pb.emplace_back(new Vpb(pool.ctx(g % pool.size()), nm.c_str())); kind.push_back(1); idx.push_back(int(pb.size()) - 1); pb.back()->eval(); }
            else { pq.emplace_back(new Vpq(pool.ctx(g % pool.size()), nm.c_str())); kind.push_back(0); idx.push_back(int(pq.size()) - 1); pq.back()->eval(); }
        }
        g_reg = nullptr;
        nodes.resize(LS);
        for (int l = 0; l < LS; l++)
            for (int g = 0; g < (NL >> (l + 1)); g++) {
                std::string nm = "n" + std::to_string(l) + "_" + std::to_string(g);
                nodes[l].emplace_back(new Vretn(pool.ctx(nn % pool.size()), nm.c_str()));
                nlist.push_back({l, g}); nn++;
            }
        for (int g = 0; g < NR; g++) roots.emplace_back(new Vroot(pool.ctx(g % pool.size()), ("r" + std::to_string(g)).c_str()));
    }
    template <class F> void each_pair(int g, F f) { if (kind[g]) f(*pb[idx[g]]); else f(*pq[idx[g]]); }
    void eval_all(uint8_t clk, uint8_t rst) {
        pool.run(nmodels(), [&](size_t i) {
            if (i < size_t(NP)) { each_pair(int(i), [&](auto& m) { m.clk = clk; m.rst_n = rst; m.eval(); }); return; }
            i -= NP;
            if (i < nn) { auto& n = *nodes[nlist[i].first][nlist[i].second]; n.clk = clk; n.rst_n = rst; n.eval(); return; }
            i -= nn;
            auto& r = *roots[i]; r.clk = clk; r.rst_n = rst; r.eval();
        });
    }
    // leaf (macro) partial of pair g, macro m
    Node leaf(int g, int m) {
        Node o{};
        each_pair(g, [&](auto& x) {
            o.v = (x.pv >> m) & 1; o.e = (x.perr >> m) & 1;
            o.d = uint32_t(getb(x.pval, 32 * m, 32));
            uint32_t pos = uint32_t(getb(x.ppos, 3 * m, 3)), row = uint32_t(getb(x.prow, 16 * m, 16));
            uint32_t seg = uint32_t(getb(x.pseg, 5 * m, 5)), ns = uint32_t(getb(x.pnseg, 5 * m, 5));
            o.t = (pos << 29) | (row << 13) | (seg << 8) | ns;
        });
        return o;
    }
    Node level_out(int l, int g) {       // output of level l (0 = leaves) position g
        if (l == 0) return leaf(g >> 1, g & 1);
        auto& n = *nodes[l - 1][g];
        return Node{n.o_v, n.o_e, n.o_t, n.o_d};
    }
    // copy broadcast to pairs
    template <class M> void bcast(M& m) {
        m.cfg_go = top.fb_cfg_go; m.cfg_ph = top.fb_cfg_ph; m.cfg_np = top.fb_cfg_np; m.go = top.fb_go;
        m.go_bf = top.fb_go_bf; m.xs_v = top.fb_xs_v; m.xs_p = top.fb_xs_p; m.xs_b = top.fb_xs_b;
        m.xs_sv = top.fb_xs_sv; m.xs_q0 = top.fb_xs_q0; m.xs_e0 = top.fb_xs_e0; m.xs_q1 = top.fb_xs_q1;
        m.xs_e1 = top.fb_xs_e1; m.xs_pos = top.fb_xs_pos; m.xb_pos = top.fb_xb_pos; m.xb_v = top.fb_xb_v;
        m.xb_b = top.fb_xb_b; m.xb_sv = top.fb_xb_sv; m.xb_u = top.fb_xb_u; m.xb_d = top.fb_xb_d;
    }
    void to_pairs(int g) { each_pair(g, [&](auto& m) { bcast(m); }); }
    void to_node(int l, int g) {         // inputs of node (l, g) from level l outputs 2g, 2g+1
        auto& n = *nodes[l][g];
        Node a = level_out(l, 2 * g), b = level_out(l, 2 * g + 1);
        n.a_v = a.v; n.a_t = a.t; n.a_d = a.d; n.a_e = a.e; n.b_v = b.v; n.b_t = b.t; n.b_d = b.d; n.b_e = b.e;
    }
    void to_root(int g) {
        auto& r = *roots[g];
        Node a = level_out(LS, g);
        r.i_v = a.v; r.i_t = a.t; r.i_d = a.d; r.i_e = a.e;
    }
    void to_top() {
        uint64_t f = 0;
        for (int g = 0; g < NR; g++) {
            auto& r = *roots[g];
            setb(top.fr_v, g, 1, r.r_v); setb(top.fr_row, 16 * g, 16, r.r_row); setb(top.fr_pos, 3 * g, 3, r.r_pos);
            setb(top.fr_fp32, 32 * g, 32, r.r_fp32); setb(top.fr_bf16, 16 * g, 16, r.r_bf16); setb(top.fr_e, g, 1, r.r_e);
            f |= r.fault;
        }
        for (int g = 0; g < NP; g++) each_pair(g, [&](auto& m) { f |= m.fault; });
        for (auto& lv : nodes) for (auto& n : lv) f |= n->fault;
        top.fr_fault = f ? 1 : 0;
    }
    void propagate() {
        pool.run(size_t(NP), [&](size_t g) { to_pairs(int(g)); });
        for (int l = 0; l < LS; l++) for (int g = 0; g < (NL >> (l + 1)); g++) to_node(l, g);
        for (int g = 0; g < NR; g++) to_root(g);
        to_top();
    }
};

struct Op { int ph, np, xbase, xps, obase, ops; };

int main(int argc, char** argv) {
    if (argc < 3) { printf("usage: gate DIR OPS [--wrong-edge] [--no-ref]\n"); return 2; }
    std::string dir = argv[1];
    bool wrong = false, noref = false;
    for (int i = 3; i < argc; i++) { if (!strcmp(argv[i], "--wrong-edge")) wrong = true; if (!strcmp(argv[i], "--no-ref")) noref = true; }
    std::vector<Op> ops;
    { std::ifstream f(argv[2]); std::string line;
      while (std::getline(f, line)) { auto t = split(line); if (t.size() == 6) ops.push_back({std::stoi(t[0]), std::stoi(t[1]), std::stoi(t[2]), std::stoi(t[3]), std::stoi(t[4]), std::stoi(t[5])}); } }
    int threads = 4;
    if (const char* t = getenv("RT_THREADS")) threads = atoi(t);
    std::string plus = "+OT_ROM_DIR=" + dir;
    const char* av[] = {"gate", plus.c_str()};
    RtPool pool(threads);
    for (int w = 0; w < pool.size(); w++) pool.ctx(w)->commandArgs(2, av);
    VerilatedContext rctx; rctx.randReset(0); rctx.commandArgs(2, av);
    VerilatedContext cctx; cctx.randReset(0); cctx.commandArgs(2, av);
    std::unique_ptr<Vflat> ref;
    if (!noref) ref.reset(new Vflat(&rctx, "flat"));
    Vcut cut(&cctx, "cut");
    Field fld(cut, pool, dir);
    uint8_t rst = 0;
    auto drive = [&](auto& m, const Op* o, bool go) {
        m.go = go; m.rst_n = rst;
        if (o) { m.i_ph = o->ph; m.i_np = o->np; m.i_xbase = o->xbase; m.i_xps = o->xps; m.i_obase = o->obase; m.i_ops = o->ops; }
    };
    long cyc = 0, writes = 0, checks = 0;
    auto check = [&]() {
        if (!ref) return;
        checks++;
        const char* bad = nullptr;
        if (ref->ready != cut.ready) bad = "ready";
        else if (ref->idle != cut.idle) bad = "idle";
        else if (!same(ref->o_we, cut.o_we)) bad = "o_we";
        else if (!same(ref->o_addr, cut.o_addr)) bad = "o_addr";
        else if (!same(ref->o_data, cut.o_data)) bad = "o_data";
        else if (ref->fault != cut.fault) bad = "fault";
        else if (ref->phase_cycles != cut.phase_cycles) bad = "phase_cycles";
        if (bad) {
            for (int k = 0; k < NR; k++)
                printf("DIAG port %d ref we=%d a=%lu d=%08lx | cut we=%d a=%lu d=%08lx\n", k,
                       int((uint64_t(ref->o_we) >> k) & 1), (unsigned long)getb(ref->o_addr, VAW * k, VAW),
                       (unsigned long)getb(ref->o_data, 32 * k, 32), int((uint64_t(cut.o_we) >> k) & 1),
                       (unsigned long)getb(cut.o_addr, VAW * k, VAW), (unsigned long)getb(cut.o_data, 32 * k, 32));
            printf("FAIL case=0 tick=%ld port=%s\n", cyc, bad); fflush(stdout); exit(1);
        }
    };
    auto tick = [&](const Op* o, bool go) {
        // inputs before the edge
        if (ref) drive(*ref, o, go);
        drive(cut, o, go);
        if (!wrong) {
            if (ref) { ref->clk = 1; ref->eval(); }
            cut.clk = 1; cut.eval();
            fld.eval_all(1, rst);
            fld.propagate();
        } else {
            // negative control: each model's outputs reach its consumers before they evaluate the edge
            if (ref) { ref->clk = 1; ref->eval(); }
            cut.clk = 1; cut.eval();
            for (int g = 0; g < NP; g++) { fld.to_pairs(g); fld.each_pair(g, [&](auto& m) { m.clk = 1; m.rst_n = rst; m.eval(); }); }
            for (int l = 0; l < Field::LS; l++)
                for (int g = 0; g < ((2 * NP) >> (l + 1)); g++) { fld.to_node(l, g); auto& n = *fld.nodes[l][g]; n.clk = 1; n.rst_n = rst; n.eval(); }
            for (int g = 0; g < NR; g++) { fld.to_root(g); auto& r = *fld.roots[g]; r.clk = 1; r.rst_n = rst; r.eval(); }
            fld.propagate();
        }
        if (ref) { ref->clk = 0; ref->eval(); }
        cut.clk = 0; cut.eval();
        fld.eval_all(0, rst);
        cyc++;
        check();
        if (getenv("RT_LEAF"))
            for (int g = 0; g < NP; g++)
                for (int m = 0; m < 2; m++) {
                    Node n = fld.leaf(g, m);
                    if (n.v) printf("L %ld pair=%d m=%d row=%u seg=%u nseg=%u val=%08x\n", cyc, g, m, (n.t >> 13) & 0xffff,
                                    (n.t >> 8) & 31, n.t & 31, n.d);
                }
        if (getenv("RT_BEATS") && cut.fb_xs_v) {
            printf("B %ld p=%u b=%u sv=%u e0=%u e1=%u q0=", cyc, cut.fb_xs_p, cut.fb_xs_b, cut.fb_xs_sv, cut.fb_xs_e0, cut.fb_xs_e1);
            for (int k = 7; k >= 0; k--) printf("%08x", cut.fb_xs_q0[k]);
            printf(" q1=");
            for (int k = 7; k >= 0; k--) printf("%08x", cut.fb_xs_q1[k]);
            printf("\n");
        }
        if (getenv("RT_BEATS") && (cut.fb_go || cut.fb_cfg_go)) printf("G %ld go=%d cfg=%d\n", cyc, cut.fb_go, cut.fb_cfg_go);
        if (ref && getenv("RT_REFW"))
            for (int k = 0; k < NR; k++)
                if ((uint64_t(ref->o_we) >> k) & 1)
                    printf("R %lu %08lx\n", (unsigned long)getb(ref->o_addr, VAW * k, VAW), (unsigned long)getb(ref->o_data, 32 * k, 32));
        for (int k = 0; k < NR; k++)
            if ((uint64_t(cut.o_we) >> k) & 1) {
                printf("W %lu %08lx\n", (unsigned long)getb(cut.o_addr, VAW * k, VAW), (unsigned long)getb(cut.o_data, 32 * k, 32));
                writes++;
            }
    };
    for (int i = 0; i < 6; i++) tick(nullptr, false);
    rst = 1;
    for (int i = 0; i < 4; i++) tick(nullptr, false);
    const long LIMIT = 4000000;
    for (size_t k = 0; k < ops.size(); k++) {
        while (!cut.ready) { tick(nullptr, false); if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; } }
        tick(&ops[k], true);
        long t0 = cyc;
        do { tick(&ops[k], false); if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; } } while (!cut.idle);
        printf("OP %zu ph=%d cycles=%u wall=%ld fault=%d\n", k, ops[k].ph, cut.phase_cycles, cyc - t0 + 1, cut.fault);
        if (cut.fault) { printf("FAIL fault op=%zu\n", k); return 1; }
    }
    for (int i = 0; i < 32; i++) tick(nullptr, false);
    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
    printf("PASS cycles=%ld checks=%ld writes=%ld pairs=%d nodes=%zu roots=%d maxrss_kib=%ld\n", cyc, checks, writes, NP,
           fld.nn, NR, ru.ru_maxrss);
    return 0;
}
