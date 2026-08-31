// ---------------------------------------------------------------------------
// Verilator checker for the ABI 3.0 engine datapaths.
//
// The second of the two independently written checkers over the same RTL and
// the same generated images.  It shares no code with rtl/test/tb_a3_engine.sv:
// it loads the expected images itself, sequences the design itself, counts
// what it actually checked, and prints the marker only if its own counts equal
// the totals the image declares.  Agreement between the two is therefore
// agreement between two readers of one contract, not one reader reflected
// twice.
// ---------------------------------------------------------------------------
#include "Vot_a3_engine_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <set>
#include <string>
#include <vector>

namespace {

constexpr int kCaseStride = 32;
constexpr int kArithStride = 8;
constexpr uint32_t kUnwritten = 0xdeadbeefu;
constexpr uint32_t kErrNone = 0;
constexpr uint32_t kErrShape = 7;
constexpr uint32_t kFlagWork = 0x1;
constexpr uint32_t kFlagToken = 0x2;
constexpr uint32_t kFlagUntouched = 0x4;
constexpr uint32_t kFlagSaturation = 0x8;

long failures = 0;
long checks = 0;

void report(const std::string& label, uint64_t got, uint64_t want) {
    ++checks;
    if (got == want) return;
    ++failures;
    if (failures < 20) {
        std::printf("FAIL: %s got %llu want %llu\n", label.c_str(),
                    static_cast<unsigned long long>(got),
                    static_cast<unsigned long long>(want));
    }
}

std::vector<uint32_t> load_hex(const char* path) {
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

void tick(Vot_a3_engine_top& dut) {
    dut.clk = 0;
    dut.eval();
    dut.clk = 1;
    dut.eval();
}

void settle(Vot_a3_engine_top& dut) { dut.eval(); }

void launch(Vot_a3_engine_top& dut) {
    dut.start = 1;
    tick(dut);
    dut.start = 0;
    long guard = 0;
    while (dut.done == 0 && guard < 40000000L) {
        tick(dut);
        ++guard;
    }
    if (dut.done == 0) {
        ++failures;
        std::printf("FAIL: engine never completed\n");
    }
}

uint32_t case_word(Vot_a3_engine_top& dut, int index, int field) {
    dut.case_rd_addr = static_cast<uint32_t>(index * kCaseStride + field);
    settle(dut);
    return dut.case_rd_data;
}

uint32_t meta_word(Vot_a3_engine_top& dut, int index) {
    dut.meta_rd_addr = static_cast<uint32_t>(index);
    settle(dut);
    return dut.meta_rd_data;
}

uint32_t result_word(Vot_a3_engine_top& dut, uint32_t address) {
    dut.res_rd_addr = address;
    settle(dut);
    return dut.res_rd_data;
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_a3_engine_top dut;

    const std::vector<uint32_t> expected = load_hex("e3_expect.hex");
    const std::vector<uint32_t> decode = load_hex("e3_decode.hex");
    const std::vector<uint32_t> arith = load_hex("e3_arith.hex");

    dut.rst_n = 0;
    dut.start = 0;
    for (int i = 0; i < 4; ++i) tick(dut);
    dut.rst_n = 1;
    for (int i = 0; i < 2; ++i) tick(dut);

    const uint32_t meta_cases = meta_word(dut, 0);
    const uint32_t meta_families = meta_word(dut, 1);
    const uint32_t meta_results = meta_word(dut, 2);
    const uint32_t meta_macs = meta_word(dut, 3);
    const uint32_t meta_faults = meta_word(dut, 4);
    const uint32_t meta_decodes = meta_word(dut, 5);
    const uint32_t meta_stride = meta_word(dut, 6);
    const uint32_t meta_arith = meta_word(dut, 7);

    uint64_t counted_cases = 0;
    uint64_t counted_results = 0;
    uint64_t counted_faults = 0;
    uint64_t counted_decodes = 0;
    uint64_t counted_arith = 0;
    uint64_t counted_macs = 0;
    std::set<uint32_t> families;

    for (uint32_t index = 0; index < meta_cases; ++index) {
        uint32_t field[kCaseStride];
        for (int slot = 0; slot < kCaseStride; ++slot) {
            field[slot] = case_word(dut, static_cast<int>(index), slot);
        }

        dut.cfg_family = static_cast<uint8_t>(field[0]);
        dut.cfg_sub = static_cast<uint8_t>(field[1]);
        dut.cfg_rows = static_cast<uint16_t>(field[2]);
        dut.cfg_cols = static_cast<uint16_t>(field[3]);
        dut.cfg_depth = static_cast<uint16_t>(field[4]);
        dut.cfg_count = field[5];
        dut.cfg_dtype_a = static_cast<uint8_t>(field[6]);
        dut.cfg_dtype_b = static_cast<uint8_t>(field[7]);
        dut.cfg_a_base = field[8];
        dut.cfg_b_base = field[9];
        dut.cfg_c_base = field[10];
        dut.cfg_out_base = field[11];
        dut.cfg_scale_a = static_cast<uint8_t>(field[12] & 1u);
        dut.cfg_scale_b = static_cast<uint8_t>(field[13] & 1u);
        dut.cfg_block_a = static_cast<uint16_t>(field[14]);
        dut.cfg_block_b = static_cast<uint16_t>(field[15]);
        dut.cfg_block_rows_a = static_cast<uint16_t>(field[16]);
        dut.cfg_block_rows_b = static_cast<uint16_t>(field[17]);
        dut.cfg_scale_a_base = field[18];
        dut.cfg_scale_b_base = field[19];
        dut.cfg_slots = field[20];
        dut.cfg_trailing = field[21];
        dut.cfg_extent = field[22];

        launch(dut);

        ++counted_cases;
        families.insert((field[0] << 8) | field[1]);
        if (field[0] == 0x20u) {
            counted_macs += static_cast<uint64_t>(field[2]) * field[3] * field[4];
        }
        if (field[23] != kErrNone) ++counted_faults;

        report("fault code", dut.error_code, field[23]);
        report("result count", dut.result_count, field[24]);
        if (field[31] & kFlagSaturation) {
            report("saturations", dut.saturation_count, field[25]);
        }
        if (field[31] & kFlagWork) {
            report("work", dut.work_count, field[26]);
        }
        if (field[31] & kFlagToken) {
            report("token", dut.token, field[27]);
            report("tie multiplicity", dut.tie_multiplicity, field[28]);
        }

        for (uint32_t word = 0; word < field[30]; ++word) {
            const uint32_t got = result_word(dut, field[11] + word);
            const uint32_t want = expected.at(field[29] + word);
            ++checks;
            ++counted_results;
            if (got != want) {
                ++failures;
                if (failures < 20) {
                    std::printf(
                        "FAIL: case %u word %u got %08x want %08x\n",
                        index, word, got, want);
                }
            }
        }
    }

    // Fail-closed dispatch: an operation this array does not implement.
    dut.cfg_family = 0x40;    // ATTENTION
    dut.cfg_sub = 0x00;
    dut.cfg_rows = 1;
    dut.cfg_cols = 1;
    dut.cfg_depth = 1;
    dut.cfg_count = 1;
    launch(dut);
    report("unimplemented operation is refused", dut.error_code, kErrShape);
    report("unimplemented operation writes nothing", dut.result_count, 0);

    for (uint32_t entry = 0; entry < meta_decodes; ++entry) {
        dut.probe_format = static_cast<uint8_t>(decode.at(entry * 4));
        dut.probe_word = decode.at(entry * 4 + 1);
        settle(dut);
        ++counted_decodes;
        checks += 2;
        const uint64_t observed = dut.probe_result;
        const uint32_t error = static_cast<uint32_t>((observed >> 32) & 0x3u);
        const uint32_t value = static_cast<uint32_t>(observed & 0xffffffffu);
        if (error != decode.at(entry * 4 + 2)) {
            ++failures;
            if (failures < 20) {
                std::printf("FAIL: decode %u format %02x word %08x error %u want %u\n",
                            entry, dut.probe_format, dut.probe_word, error,
                            decode.at(entry * 4 + 2));
            }
        }
        if (decode.at(entry * 4 + 2) == 0 && value != decode.at(entry * 4 + 3)) {
            ++failures;
            if (failures < 20) {
                std::printf("FAIL: decode %u format %02x word %08x got %08x want %08x\n",
                            entry, dut.probe_format, dut.probe_word, value,
                            decode.at(entry * 4 + 3));
            }
        }
    }

    // Binary32 add, multiply and BF16 rounding against the exact
    // fractions.Fraction reference in runtime.reference.formats.
    for (uint32_t entry = 0; entry < meta_arith; ++entry) {
        const uint32_t base = entry * kArithStride;
        dut.arith_a = arith.at(base);
        dut.arith_b = arith.at(base + 1);
        settle(dut);
        ++counted_arith;
        checks += 3;
        const uint64_t sum = dut.arith_add;
        const uint32_t sum_error = static_cast<uint32_t>((sum >> 32) & 0x3u);
        const uint32_t sum_value = static_cast<uint32_t>(sum & 0xffffffffu);
        if (sum_error != arith.at(base + 2) ||
            (arith.at(base + 2) == 0 && sum_value != arith.at(base + 3))) {
            ++failures;
            if (failures < 20) {
                std::printf("FAIL: add %u a=%08x b=%08x got %u:%08x want %u:%08x\n",
                            entry, dut.arith_a, dut.arith_b, sum_error, sum_value,
                            arith.at(base + 2), arith.at(base + 3));
            }
        }
        const uint64_t product = dut.arith_mul;
        const uint32_t mul_error = static_cast<uint32_t>((product >> 32) & 0x3u);
        const uint32_t mul_value = static_cast<uint32_t>(product & 0xffffffffu);
        if (mul_error != arith.at(base + 4) ||
            (arith.at(base + 4) == 0 && mul_value != arith.at(base + 5))) {
            ++failures;
            if (failures < 20) {
                std::printf("FAIL: mul %u a=%08x b=%08x got %u:%08x want %u:%08x\n",
                            entry, dut.arith_a, dut.arith_b, mul_error, mul_value,
                            arith.at(base + 4), arith.at(base + 5));
            }
        }
        const uint32_t narrowed = dut.arith_bf16;
        const uint32_t bf_field = (narrowed >> 16) & 0x7u;
        const uint32_t bf_value = narrowed & 0xffffu;
        if (bf_field != arith.at(base + 6) ||
            (arith.at(base + 6) < 2 && bf_value != (arith.at(base + 7) & 0xffffu))) {
            ++failures;
            if (failures < 20) {
                std::printf("FAIL: bf16 %u a=%08x got %u:%04x want %u:%04x\n",
                            entry, dut.arith_a, bf_field, bf_value,
                            arith.at(base + 6), arith.at(base + 7));
            }
        }
    }

    report("case count", counted_cases, meta_cases);
    report("family count", families.size(), meta_families);
    report("result word count", counted_results, meta_results);
    report("mac count", counted_macs, meta_macs);
    report("fault case count", counted_faults, meta_faults);
    report("decode probe count", counted_decodes, meta_decodes);
    report("arithmetic probe count", counted_arith, meta_arith);
    report("case stride", meta_stride, kCaseStride);

    if (failures == 0) {
        std::printf(
            "PASS: ABI3 RTL engine datapaths cases=%llu families=%llu "
            "results=%llu macs=%llu faults=%llu decodes=%llu arith=%llu\n",
            static_cast<unsigned long long>(counted_cases),
            static_cast<unsigned long long>(families.size()),
            static_cast<unsigned long long>(counted_results),
            static_cast<unsigned long long>(counted_macs),
            static_cast<unsigned long long>(counted_faults),
            static_cast<unsigned long long>(counted_decodes),
            static_cast<unsigned long long>(counted_arith));
        std::printf("checks=%ld\n", checks);
        return 0;
    }
    std::printf("FAILURES: %ld after checks=%ld\n", failures, checks);
    return 1;
}
