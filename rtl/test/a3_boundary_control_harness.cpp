// ---------------------------------------------------------------------------
// Verilator checker for the dependent-boundary control probe.
//
// The second, independently written checker of
// rtl/test/a3_boundary_control_top.sv.  It reads the same case table the top
// reads -- from the file, not from the design -- so the two checkers agree on
// what was asked for without sharing a line of code, and it compares the
// protocol outcome of every case with the table's prediction.  Like the Icarus
// checker it predicts no cycle count: the cycles are the measurement, and both
// simulators must report the same ones because the top is deterministic and
// the stimulus is inside it.
//
// The line format is transcribed identically in
// rtl/test/tb_a3_boundary_control.sv.
// ---------------------------------------------------------------------------
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "Vot_a3_boundary_control_top.h"
#include "verilated.h"

namespace {

constexpr unsigned kCaseStride = 16;
constexpr unsigned kGuard = 400000;

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
    Vot_a3_boundary_control_top dut;

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
        dut.meta_rd_addr = 0;
        for (unsigned i = 0; i < 6; ++i) step();
        dut.rst_n = 1;
        for (unsigned i = 0; i < 4; ++i) step();
    }
};

// One case's verdict.  The site codes are the Icarus checker's, transcribed.
struct Verdict {
    unsigned checks = 0;
    int code = 0;
    void eq(int site, long long actual, long long expected) {
        ++checks;
        if (actual != expected && code == 0) code = site;
    }
};

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

    const std::vector<uint32_t> cases = read_hex("bc_case.hex");
    const std::vector<uint32_t> meta = read_hex("bc_meta.hex");
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
        const unsigned producers = w[0];
        const unsigned leave_pending = w[5];
        const unsigned dest_x = w[9];
        const unsigned expect_trap = w[10];
        const unsigned expect_ok = w[11];
        const unsigned unsignalled = w[12];
        const unsigned tag = w[13];

        model.dut.run_case = index;
        model.dut.run = 1;
        model.step();
        model.dut.run = 0;
        unsigned guard = 0;
        while (!model.dut.done && guard < kGuard) {
            model.step();
            ++guard;
        }
        if (!model.dut.done) {
            std::cerr << "FAIL: case " << index << " did not finish\n";
            return 1;
        }

        Verdict v;
        v.eq(1, model.dut.obs_trap_class, expect_trap);
        v.eq(2, model.dut.obs_wait_ok ? 1 : 0, expect_ok);
        v.eq(3, model.dut.obs_stalled ? 1 : 0, leave_pending ? 1 : 0);
        v.eq(4, model.dut.obs_timeout, 0);
        v.eq(5, model.dut.obs_protocol_error ? 1 : 0, 0);
        v.eq(6, model.dut.obs_signal_error ? 1 : 0, 0);
        v.eq(7, model.dut.obs_misroute ? 1 : 0, 0);
        v.eq(8, model.dut.obs_wait_count, 1);
        v.eq(9, model.dut.obs_signal_count, unsignalled ? 0 : producers);
        ++v.checks;
        if (model.dut.boundary_cycles == 0 && v.code == 0) v.code = 10;
        v.eq(11,
             static_cast<long long>(model.dut.span_retire) +
                 model.dut.span_mesh + model.dut.span_wait + model.dut.span_admit,
             model.dut.boundary_cycles);
        v.eq(12,
             static_cast<long long>(model.dut.boundary_cycles) - model.dut.span_mesh,
             model.dut.boundary_control_cycles);
        checks += v.checks;
        if (v.code != 0) ++failures;

        std::printf(
            "BCASE %u tag=%u %s site=%d boundary=%u control=%u retire=%u "
            "mesh=%u wait=%u admit=%u trap=%u ok=%u stalled=%u producers=%u "
            "hops=%u waits=%u signals=%u maxout=%u local=%u\n",
            index, tag, v.code == 0 ? "OK" : "DIVERGE", v.code,
            model.dut.boundary_cycles, model.dut.boundary_control_cycles,
            model.dut.span_retire, model.dut.span_mesh, model.dut.span_wait,
            model.dut.span_admit, model.dut.obs_trap_class,
            model.dut.obs_wait_ok ? 1u : 0u, model.dut.obs_stalled ? 1u : 0u,
            producers, dest_x, model.dut.obs_wait_count,
            model.dut.obs_signal_count, model.dut.obs_max_outstanding,
            model.dut.obs_mesh_local_deliveries);
        model.step();
    }
    model.dut.final();

    if (failures == 0) {
        std::printf(
            "PASS: ABI3 dependent-boundary control probe cases=%u checks=%lu\n",
            case_count, checks);
        return 0;
    }
    std::printf(
        "FAIL: ABI3 dependent-boundary control probe cases=%u checks=%lu failures=%u\n",
        case_count, checks, failures);
    std::cerr << "FAIL: the probe disagreed with the case table\n";
    return 1;
}
