// ot_qwen_nearhbm_exp_p == ot_hdc_exp_q and ot_qwen_nearhbm_recip_p == ot_hdc_recip_q (y and fault) on a range of the
// 2^32 binary32 inputs:  ./Vequiv <first> <count>  (the full domain is split across processes).
#include "Vot_qwen_nearhbm_sfu_equiv_top.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <deque>
int main(int argc, char** argv) {
    uint64_t first = strtoull(argv[1], 0, 0), count = strtoull(argv[2], 0, 0);
    Vot_qwen_nearhbm_sfu_equiv_top* t = new Vot_qwen_nearhbm_sfu_equiv_top;
    std::deque<uint64_t> eq, ep, rq, rp;      // {fault, y}
    t->rst_n = 0; t->v = 0; t->clk = 0; t->eval(); t->clk = 1; t->eval(); t->rst_n = 1;
    uint64_t sent = 0, bad = 0, ce = 0, cr = 0;
    auto cmp = [&](std::deque<uint64_t>& a, std::deque<uint64_t>& b, uint64_t& n, const char* w) {
        while (!a.empty() && !b.empty()) {
            if (a.front() != b.front()) { if (bad < 10) fprintf(stderr, "%s MISMATCH #%llu %llx %llx\n", w, (unsigned long long)(first + n), (unsigned long long)a.front(), (unsigned long long)b.front()); bad++; }
            a.pop_front(); b.pop_front(); n++;
        }
    };
    while (ce < count || cr < count) {
        t->v = sent < count; t->x = (uint32_t)(first + sent);
        t->clk = 0; t->eval(); t->clk = 1; t->eval();
        if (sent < count) sent++;
        if (t->eq_v) eq.push_back(((uint64_t)t->eq_f << 32) | t->eq_y);
        if (t->ep_v) ep.push_back(((uint64_t)t->ep_f << 32) | t->ep_y);
        if (t->rq_v) rq.push_back(((uint64_t)t->rq_f << 32) | t->rq_y);
        if (t->rp_v) rp.push_back(((uint64_t)t->rp_f << 32) | t->rp_y);
        cmp(eq, ep, ce, "exp"); cmp(rq, rp, cr, "recip");
    }
    printf("{\"first\": %llu, \"count\": %llu, \"exp_compared\": %llu, \"recip_compared\": %llu, \"mismatches\": %llu}\n",
           (unsigned long long)first, (unsigned long long)count, (unsigned long long)ce, (unsigned long long)cr, (unsigned long long)bad);
    delete t;
    return bad ? 1 : 0;
}
