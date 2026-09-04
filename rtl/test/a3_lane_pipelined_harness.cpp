// ---------------------------------------------------------------------------
// Verilator checker for the pipelined contraction lane (gates D1, D2, D5).
//
// The second of the two independently written checkers over the same RTL and
// the same generated images.  It shares no code with
// rtl/test/tb_a3_lane_pipelined.sv: it loads the expectation image itself,
// sequences both lanes itself, counts what it actually checked, and prints the
// marker only if its own counts equal the totals the image declares.
//
// Record layout, expectation image and markers are documented in the Icarus
// checker; the two must agree on them and on nothing else.
// ---------------------------------------------------------------------------
#include "Vot_a3_lane_pipelined_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr int kCaseStride = 40;
constexpr uint32_t kUnwritten = 0xdeadbeefu;
constexpr uint32_t kFlagRate = 0x1u;

long failures = 0;
long checks = 0;
uint32_t current_case = 0;

void report(const char* label, uint64_t got, uint64_t want) {
    ++checks;
    if (got == want) return;
    ++failures;
    if (failures < 40) {
        std::printf("FAIL: case %u %s got %llu want %llu\n", current_case, label,
                    static_cast<unsigned long long>(got),
                    static_cast<unsigned long long>(want));
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

void tick(Vot_a3_lane_pipelined_top& dut) {
    dut.clk = 0;
    dut.eval();
    dut.clk = 1;
    dut.eval();
}

void settle(Vot_a3_lane_pipelined_top& dut) { dut.eval(); }

uint32_t case_word(Vot_a3_lane_pipelined_top& dut, uint32_t index, int field) {
    dut.case_rd_addr = index * kCaseStride + static_cast<uint32_t>(field);
    settle(dut);
    return dut.case_rd_data;
}

uint32_t meta_word(Vot_a3_lane_pipelined_top& dut, int index) {
    dut.meta_rd_addr = static_cast<uint32_t>(index);
    settle(dut);
    return dut.meta_rd_data;
}

struct RunStats {
    long total_cycles = 0;
    long retired = 0;
    long first_retire = -1;
    long last_retire = -1;
    bool completed = false;
};

// Run the design under test.  Outputs are sampled after the rising edge of
// each cycle, so the retire pulse and the counters are the registered values
// of that cycle.
RunStats launch_dut(Vot_a3_lane_pipelined_top& dut) {
    RunStats stats;
    dut.start_dut = 1;
    tick(dut);
    dut.start_dut = 0;
    long cycle = 0;
    while (dut.dut_done == 0 && cycle < 60000000L) {
        if (dut.dut_op_retire) {
            ++stats.retired;
            if (stats.first_retire < 0) stats.first_retire = cycle;
            stats.last_retire = cycle;
        }
        tick(dut);
        ++cycle;
    }
    stats.total_cycles = cycle;
    stats.completed = dut.dut_done != 0;
    if (!stats.completed) {
        ++failures;
        std::printf("FAIL: case %u pipelined lane never completed\n", current_case);
    }
    return stats;
}

void launch_ref(Vot_a3_lane_pipelined_top& dut) {
    dut.start_ref = 1;
    tick(dut);
    dut.start_ref = 0;
    long guard = 0;
    while (dut.ref_done == 0 && guard < 400000000L) {
        tick(dut);
        ++guard;
    }
    if (dut.ref_done == 0) {
        ++failures;
        std::printf("FAIL: case %u sequential reference lane never completed\n",
                    current_case);
    }
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_a3_lane_pipelined_top dut;

    const std::vector<uint32_t> expect = load_hex32("lane_expect.hex");

    dut.rst_n = 0;
    dut.start_dut = 0;
    dut.start_ref = 0;
    for (int i = 0; i < 4; ++i) tick(dut);
    dut.rst_n = 1;
    for (int i = 0; i < 2; ++i) tick(dut);

    const uint32_t meta_cases = meta_word(dut, 0);
    const uint32_t meta_lane_ops = meta_word(dut, 1);
    const uint32_t meta_products = meta_word(dut, 2);
    const uint32_t meta_outputs = meta_word(dut, 3);
    const uint32_t meta_faults = meta_word(dut, 4);
    const uint32_t meta_reference = meta_word(dut, 5);
    const uint32_t meta_stride = meta_word(dut, 6);
    const uint32_t meta_ref_outputs = meta_word(dut, 7);
    const uint32_t adder_stages = dut.adder_stages;

    uint64_t counted_cases = 0;
    uint64_t counted_lane_ops = 0;
    uint64_t counted_products = 0;
    uint64_t counted_outputs = 0;
    uint64_t counted_faults = 0;
    uint64_t counted_reference = 0;
    uint64_t counted_ref_outputs = 0;
    uint64_t counted_identity = 0;

    for (uint32_t index = 0; index < meta_cases; ++index) {
        uint32_t field[kCaseStride];
        for (int slot = 0; slot < kCaseStride; ++slot) {
            field[slot] = case_word(dut, index, slot);
        }
        current_case = field[33];

        dut.cfg_rows = static_cast<uint16_t>(field[0]);
        dut.cfg_cols = static_cast<uint16_t>(field[1]);
        dut.cfg_depth = static_cast<uint16_t>(field[2]);
        dut.cfg_dtype_a = static_cast<uint8_t>(field[3]);
        dut.cfg_dtype_b = static_cast<uint8_t>(field[4]);
        dut.cfg_group = static_cast<uint8_t>(field[5]);
        dut.cfg_a_base = field[6];
        dut.cfg_b_base = field[7];
        dut.cfg_scale_a = static_cast<uint8_t>(field[8] & 1u);
        dut.cfg_scale_b = static_cast<uint8_t>(field[9] & 1u);
        dut.cfg_block_a = static_cast<uint16_t>(field[10]);
        dut.cfg_block_b = static_cast<uint16_t>(field[11]);
        dut.cfg_block_rows_a = static_cast<uint16_t>(field[12]);
        dut.cfg_block_rows_b = static_cast<uint16_t>(field[13]);
        dut.cfg_scale_a_base = field[14];
        dut.cfg_scale_b_base = field[15];
        dut.cfg_out_base = field[16];
        dut.cfg_out_fp32 = static_cast<uint8_t>(field[17] & 1u);

        const RunStats stats = launch_dut(dut);

        ++counted_cases;
        if (field[18] != 0) ++counted_faults;

        report("dut error_code", dut.dut_error_code, field[18]);
        report("dut error_detail", dut.dut_error_detail, field[19]);
        report("dut out_count", dut.dut_out_count, field[20]);
        report("dut saturation_count", dut.dut_saturation_count, field[21]);
        report("dut mac_count", dut.dut_mac_count, field[22]);
        report("dut product_count", dut.dut_product_count, field[23]);
        report("dut retired lane-ops", static_cast<uint64_t>(stats.retired), field[22]);
        counted_lane_ops += dut.dut_mac_count;
        counted_products += dut.dut_product_count;

        if (field[32] & kFlagRate) {
            const long window =
                stats.retired > 0 ? (stats.last_retire - stats.first_retire + 1) : 0;
            std::printf(
                "RATE: case=%u lane_ops=%ld products=%u total_cycles=%ld "
                "window_cycles=%ld first_retire=%ld last_retire=%ld\n",
                current_case, stats.retired, dut.dut_product_count,
                stats.total_cycles, window, stats.first_retire, stats.last_retire);
        }

        const uint32_t window = field[34];
        const uint32_t expect_offset = field[31];
        const uint32_t dut_written = field[24];
        for (uint32_t element = 0; element < window; ++element) {
            dut.res_rd_addr = field[16] + element;
            settle(dut);
            const uint32_t got_out = dut.dut_res_rd_data;
            const uint32_t got_acc = dut.dut_acc_rd_data;
            const uint32_t want_out = expect.at(expect_offset + 2 * element);
            const uint32_t want_acc = expect.at(expect_offset + 2 * element + 1);
            checks += 2;
            if (element < dut_written) {
                ++counted_outputs;
                if (got_out != want_out || got_acc != want_acc) {
                    ++failures;
                    if (failures < 40) {
                        std::printf(
                            "FAIL: case %u element %u dut got %08x/%08x want %08x/%08x\n",
                            current_case, element, got_out, got_acc, want_out, want_acc);
                    }
                }
            } else if (got_out != kUnwritten || got_acc != kUnwritten) {
                ++failures;
                if (failures < 40) {
                    std::printf(
                        "FAIL: case %u element %u written by dut after a refusal: %08x/%08x\n",
                        current_case, element, got_out, got_acc);
                }
            }
        }

        if (field[25] != 0) {
            launch_ref(dut);
            ++counted_reference;
            report("ref error_code", dut.ref_error_code, field[26]);
            report("ref out_count", dut.ref_out_count, field[27]);
            report("ref saturation_count", dut.ref_saturation_count, field[28]);
            report("ref mac_count", dut.ref_mac_count, field[29]);
            report("ref and dut error class", dut.ref_error_code, dut.dut_error_code);
            const uint32_t ref_written = field[30];
            for (uint32_t element = 0; element < window; ++element) {
                dut.res_rd_addr = field[16] + element;
                settle(dut);
                const uint32_t got_out = dut.dut_res_rd_data;
                const uint32_t got_acc = dut.dut_acc_rd_data;
                const uint32_t got_ref_out = dut.ref_res_rd_data;
                const uint32_t got_ref_acc = dut.ref_acc_rd_data;
                const uint32_t want_out = expect.at(expect_offset + 2 * element);
                const uint32_t want_acc = expect.at(expect_offset + 2 * element + 1);
                checks += 2;
                if (element < ref_written) {
                    ++counted_ref_outputs;
                    if (got_ref_out != want_out || got_ref_acc != want_acc) {
                        ++failures;
                        if (failures < 40) {
                            std::printf(
                                "FAIL: case %u element %u ref got %08x/%08x want %08x/%08x\n",
                                current_case, element, got_ref_out, got_ref_acc,
                                want_out, want_acc);
                        }
                    }
                } else if (got_ref_out != kUnwritten || got_ref_acc != kUnwritten) {
                    ++failures;
                    if (failures < 40) {
                        std::printf(
                            "FAIL: case %u element %u written by ref after a refusal: %08x/%08x\n",
                            current_case, element, got_ref_out, got_ref_acc);
                    }
                }
                if (element < dut_written && element < ref_written) {
                    checks += 2;
                    ++counted_identity;
                    if (got_out != got_ref_out || got_acc != got_ref_acc) {
                        ++failures;
                        if (failures < 40) {
                            std::printf(
                                "FAIL: case %u element %u dut %08x/%08x differs from ref %08x/%08x\n",
                                current_case, element, got_out, got_acc, got_ref_out,
                                got_ref_acc);
                        }
                    }
                }
            }
        }
    }

    current_case = 0xffffffffu;
    report("case count", counted_cases, meta_cases);
    report("lane-op count", counted_lane_ops, meta_lane_ops);
    report("product count", counted_products, meta_products);
    report("output count", counted_outputs, meta_outputs);
    report("fault case count", counted_faults, meta_faults);
    report("reference case count", counted_reference, meta_reference);
    report("reference output count", counted_ref_outputs, meta_ref_outputs);
    report("case stride", meta_stride, kCaseStride);

    if (failures == 0) {
        std::printf(
            "PASS: ABI3 pipelined lane cases=%llu lane_ops=%llu products=%llu "
            "outputs=%llu faults=%llu reference_cases=%llu reference_outputs=%llu "
            "identity=%llu adder_stages=%u\n",
            static_cast<unsigned long long>(counted_cases),
            static_cast<unsigned long long>(counted_lane_ops),
            static_cast<unsigned long long>(counted_products),
            static_cast<unsigned long long>(counted_outputs),
            static_cast<unsigned long long>(counted_faults),
            static_cast<unsigned long long>(counted_reference),
            static_cast<unsigned long long>(counted_ref_outputs),
            static_cast<unsigned long long>(counted_identity), adder_stages);
        std::printf("checks=%ld\n", checks);
        return 0;
    }
    std::printf("FAILURES: %ld after checks=%ld\n", failures, checks);
    return 1;
}
