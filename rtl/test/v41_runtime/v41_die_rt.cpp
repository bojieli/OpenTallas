// W17 runtime composition of the adopted V4.1 TP-4 layer-die group (tools/v41_die_rt.py).
//
// Models (Verilator, each compiled once):
//   Vdie0..Vdie3  ot_v41_rt_die RANK 0..3: ot_chip_v41x_die FULL_SHAPE, X_ROM (spine in the core), attention cut
//   Vpq / Vpb     ot_v41_pair (FP8/FP4-only / BF16-capable; V41_RT: ROM and cfg words served by this host)
//   Vretn         ot_v41_retn (one return-tree node + its wire stages)
//   Vroot         ot_v41_ret_root (one per return region)
//   Vattn         ot_hdc_v41x_attn (full geometry, hierarchical build)
// Wiring (exactly ot_v41_field's): per die, NP pair slots of which the active ones are instantiated (an absent
// slot is a constant-0 leaf: the floorplan has no element there), R regions of 2*NP/R leaves, each a binary tree of
// ot_v41_retn into its root; root j's outputs are the die's rom_fr[69j +: 69]; the die's rom_fb is every pair's
// broadcast input.  The attention engine's inputs are the die's att_to bus, its outputs the att_from bus.
// Collective links: the W15 deterministic collective releases each record at a fixed latency; here each directed
// die pair is a delay line of that latency (UCIe in package: LAT_U, T1 board link: LAT_X cycles) carrying the
// record and the reverse-direction parity credits; the link accepts one record a cycle.
//
// Clocking: every model evaluates the rising edge with the inputs present before it; the host then copies
// outputs to inputs (no model sees a same-edge value), then evaluates clk low and settles the combinational
// die <-> attention paths by repeated copy / evaluate until nothing changes (bounded; reported).
// --wrong-edge: the field and attention models see the die's same-edge outputs (negative control).
//
//   v41_die_rt IMGROOT OUT [max_cycles] : IMGROOT/r<d>/ holds die d's images (ot_v41_rt_die +DIR) and its field
//   images (e<p>.words.hex, e<p>.cfg.hex, field.json: np, r, active pairs, bf16 pairs), and cfg.txt (the die's
//   configuration inputs: name value lines).  OUT receives vm<d>.hex (final vector memories) and a log.
#include "Vdie0.h"
#include "Vdie1.h"
#include "Vdie2.h"
#include "Vdie3.h"
#include "Vpq.h"
#include "Vpb.h"
#include "Vretn.h"
#include "Vroot.h"
#include "Vattn.h"
#include "svdpi.h"
#include "qwen_rt_matvec.hpp"   // RtPool
#include <array>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <deque>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <unordered_map>
#include <sys/resource.h>

// ------------------------------------------------------------------------------------------ host memories
struct PairMem { std::vector<std::array<uint32_t, 9>> rom[2]; std::vector<uint64_t> cfg; };
static PairMem* g_reg = nullptr;
static std::unordered_map<const void*, std::pair<PairMem*, int>> g_romscope;
static std::unordered_map<const void*, PairMem*> g_cfgscope;
extern "C" void v41rt_rom_register(const char* inst) {
    if (!g_reg) { printf("FATAL rom register outside construction\n"); exit(3); }
    // Verilator passes the string parameter space-padded (" b"): the second macro's suffix is its last character
    g_romscope[svGetScope()] = {g_reg, (inst && inst[0] && inst[strlen(inst) - 1] == 'b') ? 1 : 0};
}
extern "C" void v41rt_rom_read(int addr, svBitVecVal* q) {
    auto it = g_romscope.find(svGetScope());
    if (it == g_romscope.end()) { printf("FATAL rom scope\n"); exit(3); }
    const auto& v = it->second.first->rom[it->second.second];
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
extern "C" int v41rt_vm_word(int a);

// ------------------------------------------------------------------------------------------ bit helpers
template <class V> static uint64_t getb(const V& v, size_t pos, int n) {
    if constexpr (std::is_integral_v<V>) return (uint64_t(v) >> pos) & (n >= 64 ? ~0ull : ((1ull << n) - 1));
    else {
        uint64_t r = 0;
        for (int b = 0; b < n; ) {
            size_t w = (pos + b) / 32, o = (pos + b) % 32;
            int take = std::min(n - b, int(32 - o));
            r |= uint64_t((v[w] >> o) & (take == 32 ? 0xffffffffu : ((1u << take) - 1))) << b;
            b += take;
        }
        return r;
    }
}
template <class V> static void setb(V& v, size_t pos, int n, uint64_t x) {
    if constexpr (std::is_integral_v<V>) {
        uint64_t m = (n >= 64 ? ~0ull : ((1ull << n) - 1)) << pos;
        v = (V)((uint64_t(v) & ~m) | ((x << pos) & m));
    } else {
        for (int b = 0; b < n; ) {
            size_t w = (pos + b) / 32, o = (pos + b) % 32;
            int take = std::min(n - b, int(32 - o));
            uint32_t m = (take == 32 ? 0xffffffffu : ((1u << take) - 1)) << o;
            v[w] = (v[w] & ~m) | (uint32_t(x >> b << o) & m);
            b += take;
        }
    }
}
// copy nbits from src bit offset so to dst bit offset do (wide words)
template <class D, class S> static void copyb(D& d, size_t dofs, const S& s, size_t sofs, size_t n) {
    for (size_t b = 0; b < n; ) {
        int take = int(std::min<size_t>(32, n - b));
        setb(d, dofs + b, take, getb(s, sofs + b, take));
        b += take;
    }
}
template <class V> static bool vsame(const V& a, const V& b) {
    if constexpr (std::is_integral_v<V>) return a == b;
    else { for (size_t i = 0; i < sizeof(a) / 4; i++) if (a[i] != b[i]) return false; return true; }
}
static std::vector<std::string> split(const std::string& s) {
    std::istringstream is(s); std::vector<std::string> r; std::string t;
    while (is >> t) r.push_back(t);
    return r;
}

// ------------------------------------------------------------------------------------------ field of one die
struct Node { uint8_t v, e; uint32_t t, d; };
struct FieldMeta { int np = 0, r = 0; std::vector<int> active, bf; };
static FieldMeta load_meta(const std::string& f) {
    FieldMeta m; std::ifstream in(f); std::string line;
    while (std::getline(in, line)) {
        auto t = split(line);
        if (t.empty()) continue;
        if (t[0] == "np") m.np = std::stoi(t[1]);
        else if (t[0] == "r") m.r = std::stoi(t[1]);
        else if (t[0] == "active") for (size_t i = 1; i < t.size(); i++) m.active.push_back(std::stoi(t[i]));
        else if (t[0] == "bf16") for (size_t i = 1; i < t.size(); i++) m.bf.push_back(std::stoi(t[i]));
    }
    return m;
}
static void load_pair(PairMem& m, const std::string& dir, int p) {
    for (int mb = 0; mb < 2; mb++) {
        std::ifstream f(dir + "/e" + std::to_string(p) + (mb ? "b" : "") + ".words.hex");
        std::string line;
        while (std::getline(f, line)) {
            auto t = split(line);
            if (t.size() != 2) continue;
            size_t a = std::stoul(t[0], nullptr, 16);
            if (m.rom[mb].size() <= a) m.rom[mb].resize(a + 1, std::array<uint32_t, 9>{});
            std::array<uint32_t, 9> w{};
            const std::string& h = t[1];
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

template <class DIE> struct Field {
    FieldMeta meta;
    int NL, L, LR, LS;
    DIE& die;
    RtPool& pool;
    std::vector<PairMem> mem;
    std::vector<int> slot_kind, slot_idx;           // per pair slot: -1 absent, 0 pq, 1 pb
    std::vector<std::unique_ptr<Vpq>> pq;
    std::vector<std::unique_ptr<Vpb>> pb;
    std::vector<std::vector<std::unique_ptr<Vretn>>> nodes;
    std::vector<std::unique_ptr<Vroot>> roots;
    std::vector<int> act;                           // active slot list
    Field(DIE& d, RtPool& p, const std::string& dir, int die_id) : die(d), pool(p) {
        meta = load_meta(dir + "/field.txt");
        NL = 2 * meta.np; L = __builtin_ctz(NL); LR = __builtin_ctz(meta.r); LS = L - LR;
        slot_kind.assign(meta.np, -1); slot_idx.assign(meta.np, -1);
        std::vector<char> isbf(meta.np, 0);
        for (int b : meta.bf) isbf[b] = 1;
        mem.resize(meta.np);
        for (int s : meta.active) load_pair(mem[s], dir, s);
        int k = 0;
        for (int s : meta.active) {
            g_reg = &mem[s];
            std::string nm = "d" + std::to_string(die_id) + "p" + std::to_string(s);
            if (isbf[s]) { pb.emplace_back(new Vpb(pool.ctx(k % pool.size()), nm.c_str())); slot_kind[s] = 1; slot_idx[s] = int(pb.size()) - 1; pb.back()->eval(); }
            else { pq.emplace_back(new Vpq(pool.ctx(k % pool.size()), nm.c_str())); slot_kind[s] = 0; slot_idx[s] = int(pq.size()) - 1; pq.back()->eval(); }
            act.push_back(s); k++;
        }
        g_reg = nullptr;
        nodes.resize(LS);
        for (int l = 0; l < LS; l++)
            for (int g = 0; g < (NL >> (l + 1)); g++)
                nodes[l].emplace_back(new Vretn(pool.ctx((k++) % pool.size()), ("d" + std::to_string(die_id) + "n").c_str()));
        for (int g = 0; g < meta.r; g++)
            roots.emplace_back(new Vroot(pool.ctx((k++) % pool.size()), ("d" + std::to_string(die_id) + "r").c_str()));
    }
    template <class F> void each_pair(int s, F f) { if (slot_kind[s] == 1) f(*pb[slot_idx[s]]); else if (slot_kind[s] == 0) f(*pq[slot_idx[s]]); }
    size_t nmodels() const { size_t n = act.size() + roots.size(); for (auto& l : nodes) n += l.size(); return n; }
    void model_at(size_t i, uint8_t clk, uint8_t rst) {
        if (i < act.size()) { each_pair(act[i], [&](auto& m) { m.clk = clk; m.rst_n = rst; m.eval(); }); return; }
        i -= act.size();
        for (auto& l : nodes) { if (i < l.size()) { auto& n = *l[i]; n.clk = clk; n.rst_n = rst; n.eval(); return; } i -= l.size(); }
        auto& r = *roots[i]; r.clk = clk; r.rst_n = rst; r.eval();
    }
    Node leaf(int g, int m) {
        Node o{};
        if (slot_kind[g] < 0) return o;
        each_pair(g, [&](auto& x) {
            o.v = (x.pv >> m) & 1; o.e = (x.perr >> m) & 1;
            o.d = uint32_t(getb(x.pval, 32 * m, 32));
            uint32_t pos = uint32_t(getb(x.ppos, 3 * m, 3)), row = uint32_t(getb(x.prow, 16 * m, 16));
            uint32_t seg = uint32_t(getb(x.pseg, 5 * m, 5)), ns = uint32_t(getb(x.pnseg, 5 * m, 5));
            o.t = (pos << 29) | (row << 13) | (seg << 8) | ns;
        });
        return o;
    }
    Node level_out(int l, int g) {
        if (l == 0) return leaf(g >> 1, g & 1);
        auto& n = *nodes[l - 1][g];
        return Node{n.o_v, n.o_e, n.o_t, n.o_d};
    }
    // the die's broadcast bus -> every pair (bit layout: ot_v41_spine bc_in)
    template <class M> void bcast(M& m) {
        const auto& b = die.rom_fb;
        // fields from the LSB end (reverse of the concatenation order)
        constexpr int PHW = ROM_PHW;
        size_t bo = 0;
        auto at = [&](int n) { size_t p = bo; bo += n; return p; };
        size_t p_xb_d = at(1024), p_xb_u = at(32), p_xb_sv = at(4), p_xb_b = at(3), p_xb_v = at(1), p_xb_pos = at(3),
               p_xs_pos = at(3), p_xs_e1 = at(10), p_xs_q1 = at(256), p_xs_e0 = at(10), p_xs_q0 = at(256),
               p_xs_sv = at(2), p_xs_b = at(3), p_xs_p = at(8), p_xs_v = at(1), p_go_bf = at(1), p_go = at(1),
               p_np = at(3), p_ph = at(PHW), p_cfg = at(1);
        m.cfg_go = getb(b, p_cfg, 1); m.cfg_ph = getb(b, p_ph, PHW); m.cfg_np = getb(b, p_np, 3);
        m.go = getb(b, p_go, 1); m.go_bf = getb(b, p_go_bf, 1); m.xs_v = getb(b, p_xs_v, 1);
        m.xs_p = getb(b, p_xs_p, 8); m.xs_b = getb(b, p_xs_b, 3); m.xs_sv = getb(b, p_xs_sv, 2);
        copyb(m.xs_q0, 0, b, p_xs_q0, 256); m.xs_e0 = getb(b, p_xs_e0, 10);
        copyb(m.xs_q1, 0, b, p_xs_q1, 256); m.xs_e1 = getb(b, p_xs_e1, 10);
        m.xs_pos = getb(b, p_xs_pos, 3); m.xb_pos = getb(b, p_xb_pos, 3); m.xb_v = getb(b, p_xb_v, 1);
        m.xb_b = getb(b, p_xb_b, 3); m.xb_sv = getb(b, p_xb_sv, 4); m.xb_u = getb(b, p_xb_u, 32);
        copyb(m.xb_d, 0, b, p_xb_d, 1024);
    }
    void to_node(int l, int g) {
        auto& n = *nodes[l][g];
        Node a = level_out(l, 2 * g), b = level_out(l, 2 * g + 1);
        n.a_v = a.v; n.a_t = a.t; n.a_d = a.d; n.a_e = a.e; n.b_v = b.v; n.b_t = b.t; n.b_d = b.d; n.b_e = b.e;
    }
    void propagate() {
        pool.run(act.size(), [&](size_t i) { each_pair(act[i], [&](auto& m) { bcast(m); }); });
        for (int l = 0; l < LS; l++) {
            int n = NL >> (l + 1);
            pool.run(size_t(n), [&](size_t g) { to_node(l, int(g)); });
        }
        uint64_t f = 0;
        for (int g = 0; g < meta.r; g++) {
            auto& r = *roots[g];
            Node a = level_out(LS, g);
            r.i_v = a.v; r.i_t = a.t; r.i_d = a.d; r.i_e = a.e;
            // root j's outputs -> rom_fr[69j +: 69] = {v, row16, pos3, fp32, bf16, e}
            size_t o = size_t(69) * g;
            setb(die.rom_fr, o + 0, 1, r.r_e); setb(die.rom_fr, o + 1, 16, r.r_bf16); setb(die.rom_fr, o + 17, 32, r.r_fp32);
            setb(die.rom_fr, o + 49, 3, r.r_pos); setb(die.rom_fr, o + 52, 16, r.r_row); setb(die.rom_fr, o + 68, 1, r.r_v);
            f |= r.fault;
        }
        for (int s : act) each_pair(s, [&](auto& m) { f |= m.fault; });
        for (auto& l : nodes) for (auto& n : l) f |= n->fault;
        die.rom_ffault = f ? 1 : 0;
    }
};

// ------------------------------------------------------------------------------------------ one die
struct DieBase {
    virtual ~DieBase() {}
    virtual void set_inputs(uint8_t clk, uint8_t rst) = 0;
    virtual void eval() = 0;
    virtual void field_eval(size_t i, uint8_t clk, uint8_t rst) = 0;
    virtual size_t field_models() = 0;
    virtual void field_propagate() = 0;
    virtual bool att_propagate() = 0;       // die <-> attention buses; true if anything changed
    virtual void att_eval(uint8_t clk, uint8_t rst) = 0;
    virtual bool done() = 0;
    virtual uint32_t cycles() = 0;
    virtual uint32_t fault() = 0;
    virtual void cfg(const std::string& name, uint64_t v) = 0;
    virtual uint32_t vm_word(int a) = 0;
    // collective ports
    virtual uint8_t ucie_tx_v() = 0; virtual void ucie_tx(std::vector<uint32_t>& rec) = 0;
    virtual uint8_t bl_tx_v() = 0;   virtual void bl_tx(std::vector<uint32_t>& rec) = 0;
    virtual uint8_t ucie_cr() = 0;   virtual uint8_t bl_cr() = 0;
    virtual void set_links(uint8_t u_v, const std::vector<uint32_t>& u_rec, uint8_t u_cr,
                           uint8_t b_v, const std::vector<uint32_t>& b_rec0, const std::vector<uint32_t>& b_rec1,
                           uint8_t b_cr) = 0;
    virtual void start(uint8_t s, uint32_t tok, uint32_t pos, uint32_t user) = 0;
    virtual void prime(uint8_t v, uint32_t row) = 0;
    virtual bool prime_ready() = 0;
    std::vector<uint32_t> primes;
};
template <class DIE> struct Die : DieBase {
    VerilatedContext ctx;
    std::unique_ptr<DIE> d;
    std::unique_ptr<Vattn> a;
    std::unique_ptr<Field<DIE>> f;
    int id;
    Die(RtPool& pool, const std::string& dir, int id_, int argc, const char** argv) : id(id_) {
        ctx.randReset(0); ctx.commandArgs(argc, argv);
        d.reset(new DIE(&ctx, ("die" + std::to_string(id)).c_str()));
        a.reset(new Vattn(&ctx, ("att" + std::to_string(id)).c_str()));
        f.reset(new Field<DIE>(*d, pool, dir, id));
    }
    void set_inputs(uint8_t clk, uint8_t rst) override { d->clk = clk; d->rst_n = rst; a->clk = clk; a->rst_n = rst; }
    void eval() override { d->eval(); }
    void field_eval(size_t i, uint8_t clk, uint8_t rst) override { f->model_at(i, clk, rst); }
    size_t field_models() override { return f->nmodels(); }
    void field_propagate() override { f->propagate(); }
    void att_eval(uint8_t clk, uint8_t rst) override { a->clk = clk; a->rst_n = rst; a->eval(); }
    bool att_propagate() override {
        // att_to = {job_v, T16, q_v, q_w, kv_v, kv_m, kv_w, sc_cr, p_v, p_w, pv_cr} (MSB first)
        const auto& t = d->att_to;
        size_t o = 0;
        auto at = [&](int n) { size_t p = o; o += n; return p; };
        size_t p_pv_cr = at(1), p_p_w = at(32 * 16), p_p_v = at(1), p_sc_cr = at(1), p_kv_w = at(4 * 16 * 265),
               p_kv_m = at(4), p_kv_v = at(1), p_q_w = at(512 * 16), p_q_v = at(1), p_T = at(16), p_job_v = at(1);
        bool ch = false;
        auto s1 = [&](auto& dst, size_t p, int n) { uint64_t v = getb(t, p, n); if (uint64_t(dst) != v) { dst = v; ch = true; } };
        s1(a->job_v, p_job_v, 1); s1(a->job_t, p_T, 16); s1(a->q_v, p_q_v, 1); s1(a->kv_v, p_kv_v, 1);
        s1(a->kv_m, p_kv_m, 4); s1(a->sc_cr, p_sc_cr, 1); s1(a->p_v, p_p_v, 1); s1(a->pv_cr, p_pv_cr, 1);
        { auto old = a->q_w; copyb(a->q_w, 0, t, p_q_w, 512 * 16); ch |= !vsame(old, a->q_w); }
        { auto old = a->kv_w; copyb(a->kv_w, 0, t, p_kv_w, 4 * 16 * 265); ch |= !vsame(old, a->kv_w); }
        { auto old = a->p_w; copyb(a->p_w, 0, t, p_p_w, 32 * 16); ch |= !vsame(old, a->p_w); }
        // att_from = {job_ready, q_ready, kv_ready, p_ready, sc_row, sc_m, sc_y, sc_f, sc_v, pv_v, pv_c, pv_y, pv_f}
        auto old = d->att_from;
        auto& fr = d->att_from;
        size_t q = 0;
        auto put = [&](int n) { size_t p = q; q += n; return p; };
        size_t p_pv_f = put(4 * 16 * 16), p_pv_y = put(4 * 16 * 16 * 32), p_pv_c = put(8), p_pvv = put(1), p_scv = put(1),
               p_sc_f = put(4 * 16), p_sc_y = put(4 * 16 * 32), p_sc_m = put(4), p_sc_row = put(16), p_pr = put(1),
               p_kr = put(1), p_qr = put(1), p_jr = put(1);
        copyb(fr, p_pv_f, a->pv_f, 0, 4 * 16 * 16); copyb(fr, p_pv_y, a->pv_y, 0, 4 * 16 * 16 * 32);
        setb(fr, p_pv_c, 8, a->pv_c); setb(fr, p_pvv, 1, a->pv_v); setb(fr, p_scv, 1, a->sc_v);
        copyb(fr, p_sc_f, a->sc_f, 0, 4 * 16); copyb(fr, p_sc_y, a->sc_y, 0, 4 * 16 * 32);
        setb(fr, p_sc_m, 4, a->sc_m); setb(fr, p_sc_row, 16, a->sc_row); setb(fr, p_pr, 1, a->p_ready);
        setb(fr, p_kr, 1, a->kv_ready); setb(fr, p_qr, 1, a->q_ready); setb(fr, p_jr, 1, a->job_ready);
        ch |= !vsame(old, fr);
        return ch;
    }
    bool done() override { return d->done; }
    uint32_t cycles() override { return d->cycles; }
    uint32_t fault() override { return d->fault; }
    void cfg(const std::string& n, uint64_t v) override {
        if (n == "cfg_ik_base") d->cfg_ik_base = v;
        else if (n == "window_region_valid") d->window_region_valid = v;
        else if (n == "window_region_base") d->window_region_base = v;
        else if (n == "window_region_count") d->window_region_count = v;
        else if (n == "window_prime_user") d->window_prime_user = v;
        else if (n == "rope_table_present") d->rope_table_present = v;
        else if (n.rfind("rope_reserved_end", 0) == 0) setb(d->rope_reserved_end, 30 * (n.back() - '0'), 30, v);
        else if (n.rfind("rope_plain_base", 0) == 0) setb(d->rope_plain_base, 30 * (n.back() - '0'), 30, v);
        else if (n.rfind("rope_yarn_base", 0) == 0) setb(d->rope_yarn_base, 30 * (n.back() - '0'), 30, v);
        else { printf("FATAL unknown cfg %s\n", n.c_str()); exit(2); }
    }
    uint32_t vm_word(int adr) override {
        svSetScope(svGetScopeFromName(("die" + std::to_string(id) + ".ot_v41_rt_die").c_str()));
        return uint32_t(v41rt_vm_word(adr));
    }
    uint8_t ucie_tx_v() override { return d->ucie_ctx_valid; }
    void ucie_tx(std::vector<uint32_t>& r) override { r.assign(std::begin(d->ucie_ctx_rec), std::end(d->ucie_ctx_rec)); }
    uint8_t bl_tx_v() override { return d->bl_ctx_valid; }
    void bl_tx(std::vector<uint32_t>& r) override { r.assign(std::begin(d->bl_ctx_rec), std::end(d->bl_ctx_rec)); }
    uint8_t ucie_cr() override { return d->ucie_ccr_out; }
    uint8_t bl_cr() override { return d->bl_ccr_out; }
    void set_links(uint8_t u_v, const std::vector<uint32_t>& u_rec, uint8_t u_cr, uint8_t b_v,
                   const std::vector<uint32_t>& b0, const std::vector<uint32_t>& b1, uint8_t b_cr) override {
        d->ucie_ctx_ready = 1; d->bl_ctx_ready = 3;
        d->ucie_crx_valid = u_v; d->ucie_ccr_in = u_cr;
        d->bl_crx_valid = b_v; d->bl_ccr_in = b_cr;
        const int PW = CL_PW_BITS;
        for (int b = 0; b < PW; b += 32) {
            int n = std::min(32, PW - b);
            setb(d->ucie_crx_rec, b, n, getb(u_rec, b, n));
            setb(d->bl_crx_rec, b, n, getb(b0, b, n));
            setb(d->bl_crx_rec, PW + b, n, getb(b1, b, n));
        }
    }
    void prime(uint8_t v, uint32_t row) override { d->window_prime_v = v; d->window_prime_row = row; }
    bool prime_ready() override { return d->window_prime_ready; }
    void start(uint8_t s, uint32_t tok, uint32_t pos, uint32_t user) override {
        d->start = s; d->token = tok; d->pos = pos; d->user = user;
    }
};

// ------------------------------------------------------------------------------------------ links
struct Line { int lat; std::deque<std::pair<long, std::pair<uint8_t, std::vector<uint32_t>>>> q; };

int main(int argc, char** argv) {
    if (argc < 3) { printf("usage: v41_die_rt IMGROOT OUT [max_cycles] [--wrong-edge]\n"); return 2; }
    std::string root = argv[1], out = argv[2];
    long maxc = (argc > 3 && argv[3][0] != '-') ? atol(argv[3]) : 2000000;
    bool wrong = false;
    for (int i = 3; i < argc; i++) if (!strcmp(argv[i], "--wrong-edge")) wrong = true;
    int threads = 16;
    if (const char* t = getenv("RT_THREADS")) threads = atoi(t);
    RtPool pool(threads);
    std::vector<std::unique_ptr<DieBase>> dies;
    std::vector<std::string> plus(4), plus2(4);
    std::vector<std::vector<const char*>> av(4);
    for (int d = 0; d < 4; d++) {
        plus[d] = "+DIR=" + root + "/r" + std::to_string(d);
        plus2[d] = "+OT_ROM_DIR=" + root + "/r" + std::to_string(d);   // the spine's phase / stream / key ROMs
        av[d] = {"v41_die_rt", plus[d].c_str(), plus2[d].c_str()};
    }
    auto t0 = std::chrono::steady_clock::now();
    dies.emplace_back(new Die<Vdie0>(pool, root + "/r0", 0, 3, av[0].data()));
    dies.emplace_back(new Die<Vdie1>(pool, root + "/r1", 1, 3, av[1].data()));
    dies.emplace_back(new Die<Vdie2>(pool, root + "/r2", 2, 3, av[2].data()));
    dies.emplace_back(new Die<Vdie3>(pool, root + "/r3", 3, 3, av[3].data()));
    uint32_t tok = 0, pos = 0, user = 0;
    for (int d = 0; d < 4; d++) {
        std::ifstream f(root + "/r" + std::to_string(d) + "/cfg.txt"); std::string line;
        while (std::getline(f, line)) {
            auto t = split(line);
            if (t.size() != 2) continue;
            uint64_t v = std::stoull(t[1], nullptr, 0);
            if (t[0] == "token") tok = v; else if (t[0] == "pos") pos = v; else if (t[0] == "user") user = v;
            else dies[d]->cfg(t[0], v);
        }
    }
    for (int d = 0; d < 4; d++) {
        std::ifstream f(root + "/r" + std::to_string(d) + "/prime.txt"); std::string line;
        while (std::getline(f, line)) if (!line.empty()) dies[d]->primes.push_back(uint32_t(std::stoul(line, nullptr, 0)));
    }
    double setup_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    printf("SETUP %.1f s\n", setup_s); fflush(stdout);
    // links: die d's package peer d^1 over UCIe; partner package dies 2*(1-pkg)+J over T1
    int LAT_U = 48, LAT_X = 177;
    if (const char* s = getenv("RT_LAT_U")) LAT_U = atoi(s);
    if (const char* s = getenv("RT_LAT_X")) LAT_X = atoi(s);
    // per destination die: its UCIe receive line and its two T1 receive lines (index J = source rank % 2)
    struct Rx { Line u, x[2]; };
    std::vector<Rx> rx(4);
    for (auto& r : rx) { r.u.lat = LAT_U; r.x[0].lat = LAT_X; r.x[1].lat = LAT_X; }
    long cyc = 0;
    uint8_t rst = 0;
    int max_settle = 0;
    std::vector<uint32_t> rec;
    auto link_step = [&]() {
        // senders' outputs after the edge enter the lines; deliveries due now drive receivers' inputs
        for (int s = 0; s < 4; s++) {
            int peer = s ^ 1, pkg = s / 2;
            if (dies[s]->ucie_tx_v() || dies[s]->ucie_cr()) {
                dies[s]->ucie_tx(rec);
                rx[peer].u.q.push_back({cyc + LAT_U, {uint8_t(dies[s]->ucie_tx_v() | (dies[s]->ucie_cr() << 1)), rec}});
            }
            uint8_t bv = dies[s]->bl_tx_v(), bc = dies[s]->bl_cr();
            for (int J = 0; J < 2; J++) {
                int dst = 2 * (1 - pkg) + J;
                uint8_t v = (bv >> J) & 1, c = (bc >> (2 * J)) & 3;
                if (v || c) { dies[s]->bl_tx(rec); rx[dst].x[s % 2].q.push_back({cyc + LAT_X, {uint8_t(v | (c << 1)), rec}}); }
            }
        }
        static const std::vector<uint32_t> zero(64, 0);
        for (int d = 0; d < 4; d++) {
            uint8_t uv = 0, ucr = 0, bv = 0, bcr = 0;
            std::vector<uint32_t> ur = zero, b0 = zero, b1 = zero;
            if (!rx[d].u.q.empty() && rx[d].u.q.front().first <= cyc) {
                auto& e = rx[d].u.q.front().second; uv = e.first & 1; ucr = e.first >> 1; ur = e.second; ur.resize(64, 0);
                rx[d].u.q.pop_front();
            }
            for (int J = 0; J < 2; J++)
                if (!rx[d].x[J].q.empty() && rx[d].x[J].q.front().first <= cyc) {
                    auto& e = rx[d].x[J].q.front().second;
                    bv |= (e.first & 1) << J; bcr |= (e.first >> 1) << (2 * J);
                    (J ? b1 : b0) = e.second; (J ? b1 : b0).resize(64, 0);
                    rx[d].x[J].q.pop_front();
                }
            dies[d]->set_links(uv, ur, ucr, bv, b0, b1, bcr);
        }
    };
    auto settle = [&]() {
        int n = 0;
        for (;; n++) {
            if (n > 64) { printf("FATAL settle did not converge\n"); exit(4); }
            bool ch = false;
            for (auto& d : dies) { d->eval(); ch |= d->att_propagate(); }
            if (!ch) break;
            for (auto& d : dies) d->att_eval(0, rst);
        }
        max_settle = std::max(max_settle, n + 1);
    };
    auto tick = [&]() {
        for (auto& d : dies) d->set_inputs(1, rst);
        if (!wrong) {
            for (auto& d : dies) { d->eval(); d->att_eval(1, rst); }
            size_t tot = 0; std::vector<size_t> base;
            for (auto& d : dies) { base.push_back(tot); tot += d->field_models(); }
            pool.run(tot, [&](size_t i) {
                int k = 3; while (base[k] > i) k--;
                dies[k]->field_eval(i - base[k], 1, rst);
            });
            for (auto& d : dies) { d->field_propagate(); d->att_propagate(); }
        } else {
            for (auto& d : dies) { d->eval(); d->field_propagate(); d->att_propagate(); d->att_eval(1, rst); }
            size_t tot = 0; std::vector<size_t> base;
            for (auto& d : dies) { base.push_back(tot); tot += d->field_models(); }
            pool.run(tot, [&](size_t i) { int k = 3; while (base[k] > i) k--; dies[k]->field_eval(i - base[k], 1, rst); });
            for (auto& d : dies) d->field_propagate();
        }
        link_step();
        for (auto& d : dies) d->set_inputs(0, rst);
        size_t tot = 0; std::vector<size_t> base;
        for (auto& d : dies) { base.push_back(tot); tot += d->field_models(); }
        pool.run(tot, [&](size_t i) { int k = 3; while (base[k] > i) k--; dies[k]->field_eval(i - base[k], 0, rst); });
        for (auto& d : dies) d->att_eval(0, rst);
        settle();
        cyc++;
    };
    for (int i = 0; i < 8; i++) tick();
    rst = 1;
    for (int i = 0; i < 8; i++) tick();
    // window priming (the live-chain bench's sequence): one row a handshake, every die in parallel
    {
        std::vector<size_t> k(4, 0);
        long pstart = cyc;
        for (;;) {
            bool left = false;
            for (int d = 0; d < 4; d++) {
                if (k[d] < dies[d]->primes.size()) { dies[d]->prime(1, dies[d]->primes[k[d]]); left = true; }
                else dies[d]->prime(0, 0);
            }
            if (!left) break;
            std::vector<bool> rdy(4);
            for (int d = 0; d < 4; d++) rdy[d] = dies[d]->prime_ready();
            tick();
            for (int d = 0; d < 4; d++) if (k[d] < dies[d]->primes.size() && rdy[d]) k[d]++;
            if (cyc - pstart > 200000) { printf("FATAL window priming stalled\n"); return 5; }
        }
        for (int d = 0; d < 4; d++) dies[d]->prime(0, 0);
        printf("PRIMED cycles=%ld\n", cyc - pstart); fflush(stdout);
        for (int i = 0; i < 64; i++) tick();
    }
    for (auto& d : dies) d->start(1, tok, pos, user);
    tick();
    for (auto& d : dies) d->start(0, tok, pos, user);
    auto t1 = std::chrono::steady_clock::now();
    std::vector<long> done_at(4, -1);
    while (cyc < maxc) {
        tick();
        for (int d = 0; d < 4; d++) if (done_at[d] < 0 && dies[d]->done()) {
            done_at[d] = cyc;
            printf("DONE die=%d cyc=%ld core_cycles=%u fault=%02x\n", d, cyc, dies[d]->cycles(), dies[d]->fault()); fflush(stdout);
        }
        bool all = true; for (long x : done_at) all &= x >= 0;
        if (all) break;
        for (int d = 0; d < 4; d++) if (dies[d]->fault()) { printf("FAULT die=%d cyc=%ld code=%02x\n", d, cyc, dies[d]->fault()); fflush(stdout); }
        if (cyc % 1000 == 0) { printf("CYC %ld\n", cyc); fflush(stdout); }
    }
    double run_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t1).count();
    for (int d = 0; d < 4; d++) {
        FILE* fo = fopen((out + "/vm" + std::to_string(d) + ".hex").c_str(), "w");
        for (int a = 0; a < (1 << 19); a++) fprintf(fo, "%08x\n", dies[d]->vm_word(a));
        fclose(fo);
    }
    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
    bool all = true; for (long x : done_at) all &= x >= 0;
    printf("%s cycles=%ld run_s=%.1f setup_s=%.1f max_settle=%d maxrss_kib=%ld\n", all ? "END" : "TIMEOUT", cyc, run_s,
           setup_s, max_settle, ru.ru_maxrss);
    return all ? 0 : 1;
}
