// ---------------------------------------------------------------------------
// Verilator checker for PC64, the partial collector.
//
// The second, independently written checker of rtl/test/a3_collector_top.sv.
// It reads the case table, the partial image and the root expectations from
// the FILES the top reads, not from the design, and reconstructs every leaf
// vector from the partial image itself: vector v is slot (lane = v / elems,
// element = v mod elems) and its leaf k is K-block k's partial of that slot.
// That is the transposition the collector exists to perform, restated
// independently rather than read out of the block.
//
// The line format is transcribed identically in rtl/test/tb_a3_collector.sv.
// ---------------------------------------------------------------------------
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "Vot_a3_collector_top.h"
#include "verilated.h"

namespace {

constexpr unsigned kCaseStride = 24;
constexpr unsigned kTileLanes = 64;
constexpr unsigned kLeaves = 8;
constexpr unsigned kVecStride = kLeaves + 2;
constexpr unsigned kGuard = 2000000;

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
    Vot_a3_collector_top dut;

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
        dut.part_rd_addr = 0;
        dut.case_rd_addr = 0;
        dut.expect_rd_addr = 0;
        dut.meta_rd_addr = 0;
        dut.vec_rd_addr = 0;
        dut.root_rd_addr = 0;
        for (unsigned i = 0; i < 6; ++i) step();
        dut.rst_n = 1;
        for (unsigned i = 0; i < 4; ++i) step();
    }

    uint32_t vec(unsigned addr) {
        dut.vec_rd_addr = addr;
        dut.eval();
        return dut.vec_rd_data;
    }
    uint32_t root(unsigned addr) {
        dut.root_rd_addr = addr;
        dut.eval();
        return dut.root_rd_data;
    }
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

    const std::vector<uint32_t> cases = read_hex("pc_case.hex");
    const std::vector<uint32_t> part = read_hex("pc_part.hex");
    const std::vector<uint32_t> expect = read_hex("pc_expect.hex");
    const std::vector<uint32_t> meta = read_hex("pc_meta.hex");
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
    unsigned long total_vectors = 0;
    unsigned long total_roots = 0;
    for (unsigned index = 0; index < case_count; ++index) {
        const uint32_t* w = cases.data() + static_cast<size_t>(index) * kCaseStride;
        const unsigned blocks = w[0];
        const unsigned elems = w[1];
        const unsigned part_base = w[3];
        const unsigned mode = w[4];
        const unsigned inject = w[5];
        const unsigned e_code = w[8];
        const unsigned e_detail = w[9];
        const unsigned e_lane = w[10];
        const unsigned e_slot = w[11];
        const unsigned e_vectors = w[12];
        const unsigned e_captured = w[13];
        const unsigned e_roots = w[14];
        const unsigned root_base = w[15];

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
        v.eq(1, model.dut.obs_error_code, e_code);
        v.eq(2, model.dut.obs_error_detail, e_detail);
        v.eq(3, model.dut.obs_error_lane, e_lane);
        v.eq(4, model.dut.obs_error_slot, e_slot);
        v.eq(5, model.dut.obs_vectors, e_vectors);
        v.eq(6, model.dut.obs_captured, e_captured);
        v.eq(7, model.dut.obs_roots, e_roots);
        v.eq(8, model.dut.obs_vectors_count, e_vectors);
        v.eq(9, model.dut.obs_tag_order_errors, 0);
        v.eq(10, model.dut.obs_timeout, 0);
        v.eq(11, model.dut.obs_done_pulses, 1);
        v.eq(12, model.dut.obs_tree_error_code, 0);
        v.eq(13, model.dut.obs_busy ? 1 : 0, 0);
        const unsigned vectors = model.dut.obs_vectors;
        for (unsigned n = 0; n < vectors && n < e_vectors; ++n) {
            const unsigned lane = n / elems;
            const unsigned elem = n % elems;
            for (unsigned k = 0; k < blocks; ++k) {
                const size_t src = part_base + (k * elems + elem) * kTileLanes + lane;
                const uint32_t want = src < part.size() ? part[src] : 0u;
                v.eq(14, model.vec(n * kVecStride + k), want);
            }
            v.eq(15, model.vec(n * kVecStride + kLeaves), n);
            v.eq(16, model.vec(n * kVecStride + kLeaves + 1), blocks);
            ++total_vectors;
        }
        const unsigned roots = model.dut.obs_roots;
        for (unsigned n = 0; n < roots && n < e_roots; ++n) {
            const size_t src = root_base + 2 * n;
            v.eq(17, model.root(2 * n), src < expect.size() ? expect[src] : 0u);
            v.eq(18, model.root(2 * n + 1),
                 src + 1 < expect.size() ? expect[src + 1] : 0u);
            ++total_roots;
        }
        if (guard >= kGuard && v.code == 0) v.code = 19;
        checks += v.checks;
        if (v.code != 0) ++failures;

        std::printf(
            "CCASE %u %s site=%d vectors=%u roots=%u captured=%u code=%u "
            "detail=%u lane=%u slot=%u blocks=%u elems=%u mode=%u inject=%u\n",
            index, v.code == 0 ? "OK" : "DIVERGE", v.code, model.dut.obs_vectors,
            model.dut.obs_roots, model.dut.obs_captured, model.dut.obs_error_code,
            model.dut.obs_error_detail, model.dut.obs_error_lane,
            model.dut.obs_error_slot, blocks, elems, mode, inject);
        model.step();
    }
    model.dut.final();

    std::printf("CHECKS: %lu\n", checks);
    if (failures == 0) {
        std::printf("PASS: ABI3 partial collector cases=%u vectors=%lu roots=%lu\n",
                    case_count, total_vectors, total_roots);
        return 0;
    }
    std::printf("FAILURES: %u\n", failures);
    std::cerr << "FAIL: the collector disagreed with the case table\n";
    return 1;
}
