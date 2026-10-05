// ---------------------------------------------------------------------------
// Verilator checker for OR64, the operand receiver.
//
// The second, independently written checker of rtl/test/a3_receiver_top.sv.
// It reads the case table and the expected activation window from the FILES
// the top reads, not from the design, and compares the delivered window word
// for word.  Like the Icarus checker it predicts no readiness delay: the
// delay is a measurement, and both simulators must report the same one
// because the top is deterministic and the stimulus is inside it.
//
// The line format is transcribed identically in rtl/test/tb_a3_receiver.sv.
// ---------------------------------------------------------------------------
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "Vot_a3_receiver_top.h"
#include "verilated.h"

namespace {

constexpr unsigned kCaseStride = 24;
constexpr unsigned kGuard = 200000;

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
    Vot_a3_receiver_top dut;

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
        dut.root_rd_addr = 0;
        dut.expect_rd_addr = 0;
        dut.meta_rd_addr = 0;
        dut.act_rd_addr = 0;
        dut.trace_rd_addr = 0;
        for (unsigned i = 0; i < 6; ++i) step();
        dut.rst_n = 1;
        for (unsigned i = 0; i < 4; ++i) step();
    }
    uint32_t act(unsigned addr) {
        dut.act_rd_addr = addr;
        dut.eval();
        return dut.act_rd_data;
    }
    uint32_t trace(unsigned addr) {
        dut.trace_rd_addr = addr;
        dut.eval();
        return dut.trace_rd_data;
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

    const std::vector<uint32_t> cases = read_hex("or_case.hex");
    const std::vector<uint32_t> expect = read_hex("or_expect.hex");
    const std::vector<uint32_t> meta = read_hex("or_meta.hex");
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
    unsigned long total_words = 0;
    unsigned long total_slices = 0;
    for (unsigned index = 0; index < case_count; ++index) {
        const uint32_t* w = cases.data() + static_cast<size_t>(index) * kCaseStride;
        const unsigned blocks = w[0];
        const unsigned group = w[2];
        const unsigned act_base = w[5];
        const unsigned inject = w[9];
        const unsigned e_code = w[10];
        const unsigned e_detail = w[11];
        const unsigned e_tag = w[12];
        const unsigned e_words = w[13];
        const unsigned e_slices = w[14];
        const unsigned e_roots = w[15];
        const unsigned e_sat = w[16];
        const unsigned act_expect_base = w[17];
        const unsigned act_window = w[18];
        const unsigned gap = w[20];

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
        v.eq(3, model.dut.obs_error_tag, e_tag);
        v.eq(4, model.dut.obs_words_written, e_words);
        v.eq(5, model.dut.obs_slices_ready, e_slices);
        v.eq(6, model.dut.obs_act_ready_kblocks, e_slices);
        v.eq(7, model.dut.obs_roots_count, e_roots);
        v.eq(8, model.dut.obs_saturation_count, e_sat);
        v.eq(9, model.dut.obs_timeout, 0);
        v.eq(10, model.dut.obs_done_pulses, 1);
        v.eq(11, model.dut.obs_busy ? 1 : 0, 0);
        v.eq(12, model.dut.obs_scale_writes, 0);
        for (unsigned n = 0; n < act_window; ++n) {
            const size_t lo = act_expect_base + 2 * n;
            v.eq(13, model.act(2 * (act_base + n)), lo < expect.size() ? expect[lo] : 0u);
            v.eq(14, model.act(2 * (act_base + n) + 1),
                 lo + 1 < expect.size() ? expect[lo + 1] : 0u);
        }
        const uint32_t delay = model.trace(0);
        if (e_slices > 0) {
            ++v.checks;
            if (delay == 0xffffffffu && v.code == 0) v.code = 15;
        }
        total_words += e_words;
        total_slices += e_slices;
        if (guard >= kGuard && v.code == 0) v.code = 16;
        checks += v.checks;
        if (v.code != 0) ++failures;

        std::printf(
            "RCASE %u %s site=%d words=%u slices=%u roots=%u sat=%u code=%u "
            "detail=%u tag=%u ready=%u delay=%u blocks=%u group=%u gap=%u inject=%u\n",
            index, v.code == 0 ? "OK" : "DIVERGE", v.code, model.dut.obs_words_written,
            model.dut.obs_slices_ready, model.dut.obs_roots_count,
            model.dut.obs_saturation_count, model.dut.obs_error_code,
            model.dut.obs_error_detail, model.dut.obs_error_tag,
            model.dut.obs_act_ready_kblocks, delay, blocks, group, gap, inject);
        model.step();
    }
    model.dut.final();

    std::printf("CHECKS: %lu\n", checks);
    if (failures == 0) {
        std::printf("PASS: ABI3 operand receiver cases=%u words=%lu slices=%lu\n",
                    case_count, total_words, total_slices);
        return 0;
    }
    std::printf("FAILURES: %u\n", failures);
    std::cerr << "FAIL: the receiver disagreed with the case table\n";
    return 1;
}
