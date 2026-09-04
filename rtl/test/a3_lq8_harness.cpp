// ---------------------------------------------------------------------------
// Verilator checker for the LQ8 lane block (results/rtl/abi3_lq8.json).
//
// The second of the two independently written checkers over the same RTL and
// the same generated images.  It shares no code with rtl/test/tb_a3_lq8.sv:
// it loads the expectation image itself, sequences the block and the single
// reference lane itself, counts what it actually checked, and prints the
// marker only if its own counts equal the totals the image declares.
//
// Record layout, expectation image and markers are documented in the Icarus
// checker; the two must agree on them and on nothing else.
// ---------------------------------------------------------------------------
#include "Vot_a3_lq8_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr int kCaseStride = 128;
constexpr uint32_t kUnwritten = 0xdeadbeefu;
constexpr uint32_t kFlagRate = 0x1u;
constexpr uint32_t kFlagBlockRefused = 0x4u;

long failures = 0;
long checks = 0;
uint32_t current_case = 0;
int current_lane = -1;

void report(const char* label, uint64_t got, uint64_t want) {
    ++checks;
    if (got == want) return;
    ++failures;
    if (failures < 40) {
        std::printf("FAIL: case %u lane %d %s got %llu want %llu\n", current_case, current_lane,
                    label, static_cast<unsigned long long>(got),
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

void tick(Vot_a3_lq8_top& top) {
    top.clk = 0;
    top.eval();
    top.clk = 1;
    top.eval();
}

void settle(Vot_a3_lq8_top& top) { top.eval(); }

uint32_t case_word(Vot_a3_lq8_top& top, uint32_t index, int field) {
    top.case_rd_addr = index * kCaseStride + static_cast<uint32_t>(field);
    settle(top);
    return top.case_rd_data;
}

uint32_t meta_word(Vot_a3_lq8_top& top, int index) {
    top.meta_rd_addr = static_cast<uint32_t>(index);
    settle(top);
    return top.meta_rd_data;
}

struct RunStats {
    long total_cycles = 0;
    long retired = 0;
    long first_retire = -1;
    long last_retire = -1;
    bool completed = false;
};

// Run the block.  Outputs are sampled after the rising edge of each cycle, so
// the retire count and the counters are the registered values of that cycle.
RunStats launch_dut(Vot_a3_lq8_top& top) {
    RunStats stats;
    top.start_dut = 1;
    tick(top);
    top.start_dut = 0;
    long cycle = 0;
    while (top.dut_done == 0 && cycle < 60000000L) {
        const int retiring = top.dut_retire_count;
        if (retiring != 0) {
            stats.retired += retiring;
            if (stats.first_retire < 0) stats.first_retire = cycle;
            stats.last_retire = cycle;
        }
        tick(top);
        ++cycle;
    }
    stats.total_cycles = cycle;
    stats.completed = top.dut_done != 0;
    if (!stats.completed) {
        ++failures;
        std::printf("FAIL: case %u lane block never completed\n", current_case);
    }
    return stats;
}

void launch_ref(Vot_a3_lq8_top& top) {
    top.start_ref = 1;
    tick(top);
    top.start_ref = 0;
    long guard = 0;
    while (top.ref_done == 0 && guard < 60000000L) {
        tick(top);
        ++guard;
    }
    if (top.ref_done == 0) {
        ++failures;
        std::printf("FAIL: case %u lane %d reference lane never completed\n", current_case,
                    current_lane);
    }
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_a3_lq8_top top;

    const std::vector<uint32_t> expect = load_hex32("lq8_expect.hex");

    top.rst_n = 0;
    top.start_dut = 0;
    top.start_ref = 0;
    for (int i = 0; i < 4; ++i) tick(top);
    top.rst_n = 1;
    for (int i = 0; i < 2; ++i) tick(top);

    const uint32_t meta_cases = meta_word(top, 0);
    const uint32_t meta_lane_ops = meta_word(top, 1);
    const uint32_t meta_products = meta_word(top, 2);
    const uint32_t meta_outputs = meta_word(top, 3);
    const uint32_t meta_faults = meta_word(top, 4);
    const uint32_t meta_reference = meta_word(top, 5);
    const uint32_t meta_stride = meta_word(top, 6);
    const uint32_t meta_ref_outputs = meta_word(top, 7);
    const uint32_t meta_lanes = meta_word(top, 8);
    const uint32_t adder_stages = top.adder_stages;
    const uint32_t lanes = top.lanes;
    const uint32_t region_words = top.region_words;

    current_case = 0xffffffffu;
    report("lane count in image", meta_lanes, lanes);

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
            field[slot] = case_word(top, index, slot);
        }
        current_case = field[29];
        current_lane = -1;

        top.cfg_rows = static_cast<uint16_t>(field[0]);
        top.cfg_cols = static_cast<uint16_t>(field[1]);
        top.cfg_depth = static_cast<uint16_t>(field[2]);
        top.cfg_dtype_a = static_cast<uint8_t>(field[3]);
        top.cfg_dtype_b = static_cast<uint8_t>(field[4]);
        top.cfg_group = static_cast<uint8_t>(field[5]);
        top.cfg_a_base = field[6];
        top.cfg_w_base = field[7];
        top.cfg_scale_a = static_cast<uint8_t>(field[8] & 1u);
        top.cfg_scale_b = static_cast<uint8_t>(field[9] & 1u);
        top.cfg_block_a = static_cast<uint16_t>(field[10]);
        top.cfg_block_b = static_cast<uint16_t>(field[11]);
        top.cfg_block_rows_a = static_cast<uint16_t>(field[12]);
        top.cfg_scale_a_base = field[14];
        top.cfg_ws_base = field[15];
        top.cfg_out_base = field[16];
        top.cfg_out_fp32 = static_cast<uint8_t>(field[17] & 1u);

        const RunStats stats = launch_dut(top);
        const uint32_t window = field[30];
        const uint32_t expect_offset = field[27];
        const bool refused = (field[28] & kFlagBlockRefused) != 0;

        ++counted_cases;
        if (field[18] != 0) ++counted_faults;

        report("block error_code", top.dut_error_code, field[18]);
        report("block error_detail", top.dut_error_detail, field[19]);
        report("block error_lane", top.dut_error_lane, field[20]);
        report("block out_count", top.dut_out_count, field[21]);
        report("block saturation_count", top.dut_saturation_count, field[22]);
        report("block mac_count", top.dut_mac_count, field[23]);
        report("block product_count", top.dut_product_count, field[24]);
        report("block retired lane-ops", static_cast<uint64_t>(stats.retired), field[23]);
        report("lockstep violations", top.lockstep_violations, 0);
        counted_lane_ops += top.dut_mac_count;
        counted_products += top.dut_product_count;

        if (field[28] & kFlagRate) {
            const long rate_window =
                stats.retired > 0 ? (stats.last_retire - stats.first_retire + 1) : 0;
            std::printf(
                "RATE: case=%u lane_ops=%ld products=%u total_cycles=%ld window_cycles=%ld "
                "first_retire=%ld last_retire=%ld lanes=%u\n",
                current_case, stats.retired, top.dut_product_count, stats.total_cycles,
                rate_window, stats.first_retire, stats.last_retire, lanes);
        }

        for (uint32_t lane = 0; lane < lanes; ++lane) {
            current_lane = static_cast<int>(lane);
            top.lane_rd_sel = static_cast<uint8_t>(lane);
            settle(top);
            if (!refused) {
                report("lane error_code", top.lane_rd_error_code, field[56 + lane]);
                report("lane error_detail", top.lane_rd_error_detail, field[64 + lane]);
                report("lane out_count", top.lane_rd_out_count, field[88 + lane]);
                report("lane saturation_count", top.lane_rd_saturation_count, field[96 + lane]);
                report("lane mac_count", top.lane_rd_mac_count, field[72 + lane]);
                report("lane product_count", top.lane_rd_product_count, field[80 + lane]);
            }
            const uint32_t written = field[48 + lane];
            for (uint32_t element = 0; element < window; ++element) {
                top.res_rd_addr = lane * region_words + field[16] + element;
                settle(top);
                const uint32_t got_out = top.dut_res_rd_data;
                const uint32_t got_acc = top.dut_acc_rd_data;
                const size_t base = expect_offset + lane * 2 * window + 2 * element;
                const uint32_t want_out = expect.at(base);
                const uint32_t want_acc = expect.at(base + 1);
                checks += 2;
                if (element < written) {
                    ++counted_outputs;
                    if (got_out != want_out || got_acc != want_acc) {
                        ++failures;
                        if (failures < 40) {
                            std::printf(
                                "FAIL: case %u lane %u element %u block got %08x/%08x want %08x/%08x\n",
                                current_case, lane, element, got_out, got_acc, want_out, want_acc);
                        }
                    }
                } else if (got_out != kUnwritten || got_acc != kUnwritten) {
                    ++failures;
                    if (failures < 40) {
                        std::printf(
                            "FAIL: case %u lane %u element %u written by the block after a refusal: %08x/%08x\n",
                            current_case, lane, element, got_out, got_acc);
                    }
                }
            }
        }

        if (field[25] != 0) {
            ++counted_reference;
            for (uint32_t lane = 0; lane < lanes; ++lane) {
                current_lane = static_cast<int>(lane);
                top.ref_cfg_cols = static_cast<uint16_t>(field[26]);
                top.ref_cfg_b_base = field[32 + lane];
                top.ref_cfg_scale_b_base = field[40 + lane];
                top.ref_lane = static_cast<uint8_t>(lane);
                launch_ref(top);
                report("ref error_code", top.ref_error_code, field[56 + lane]);
                report("ref error_detail", top.ref_error_detail, field[64 + lane]);
                report("ref out_count", top.ref_out_count, field[88 + lane]);
                report("ref saturation_count", top.ref_saturation_count, field[96 + lane]);
                report("ref mac_count", top.ref_mac_count, field[72 + lane]);
                report("ref product_count", top.ref_product_count, field[80 + lane]);
                top.lane_rd_sel = static_cast<uint8_t>(lane);
                settle(top);
                report("ref and block lane error class", top.ref_error_code, top.lane_rd_error_code);
                report("ref and block lane error detail", top.ref_error_detail,
                       top.lane_rd_error_detail);
                const uint32_t written = field[48 + lane];
                for (uint32_t element = 0; element < window; ++element) {
                    top.res_rd_addr = lane * region_words + field[16] + element;
                    settle(top);
                    const uint32_t got_out = top.dut_res_rd_data;
                    const uint32_t got_acc = top.dut_acc_rd_data;
                    const uint32_t got_ref_out = top.ref_res_rd_data;
                    const uint32_t got_ref_acc = top.ref_acc_rd_data;
                    const size_t base = expect_offset + lane * 2 * window + 2 * element;
                    const uint32_t want_out = expect.at(base);
                    const uint32_t want_acc = expect.at(base + 1);
                    checks += 2;
                    if (element < written) {
                        ++counted_ref_outputs;
                        if (got_ref_out != want_out || got_ref_acc != want_acc) {
                            ++failures;
                            if (failures < 40) {
                                std::printf(
                                    "FAIL: case %u lane %u element %u ref got %08x/%08x want %08x/%08x\n",
                                    current_case, lane, element, got_ref_out, got_ref_acc, want_out,
                                    want_acc);
                            }
                        }
                        checks += 2;
                        ++counted_identity;
                        if (got_out != got_ref_out || got_acc != got_ref_acc) {
                            ++failures;
                            if (failures < 40) {
                                std::printf(
                                    "FAIL: case %u lane %u element %u block %08x/%08x differs from ref %08x/%08x\n",
                                    current_case, lane, element, got_out, got_acc, got_ref_out,
                                    got_ref_acc);
                            }
                        }
                    } else if (got_ref_out != kUnwritten || got_ref_acc != kUnwritten) {
                        ++failures;
                        if (failures < 40) {
                            std::printf(
                                "FAIL: case %u lane %u element %u written by ref after a refusal: %08x/%08x\n",
                                current_case, lane, element, got_ref_out, got_ref_acc);
                        }
                    }
                }
            }
        }
    }

    current_case = 0xffffffffu;
    current_lane = -1;
    report("case count", counted_cases, meta_cases);
    report("lane-op count", counted_lane_ops, meta_lane_ops);
    report("product count", counted_products, meta_products);
    report("output count", counted_outputs, meta_outputs);
    report("fault case count", counted_faults, meta_faults);
    report("reference case count", counted_reference, meta_reference);
    report("reference output count", counted_ref_outputs, meta_ref_outputs);
    report("case stride", meta_stride, kCaseStride);
    report("final lockstep violations", top.lockstep_violations, 0);

    if (failures == 0) {
        std::printf(
            "PASS: ABI3 lq8 cases=%llu lane_ops=%llu products=%llu outputs=%llu faults=%llu "
            "reference_cases=%llu reference_outputs=%llu identity=%llu lanes=%u adder_stages=%u\n",
            static_cast<unsigned long long>(counted_cases),
            static_cast<unsigned long long>(counted_lane_ops),
            static_cast<unsigned long long>(counted_products),
            static_cast<unsigned long long>(counted_outputs),
            static_cast<unsigned long long>(counted_faults),
            static_cast<unsigned long long>(counted_reference),
            static_cast<unsigned long long>(counted_ref_outputs),
            static_cast<unsigned long long>(counted_identity), lanes, adder_stages);
        std::printf("checks=%ld\n", checks);
        return 0;
    }
    std::printf("FAILURES: %ld after checks=%ld\n", failures, checks);
    return 1;
}
