#pragma once
// Evaluate the eight independent per-rank model groups (LV6 core, frontend,
// attention kernel, sector adapter, HBM PC provider) of one clock phase on
// eight host threads. Each rank's phase only touches that rank's own models
// and adapters; every cross-rank model (collector, HOST, embedding) still runs
// on the calling thread after the join, so the edge order and every sampled
// value are identical to the sequential loop. OT_RANK_THREADS=1 restores the
// sequential evaluation (for an A/B identity check). The first exception of a
// phase is re-thrown on the calling thread after all ranks finished.
#include <condition_variable>
#include <cstdlib>
#include <exception>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>

class RankPool {
 public:
  explicit RankPool(unsigned n) : n_(n) {
    const char* env = std::getenv("OT_RANK_THREADS");
    parallel_ = !(env && std::string(env) == "1");
    if (parallel_)
      for (unsigned i = 0; i < n_; i++) workers_.emplace_back([this, i] { loop(i); });
  }
  ~RankPool() {
    { std::lock_guard<std::mutex> l(m_); stop_ = true; ++gen_; }
    cv_.notify_all();
    for (auto& t : workers_) t.join();
  }
  bool parallel() const { return parallel_; }
  void run(const std::function<void(unsigned)>& fn) {
    if (!parallel_) { for (unsigned i = 0; i < n_; i++) fn(i); return; }
    {
      std::lock_guard<std::mutex> l(m_);
      fn_ = &fn; pending_ = n_; error_ = nullptr; ++gen_;
    }
    cv_.notify_all();
    std::unique_lock<std::mutex> l(m_);
    done_.wait(l, [this] { return pending_ == 0; });
    fn_ = nullptr;
    if (error_) std::rethrow_exception(error_);
  }

 private:
  void loop(unsigned i) {
    uint64_t seen = 0;
    for (;;) {
      const std::function<void(unsigned)>* fn;
      {
        std::unique_lock<std::mutex> l(m_);
        cv_.wait(l, [&] { return gen_ != seen; });
        seen = gen_;
        if (stop_) return;
        fn = fn_;
      }
      std::exception_ptr e;
      try { (*fn)(i); } catch (...) { e = std::current_exception(); }
      std::lock_guard<std::mutex> l(m_);
      if (e && !error_) error_ = e;
      if (--pending_ == 0) done_.notify_one();
    }
  }
  unsigned n_;
  bool parallel_ = true, stop_ = false;
  uint64_t gen_ = 0;
  unsigned pending_ = 0;
  const std::function<void(unsigned)>* fn_ = nullptr;
  std::exception_ptr error_;
  std::mutex m_;
  std::condition_variable cv_, done_;
  std::vector<std::thread> workers_;
};

inline RankPool& rank_pool() { static RankPool pool(8); return pool; }
