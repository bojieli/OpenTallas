// ---------------------------------------------------------------------------
// Verilator checker for the T64 tile (results/rtl/abi3_tile64.json).
//
// The second of the two independently written checkers over the same RTL and
// the same generated images.  It shares no code with rtl/test/tb_a3_tile64.sv:
// it loads the expectation image itself, sequences the tile, the environment
// models and the tree endpoint itself, counts what it actually checked, and
// prints the marker only if its own counts equal the totals the image
// declares.  Record, expectation and marker layouts are documented in the
// Icarus checker; the two must agree on them and on nothing else.
// ---------------------------------------------------------------------------
#include "Vot_a3_tile64_top.h"
#include "verilated.h"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr int kCaseStride = 320;
constexpr int kLanes = 64;
constexpr int kLeaves = 8;
constexpr uint32_t kUnwritten = 0xdeadbeefu;
constexpr uint32_t kDontCare = 0xffffffffu;
constexpr uint32_t kFlagRate = 0x1u;
constexpr uint32_t kFlagRefused = 0x4u;
constexpr uint32_t kFlagBlockUnchecked = 0x8u;
constexpr uint32_t kFlagSdnIgnore = 0x20u;

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

void tick(Vot_a3_tile64_top& top) {
    top.clk = 0;
    top.eval();
    top.clk = 1;
    top.eval();
}

uint32_t case_word(Vot_a3_tile64_top& top, uint32_t index, int field) {
    top.case_rd_addr = index * kCaseStride + static_cast<uint32_t>(field);
    top.eval();
    return top.case_rd_data;
}

uint32_t meta_word(Vot_a3_tile64_top& top, int index) {
    top.meta_rd_addr = static_cast<uint32_t>(index);
    top.eval();
    return top.meta_rd_data;
}

uint32_t result_word(Vot_a3_tile64_top& top, uint32_t address, uint32_t* acc) {
    top.res_rd_addr = address;
    top.eval();
    if (acc) *acc = top.acc_rd_data;
    return top.res_rd_data;
}

struct RunStats {
    long total_cycles = 0;
    long retired = 0;
    long first_retire = -1;
    long last_retire = -1;
    long kb_count = 0;
    long kb_min = -1;
    long kb_max = 0;
    long kb_sum = 0;
    bool completed = false;
};

// Outputs are sampled after each rising edge, so they are that edge's registered values.
RunStats launch(Vot_a3_tile64_top& top) {
    RunStats stats;
    top.op_start = 1;
    tick(top);
    top.op_start = 0;
    top.env_start = 1;
    tick(top);
    top.env_start = 0;
    long cycle = 2;
    long active = 0;
    while (top.dut_done == 0 && cycle < 40000000L) {
        const int retiring = top.dut_retire_count;
        if (retiring != 0) {
            stats.retired += retiring;
            if (stats.first_retire < 0) stats.first_retire = cycle;
            stats.last_retire = cycle;
        }
        if (top.dut_kblock_active) ++active;
        if (top.dut_kblock_done) {
            ++stats.kb_count;
            stats.kb_sum += active;
            if (stats.kb_min < 0 || active < stats.kb_min) stats.kb_min = active;
            if (active > stats.kb_max) stats.kb_max = active;
            active = 0;
        }
        tick(top);
        ++cycle;
    }
    stats.total_cycles = cycle;
    stats.completed = top.dut_done != 0;
    if (!stats.completed) {
        ++failures;
        std::printf("FAIL: case %u tile never completed\n", current_case);
    }
    long guard = 0;
    while (top.env_busy && guard < 100000) {
        tick(top);
        ++guard;
    }
    return stats;
}

// One endpoint vector through the tree beside the tile; returns its result.
uint32_t tree_vector(Vot_a3_tile64_top& top, const uint32_t* leaves, int count, uint16_t tag) {
    top.tree_in_valid = 1;
    top.tree_in_count = static_cast<uint8_t>(count);
    top.tree_in_tag = tag;
    for (int k = 0; k < kLeaves; ++k) top.tree_in_leaf[k] = (k < count) ? leaves[k] : 0u;
    tick(top);
    top.tree_in_valid = 0;
    for (int guard = 0; guard < 40; ++guard) {
        if (top.tree_out_valid) {
            if (top.tree_out_tag != tag) {
                ++failures;
                std::printf("FAIL: case %u tree output tag %u, expected %u\n", current_case, top.tree_out_tag, tag);
            }
            return top.tree_out_data;
        }
        tick(top);
    }
    ++failures;
    std::printf("FAIL: case %u tree endpoint produced no output\n", current_case);
    return 0xbad0bad0u;
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_a3_tile64_top top;
    const std::vector<uint32_t> expect = load_hex32("t64_expect.hex");

    top.rst_n = 0;
    top.op_start = 0;
    top.env_start = 0;
    top.tree_in_valid = 0;
    top.tree_clear = 0;
    for (int i = 0; i < 4; ++i) tick(top);
    top.rst_n = 1;
    for (int i = 0; i < 2; ++i) tick(top);

    const uint32_t meta_cases = meta_word(top, 0);
    const uint32_t meta_lane_ops = meta_word(top, 1);
    const uint32_t meta_products = meta_word(top, 2);
    const uint32_t meta_partials = meta_word(top, 3);
    const uint32_t meta_faults = meta_word(top, 4);
    const uint32_t meta_roots = meta_word(top, 5);
    const uint32_t meta_stride = meta_word(top, 6);
    const uint32_t meta_tree_vectors = meta_word(top, 7);
    const uint32_t meta_lanes = meta_word(top, 8);
    const uint32_t meta_kblocks = meta_word(top, 9);
    const uint32_t adder_stages = top.adder_stages;
    const uint32_t lanes = top.lanes;
    const uint32_t region_words = top.region_words;
    const uint32_t weight_source = top.weight_source;
    const uint32_t staging_in_tile = top.staging_in_tile;

    current_case = 0xffffffffu;
    report("lane count in image", meta_lanes, lanes);
    report("case stride", meta_stride, kCaseStride);

    uint64_t counted_cases = 0, counted_lane_ops = 0, counted_products = 0, counted_partials = 0;
    uint64_t counted_faults = 0, counted_roots = 0, counted_tree_vectors = 0, counted_kblocks = 0;

    for (uint32_t index = 0; index < meta_cases; ++index) {
        uint32_t field[kCaseStride];
        for (int slot = 0; slot < kCaseStride; ++slot) field[slot] = case_word(top, index, slot);
        current_case = field[38];

        top.op_rows = static_cast<uint16_t>(field[0]);
        top.op_cols = static_cast<uint16_t>(field[1]);
        top.op_depth = static_cast<uint16_t>(field[2]);
        top.op_kblock = static_cast<uint16_t>(field[3]);
        top.op_dtype_a = static_cast<uint8_t>(field[4]);
        top.op_dtype_b = static_cast<uint8_t>(field[5]);
        top.op_group = static_cast<uint8_t>(field[6]);
        top.op_scale_a = static_cast<uint8_t>(field[7] & 1u);
        top.op_block_a = static_cast<uint16_t>(field[8]);
        top.op_block_rows_a = static_cast<uint16_t>(field[9]);
        top.op_scale_b = static_cast<uint8_t>(field[10] & 1u);
        top.op_block_b = static_cast<uint16_t>(field[11]);
        top.op_a_base = field[12];
        top.op_a_block_stride = static_cast<uint16_t>(field[13]);
        top.op_scale_a_base = field[14];
        top.op_scale_a_block_stride = static_cast<uint16_t>(field[15]);
        top.op_w_base = field[16];
        top.op_w_words = field[17];
        top.op_ws_base = field[18];
        top.op_ws_block_stride = field[19];
        top.op_out_base = field[20];
        top.op_out_block_stride = field[21];
        top.op_out_fp32 = static_cast<uint8_t>(field[22] & 1u);
        top.env_sdn_base = field[16];
        top.env_sdn_words = field[48];
        top.env_sdn_ignore_credit = (field[24] & kFlagSdnIgnore) ? 1 : 0;
        top.env_act_img_base = field[39];
        top.env_act_slice_full = static_cast<uint16_t>(field[40]);
        top.env_act_slice_last = static_cast<uint16_t>(field[41]);
        top.env_act_stride = static_cast<uint16_t>(field[13]);
        top.env_act_region_base = field[12];
        top.env_scale_img_base = field[42];
        top.env_scale_slice_full = static_cast<uint16_t>(field[43]);
        top.env_scale_slice_last = static_cast<uint16_t>(field[44]);
        top.env_scale_stride = static_cast<uint16_t>(field[15]);
        top.env_scale_region_base = field[14];
        top.env_blocks = static_cast<uint16_t>(field[23]);

        const RunStats stats = launch(top);
        const uint32_t window = field[36];
        const uint32_t blocks = field[23];
        const uint32_t cpl = field[45];
        const bool refused = (field[24] & kFlagRefused) != 0;
        const bool unchecked = (field[24] & kFlagBlockUnchecked) != 0;
        const bool faulted = field[25] != 0;

        ++counted_cases;
        if (faulted) ++counted_faults;
        counted_kblocks += static_cast<uint64_t>(stats.kb_count);

        report("error_code", top.dut_error_code, field[25]);
        report("error_detail", top.dut_error_detail, field[26]);
        report("error_kblock", top.dut_error_kblock, field[27]);
        report("error_lq8", top.dut_error_lq8, field[28]);
        report("error_lane", top.dut_error_lane, field[29]);
        report("out_count", top.dut_out_count, field[30]);
        report("saturation_count", top.dut_saturation_count, 0);
        report("mac_count", top.dut_mac_count, field[31]);
        report("product_count", top.dut_product_count, field[32]);
        report("retired lane-ops", static_cast<uint64_t>(stats.retired), field[31]);
        if (field[33] != kDontCare) report("staging_underruns", top.dut_staging_underruns, field[33]);
        if (field[26] == 23) report("staging_overruns nonzero", top.dut_staging_overruns != 0 ? 1 : 0, 1);
        if (field[34] != kDontCare) report("stream_words_consumed", top.dut_stream_words_consumed, field[34]);
        report("K-blocks run", static_cast<uint64_t>(stats.kb_count),
               refused ? 0u : (faulted ? field[27] + 1u : blocks));
        report("lockstep violations", top.lockstep_violations, 0);
        counted_lane_ops += top.dut_mac_count;
        counted_products += top.dut_product_count;

        if (field[24] & kFlagRate) {
            const long window_cycles = stats.retired > 0 ? (stats.last_retire - stats.first_retire + 1) : 0;
            std::printf(
                "RATE: case=%u lane_ops=%ld products=%u total_cycles=%ld window_cycles=%ld first_retire=%ld "
                "last_retire=%ld lanes=%u kblocks=%ld kblock_cycles_min=%ld kblock_cycles_max=%ld "
                "kblock_cycles_sum=%ld\n",
                current_case, stats.retired, top.dut_product_count, stats.total_cycles, window_cycles,
                stats.first_retire, stats.last_retire, lanes, stats.kb_count, stats.kb_min, stats.kb_max,
                stats.kb_sum);
        }

        for (uint32_t lane = 0; lane < lanes; ++lane) {
            top.lane_rd_sel = static_cast<uint8_t>(lane);
            top.eval();
            report("lane error_code", top.lane_rd_error_code, field[144 + lane]);
            report("lane error_detail", top.lane_rd_error_detail, field[208 + lane]);
            if (lane % 8 == 0) {
                report("lq8 error_code", top.lq8_rd_error_code, field[64 + lane / 8]);
                report("lq8 error_detail", top.lq8_rd_error_detail, field[72 + lane / 8]);
            }
        }

        uint64_t checked_here = 0;
        for (uint32_t lane = 0; lane < lanes; ++lane) {
            for (uint32_t b = 0; b < blocks; ++b) {
                long written;
                if (b < field[46]) written = window;
                else if (b == field[46] && faulted && !unchecked && !refused) written = field[80 + lane];
                else if (b == field[46] && unchecked) written = -1;
                else written = 0;
                if (written < 0) continue;
                for (uint32_t e = 0; e < window; ++e) {
                    uint32_t acc = 0;
                    const uint32_t got = result_word(top, lane * region_words + field[20] + b * field[21] + e, &acc);
                    const uint32_t want = expect.at(field[35] + (lane * blocks + b) * window + e);
                    checks += 2;
                    if (static_cast<long>(e) < written) {
                        ++checked_here;
                        if (got != want || acc != want) {
                            ++failures;
                            if (failures < 40) {
                                std::printf("FAIL: case %u lane %u block %u element %u got %08x/%08x want %08x\n",
                                            current_case, lane, b, e, got, acc, want);
                            }
                        }
                    } else if (got != kUnwritten || acc != kUnwritten) {
                        ++failures;
                        if (failures < 40) {
                            std::printf("FAIL: case %u lane %u block %u element %u written after the fault: %08x\n",
                                        current_case, lane, b, e, got);
                        }
                    }
                }
            }
        }
        counted_partials += checked_here;

        if (field[47] != 0) {
            uint64_t vectors = 0;
            uint16_t tag = 1;
            std::vector<uint32_t> nodes(blocks), next;
            for (uint32_t row = 0; row < field[0]; ++row) {
                for (uint32_t n = 0; n < field[1]; ++n) {
                    const uint32_t lane = n % kLanes;
                    const uint32_t c = n / kLanes;
                    nodes.resize(blocks);
                    for (uint32_t b = 0; b < blocks; ++b) {
                        nodes[b] = result_word(top, lane * region_words + field[20] + b * field[21] + row * cpl + c,
                                               nullptr);
                    }
                    while (nodes.size() > 1) {
                        next.clear();
                        for (size_t g = 0; g < nodes.size(); g += kLeaves) {
                            const int count = static_cast<int>(std::min<size_t>(kLeaves, nodes.size() - g));
                            next.push_back(tree_vector(top, &nodes[g], count, tag++));
                            ++vectors;
                        }
                        nodes = next;
                    }
                    const uint32_t want = expect.at(field[37] + row * field[1] + n);
                    ++checks;
                    ++counted_roots;
                    if (nodes[0] != want) {
                        ++failures;
                        if (failures < 40) {
                            std::printf("FAIL: case %u row %u column %u tree root got %08x want %08x\n",
                                        current_case, row, n, nodes[0], want);
                        }
                    }
                }
            }
            report("tree vectors", vectors, field[49]);
            report("tree error_code", top.tree_error_code, 0);
            counted_tree_vectors += vectors;
        }
    }

    current_case = 0xffffffffu;
    report("case count", counted_cases, meta_cases);
    report("lane-op count", counted_lane_ops, meta_lane_ops);
    report("product count", counted_products, meta_products);
    report("partial count", counted_partials, meta_partials);
    report("fault case count", counted_faults, meta_faults);
    report("root count", counted_roots, meta_roots);
    report("tree vector count", counted_tree_vectors, meta_tree_vectors);
    report("K-block count", counted_kblocks, meta_kblocks);
    report("final lockstep violations", top.lockstep_violations, 0);

    if (failures == 0) {
        std::printf(
            "PASS: ABI3 tile64 cases=%llu lane_ops=%llu products=%llu partials=%llu faults=%llu roots=%llu "
            "tree_vectors=%llu kblocks=%llu lanes=%u adder_stages=%u weight_source=%u staging_in_tile=%u\n",
            static_cast<unsigned long long>(counted_cases), static_cast<unsigned long long>(counted_lane_ops),
            static_cast<unsigned long long>(counted_products), static_cast<unsigned long long>(counted_partials),
            static_cast<unsigned long long>(counted_faults), static_cast<unsigned long long>(counted_roots),
            static_cast<unsigned long long>(counted_tree_vectors), static_cast<unsigned long long>(counted_kblocks),
            lanes, adder_stages, weight_source, staging_in_tile);
        std::printf("checks=%ld\n", checks);
        return 0;
    }
    std::printf("FAILURES: %ld after checks=%ld\n", failures, checks);
    return 1;
}
