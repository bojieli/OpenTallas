// ---------------------------------------------------------------------------
// Verilator checker for the RE8 pairwise-tree endpoint (results/rtl/abi3_re8.json).
//
// The second of the two independently written checkers over the same RTL and
// the same generated images.  It shares no code with rtl/test/tb_a3_re8.sv:
// it loads the vector image itself, sequences the endpoint itself, counts
// what it actually checked, and prints the marker only if its own counts
// equal the totals the image declares.
//
// Cycle accounting: inputs are set before tick k, the rising edge that
// samples them; outputs read after tick k are the registered values of that
// edge.  latency = k_out - k_in, the rising edges from the edge that sampled
// the first vector to the edge at which its result is registered.
//
// Record, vector and marker layouts are documented in the Icarus checker; the
// two must agree on them and on nothing else.
// ---------------------------------------------------------------------------
#include "Vot_a3_re8_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr int kCaseStride = 16;
constexpr int kVecStride = 12;
constexpr int kLeaves = 8;
constexpr uint32_t kFlagFault = 0x2u;
constexpr uint32_t kFlagRate = 0x4u;
constexpr uint32_t kFlagSingle = 0x8u;
constexpr uint32_t kVecFlagExpect = 0x2u;
constexpr int kDrain = 32;

long failures = 0;
long checks = 0;
uint32_t current_case = 0;

void report(const char* label, uint64_t got, uint64_t want) {
    ++checks;
    if (got == want) return;
    ++failures;
    if (failures < 40) {
        std::printf("FAIL: case %u %s got %llu want %llu\n", current_case, label,
                    static_cast<unsigned long long>(got), static_cast<unsigned long long>(want));
    }
}

std::vector<uint32_t> load_hex32(const char* path) {
    std::ifstream stream(path);
    if (!stream) {
        std::printf("FAIL: cannot open %s\n", path);
        std::exit(1);
    }
    std::vector<uint32_t> words;
    std::string line;
    while (std::getline(stream, line)) {
        if (line.empty()) continue;
        words.push_back(static_cast<uint32_t>(std::stoul(line, nullptr, 16)));
    }
    return words;
}

void tick(Vot_a3_re8_top& top) {
    top.clk = 0;
    top.eval();
    top.clk = 1;
    top.eval();
}

uint32_t meta_word(Vot_a3_re8_top& top, int index) {
    top.meta_rd_addr = static_cast<uint32_t>(index);
    top.eval();
    return top.meta_rd_data;
}

uint32_t case_word(Vot_a3_re8_top& top, uint32_t index, int field) {
    top.case_rd_addr = index * kCaseStride + static_cast<uint32_t>(field);
    top.eval();
    return top.case_rd_data;
}

struct Run {
    long outputs = 0;
    long first_in = -1;
    long first_out = -1;
    long last_out = -1;
    size_t expect_index = 0;
    uint32_t vec_base = 0;
    uint32_t vec_count = 0;
};

// Expected code of the next output: the next vector flagged expect, in order.
uint32_t next_expected(const std::vector<uint32_t>& image, Run& run) {
    for (; run.expect_index < run.vec_count; ++run.expect_index) {
        const size_t base = (run.vec_base + run.expect_index) * kVecStride;
        if (image.at(base + 2) & kVecFlagExpect) {
            const uint32_t want = image.at(base + 11);
            ++run.expect_index;
            return want;
        }
    }
    return 0xdeadbeefu;
}

void drive(Vot_a3_re8_top& top, const std::vector<uint32_t>& image, uint32_t vector) {
    const size_t base = vector * kVecStride;
    top.in_valid = 1;
    top.in_leaf_count = static_cast<uint8_t>(image.at(base) & 0xFu);
    top.in_tag = static_cast<uint16_t>(image.at(base + 1));
    top.in_last = static_cast<uint8_t>(image.at(base + 2) & 1u);
    for (int k = 0; k < kLeaves; ++k) top.in_leaf[k] = image.at(base + 3 + k);
}

void sample(Vot_a3_re8_top& top, const std::vector<uint32_t>& image, Run& run, long cycle) {
    if (!top.out_valid) return;
    if (run.first_out < 0) run.first_out = cycle;
    run.last_out = cycle;
    ++run.outputs;
    const uint32_t want = next_expected(image, run);
    ++checks;
    if (top.out_data != want) {
        ++failures;
        if (failures < 40) {
            std::printf("FAIL: case %u output %ld tag %u got %08x want %08x\n", current_case,
                        run.outputs - 1, top.out_tag, top.out_data, want);
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_a3_re8_top top;
    const std::vector<uint32_t> image = load_hex32("re8_vec.hex");

    top.rst_n = 0;
    top.in_valid = 0;
    top.clear = 0;
    for (int i = 0; i < 4; ++i) tick(top);
    top.rst_n = 1;
    for (int i = 0; i < 2; ++i) tick(top);

    const uint32_t meta_cases = meta_word(top, 0);
    const uint32_t meta_vectors = meta_word(top, 1);
    const uint32_t meta_outputs = meta_word(top, 2);
    const uint32_t meta_faults = meta_word(top, 3);
    const uint32_t meta_adds = meta_word(top, 4);
    const uint32_t meta_combines = meta_word(top, 5);
    const uint32_t meta_case_stride = meta_word(top, 6);
    const uint32_t meta_vec_stride = meta_word(top, 7);
    const uint32_t adder_stages = top.adder_stages;
    const uint32_t leaves = top.leaves;

    current_case = 0xffffffffu;
    report("leaf count in image", leaves, kLeaves);
    report("case stride", meta_case_stride, kCaseStride);
    report("vector stride", meta_vec_stride, kVecStride);

    uint64_t counted_cases = 0, counted_vectors = 0, counted_outputs = 0, counted_faults = 0;
    uint64_t counted_adds = 0, counted_combines = 0;

    for (uint32_t index = 0; index < meta_cases; ++index) {
        uint32_t field[kCaseStride];
        for (int slot = 0; slot < kCaseStride; ++slot) field[slot] = case_word(top, index, slot);
        current_case = field[0];
        Run run;
        run.vec_base = field[1];
        run.vec_count = field[2];
        const uint32_t adds_before = top.adds_count;
        const uint32_t combines_before = top.combines_count;
        long cycle = 0;
        ++counted_cases;
        counted_vectors += run.vec_count;
        if (field[4] != 0) ++counted_faults;

        if (field[3] & kFlagSingle) {
            for (uint32_t v = 0; v < run.vec_count; ++v) {
                drive(top, image, run.vec_base + v);
                if (run.first_in < 0) run.first_in = cycle;
                tick(top);
                ++cycle;
                sample(top, image, run, cycle);
                top.in_valid = 0;
                for (int d = 0; d < kDrain; ++d) {
                    tick(top);
                    ++cycle;
                    sample(top, image, run, cycle);
                }
            }
        } else {
            for (uint32_t v = 0; v < run.vec_count; ++v) {
                drive(top, image, run.vec_base + v);
                if (run.first_in < 0) run.first_in = cycle;
                tick(top);
                ++cycle;
                sample(top, image, run, cycle);
            }
            top.in_valid = 0;
            for (int d = 0; d < kDrain; ++d) {
                tick(top);
                ++cycle;
                sample(top, image, run, cycle);
            }
        }

        report("outputs", static_cast<uint64_t>(run.outputs), field[8]);
        report("adds", top.adds_count - adds_before, field[9]);
        report("combines", top.combines_count - combines_before, field[10]);
        report("error_code", top.error_code, field[4]);
        report("error_detail", top.error_detail, field[5]);
        report("error_level", top.error_level, field[6]);
        report("error_tag", top.error_tag, field[7]);
        report("busy after drain", top.busy, 0);
        counted_outputs += static_cast<uint64_t>(run.outputs);
        counted_adds += top.adds_count - adds_before;
        counted_combines += top.combines_count - combines_before;

        if (field[3] & kFlagRate) {
            // The first vector was sampled at edge first_in + 1 (the tick after it was driven).
            std::printf(
                "RATE: case=%u vectors=%u outputs=%ld first_in=%ld first_out=%ld last_out=%ld "
                "latency_cycles=%ld window_cycles=%ld\n",
                current_case, run.vec_count, run.outputs, run.first_in, run.first_out, run.last_out,
                run.first_out - (run.first_in + 1),
                run.outputs > 0 ? (run.last_out - run.first_out + 1) : 0L);
        }

        if (field[4] != 0) {
            tick(top);
            top.clear = 1;
            tick(top);
            top.clear = 0;
            tick(top);
            report("error_code after clear", top.error_code, 0);
        }
    }

    current_case = 0xffffffffu;
    report("case count", counted_cases, meta_cases);
    report("vector count", counted_vectors, meta_vectors);
    report("output count", counted_outputs, meta_outputs);
    report("fault case count", counted_faults, meta_faults);
    report("adds total", counted_adds, meta_adds);
    report("combines total", counted_combines, meta_combines);

    if (failures == 0) {
        std::printf(
            "PASS: ABI3 re8 cases=%llu vectors=%llu outputs=%llu faults=%llu adds=%llu combines=%llu "
            "leaves=%u adder_stages=%u\n",
            static_cast<unsigned long long>(counted_cases), static_cast<unsigned long long>(counted_vectors),
            static_cast<unsigned long long>(counted_outputs), static_cast<unsigned long long>(counted_faults),
            static_cast<unsigned long long>(counted_adds), static_cast<unsigned long long>(counted_combines),
            leaves, adder_stages);
        std::printf("checks=%ld\n", checks);
        return 0;
    }
    std::printf("FAILURES: %ld after checks=%ld\n", failures, checks);
    return 1;
}
