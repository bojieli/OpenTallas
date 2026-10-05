// Simulation-only runtime composition of ot_hdc_matvec from separately
// compiled Verilator models (see ot_qwen_rt_matvec_seq.sv for the contract).
//
// T      : a top that exposes the sequencer's b_* outputs and x_* inputs
//          (Vot_qwen_rt_matvec_seq in the equivalence gate, the die top in
//          the connected run).
// Slice  : Vot_qwen_rt_matvec_slice (G instances, gi = 0..G-1)
// CellA/H: ot_qwen_rt_tree_cell ADDS=1 / ADDS=0
// AmaxN  : ot_qwen_rt_amax_tree with LEVELS=N (one class per used N)
//
// Clocking.  The host keeps every model's inputs at the values present before
// an edge, raises clk on every model, evaluates each once, and only then copies
// the new outputs to the consumers (then settles combinational paths).  No
// model ever sees a value registered on the same edge.  Memory responses are
// applied by the caller after the edge through the same discipline.
#pragma once
#include <verilated.h>
#include <atomic>
#include <condition_variable>
#include <mutex>
#include <cstdint>
#include <functional>
#include <memory>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <algorithm>
#include <vector>

template <class A> static inline bool rt_set(A& d, const A& s) {
    if (d != s) { d = s; return true; }
    return false;
}

// Fixed-partition worker pool: task i always runs on worker i % n so that a
// model is evaluated by exactly one thread, with its own VerilatedContext.
class RtPool {
  public:
    explicit RtPool(int n) : n_(n) {
        for (int w = 0; w < n; w++) {
            ctx_.emplace_back(new VerilatedContext);
            ctx_.back()->randReset(0);
            th_.emplace_back([this, w] { loop(w); });
        }
    }
    ~RtPool() {
        { std::lock_guard<std::mutex> l(m_); stop_ = true; gen_++; }
        cv_.notify_all();
        for (auto& t : th_) t.join();
    }
    int size() const { return n_; }
    VerilatedContext* ctx(int w) { return ctx_[w].get(); }
    // run f(i) for i in [0, count) with static partition i % n (blocking; no spinning)
    void run(size_t count, const std::function<void(size_t)>& f) {
        {
            std::lock_guard<std::mutex> l(m_);
            count_ = count; f_ = &f; left_ = n_; gen_++;
        }
        cv_.notify_all();
        std::unique_lock<std::mutex> l(m_);
        done_.wait(l, [&] { return left_ == 0; });
    }
  private:
    void loop(int w) {
        uint64_t seen = 0;
        for (;;) {
            size_t count; const std::function<void(size_t)>* f;
            {
                std::unique_lock<std::mutex> l(m_);
                cv_.wait(l, [&] { return gen_ != seen; });
                seen = gen_;
                if (stop_) return;
                count = count_; f = f_;
            }
            for (size_t i = w; i < count; i += n_) (*f)(i);
            {
                std::lock_guard<std::mutex> l(m_);
                if (--left_ == 0) done_.notify_one();
            }
        }
    }
    int n_;
    std::mutex m_;
    std::condition_variable cv_, done_;
    std::vector<std::unique_ptr<VerilatedContext>> ctx_;
    std::vector<std::thread> th_;
    bool stop_ = false;
    uint64_t gen_ = 0;
    int left_ = 0;
    size_t count_ = 0;
    const std::function<void(size_t)>* f_ = nullptr;
};

template <class T, class Slice, class CellA, class AmaxLo, class AmaxHi>
struct RtMatvec {
    // Upper argmax: U = log2ceil(G) levels above a group node, built as a
    // first stage of AmaxLo (LO levels) instances and an optional second
    // stage of one AmaxHi (U - LO levels) instance.  LO = U when U <= 7.
    //
    // Split-tree positions that own a pair (q < G >> lv) are Verilated
    // ot_qwen_rt_tree_cell ADDS=1 models.  Held-only positions (the g_rest
    // region: ot_hdc_delay D=TA=3 without reset, then the lq register) are
    // a native four-register shift in the host, updated at the same edge from
    // pre-edge values.  The equivalence gate covers this form too.
    using Vec = std::remove_reference_t<decltype(std::declval<Slice&>().sum)>;
    struct Hold { Vec line[3]; Vec lq; };
    int G, LG, LO, HI;
    T& top;
    RtPool& pool;
    std::vector<std::unique_ptr<Slice>> s;
    std::vector<std::unique_ptr<CellA>> ca;   // index lv*G+q if adds
    std::vector<Hold> hold;                   // index lv*G+q if !adds
    std::vector<uint8_t> adds;                // [lv][q]
    std::vector<size_t> addidx;               // list of lv*G+q with adds
    std::vector<std::unique_ptr<AmaxLo>> alo;
    std::unique_ptr<AmaxHi> ahi;
    std::function<uint8_t()> rst;             // reset seen by the engine
    std::vector<uint8_t> dirty;               // slices, add cells (by addidx), alo, ahi
    long evals = 0;

    RtMatvec(T& t, RtPool& p, int groups, int lo_levels, std::function<uint8_t()> r)
        : G(groups), top(t), pool(p), rst(std::move(r)) {
        LG = 0; while ((1 << LG) < G) LG++;
        LO = lo_levels; HI = LG - LO;
        if (LO < 1 || HI < 0) throw std::runtime_error("amax split");
        for (int g = 0; g < G; g++) {
            s.emplace_back(new Slice(pool.ctx(g % pool.size()), "s"));
            s.back()->gi = g;
        }
        ca.resize(size_t(LG + 1) * G); hold.resize(size_t(LG + 1) * G); adds.resize(size_t(LG + 1) * G);
        for (int lv = 1; lv <= LG; lv++)
            for (int q = 0; q < G; q++) {
                size_t i = size_t(lv) * G + q;
                adds[i] = q < (G >> lv);
                if (adds[i]) {
                    ca[i].reset(new CellA(pool.ctx(addidx.size() % pool.size()), "c"));
                    addidx.push_back(i);
                }
            }
        for (auto& h : hold) { for (auto& l : h.line) zero(l); zero(h.lq); }
        int nlo = 1 << HI;
        for (int i = 0; i < nlo; i++) alo.emplace_back(new AmaxLo(pool.ctx(i % pool.size()), "a"));
        if (HI > 0) ahi.reset(new AmaxHi(pool.ctx(0), "A"));
        dirty.assign(s.size() + addidx.size() + alo.size() + 1, 1);
        nthr_ = pool.size();
        red_.assign(size_t(nthr_) * 8, 0);
    }

    // split-tree output of level lv (lv >= 1), position q
    const Vec& cell_y(int lv, int q) const {
        size_t i = size_t(lv) * G + q;
        return adds[i] ? ca[i]->y : hold[i].lq;
    }
    const Vec& prev_out(int lv, int p) const { return lv == 1 ? s[p]->sum : cell_y(lv - 1, p); }

    void set_clk(uint8_t c) {
        if (clk_known_ && c == clk_) return;   // unchanged clock: nothing to re-evaluate
        clk_known_ = true; clk_ = c;
        for (auto& p : s) p->clk = c;
        for (size_t i : addidx) ca[i]->clk = c;
        for (auto& a : alo) a->clk = c;
        if (ahi) ahi->clk = c;
        std::fill(dirty.begin(), dirty.end(), 1);
    }

    // The host wrote model inputs directly (memory responses): re-evaluate all.
    void mark_all() { std::fill(dirty.begin(), dirty.end(), 1); }

    // Evaluate the models whose inputs (or clock) changed since their last
    // evaluation; an evaluation with unchanged inputs is a no-op.
    void eval_models(bool all = false) {
        size_t ns = s.size(), na = addidx.size(), nl = alo.size();
        if (!all && std::find(dirty.begin(), dirty.end(), 1) == dirty.end()) return;
        evaluated_ = true;
        pool.run(ns + na + nl, [&](size_t i) {
            if (!all && !dirty[i]) return;
            dirty[i] = 0;
            if (i < ns) s[i]->eval();
            else if (i < ns + na) ca[addidx[i - ns]]->eval();
            else alo[i - ns - na]->eval();
        });
        if (ahi && (all || dirty.back())) { ahi->eval(); dirty.back() = 0; }
    }

    // Rising edge: native held positions shift using pre-edge values (top
    // level first, so each reads the level below before it moves), then every
    // Verilated model evaluates with its pre-edge inputs.
    void eval_edge() {
        evaluated_ = true;
        for (int lv = LG; lv >= 1; lv--) {
            pool.run(size_t(G), [&](size_t q) {
                size_t i = size_t(lv) * G + q;
                if (adds[i]) return;
                Hold& h = hold[i];
                h.lq = h.line[2]; h.line[2] = h.line[1]; h.line[1] = h.line[0]; h.line[0] = prev_out(lv, int(q));
            });
        }
        eval_models(true);
    }

    // Copy producer outputs to consumer inputs; returns true if anything moved.
    bool propagate() {
        // Fast path: no engine model evaluated since the last propagation and
        // the sequencer's broadcast and reset unchanged -> no wire can move.
        {
            bool same = !evaluated_ && have_shadow_;
            same &= !rt_set(sh_.b_active, top.b_active); same &= !rt_set(sh_.b_cur, top.b_cur);
            same &= !rt_set(sh_.b_split_r, top.b_split_r); same &= !rt_set(sh_.b_ts_r, top.b_ts_r);
            same &= !rt_set(sh_.b_wcs_r, top.b_wcs_r); same &= !rt_set(sh_.b_xc, top.b_xc);
            same &= !rt_set(sh_.b_xcs_r, top.b_xcs_r); same &= !rt_set(sh_.b_wsrc_r, top.b_wsrc_r);
            same &= !rt_set(sh_.b_k, top.b_k); same &= !rt_set(sh_.b_ktot_r, top.b_ktot_r);
            same &= !rt_set(sh_.b_s1b_wsrc, top.b_s1b_wsrc); same &= !rt_set(sh_.b_s2_round, top.b_s2_round);
            same &= !rt_set(sh_.b_s3_v, top.b_s3_v); same &= !rt_set(sh_.b_fl_first4, top.b_fl_first4);
            same &= !rt_set(sh_.b_vline5, top.b_vline5); same &= !rt_set(sh_.b_pre_v, top.b_pre_v);
            same &= !rt_set(sh_.b_pre, top.b_pre); same &= !rt_set(sh_.b_raw_v, top.b_raw_v);
            same &= !rt_set(sh_.b_raw, top.b_raw); same &= !rt_set(sh_.b_r_v, top.b_r_v);
            same &= !rt_set(sh_.b_r, top.b_r);
            same &= !rt_set(sh_.b_reduce_valid, top.b_reduce_valid);
            same &= !rt_set(sh_.b_reduce_select, top.b_reduce_select);
            uint8_t r0 = rst(); same &= !rt_set(sh_rst_, r0);
            have_shadow_ = true;
            if (same) return false;
            evaluated_ = false;
        }
        std::atomic<bool> any{false};
        uint8_t r = rst();
        const uint32_t rv = top.b_reduce_valid, rs = top.b_reduce_select;
        size_t ns = s.size(), na = addidx.size();
        std::fill(red_.begin(), red_.end(), 0);
        pool.run(ns + na, [&](size_t i) {
            bool ch_ = false;
            uint8_t* red = &red_[(i % nthr_) * 8];
            if (i < ns) {
                Slice& x = *s[i];
                ch_ |= rt_set(x.rst_n, r);
                ch_ |= rt_set(x.b_active, top.b_active); ch_ |= rt_set(x.b_cur, top.b_cur);
                ch_ |= rt_set(x.b_split_r, top.b_split_r); ch_ |= rt_set(x.b_ts_r, top.b_ts_r);
                ch_ |= rt_set(x.b_wcs_r, top.b_wcs_r); ch_ |= rt_set(x.b_xc, top.b_xc);
                ch_ |= rt_set(x.b_xcs_r, top.b_xcs_r); ch_ |= rt_set(x.b_wsrc_r, top.b_wsrc_r);
                ch_ |= rt_set(x.b_k, top.b_k); ch_ |= rt_set(x.b_ktot_r, top.b_ktot_r);
                ch_ |= rt_set(x.b_s1b_wsrc, top.b_s1b_wsrc); ch_ |= rt_set(x.b_s2_round, top.b_s2_round);
                ch_ |= rt_set(x.b_s3_v, top.b_s3_v); ch_ |= rt_set(x.b_fl_first4, top.b_fl_first4);
                ch_ |= rt_set(x.b_vline5, top.b_vline5); ch_ |= rt_set(x.b_pre_v, top.b_pre_v);
                ch_ |= rt_set(x.b_pre, top.b_pre); ch_ |= rt_set(x.b_raw_v, top.b_raw_v);
                ch_ |= rt_set(x.b_raw, top.b_raw); ch_ |= rt_set(x.b_r_v, top.b_r_v);
                ch_ |= rt_set(x.b_r, top.b_r);
                if (LG > 0) ch_ |= rt_set(x.raw_res, cell_y(LG, int(i)));
                else ch_ |= rt_set(x.raw_res, x.sum);
                red[0] |= x.pre_scale_active; red[1] |= x.fault_q; red[2] |= x.scale_fault;
            } else {
                size_t j = addidx[i - ns];
                int lv = int(j / G), q = int(j % G);
                uint8_t v = (rv >> (lv - 1)) & 1, sl = (rs >> (lv - 1)) & 1;
                CellA& c = *ca[j];
                ch_ |= rt_set(c.rst_n, r); ch_ |= rt_set(c.v, v); ch_ |= rt_set(c.sel, sl);
                ch_ |= rt_set(c.h, prev_out(lv, q)); ch_ |= rt_set(c.a, prev_out(lv, 2 * q));
                ch_ |= rt_set(c.b, prev_out(lv, 2 * q + 1));
                red[3] |= c.fault;
            }
            if (ch_) { dirty[i] = 1; any.store(true, std::memory_order_relaxed); }
        });
        // argmax tree inputs (pad groups are constant zero)
        const int CW = cw_bits();
        int per = 1 << LO;
        pool.run(alo.size(), [&](size_t a) {
            std::remove_reference_t<decltype(alo[a]->x)> nx;
            for (auto& w : nx.m_storage) w = 0;
            for (int e = 0; e < per; e++) {
                int g = int(a) * per + e;
                if (g < G) put_bits(nx.m_storage, size_t(e) * CW, CW, uint64_t(s[g]->amax_node));
            }
            if (rt_set(alo[a]->x, nx)) { dirty[ns + na + a] = 1; any.store(true, std::memory_order_relaxed); }
        });
        uint64_t topnode;
        if (ahi) {
            std::remove_reference_t<decltype(ahi->x)> nx;
            for (auto& w : nx.m_storage) w = 0;
            for (size_t a = 0; a < alo.size(); a++) put_bits(nx.m_storage, a * CW, CW, uint64_t(alo[a]->y));
            if (rt_set(ahi->x, nx)) { dirty.back() = 1; any = true; }
            topnode = ahi->y;
        } else {
            topnode = alo[0]->y;
        }
        uint8_t red[4] = {0, 0, 0, 0};
        for (int w = 0; w < nthr_; w++) for (int k = 0; k < 4; k++) red[k] |= red_[w * 8 + k];
        bool c2 = false;
        c2 |= rt_set(top.x_scale_any, red[0]); c2 |= rt_set(top.x_group_fault_q, red[1]);
        c2 |= rt_set(top.x_scale_fault, red[2]); c2 |= rt_set(top.x_tfault, red[3]);
        c2 |= rt_set(top.x_top, (std::remove_reference_t<decltype(top.x_top)>)topnode);
        return any || c2;
    }

    int cw_bits() const { return 1 + 32 + nw_; }
    void set_nw(int nw) { nw_ = nw; }

  private:
    struct Shadow {
#define RT_SH(f) std::remove_cv_t<std::remove_reference_t<decltype(std::declval<T&>().f)>> f{};
        RT_SH(b_active) RT_SH(b_cur) RT_SH(b_split_r) RT_SH(b_ts_r) RT_SH(b_wcs_r) RT_SH(b_xc) RT_SH(b_xcs_r)
        RT_SH(b_wsrc_r) RT_SH(b_k) RT_SH(b_ktot_r) RT_SH(b_s1b_wsrc) RT_SH(b_s2_round) RT_SH(b_s3_v)
        RT_SH(b_fl_first4) RT_SH(b_vline5) RT_SH(b_pre_v) RT_SH(b_pre) RT_SH(b_raw_v) RT_SH(b_raw) RT_SH(b_r_v)
        RT_SH(b_r) RT_SH(b_reduce_valid) RT_SH(b_reduce_select)
#undef RT_SH
    } sh_;
    uint8_t sh_rst_ = 0, clk_ = 0;
    bool have_shadow_ = false, evaluated_ = true, clk_known_ = false;
    int nw_ = 16, nthr_ = 1;
    std::vector<uint8_t> red_;
    static void zero(Vec& v) { for (auto& w : v.m_storage) w = 0; }
    template <class Arr> static void put_bits(Arr& w, size_t pos, int n, uint64_t v) {
        if (n < 64) v &= (1ull << n) - 1;
        size_t word = pos / 32, off = pos % 32;
        w[word] |= uint32_t(v << off);
        uint64_t rest = off ? (v >> (32 - off)) : (v >> 32);
        size_t k = word + 1;
        while (rest && k < sizeof(w) / sizeof(w[0])) { w[k++] |= uint32_t(rest); rest >>= 32; }
    }
};
