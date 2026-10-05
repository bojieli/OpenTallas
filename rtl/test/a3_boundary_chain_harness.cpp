// ---------------------------------------------------------------------------
// Verilator checker for the two-tile dependent chain (section 13 item 13).
//
// The second, independently written checker of
// rtl/test/a3_boundary_chain_top.sv.  It reads the case table and the
// expectations from the FILES the top reads, not from the design, and checks
// the composition end to end: every root against the AM-E1 reference, every
// delivered activation word against the BF16 narrowing of that root, and every
// consumer partial against a case that was BUILT from those roots -- so a
// wrong value anywhere in the chain cannot reach the end unnoticed.
//
// Like the Icarus checker it predicts no cycle count.  The boundary is the
// measurement, and the campaign requires the two simulators to report the
// same one.
//
// The line format is transcribed identically in rtl/test/tb_a3_boundary_chain.sv.
// ---------------------------------------------------------------------------
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "Vot_a3_boundary_chain_top.h"
#include "verilated.h"

namespace {

constexpr unsigned kCaseStride = 32;
constexpr unsigned kTileLanes = 64;
constexpr unsigned kGuard = 4000000;

std::vector<uint32_t> read_hex(const char* path) {
    std::ifstream in(path);
    if (!in) {
        std::cerr << "FAIL: cannot open " << path << "\n";
        std::exit(2);
    }
    std::vector<uint32_t> words;
    std::string line;
    while (std::getline(in, line)) {
        std::string trimmed;
        for (char c : line) {
            if (std::isxdigit(static_cast<unsigned char>(c))) trimmed.push_back(c);
            else if (!trimmed.empty()) break;
        }
        if (trimmed.empty()) continue;
        words.push_back(static_cast<uint32_t>(std::stoul(trimmed, nullptr, 16)));
    }
    return words;
}

struct Model {
    Vot_a3_boundary_chain_top dut;

    void step() {
        dut.clk = 1;
        dut.eval();
        dut.clk = 0;
        dut.eval();
    }
    void reset() {
        dut.rst_n = 0;
        dut.run = 0;
        dut.run_case = 0;
        dut.case_rd_addr = 0;
        dut.expect_rd_addr = 0;
        dut.meta_rd_addr = 0;
        dut.root_rd_addr = 0;
        dut.act_rd_addr = 0;
        dut.res_rd_addr = 0;
        for (unsigned i = 0; i < 6; ++i) step();
        dut.rst_n = 1;
        for (unsigned i = 0; i < 4; ++i) step();
    }
    uint32_t root(unsigned a) { dut.root_rd_addr = a; dut.eval(); return dut.root_rd_data; }
    uint32_t act(unsigned a)  { dut.act_rd_addr = a;  dut.eval(); return dut.act_rd_data; }
    uint32_t res(unsigned a)  { dut.res_rd_addr = a;  dut.eval(); return dut.res_rd_data; }
};

struct Verdict {
    unsigned long checks = 0;
    int code = 0;
    void eq(int site, long long actual, long long expected) {
        ++checks;
        if (actual != expected && code == 0) code = site;
    }
};

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

    const std::vector<uint32_t> cases = read_hex("ch_case.hex");
    const std::vector<uint32_t> expect = read_hex("ch_expect.hex");
    const std::vector<uint32_t> meta = read_hex("ch_meta.hex");
    if (meta.empty() || meta[0] == 0) {
        std::cerr << "FAIL: the case table is empty\n";
        return 2;
    }
    const unsigned case_count = meta[0];
    if (cases.size() < static_cast<size_t>(case_count) * kCaseStride) {
        std::cerr << "FAIL: the case image is shorter than the case count\n";
        return 2;
    }

    Model model;
    model.reset();

    unsigned long checks = 0;
    unsigned failures = 0;
    for (unsigned index = 0; index < case_count; ++index) {
        const uint32_t* w = cases.data() + static_cast<size_t>(index) * kCaseStride;
        const unsigned blocks = w[4];
        const unsigned expect_base = w[26];

        model.dut.run_case = index;
        model.dut.run = 1;
        model.step();
        model.dut.run = 0;
        unsigned guard = 0;
        while (!model.dut.done && guard < kGuard) {
            model.step();
            ++guard;
        }

        Verdict v;
        v.eq(1, model.dut.obs_prod_error_code, 0);
        v.eq(2, model.dut.obs_cons_error_code, 0);
        v.eq(3, model.dut.obs_coll_error_code, 0);
        v.eq(4, model.dut.obs_tree_error_code, 0);
        v.eq(5, model.dut.obs_recv_error_code, 0);
        v.eq(6, model.dut.obs_prod_out_count, static_cast<long long>(blocks) * kTileLanes);
        v.eq(7, model.dut.obs_cons_out_count, kTileLanes);
        v.eq(8, model.dut.obs_coll_vectors, kTileLanes);
        v.eq(9, model.dut.obs_recv_words, kTileLanes);
        v.eq(10, model.dut.obs_act_ready, 1);
        v.eq(11, model.dut.obs_roots, kTileLanes);
        v.eq(12, model.dut.obs_laneop_before_ready, 0);
        v.eq(13, model.dut.obs_timeout, 0);
        v.eq(14, model.dut.obs_prod_underruns, 0);
        v.eq(15, model.dut.obs_cons_underruns, 0);
        for (unsigned lane = 0; lane < kTileLanes; ++lane) {
            const size_t r = expect_base + lane;
            const size_t a = expect_base + kTileLanes + lane;
            const size_t p = expect_base + 2 * kTileLanes + lane;
            v.eq(16, model.root(lane), r < expect.size() ? expect[r] : 0u);
            v.eq(17, model.act(2 * lane) & 0xFFFFu, a < expect.size() ? expect[a] : 0u);
            v.eq(18, model.res(4 * lane), p < expect.size() ? expect[p] : 0u);
        }
        ++v.checks;
        if (model.dut.boundary_cycles == 0 && v.code == 0) v.code = 19;
        v.eq(20,
             static_cast<long long>(model.dut.leg_collect) + model.dut.leg_tree +
                 model.dut.leg_receive + model.dut.leg_readiness +
                 model.dut.leg_admit + model.dut.leg_lane_admission,
             model.dut.boundary_cycles);
        v.eq(21,
             static_cast<long long>(model.dut.leg_collect) + model.dut.leg_tree +
                 model.dut.leg_receive + model.dut.leg_readiness + model.dut.leg_admit,
             model.dut.boundary_to_kblock_cycles);
        ++v.checks;
        if (model.dut.producer_kblock_cycles == 0 && v.code == 0) v.code = 22;
        if (guard >= kGuard && v.code == 0) v.code = 23;
        checks += v.checks;
        if (v.code != 0) ++failures;

        std::printf(
            "XCASE %u %s site=%d blocks=%u boundary=%u kblock=%u collect=%u "
            "tree=%u receive=%u ready=%u admit=%u laneadmit=%u firstroot=%u "
            "leafspan=%u prodcycles=%u prodkblock=%u roots=%u words=%u stages=%u\n",
            index, v.code == 0 ? "OK" : "DIVERGE", v.code, blocks,
            model.dut.boundary_cycles, model.dut.boundary_to_kblock_cycles,
            model.dut.leg_collect, model.dut.leg_tree, model.dut.leg_receive,
            model.dut.leg_readiness, model.dut.leg_admit,
            model.dut.leg_lane_admission, model.dut.endpoint_first_root_cycles,
            model.dut.leaf_span_cycles, model.dut.producer_cycles,
            model.dut.producer_kblock_cycles, model.dut.obs_roots,
            model.dut.obs_recv_words, model.dut.adder_stages_param);
        model.step();
    }
    model.dut.final();

    std::printf("CHECKS: %lu\n", checks);
    if (failures == 0) {
        std::printf("PASS: ABI3 two-tile dependent chain cases=%u\n", case_count);
        return 0;
    }
    std::printf("FAILURES: %u\n", failures);
    std::cerr << "FAIL: the chain disagreed with the reference\n";
    return 1;
}
