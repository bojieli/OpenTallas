// otatpg -- stuck-at ATPG for full-scan combinational models.
//
// Input: a primitive-gate model written by tools/dft/atpg_model.py (sources
// are primary inputs, some held at constraint values, and scan-cell states;
// observation points are primary outputs and scan-cell next states) and a
// stuck-at fault list over its nodes.
//
// Flow:
//   1. random patterns, 64 at a time, fault-simulated (parallel-pattern,
//      single-fault, event-driven propagation) with fault dropping, until a
//      block of patterns stops paying;
//   2. PODEM on every remaining fault (SCOAP-guided backtrace, X-path check,
//      backtrack limit), with dynamic compaction: each pattern's test cube is
//      grown by targeting further faults under its assignments before its
//      unspecified bits are randomly filled;
//   3. reverse-order fault simulation to drop patterns that detect nothing
//      new (static compaction).
//
// A fault PODEM exhausts without an abort is proved untestable under the
// constraints (redundant, tied or blocked).  Every detection is confirmed by
// fault simulation of the final, fully specified pattern -- PODEM's own claim
// is never counted.
//
// Output: per-fault status and detecting pattern, the pattern set (source
// values and expected observation values, hex), and a JSON summary.

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <mutex>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

using u64 = uint64_t;
using u32 = uint32_t;

enum { T_CONST0, T_CONST1, T_INPUT, T_BUF, T_NOT, T_AND, T_NAND, T_OR, T_NOR, T_XOR, T_XNOR };

struct Circuit {
  u32 n = 0;
  std::vector<uint8_t> type;
  std::vector<u32> fin_begin, fin_count, fanins;
  std::vector<u32> fout_begin, fout_count, fanouts;
  std::vector<u32> level, order;  // order: topological
  u32 max_level = 0;
  std::vector<u32> sources;       // PI then PPI node ids, in file order
  std::vector<int> source_constraint;  // -1 free, 0/1 held
  std::vector<int> source_index;  // node -> index in sources or -1
  std::vector<u32> obs;
  std::vector<uint8_t> is_obs;
  u32 n_pi = 0;
  // chain-test (shift model) records
  std::vector<std::pair<u32, u32>> seq;        // state node -> next-state node
  std::vector<u32> flush_in;                   // scan-in inputs
  std::vector<std::pair<u32, u32>> flush_obs;  // scan-out node, chain length
  std::vector<std::array<u32, 3>> scanpos;     // next-state node, chain position, chain length
};

static void die(const std::string& msg) {
  std::cerr << "otatpg: " << msg << "\n";
  std::exit(2);
}

static Circuit read_model(const std::string& path) {
  std::ifstream in(path);
  if (!in) die("cannot open " + path);
  Circuit c;
  std::string tag;
  in >> tag;
  if (tag != "OTATPG") die("not an OTATPG model");
  int ver;
  in >> ver;
  in >> tag >> c.n;
  c.type.resize(c.n);
  c.fin_begin.resize(c.n);
  c.fin_count.resize(c.n);
  for (u32 i = 0; i < c.n; i++) {
    int t, k;
    in >> tag >> t >> k;
    if (tag != "G") die("bad gate line");
    c.type[i] = (uint8_t)t;
    c.fin_begin[i] = c.fanins.size();
    c.fin_count[i] = k;
    for (int j = 0; j < k; j++) {
      u32 f;
      in >> f;
      if (f >= c.n) die("fanin out of range");
      c.fanins.push_back(f);
    }
  }
  c.source_index.assign(c.n, -1);
  c.is_obs.assign(c.n, 0);
  while (in >> tag) {
    if (tag == "PI") {
      u32 node;
      int con;
      in >> node >> con;
      c.source_index[node] = c.sources.size();
      c.sources.push_back(node);
      c.source_constraint.push_back(con);
      c.n_pi++;
    } else if (tag == "PPI") {
      u32 node;
      in >> node;
      c.source_index[node] = c.sources.size();
      c.sources.push_back(node);
      c.source_constraint.push_back(-1);
    } else if (tag == "OBS") {
      u32 node;
      in >> node;
      c.obs.push_back(node);
      c.is_obs[node] = 1;
    } else if (tag == "SEQ") {
      u32 a, b;
      in >> a >> b;
      c.seq.push_back({a, b});
    } else if (tag == "FLUSHIN") {
      u32 a;
      in >> a;
      c.flush_in.push_back(a);
    } else if (tag == "SCANPOS") {
      u32 a, pos, len;
      in >> a >> pos >> len;
      c.scanpos.push_back({a, pos, len});
    } else if (tag == "FLUSHOBS") {
      u32 a, len;
      in >> a >> len;
      c.flush_obs.push_back({a, len});
    } else {
      die("unknown record " + tag);
    }
  }
  // fanouts
  std::vector<u32> cnt(c.n, 0);
  for (u32 f : c.fanins) cnt[f]++;
  c.fout_begin.resize(c.n);
  c.fout_count.assign(c.n, 0);
  u32 acc = 0;
  for (u32 i = 0; i < c.n; i++) {
    c.fout_begin[i] = acc;
    acc += cnt[i];
  }
  c.fanouts.resize(acc);
  for (u32 i = 0; i < c.n; i++)
    for (u32 j = 0; j < c.fin_count[i]; j++) {
      u32 f = c.fanins[c.fin_begin[i] + j];
      c.fanouts[c.fout_begin[f] + c.fout_count[f]++] = i;
    }
  // levelise (Kahn)
  c.level.assign(c.n, 0);
  std::vector<u32> indeg(c.n);
  std::vector<u32> q;
  q.reserve(c.n);
  for (u32 i = 0; i < c.n; i++) {
    indeg[i] = c.fin_count[i];
    if (indeg[i] == 0) q.push_back(i);
  }
  for (size_t h = 0; h < q.size(); h++) {
    u32 v = q[h];
    for (u32 j = 0; j < c.fout_count[v]; j++) {
      u32 w = c.fanouts[c.fout_begin[v] + j];
      c.level[w] = std::max(c.level[w], c.level[v] + 1);
      if (--indeg[w] == 0) q.push_back(w);
    }
  }
  if (q.size() != c.n) die("combinational loop in model");
  c.order = q;
  for (u32 i = 0; i < c.n; i++) c.max_level = std::max(c.max_level, c.level[i]);
  for (u32 i = 0; i < c.n; i++)
    if (c.type[i] == T_INPUT && c.source_index[i] < 0) die("INPUT node not declared PI/PPI");
  return c;
}

// ---------------------------------------------------------------------------
// two-valued, 64-pattern-parallel evaluation
// ---------------------------------------------------------------------------

static inline u64 eval_word(const Circuit& c, u32 v, const u64* val) {
  const u32* f = &c.fanins[c.fin_begin[v]];
  u32 k = c.fin_count[v];
  u64 r;
  switch (c.type[v]) {
    case T_CONST0: return 0;
    case T_CONST1: return ~0ULL;
    case T_BUF: return val[f[0]];
    case T_NOT: return ~val[f[0]];
    case T_AND: case T_NAND:
      r = ~0ULL;
      for (u32 j = 0; j < k; j++) r &= val[f[j]];
      return c.type[v] == T_AND ? r : ~r;
    case T_OR: case T_NOR:
      r = 0;
      for (u32 j = 0; j < k; j++) r |= val[f[j]];
      return c.type[v] == T_OR ? r : ~r;
    case T_XOR: case T_XNOR:
      r = 0;
      for (u32 j = 0; j < k; j++) r ^= val[f[j]];
      return c.type[v] == T_XOR ? r : ~r;
  }
  return 0;
}

struct Fault {
  u32 node;
  uint8_t stuck;
  uint8_t status;  // 0 undetected, 1 detected, 2 untestable, 3 aborted
  int32_t pattern; // detecting pattern (final numbering) or -1
};
enum { ST_UND = 0, ST_DT = 1, ST_UT = 2, ST_AU = 3 };

// Per-thread scratch for event-driven fault propagation.
struct FsScratch {
  std::vector<u64> fval;
  std::vector<u32> stamp;
  std::vector<u32> queued;
  std::vector<std::vector<u32>> bucket;
  u32 epoch = 0;
  void init(const Circuit& c) {
    fval.assign(c.n, 0);
    stamp.assign(c.n, 0);
    queued.assign(c.n, 0);
    bucket.assign(c.max_level + 1, {});
  }
};

// Returns the mask of patterns (bits) that detect the fault.
static u64 simulate_fault(const Circuit& c, const std::vector<u64>& good, const Fault& f,
                          u64 valid, FsScratch& s) {
  u32 site = f.node;
  u64 fw = f.stuck ? ~0ULL : 0ULL;
  u64 diff = (good[site] ^ fw) & valid;
  if (!diff) return 0;
  s.epoch++;
  if (s.epoch == 0) {  // wrapped
    std::fill(s.stamp.begin(), s.stamp.end(), 0);
    std::fill(s.queued.begin(), s.queued.end(), 0);
    s.epoch = 1;
  }
  u32 ep = s.epoch;
  s.fval[site] = fw;
  s.stamp[site] = ep;
  u64 det = 0;
  if (c.is_obs[site]) det |= diff;
  u32 lo = c.max_level + 1, hi = 0;
  auto push = [&](u32 w) {
    if (s.queued[w] == ep) return;
    s.queued[w] = ep;
    u32 l = c.level[w];
    s.bucket[l].push_back(w);
    lo = std::min(lo, l);
    hi = std::max(hi, l);
  };
  for (u32 j = 0; j < c.fout_count[site]; j++) push(c.fanouts[c.fout_begin[site] + j]);
  for (u32 l = lo; l <= hi && l <= c.max_level; l++) {
    auto& b = s.bucket[l];
    for (size_t h = 0; h < b.size(); h++) {
      u32 v = b[h];
      if (v == site) continue;
      // evaluate with faulty values where stamped
      const u32* fi = &c.fanins[c.fin_begin[v]];
      u32 k = c.fin_count[v];
      u64 r;
      auto in = [&](u32 j) -> u64 { u32 x = fi[j]; return s.stamp[x] == ep ? s.fval[x] : good[x]; };
      switch (c.type[v]) {
        case T_BUF: r = in(0); break;
        case T_NOT: r = ~in(0); break;
        case T_AND: r = ~0ULL; for (u32 j = 0; j < k; j++) r &= in(j); break;
        case T_NAND: r = ~0ULL; for (u32 j = 0; j < k; j++) r &= in(j); r = ~r; break;
        case T_OR: r = 0; for (u32 j = 0; j < k; j++) r |= in(j); break;
        case T_NOR: r = 0; for (u32 j = 0; j < k; j++) r |= in(j); r = ~r; break;
        case T_XOR: r = 0; for (u32 j = 0; j < k; j++) r ^= in(j); break;
        case T_XNOR: r = 0; for (u32 j = 0; j < k; j++) r ^= in(j); r = ~r; break;
        default: r = good[v];
      }
      u64 d = (r ^ good[v]) & valid;
      if (!d) continue;
      s.fval[v] = r;
      s.stamp[v] = ep;
      if (c.is_obs[v]) det |= d;
      for (u32 j = 0; j < c.fout_count[v]; j++) push(c.fanouts[c.fout_begin[v] + j]);
    }
    b.clear();
  }
  return det;
}

static void good_sim(const Circuit& c, const std::vector<u64>& src_words, std::vector<u64>& good) {
  good.resize(c.n);
  for (u32 v : c.order) {
    int si = c.source_index[v];
    if (si >= 0)
      good[v] = src_words[si];
    else
      good[v] = eval_word(c, v, good.data());
  }
}

// Fault-simulate one block of up to 64 patterns against every fault in
// `targets`; returns per-target detection masks.
static void fault_sim_block(const Circuit& c, const std::vector<u64>& good, u64 valid,
                            const std::vector<Fault>& faults, const std::vector<u32>& targets,
                            std::vector<u64>& det, std::vector<FsScratch>& scratch, int threads) {
  det.assign(targets.size(), 0);
  std::atomic<size_t> next{0};
  auto work = [&](int t) {
    FsScratch& s = scratch[t];
    while (true) {
      size_t start = next.fetch_add(256);
      if (start >= targets.size()) break;
      size_t end = std::min(targets.size(), start + 256);
      for (size_t i = start; i < end; i++) det[i] = simulate_fault(c, good, faults[targets[i]], valid, s);
    }
  };
  std::vector<std::thread> pool;
  for (int t = 1; t < threads; t++) pool.emplace_back(work, t);
  work(0);
  for (auto& th : pool) th.join();
}

// ---------------------------------------------------------------------------
// PODEM with three-valued good and faulty machines
// ---------------------------------------------------------------------------

enum : uint8_t { V0 = 0, V1 = 1, VX = 2 };

struct Podem {
  const Circuit& c;
  std::vector<uint8_t> g, f;          // good / faulty values
  std::vector<uint32_t> cc0, cc1, co;
  struct Undo { u32 node; uint8_t g, f; };
  std::vector<Undo> trail;
  std::vector<std::vector<u32>> bucket;
  std::vector<u32> queued;
  u32 epoch = 1;
  u32 fsite = 0;
  uint8_t fstuck = 0;
  bool fault_on = false;
  std::vector<uint8_t> base_g;        // values with only constraints applied
  std::vector<u32> mark;
  u32 mark_epoch = 1;

  explicit Podem(const Circuit& cc) : c(cc) {
    g.assign(c.n, VX);
    f.assign(c.n, VX);
    bucket.assign(c.max_level + 1, {});
    queued.assign(c.n, 0);
    mark.assign(c.n, 0);
    scoap();
    // constants and constraints
    for (u32 v : c.order) {
      uint8_t val = VX;
      int si = c.source_index[v];
      if (si >= 0) {
        int con = c.source_constraint[si];
        val = con < 0 ? VX : (uint8_t)con;
      } else {
        val = eval3(v, g);
      }
      g[v] = f[v] = val;
    }
    base_g = g;
  }

  static inline uint8_t inv3(uint8_t a) { return a == VX ? VX : (uint8_t)(1 - a); }

  uint8_t eval3(u32 v, const std::vector<uint8_t>& val) const {
    const u32* fi = &c.fanins[c.fin_begin[v]];
    u32 k = c.fin_count[v];
    switch (c.type[v]) {
      case T_CONST0: return V0;
      case T_CONST1: return V1;
      case T_INPUT: return val[v];
      case T_BUF: return val[fi[0]];
      case T_NOT: return inv3(val[fi[0]]);
      case T_AND: case T_NAND: {
        bool x = false;
        for (u32 j = 0; j < k; j++) {
          uint8_t a = val[fi[j]];
          if (a == V0) return c.type[v] == T_AND ? V0 : V1;
          if (a == VX) x = true;
        }
        if (x) return VX;
        return c.type[v] == T_AND ? V1 : V0;
      }
      case T_OR: case T_NOR: {
        bool x = false;
        for (u32 j = 0; j < k; j++) {
          uint8_t a = val[fi[j]];
          if (a == V1) return c.type[v] == T_OR ? V1 : V0;
          if (a == VX) x = true;
        }
        if (x) return VX;
        return c.type[v] == T_OR ? V0 : V1;
      }
      case T_XOR: case T_XNOR: {
        uint8_t r = 0;
        for (u32 j = 0; j < k; j++) {
          uint8_t a = val[fi[j]];
          if (a == VX) return VX;
          r ^= a;
        }
        return c.type[v] == T_XOR ? r : (uint8_t)(1 - r);
      }
    }
    return VX;
  }

  void scoap() {
    const u32 INF = 1u << 28;
    cc0.assign(c.n, INF);
    cc1.assign(c.n, INF);
    for (u32 v : c.order) {
      const u32* fi = &c.fanins[c.fin_begin[v]];
      u32 k = c.fin_count[v];
      u32 a0 = 0, a1 = 0, m0 = INF, m1 = INF;
      switch (c.type[v]) {
        case T_CONST0: cc0[v] = 0; break;
        case T_CONST1: cc1[v] = 0; break;
        case T_INPUT: {
          int con = c.source_constraint[c.source_index[v]];
          cc0[v] = con == 1 ? INF : 1;
          cc1[v] = con == 0 ? INF : 1;
          break;
        }
        case T_BUF: cc0[v] = cc0[fi[0]] + 1; cc1[v] = cc1[fi[0]] + 1; break;
        case T_NOT: cc0[v] = cc1[fi[0]] + 1; cc1[v] = cc0[fi[0]] + 1; break;
        case T_AND: case T_NAND: case T_OR: case T_NOR:
          for (u32 j = 0; j < k; j++) {
            a0 = std::min(INF, a0 + cc0[fi[j]]);
            a1 = std::min(INF, a1 + cc1[fi[j]]);
            m0 = std::min(m0, cc0[fi[j]]);
            m1 = std::min(m1, cc1[fi[j]]);
          }
          if (c.type[v] == T_AND) { cc0[v] = m0 + 1; cc1[v] = a1 + 1; }
          if (c.type[v] == T_NAND) { cc1[v] = m0 + 1; cc0[v] = a1 + 1; }
          if (c.type[v] == T_OR) { cc1[v] = m1 + 1; cc0[v] = a0 + 1; }
          if (c.type[v] == T_NOR) { cc0[v] = m1 + 1; cc1[v] = a0 + 1; }
          break;
        case T_XOR: case T_XNOR: {
          // two-input approximation folded over k inputs
          u32 e0 = cc0[fi[0]], e1 = cc1[fi[0]];
          for (u32 j = 1; j < k; j++) {
            u32 b0 = cc0[fi[j]], b1 = cc1[fi[j]];
            u32 n0 = std::min(e0 + b0, e1 + b1), n1 = std::min(e0 + b1, e1 + b0);
            e0 = std::min(INF, n0);
            e1 = std::min(INF, n1);
          }
          if (c.type[v] == T_XOR) { cc0[v] = e0 + 1; cc1[v] = e1 + 1; }
          else { cc0[v] = e1 + 1; cc1[v] = e0 + 1; }
          break;
        }
      }
      cc0[v] = std::min(cc0[v], INF);
      cc1[v] = std::min(cc1[v], INF);
    }
    co.assign(c.n, INF);
    for (u32 o : c.obs) co[o] = 0;
    for (auto it = c.order.rbegin(); it != c.order.rend(); ++it) {
      u32 v = *it;
      if (co[v] >= INF) continue;
      const u32* fi = &c.fanins[c.fin_begin[v]];
      u32 k = c.fin_count[v];
      for (u32 j = 0; j < k; j++) {
        u32 extra = 0;
        switch (c.type[v]) {
          case T_AND: case T_NAND:
            for (u32 i = 0; i < k; i++) if (i != j) extra = std::min(INF, extra + cc1[fi[i]]);
            break;
          case T_OR: case T_NOR:
            for (u32 i = 0; i < k; i++) if (i != j) extra = std::min(INF, extra + cc0[fi[i]]);
            break;
          case T_XOR: case T_XNOR:
            for (u32 i = 0; i < k; i++) if (i != j) extra = std::min(INF, extra + std::min(cc0[fi[i]], cc1[fi[i]]));
            break;
          default: break;
        }
        u32 val = std::min(INF, co[v] + extra + 1);
        co[fi[j]] = std::min(co[fi[j]], val);
      }
    }
  }

  inline void set_node(u32 v, uint8_t ng, uint8_t nf) {
    trail.push_back({v, g[v], f[v]});
    g[v] = ng;
    f[v] = nf;
  }

  // propagate from a set of changed nodes
  void propagate(const std::vector<u32>& seeds) {
    epoch++;
    u32 lo = c.max_level + 1, hi = 0;
    auto push = [&](u32 w) {
      if (queued[w] == epoch) return;
      queued[w] = epoch;
      u32 l = c.level[w];
      bucket[l].push_back(w);
      lo = std::min(lo, l);
      hi = std::max(hi, l);
    };
    for (u32 s : seeds)
      for (u32 j = 0; j < c.fout_count[s]; j++) push(c.fanouts[c.fout_begin[s] + j]);
    for (u32 l = lo; l <= hi && l <= c.max_level; l++) {
      auto& b = bucket[l];
      for (size_t h = 0; h < b.size(); h++) {
        u32 v = b[h];
        uint8_t ng = eval3(v, g);
        uint8_t nf = eval3(v, f);
        if (fault_on && v == fsite) nf = fstuck;
        if (ng == g[v] && nf == f[v]) continue;
        set_node(v, ng, nf);
        for (u32 j = 0; j < c.fout_count[v]; j++) push(c.fanouts[c.fout_begin[v] + j]);
      }
      b.clear();
    }
  }

  void assign_source(u32 v, uint8_t val) {
    uint8_t nf = (fault_on && v == fsite) ? fstuck : val;
    set_node(v, val, nf);
    std::vector<u32> seeds{v};
    propagate(seeds);
  }

  void undo_to(size_t mark_pos) {
    while (trail.size() > mark_pos) {
      Undo u = trail.back();
      trail.pop_back();
      g[u.node] = u.g;
      f[u.node] = u.f;
    }
  }

  void inject(u32 site, uint8_t stuck) {
    fault_on = true;
    fsite = site;
    fstuck = stuck;
    if (f[site] != stuck) {
      set_node(site, g[site], stuck);
      std::vector<u32> seeds{site};
      propagate(seeds);
    }
  }

  void remove_fault() { fault_on = false; }

  bool detected_at_obs() const {
    // fault effect at an observation point?
    for (u32 o : c.obs)
      if (g[o] != VX && f[o] != VX && g[o] != f[o]) return true;
    return false;
  }

  // D-frontier via BFS over nodes carrying a fault effect
  void d_frontier(std::vector<u32>& front, bool& at_obs) {
    front.clear();
    at_obs = false;
    mark_epoch++;
    std::vector<u32> stack{fsite};
    mark[fsite] = mark_epoch;
    while (!stack.empty()) {
      u32 v = stack.back();
      stack.pop_back();
      bool effect = g[v] != VX && f[v] != VX && g[v] != f[v];
      if (!effect) {
        if (g[v] == VX || f[v] == VX) front.push_back(v);
        continue;
      }
      if (c.is_obs[v]) at_obs = true;
      for (u32 j = 0; j < c.fout_count[v]; j++) {
        u32 w = c.fanouts[c.fout_begin[v] + j];
        if (mark[w] == mark_epoch) continue;
        mark[w] = mark_epoch;
        stack.push_back(w);
      }
    }
  }

  bool x_path(const std::vector<u32>& front) {
    mark_epoch++;
    std::vector<u32> stack;
    for (u32 v : front) { stack.push_back(v); mark[v] = mark_epoch; }
    while (!stack.empty()) {
      u32 v = stack.back();
      stack.pop_back();
      if (c.is_obs[v]) return true;
      for (u32 j = 0; j < c.fout_count[v]; j++) {
        u32 w = c.fanouts[c.fout_begin[v] + j];
        if (mark[w] == mark_epoch) continue;
        if (g[w] != VX && f[w] != VX) continue;  // determined: blocks unless it carries effect
        mark[w] = mark_epoch;
        stack.push_back(w);
      }
    }
    return false;
  }

  // Backtrace an objective (node, value) to an unassigned source.
  bool backtrace(u32 v, uint8_t val, u32& src, uint8_t& sval) {
    for (int guard = 0; guard < 100000; guard++) {
      if (c.source_index[v] >= 0) {
        if (g[v] != VX) return false;
        src = v;
        sval = val;
        return true;
      }
      const u32* fi = &c.fanins[c.fin_begin[v]];
      u32 k = c.fin_count[v];
      uint8_t t = c.type[v];
      bool inv = (t == T_NOT || t == T_NAND || t == T_NOR || t == T_XNOR);
      uint8_t want = inv ? (uint8_t)(1 - val) : val;  // value at the non-inverted function output
      u32 best = UINT32_MAX;
      uint8_t bestval = 0;
      if (t == T_BUF || t == T_NOT) {
        if (g[fi[0]] != VX) return false;
        best = fi[0];
        bestval = want;
      } else if (t == T_AND || t == T_NAND || t == T_OR || t == T_NOR) {
        bool is_and = (t == T_AND || t == T_NAND);
        uint8_t ctrl = is_and ? V0 : V1;
        if (want == (is_and ? V0 : V1)) {
          // one input at controlling value: easiest
          u32 bc = UINT32_MAX;
          for (u32 j = 0; j < k; j++) {
            u32 x = fi[j];
            if (g[x] != VX) continue;
            u32 cost = ctrl == V0 ? cc0[x] : cc1[x];
            if (cost < bc) { bc = cost; best = x; }
          }
          bestval = ctrl;
        } else {
          // all inputs non-controlling: hardest first
          u32 bc = 0;
          bool found = false;
          for (u32 j = 0; j < k; j++) {
            u32 x = fi[j];
            if (g[x] != VX) continue;
            u32 cost = ctrl == V0 ? cc1[x] : cc0[x];
            if (!found || cost > bc) { bc = cost; best = x; found = true; }
          }
          bestval = (uint8_t)(1 - ctrl);
        }
      } else if (t == T_XOR || t == T_XNOR) {
        uint8_t parity = 0;
        u32 nx = 0;
        u32 bc = UINT32_MAX;
        for (u32 j = 0; j < k; j++) {
          u32 x = fi[j];
          if (g[x] == VX) {
            nx++;
            u32 cost = std::min(cc0[x], cc1[x]);
            if (cost < bc) { bc = cost; best = x; }
          } else {
            parity ^= g[x];
          }
        }
        // assume other X inputs end at 0
        bestval = (uint8_t)(want ^ parity);
        (void)nx;
      } else {
        return false;
      }
      if (best == UINT32_MAX) return false;
      v = best;
      val = bestval;
    }
    return false;
  }

  // Objective: activate, then propagate through the D-frontier.
  bool objective(u32& v, uint8_t& val, const std::vector<u32>& front) {
    if (g[fsite] == VX) {
      v = fsite;
      val = (uint8_t)(1 - fstuck);
      return true;
    }
    // D-frontier gate with best observability
    u32 best = UINT32_MAX, bc = UINT32_MAX;
    for (u32 w : front) {
      if (co[w] < bc) { bc = co[w]; best = w; }
    }
    if (best == UINT32_MAX) return false;
    uint8_t t = c.type[best];
    const u32* fi = &c.fanins[c.fin_begin[best]];
    u32 k = c.fin_count[best];
    uint8_t nc;
    switch (t) {
      case T_AND: case T_NAND: nc = V1; break;
      case T_OR: case T_NOR: nc = V0; break;
      default: nc = V0; break;
    }
    for (u32 j = 0; j < k; j++) {
      u32 x = fi[j];
      if (g[x] == VX) { v = x; val = nc; return true; }
    }
    // good value known but faulty value X: any unassigned source behind it
    v = best;
    val = V0;
    return true;
  }

  // Any unassigned source in the transitive fanin of v (completeness fallback:
  // a decision on any X source is a valid PODEM branch).
  bool any_x_source(u32 v, u32& src) {
    mark_epoch++;
    std::vector<u32> stack{v};
    mark[v] = mark_epoch;
    while (!stack.empty()) {
      u32 w = stack.back();
      stack.pop_back();
      if (c.source_index[w] >= 0) {
        if (g[w] == VX) { src = w; return true; }
        continue;
      }
      const u32* fi = &c.fanins[c.fin_begin[w]];
      for (u32 j = 0; j < c.fin_count[w]; j++) {
        u32 x = fi[j];
        if (mark[x] == mark_epoch) continue;
        if (g[x] != VX && f[x] != VX) continue;
        mark[x] = mark_epoch;
        stack.push_back(x);
      }
    }
    return false;
  }

  // Result: 1 detected (cube in g of sources), 0 untestable, -1 aborted.
  int run(u32 site, uint8_t stuck, int backtrack_limit, int& backtracks) {
    size_t base_mark = trail.size();
    inject(site, stuck);
    struct Dec { u32 src; uint8_t val; bool flipped; size_t mark; };
    std::vector<Dec> stack;
    std::vector<u32> front;
    backtracks = 0;
    int result = 0;
    while (true) {
      bool at_obs;
      bool fail = false;
      if (g[fsite] != VX && g[fsite] == fstuck) fail = true;
      if (!fail) {
        d_frontier(front, at_obs);
        if (at_obs) { result = 1; break; }
        if (g[fsite] != VX) {
          if (front.empty() || !x_path(front)) fail = true;
        }
      }
      if (!fail) {
        u32 ov;
        uint8_t oval;
        u32 src;
        uint8_t sval;
        bool have = objective(ov, oval, front);
        bool ok = have && backtrace(ov, oval, src, sval);
        if (!ok && have && any_x_source(ov, src)) { sval = oval; ok = true; }
        if (!ok) {
          for (u32 w : front)
            if (any_x_source(w, src)) { sval = V0; ok = true; break; }
        }
        if (ok) {
          stack.push_back({src, sval, false, trail.size()});
          assign_source(src, sval);
          continue;
        }
        fail = true;
      }
      // backtrack
      bool resumed = false;
      while (!stack.empty()) {
        Dec& d = stack.back();
        undo_to(d.mark);
        if (!d.flipped) {
          d.flipped = true;
          d.val = (uint8_t)(1 - d.val);
          if (++backtracks > backtrack_limit) break;
          assign_source(d.src, d.val);
          resumed = true;
          break;
        }
        stack.pop_back();
      }
      if (backtracks > backtrack_limit) { result = -1; break; }
      if (!resumed) { result = 0; break; }
    }
    // leave source assignments in place for the caller to read; the caller
    // restores with undo_to(base_mark) via release()
    last_mark = base_mark;
    return result;
  }
  size_t last_mark = 0;

  void release() {
    undo_to(last_mark);
    remove_fault();
  }
};

// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Chain test: sequential, three-valued fault simulation of a scan flush
// ---------------------------------------------------------------------------
//
// The shift model (scan_en = 1) plus its SEQ pairs (state -> next state) is
// clocked for 2 * (longest chain) + 2 cycles.  Scan inputs carry 0011...,
// held inputs their constraint, every other input 0, and every cell starts
// unknown (X).  A fault is detected when a scan output, at a cycle where its
// chain is already full of flush data, is known in both machines and differs.
// The good machine is simulated once per cycle; each fault keeps only the
// states where its machine differs and is propagated event-driven from them
// and from its site, so the cost follows the fault's effect, not the circuit.
// A fault on a scan-cell state node models a stopped clock: the cell holds
// its value for the whole test.

static inline uint8_t eval3_node(const Circuit& c, u32 v, const uint8_t* val) {
  const u32* fi = &c.fanins[c.fin_begin[v]];
  u32 k = c.fin_count[v];
  switch (c.type[v]) {
    case T_CONST0: return 0;
    case T_CONST1: return 1;
    case T_INPUT: return val[v];
    case T_BUF: return val[fi[0]];
    case T_NOT: { uint8_t a = val[fi[0]]; return a == 2 ? 2 : (uint8_t)(1 - a); }
    case T_AND: case T_NAND: {
      bool x = false;
      for (u32 j = 0; j < k; j++) { uint8_t a = val[fi[j]]; if (a == 0) return c.type[v] == T_AND ? 0 : 1; if (a == 2) x = true; }
      if (x) return 2;
      return c.type[v] == T_AND ? 1 : 0;
    }
    case T_OR: case T_NOR: {
      bool x = false;
      for (u32 j = 0; j < k; j++) { uint8_t a = val[fi[j]]; if (a == 1) return c.type[v] == T_OR ? 1 : 0; if (a == 2) x = true; }
      if (x) return 2;
      return c.type[v] == T_OR ? 0 : 1;
    }
    case T_XOR: case T_XNOR: {
      uint8_t r = 0;
      for (u32 j = 0; j < k; j++) { uint8_t a = val[fi[j]]; if (a == 2) return 2; r ^= a; }
      return c.type[v] == T_XOR ? r : (uint8_t)(1 - r);
    }
  }
  return 2;
}

struct FlushScratch {
  std::vector<uint8_t> fval;
  std::vector<u32> stamp, queued;
  std::vector<std::vector<u32>> bucket;
  u32 epoch = 0;
  void init(const Circuit& c) {
    fval.assign(c.n, 2);
    stamp.assign(c.n, 0);
    queued.assign(c.n, 0);
    bucket.assign(c.max_level + 1, {});
  }
};

struct FlushFault {
  u32 site;
  uint8_t stuck;
  bool detected = false;
  int cycle = -1;
  std::vector<std::pair<u32, uint8_t>> diff;   // PPI node -> faulty value
  // 0: full sequential simulation; 1: the fault reaches one scan cell's next
  // state only (first-divergence rule); 2: it reaches one scan output only
  int mode = 0;
  int pos = -1, len = -1;
  bool done = false;
};

static int run_flush(const Circuit& c, const std::string& faults_path, const std::string& only,
                     const std::string& out_prefix, int threads) {
  if (c.seq.empty() || c.flush_obs.empty()) die("flush mode needs SEQ and FLUSHOBS records");
  std::vector<FlushFault> faults;
  {
    std::ifstream in(faults_path);
    size_t n;
    in >> n;
    for (size_t i = 0; i < n; i++) {
      u32 node; int v;
      in >> node >> v;
      faults.push_back({node, (uint8_t)v});
    }
  }
  std::vector<uint8_t> active(faults.size(), 1);
  if (!only.empty()) {
    std::fill(active.begin(), active.end(), 0);
    std::ifstream in(only);
    size_t idx;
    while (in >> idx) if (idx < faults.size()) active[idx] = 1;
  }
  u32 maxlen = 0;
  for (auto& o : c.flush_obs) maxlen = std::max(maxlen, o.second);
  const int T = 2 * (int)maxlen + 2;
  std::vector<int> ppi_of_ppo(c.n, -1);
  std::vector<uint8_t> is_ppi(c.n, 0);
  for (auto& sp : c.seq) { ppi_of_ppo[sp.second] = (int)sp.first; is_ppi[sp.first] = 1; }
  std::vector<int> obs_len(c.n, -1);
  for (auto& o : c.flush_obs) obs_len[o.first] = (int)o.second;
  std::vector<uint8_t> is_flush_in(c.n, 0);
  for (u32 v : c.flush_in) is_flush_in[v] = 1;

  std::vector<uint8_t> good(c.n, 2), next_state(c.n, 2);
  for (u32 s = 0; s < c.sources.size(); s++) {
    u32 v = c.sources[s];
    if (is_ppi[v]) good[v] = 2;
  }
  std::vector<FlushScratch> scratch(threads);
  for (auto& s : scratch) s.init(c);
  // Values that are constant through the whole flush (held inputs, inputs
  // driven 0, and whatever they force), for structural blocking.
  std::vector<uint8_t> cval(c.n, 2);
  for (u32 v : c.order) {
    int si = c.source_index[v];
    if (si >= 0) {
      int con = c.source_constraint[si];
      cval[v] = (is_ppi[v] || is_flush_in[v]) ? 2 : (con >= 0 ? (uint8_t)con : 0);
    } else {
      cval[v] = eval3_node(c, v, cval.data());
    }
  }
  std::vector<int> spos(c.n, -1), slen(c.n, -1);
  for (auto& sp : c.scanpos) { spos[sp[0]] = (int)sp[1]; slen[sp[0]] = (int)sp[2]; }
  // Which next states and scan outputs can the fault reach before anything
  // else differs?  A gate passes a difference unless an input that does not
  // differ holds its controlling constant.
  size_t n_single = 0, n_obs = 0, n_full = 0;
  {
    std::vector<u32> mark(c.n, 0), lvl_q;
    std::vector<std::vector<u32>> bucket(c.max_level + 1);
    u32 ep = 0;
    for (size_t i = 0; i < faults.size(); i++) {
      if (!active[i]) continue;
      FlushFault& f = faults[i];
      ep++;
      std::vector<u32> targets;
      u32 lo = c.max_level + 1, hi = 0;
      auto push_fanouts = [&](u32 v) {
        for (u32 j = 0; j < c.fout_count[v]; j++) {
          u32 w = c.fanouts[c.fout_begin[v] + j];
          if (mark[w] == ep || mark[w] == ep + 0x80000000u) continue;
          mark[w] = ep + 0x80000000u;   // queued
          bucket[c.level[w]].push_back(w);
          lo = std::min(lo, c.level[w]);
          hi = std::max(hi, c.level[w]);
        }
      };
      mark[f.site] = ep;
      if (spos[f.site] >= 0 || obs_len[f.site] >= 0) targets.push_back(f.site);
      push_fanouts(f.site);
      bool multi = false;
      for (u32 l = lo; l <= hi && l <= c.max_level && !multi; l++) {
        for (size_t h = 0; h < bucket[l].size(); h++) {
          u32 w = bucket[l][h];
          if (c.source_index[w] >= 0) { mark[w] = 0; continue; }
          const u32* fi = &c.fanins[c.fin_begin[w]];
          bool blocked = false;
          uint8_t t = c.type[w];
          for (u32 j = 0; j < c.fin_count[w]; j++) {
            u32 u = fi[j];
            if (mark[u] == ep) continue;   // differs
            if ((t == T_AND || t == T_NAND) && cval[u] == 0) blocked = true;
            if ((t == T_OR || t == T_NOR) && cval[u] == 1) blocked = true;
          }
          if (blocked) { mark[w] = 0; continue; }
          mark[w] = ep;
          if (spos[w] >= 0 || obs_len[w] >= 0) {
            targets.push_back(w);
            if (targets.size() > 1) { multi = true; break; }
          }
          push_fanouts(w);
        }
      }
      for (u32 l = 0; l <= c.max_level; l++) {
        if (l >= lo && l <= hi) {
          for (u32 w : bucket[l]) if (mark[w] != ep) mark[w] = 0;
          bucket[l].clear();
        }
      }
      if (multi || targets.empty()) {
        f.mode = 0;
        n_full++;
      } else if (spos[targets[0]] >= 0) {
        f.mode = 1;
        f.pos = spos[targets[0]];
        f.len = slen[targets[0]];
        n_single++;
      } else {
        f.mode = 2;
        n_obs++;
      }
    }
  }
  std::vector<u32> live;
  for (u32 i = 0; i < faults.size(); i++) if (active[i]) live.push_back(i);
  auto t0 = std::chrono::steady_clock::now();

  for (int t = 0; t < T && !live.empty(); t++) {
    // good machine for this cycle
    uint8_t flush_bit = (uint8_t)((t >> 1) & 1);
    for (u32 v : c.order) {
      int si = c.source_index[v];
      if (si >= 0) {
        if (is_ppi[v]) continue;          // state carried from the last cycle
        int con = c.source_constraint[si];
        good[v] = is_flush_in[v] ? flush_bit : (con >= 0 ? (uint8_t)con : 0);
      } else {
        good[v] = eval3_node(c, v, good.data());
      }
    }
    // faulty machines
    std::atomic<size_t> next{0};
    auto work = [&](int th) {
      FlushScratch& s = scratch[th];
      while (true) {
        size_t k = next.fetch_add(1);
        if (k >= live.size()) break;
        FlushFault& f = faults[live[k]];
        if (++s.epoch == 0) {
          std::fill(s.stamp.begin(), s.stamp.end(), 0);
          std::fill(s.queued.begin(), s.queued.end(), 0);
          s.epoch = 1;
        }
        u32 ep = s.epoch;
        u32 lo = c.max_level + 1, hi = 0;
        auto push = [&](u32 w) {
          if (s.queued[w] == ep) return;
          s.queued[w] = ep;
          u32 l = c.level[w];
          s.bucket[l].push_back(w);
          lo = std::min(lo, l);
          hi = std::max(hi, l);
        };
        auto set = [&](u32 v, uint8_t val) {
          s.fval[v] = val;
          s.stamp[v] = ep;
          for (u32 j = 0; j < c.fout_count[v]; j++) push(c.fanouts[c.fout_begin[v] + j]);
        };
        for (auto& d : f.diff) if (d.first != f.site) set(d.first, d.second);
        if (good[f.site] != f.stuck) set(f.site, f.stuck);
        else if (is_ppi[f.site] || c.source_index[f.site] >= 0) { s.fval[f.site] = f.stuck; s.stamp[f.site] = ep; }
        std::vector<std::pair<u32, uint8_t>> ndiff;
        bool det = false;
        bool known_div = false;
        auto consider_output = [&](u32 v, uint8_t fv) {
          int p = ppi_of_ppo[v];
          if (p >= 0 && fv != good[v]) ndiff.push_back({(u32)p, fv});
          if (p >= 0 && fv != good[v] && fv != 2 && good[v] != 2) known_div = true;
          if (obs_len[v] >= 0 && t >= obs_len[v] && fv != 2 && good[v] != 2 && fv != good[v]) det = true;
        };
        // the site or a state may itself be an observed / next-state node
        if (s.stamp[f.site] == ep && s.fval[f.site] != good[f.site]) consider_output(f.site, s.fval[f.site]);
        for (u32 l = lo; l <= hi && l <= c.max_level; l++) {
          auto& b = s.bucket[l];
          for (size_t h = 0; h < b.size(); h++) {
            u32 v = b[h];
            if (v == f.site) continue;   // forced
            if (c.source_index[v] >= 0) continue;
            // evaluate with faulty values where stamped
            const u32* fi = &c.fanins[c.fin_begin[v]];
            u32 kk = c.fin_count[v];
            uint8_t tmp[64];
            std::vector<uint8_t> big;
            uint8_t* in = tmp;
            if (kk > 64) { big.resize(kk); in = big.data(); }
            for (u32 j = 0; j < kk; j++) { u32 x = fi[j]; in[j] = s.stamp[x] == ep ? s.fval[x] : good[x]; }
            uint8_t r;
            {
              // local evaluation over gathered inputs
              uint8_t typ = c.type[v];
              if (typ == T_BUF) r = in[0];
              else if (typ == T_NOT) r = in[0] == 2 ? 2 : (uint8_t)(1 - in[0]);
              else if (typ == T_AND || typ == T_NAND) {
                bool x = false, zero = false;
                for (u32 j = 0; j < kk; j++) { if (in[j] == 0) zero = true; else if (in[j] == 2) x = true; }
                r = zero ? 0 : (x ? 2 : 1);
                if (typ == T_NAND && r != 2) r = 1 - r;
              } else if (typ == T_OR || typ == T_NOR) {
                bool x = false, one = false;
                for (u32 j = 0; j < kk; j++) { if (in[j] == 1) one = true; else if (in[j] == 2) x = true; }
                r = one ? 1 : (x ? 2 : 0);
                if (typ == T_NOR && r != 2) r = 1 - r;
              } else if (typ == T_XOR || typ == T_XNOR) {
                uint8_t acc = 0; bool x = false;
                for (u32 j = 0; j < kk; j++) { if (in[j] == 2) x = true; else acc ^= in[j]; }
                r = x ? 2 : (typ == T_XOR ? acc : (uint8_t)(1 - acc));
              } else r = good[v];
            }
            if (r == good[v]) continue;
            s.fval[v] = r;
            s.stamp[v] = ep;
            consider_output(v, r);
            for (u32 j = 0; j < c.fout_count[v]; j++) push(c.fanouts[c.fout_begin[v] + j]);
          }
          b.clear();
        }
        if (f.mode == 1) {
          // the first divergence at scan cell pos travels, unchanged, through
          // fault-free cells to the scan output len - pos cycles later
          if (!ndiff.empty()) {
            int t_obs = t + f.len - f.pos;
            // a difference against an unknown good value can never be observed
            // as a known mismatch downstream, so only a known one counts
            if (known_div && t >= f.pos && t_obs < T) { f.detected = true; f.cycle = t_obs; }
            else if (known_div && t < f.pos) { f.mode = 0; f.diff.swap(ndiff); }
            else if (known_div) { f.done = true; }
          }
          continue;
        }
        if (det) { f.detected = true; f.cycle = t; }
        f.diff.swap(ndiff);
      }
    };
    std::vector<std::thread> pool;
    for (int th = 1; th < threads; th++) pool.emplace_back(work, th);
    work(0);
    for (auto& th : pool) th.join();
    std::vector<u32> keep;
    for (u32 i : live) if (!faults[i].detected && !faults[i].done) keep.push_back(i);
    live.swap(keep);
    // advance the good machine
    for (auto& sp : c.seq) next_state[sp.first] = good[sp.second];
    for (auto& sp : c.seq) good[sp.first] = next_state[sp.first];
  }
  size_t det = 0, act = 0;
  {
    std::ofstream o(out_prefix + ".faults");
    for (size_t i = 0; i < faults.size(); i++) {
      if (active[i]) act++;
      if (faults[i].detected) det++;
      o << (faults[i].detected ? 1 : 0) << " " << faults[i].cycle << "\n";
    }
  }
  double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  {
    std::ofstream o(out_prefix + ".summary.json");
    o << "{\n  \"mode\": \"flush\",\n  \"cycles\": " << T << ",\n  \"longest_chain\": " << maxlen
      << ",\n  \"faults_simulated\": " << act << ",\n  \"detected\": " << det
      << ",\n  \"first_divergence_faults\": " << n_single << ",\n  \"scan_out_faults\": " << n_obs
      << ",\n  \"full_simulation_faults\": " << n_full
      << ",\n  \"seconds\": " << secs << "\n}\n";
  }
  std::cerr << "otatpg: flush " << T << " cycles, " << det << "/" << act << " faults detected (" << secs << " s)\n";
  return 0;
}

struct Options {
  std::string model, faults, out_prefix;
  int threads = 8;
  int backtrack_limit = 256;
  int secondary_limit = 64;     // secondary targets tried per pattern
  int random_blocks_max = 4000;
  double random_stop = 0.001;   // stop random when a block detects < this fraction of remaining
  int random_min_blocks = 16;
  u64 seed = 1;
  bool write_patterns = true;
  bool compact = true;
  std::string only_faults;      // optional file: subset of fault indices to target
  bool flush = false;           // chain-test fault simulation instead of ATPG
  int abort_retry_factor = 16;  // aborted faults are retried once with this x the limit
};

static void write_hex(std::ostream& o, const std::vector<uint8_t>& bits) {
  static const char* hx = "0123456789abcdef";
  size_t n = bits.size();
  size_t nib = (n + 3) / 4;
  for (size_t i = 0; i < nib; i++) {
    int v = 0;
    for (int b = 0; b < 4; b++) {
      size_t idx = i * 4 + b;
      if (idx < n && bits[idx]) v |= 1 << b;
    }
    o << hx[v];
  }
}

int main(int argc, char** argv) {
  Options opt;
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    auto next = [&]() -> std::string { if (i + 1 >= argc) die("missing value for " + a); return argv[++i]; };
    if (a == "--model") opt.model = next();
    else if (a == "--faults") opt.faults = next();
    else if (a == "--out") opt.out_prefix = next();
    else if (a == "--threads") opt.threads = std::stoi(next());
    else if (a == "--backtrack-limit") opt.backtrack_limit = std::stoi(next());
    else if (a == "--secondary-limit") opt.secondary_limit = std::stoi(next());
    else if (a == "--random-blocks-max") opt.random_blocks_max = std::stoi(next());
    else if (a == "--random-stop") opt.random_stop = std::stod(next());
    else if (a == "--seed") opt.seed = std::stoull(next());
    else if (a == "--no-patterns") opt.write_patterns = false;
    else if (a == "--no-compact") opt.compact = false;
    else if (a == "--only-faults") opt.only_faults = next();
    else if (a == "--flush") opt.flush = true;
    else if (a == "--abort-retry-factor") opt.abort_retry_factor = std::stoi(next());
    else die("unknown option " + a);
  }
  if (opt.model.empty() || opt.faults.empty() || opt.out_prefix.empty()) die("need --model --faults --out");
  auto t0 = std::chrono::steady_clock::now();
  auto secs = [&]() { return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count(); };

  Circuit c = read_model(opt.model);
  if (opt.flush) return run_flush(c, opt.faults, opt.only_faults, opt.out_prefix, opt.threads);
  std::vector<Fault> faults;
  {
    std::ifstream in(opt.faults);
    size_t n;
    in >> n;
    faults.resize(n);
    for (size_t i = 0; i < n; i++) {
      u32 node;
      int v;
      in >> node >> v;
      faults[i] = {node, (uint8_t)v, ST_UND, -1};
    }
  }
  std::vector<uint8_t> targeted(faults.size(), 1);
  if (!opt.only_faults.empty()) {
    std::fill(targeted.begin(), targeted.end(), 0);
    std::ifstream in(opt.only_faults);
    size_t idx;
    while (in >> idx) if (idx < faults.size()) targeted[idx] = 1;
  }
  std::cerr << "otatpg: " << c.n << " nodes, " << c.sources.size() << " sources (" << c.n_pi
            << " PI), " << c.obs.size() << " observed, " << faults.size() << " faults, max level "
            << c.max_level << "\n";

  const u32 S = c.sources.size();
  std::mt19937_64 rng(opt.seed);
  std::vector<FsScratch> scratch(opt.threads);
  for (auto& s : scratch) s.init(c);

  // patterns: source values (one byte per source), kept in generation order
  std::vector<std::vector<uint8_t>> patterns;
  std::vector<u32> remaining;
  for (u32 i = 0; i < faults.size(); i++)
    if (targeted[i]) remaining.push_back(i);
  size_t total_targets = remaining.size();

  auto block_words = [&](size_t first, size_t count, std::vector<u64>& words) {
    words.assign(S, 0);
    for (size_t p = 0; p < count; p++) {
      const auto& pat = patterns[first + p];
      for (u32 s = 0; s < S; s++)
        if (pat[s]) words[s] |= 1ULL << p;
    }
  };

  std::vector<u64> good, words, det;
  size_t ut_contradictions = 0;
  // apply one block of patterns [first, first+count) to remaining faults, drop detected
  auto apply_block = [&](size_t first, size_t count) -> size_t {
    block_words(first, count, words);
    good_sim(c, words, good);
    u64 valid = count == 64 ? ~0ULL : ((1ULL << count) - 1);
    fault_sim_block(c, good, valid, faults, remaining, det, scratch, opt.threads);
    size_t newly = 0;
    std::vector<u32> keep;
    keep.reserve(remaining.size());
    for (size_t i = 0; i < remaining.size(); i++) {
      if (det[i]) {
        Fault& f = faults[remaining[i]];
        if (f.status == ST_UT) ut_contradictions++;
        f.status = ST_DT;
        f.pattern = (int32_t)(first + __builtin_ctzll(det[i]));
        newly++;
      } else {
        keep.push_back(remaining[i]);
      }
    }
    remaining.swap(keep);
    return newly;
  };

  auto random_pattern = [&]() {
    std::vector<uint8_t> pat(S);
    u64 r = 0;
    int left = 0;
    for (u32 s = 0; s < S; s++) {
      int con = c.source_constraint[s];
      if (con >= 0) { pat[s] = (uint8_t)con; continue; }
      if (!left) { r = rng(); left = 64; }
      pat[s] = r & 1;
      r >>= 1;
      left--;
    }
    return pat;
  };

  // ---- phase 1: random patterns --------------------------------------------
  size_t random_kept = 0, random_blocks = 0;
  for (int b = 0; b < opt.random_blocks_max && !remaining.empty(); b++) {
    size_t first = patterns.size();
    for (int p = 0; p < 64; p++) patterns.push_back(random_pattern());
    size_t before = remaining.size();
    size_t newly = apply_block(first, 64);
    random_blocks++;
    // keep only patterns credited with a first detection
    std::vector<uint8_t> used(64, 0);
    for (auto& f : faults)
      if (f.status == ST_DT && f.pattern >= (int32_t)first) used[f.pattern - first] = 1;
    std::vector<int32_t> remap(64, -1);
    size_t w = first;
    for (int p = 0; p < 64; p++) {
      if (used[p]) {
        if (w != first + p) patterns[w] = patterns[first + p];
        remap[p] = (int32_t)w++;
      }
    }
    patterns.resize(w);
    for (auto& f : faults)
      if (f.status == ST_DT && f.pattern >= (int32_t)first && f.pattern < (int32_t)(first + 64))
        f.pattern = remap[f.pattern - first];
    random_kept += w - first;
    if (b >= opt.random_min_blocks && (double)newly < opt.random_stop * (double)before) break;
  }
  size_t after_random = total_targets - remaining.size();
  std::cerr << "otatpg: random phase " << random_blocks << " blocks, " << random_kept
            << " patterns kept, " << after_random << "/" << total_targets << " detected ("
            << secs() << " s)\n";

  // ---- phase 2: PODEM with dynamic compaction, in parallel rounds ----------
  // Each round, every thread claims faults from a shared cursor, runs PODEM
  // with its own copy of the three-valued machine, grows each test cube with
  // secondary targets it also claims, and fills it randomly.  Between rounds
  // the new patterns are fault-simulated against every remaining fault and
  // detected faults are dropped, so later rounds target only what is left.
  Podem proto(c);
  std::atomic<size_t> podem_calls{0}, aborted_calls{0}, untestable{0};
  std::atomic<long long> total_backtracks{0};
  size_t podem_fail_confirm = 0;
  std::vector<std::atomic<uint8_t>> claimed(faults.size());
  for (auto& a : claimed) a.store(0);
  size_t det_patterns = 0;
  std::vector<u32> order = remaining;  // snapshot; statuses change as we go
  std::atomic<size_t> cursor{0};
  const int per_thread = std::max(1, 64 / std::max(1, opt.threads));
  std::vector<Podem> engines;
  engines.reserve(opt.threads);
  for (int t = 0; t < opt.threads; t++) engines.push_back(proto);
  std::vector<std::mt19937_64> rngs;
  for (int t = 0; t < opt.threads; t++) rngs.emplace_back(opt.seed * 7919 + t + 1);
  auto claim = [&](u32 fi) -> bool {
    uint8_t expect = 0;
    return claimed[fi].compare_exchange_strong(expect, 1);
  };
  double last_report = 0;
  // later passes pick up faults that were claimed as secondary targets,
  // released, and passed by the cursor before they got a primary attempt
  // The last pass retries every aborted fault with a backtrack limit
  // --abort-retry-factor times larger.
  int cur_limit = opt.backtrack_limit;
  size_t retried_aborts = 0;
  bool retry_done = false;
  for (int pass = 0; pass < 9; pass++) {
  if (pass > 0) {
    order.clear();
    for (u32 fi : remaining)
      if (faults[fi].status == ST_UND && !claimed[fi].load()) order.push_back(fi);
    if (order.empty() || pass == 8) {
      if (retry_done || opt.abort_retry_factor <= 1) break;
      retry_done = true;
      order.clear();
      for (u32 fi : remaining)
        if (faults[fi].status == ST_AU) { faults[fi].status = ST_UND; claimed[fi].store(0); order.push_back(fi); }
      retried_aborts = order.size();
      aborted_calls.store(0);
      cur_limit = opt.backtrack_limit * opt.abort_retry_factor;
      if (order.empty()) break;
    }
    cursor.store(0);
  }
  while (cursor.load() < order.size()) {
    std::vector<std::vector<std::vector<uint8_t>>> made(opt.threads);
    std::vector<std::vector<std::vector<u32>>> made_targets(opt.threads);
    auto worker = [&](int t) {
      Podem& pd = engines[t];
      std::mt19937_64& r = rngs[t];
      while ((int)made[t].size() < per_thread) {
        size_t k = cursor.fetch_add(1);
        if (k >= order.size()) break;
        u32 fi = order[k];
        if (faults[fi].status != ST_UND || !claim(fi)) continue;
        podem_calls++;
        int bt;
        int res = pd.run(faults[fi].node, faults[fi].stuck, cur_limit, bt);
        total_backtracks += bt;
        if (res == 0) { faults[fi].status = ST_UT; untestable++; pd.release(); continue; }
        if (res < 0) { faults[fi].status = ST_AU; aborted_calls++; pd.release(); continue; }
        std::vector<int8_t> cube(S, -1);
        for (u32 s = 0; s < S; s++) {
          uint8_t v = pd.g[c.sources[s]];
          cube[s] = v == VX ? -1 : (int8_t)v;
        }
        pd.release();
        std::vector<u32> tlist{fi};
        // apply the cube once, then try secondary targets on top of it
        size_t m0 = pd.trail.size();
        for (u32 s = 0; s < S; s++)
          if (cube[s] >= 0 && c.source_constraint[s] < 0) pd.assign_source(c.sources[s], (uint8_t)cube[s]);
        int tries = 0;
        size_t scan = k + 1;
        while (tries < opt.secondary_limit && scan < order.size()) {
          u32 fj = order[scan++];
          if (faults[fj].status != ST_UND || claimed[fj].load()) continue;
          // cheap filter: the fault must be activatable under the cube
          uint8_t gv = pd.g[faults[fj].node];
          if (gv != VX && gv == faults[fj].stuck) continue;
          if (!claim(fj)) continue;
          tries++;
          int bt2;
          int r2 = pd.run(faults[fj].node, faults[fj].stuck, std::max(8, opt.backtrack_limit / 8), bt2);
          total_backtracks += bt2;
          if (r2 == 1) {
            std::vector<u32> added;
            for (u32 s = 0; s < S; s++) {
              uint8_t v = pd.g[c.sources[s]];
              if (v != VX && cube[s] < 0) { cube[s] = (int8_t)v; added.push_back(s); }
            }
            pd.release();
            for (u32 s : added) pd.assign_source(c.sources[s], (uint8_t)cube[s]);
            tlist.push_back(fj);
          } else {
            pd.release();
            claimed[fj].store(0);   // give it back: it may be testable in another cube
          }
        }
        pd.undo_to(m0);
        std::vector<uint8_t> pat(S);
        for (u32 s = 0; s < S; s++) {
          int con = c.source_constraint[s];
          if (con >= 0) pat[s] = (uint8_t)con;
          else if (cube[s] >= 0) pat[s] = (uint8_t)cube[s];
          else pat[s] = r() & 1;
        }
        made[t].push_back(std::move(pat));
        made_targets[t].push_back(std::move(tlist));
      }
    };
    std::vector<std::thread> pool;
    for (int t = 1; t < opt.threads; t++) pool.emplace_back(worker, t);
    worker(0);
    for (auto& th : pool) th.join();
    std::vector<std::vector<u32>> round_targets;
    size_t first = patterns.size();
    for (int t = 0; t < opt.threads; t++)
      for (size_t j = 0; j < made[t].size(); j++) {
        patterns.push_back(std::move(made[t][j]));
        round_targets.push_back(std::move(made_targets[t][j]));
      }
    size_t cnt = patterns.size() - first;
    for (size_t b = 0; b < cnt; b += 64) apply_block(first + b, std::min<size_t>(64, cnt - b));
    for (auto& tl : round_targets)
      for (u32 fi : tl)
        if (faults[fi].status != ST_DT) podem_fail_confirm++;
    det_patterns += cnt;
    if (secs() - last_report > 30) {
      last_report = secs();
      std::cerr << "otatpg: podem " << podem_calls.load() << " calls, " << patterns.size()
                << " patterns, " << remaining.size() << " undetected, cursor " << cursor.load() << "/"
                << order.size() << " (" << secs() << " s)\n";
    }
  }
  }  // passes
  std::cerr << "otatpg: PODEM " << podem_calls.load() << " calls, " << untestable.load() << " untestable, "
            << aborted_calls.load() << " aborted, " << det_patterns << " deterministic patterns, "
            << podem_fail_confirm << " unconfirmed (" << secs() << " s)\n";

  // ---- phase 3: reverse-order compaction ---------------------------------
  size_t before_compact = patterns.size();
  if (opt.compact && !patterns.empty()) {
    std::vector<u32> dts;
    for (u32 i = 0; i < faults.size(); i++)
      if (faults[i].status == ST_DT) { dts.push_back(i); faults[i].status = ST_UND; faults[i].pattern = -1; }
    std::vector<std::vector<uint8_t>> rev(patterns.rbegin(), patterns.rend());
    patterns.swap(rev);
    remaining = dts;
    std::vector<uint8_t> needed(patterns.size(), 0);
    for (size_t first = 0; first < patterns.size(); first += 64) {
      size_t cnt = std::min<size_t>(64, patterns.size() - first);
      apply_block(first, cnt);
    }
    for (auto& f : faults)
      if (f.status == ST_DT) needed[f.pattern] = 1;
    std::vector<int32_t> remap(patterns.size(), -1);
    std::vector<std::vector<uint8_t>> kept;
    // restore generation order among kept patterns
    for (size_t k = patterns.size(); k-- > 0;) {
      if (needed[k]) { remap[k] = (int32_t)kept.size(); kept.push_back(patterns[k]); }
    }
    for (auto& f : faults)
      if (f.status == ST_DT) f.pattern = remap[f.pattern];
    patterns.swap(kept);
    if (!remaining.empty()) {
      std::cerr << "otatpg: WARNING " << remaining.size() << " faults lost detection in compaction\n";
    }
  }
  std::cerr << "otatpg: compaction " << before_compact << " -> " << patterns.size() << " patterns ("
            << secs() << " s)\n";

  // ---- final confirmation: re-simulate every final pattern block ----------
  size_t n_dt = 0, n_ut = 0, n_au = 0, n_und = 0;
  for (auto& f : faults) {
    if (!targeted[&f - &faults[0]]) continue;
    switch (f.status) {
      case ST_DT: n_dt++; break;
      case ST_UT: n_ut++; break;
      case ST_AU: n_au++; break;
      default: n_und++; break;
    }
  }
  // write outputs
  {
    std::ofstream o(opt.out_prefix + ".faults");
    for (auto& f : faults) o << (int)f.status << " " << f.pattern << "\n";
  }
  if (opt.write_patterns) {
    std::ofstream o(opt.out_prefix + ".patterns");
    o << "PATTERNS " << patterns.size() << " SOURCES " << S << " OBS " << c.obs.size() << "\n";
    for (size_t first = 0; first < patterns.size(); first += 64) {
      size_t cnt = std::min<size_t>(64, patterns.size() - first);
      block_words(first, cnt, words);
      good_sim(c, words, good);
      for (size_t p = 0; p < cnt; p++) {
        std::vector<uint8_t> ob(c.obs.size());
        for (size_t k = 0; k < c.obs.size(); k++) ob[k] = (good[c.obs[k]] >> p) & 1;
        write_hex(o, patterns[first + p]);
        o << " ";
        write_hex(o, ob);
        o << "\n";
      }
    }
  }
  {
    std::ofstream o(opt.out_prefix + ".summary.json");
    o << "{\n";
    o << "  \"nodes\": " << c.n << ",\n";
    o << "  \"sources\": " << S << ",\n";
    o << "  \"primary_inputs\": " << c.n_pi << ",\n";
    o << "  \"observed\": " << c.obs.size() << ",\n";
    o << "  \"max_level\": " << c.max_level << ",\n";
    o << "  \"faults_targeted\": " << total_targets << ",\n";
    o << "  \"detected\": " << n_dt << ",\n";
    o << "  \"untestable\": " << n_ut << ",\n";
    o << "  \"aborted\": " << n_au << ",\n";
    o << "  \"undetected_other\": " << n_und << ",\n";
    o << "  \"patterns\": " << patterns.size() << ",\n";
    o << "  \"patterns_before_compaction\": " << before_compact << ",\n";
    o << "  \"random_blocks\": " << random_blocks << ",\n";
    o << "  \"random_patterns_kept\": " << random_kept << ",\n";
    o << "  \"detected_after_random\": " << after_random << ",\n";
    o << "  \"podem_calls\": " << podem_calls.load() << ",\n";
    o << "  \"podem_backtracks\": " << total_backtracks.load() << ",\n";
    o << "  \"podem_unconfirmed\": " << podem_fail_confirm << ",\n";
    o << "  \"untestable_but_detected\": " << ut_contradictions << ",\n";
    o << "  \"backtrack_limit\": " << opt.backtrack_limit << ",\n";
    o << "  \"abort_retry_backtrack_limit\": " << opt.backtrack_limit * opt.abort_retry_factor << ",\n";
    o << "  \"aborted_retried\": " << retried_aborts << ",\n";
    o << "  \"seed\": " << opt.seed << ",\n";
    o << "  \"threads\": " << opt.threads << ",\n";
    o << "  \"seconds\": " << secs() << "\n";
    o << "}\n";
  }
  std::cerr << "otatpg: " << n_dt << " detected, " << n_ut << " untestable, " << n_au << " aborted, "
            << n_und << " other; " << patterns.size() << " patterns (" << secs() << " s)\n";
  return 0;
}
