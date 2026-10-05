// ---------------------------------------------------------------------------
// Verilator checker for ROUTE.CANDIDATE_MASK.
//
// The second, independently written checker of rtl/test/a3_candidate_mask_top.sv.
// It reads the case table and the id image out of the FILES the top reads, not
// out of the design, and derives every expected mask word by a different route
// from either the Python reference or the Icarus checker: for each output word
// it walks only the candidate blocks that OVERLAP that word's position span and
// fills the overlapping bit range, instead of deciding each position from its
// block index.  Three derivations that agree -- this one, the Verilog checker's
// per-position one, and runtime/reference/candidate_pool.py's -- are what make
// the masks bit-exact against something other than the block itself.
//
// The line format is transcribed identically in rtl/test/tb_a3_candidate_mask.sv.
// ---------------------------------------------------------------------------
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "Vot_a3_candidate_mask_top.h"
#include "verilated.h"

namespace {

constexpr unsigned kCaseStride = 16;
constexpr unsigned kWordBits = 32;
constexpr unsigned kGeoms = 5;
constexpr uint32_t kAbsentId = 0xffffffffu;
constexpr uint32_t kDontCheck = 0xffffffffu;
constexpr unsigned long kGuard = 20000000;

struct Geometry {
    unsigned block;
    unsigned max_width;
    unsigned max_ids;
    unsigned pin;
};

//: Transcribed from rtl/test/a3_candidate_mask_top.sv's parameters and checked
//: against the obs_param_* each instance drives out.
const Geometry kGeom[kGeoms] = {
    {8, 1048576, 2048, 1},
    {1, 4096, 4096, 1},
    {3, 4095, 1365, 1},
    {16, 8192, 512, 1},
    {8, 4096, 2048, 0},
};

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
    // The context that OWNS the model must be the one that takes the command
    // line: a global Verilated::commandArgs would not reach this model's
    // plusargs.
    const std::unique_ptr<VerilatedContext> ctx{new VerilatedContext};
    ctx->commandArgs(argc, argv);
    const std::unique_ptr<Vot_a3_candidate_mask_top> dut{
        new Vot_a3_candidate_mask_top{ctx.get(), "top"}};

    const std::vector<uint32_t> cases = read_hex("cm_case.hex");
    const std::vector<uint32_t> ids = read_hex("cm_ids.hex");
    const std::vector<uint32_t> expect = read_hex("cm_expect.hex");
    const std::vector<uint32_t> meta = read_hex("cm_meta.hex");
    if (meta.empty() || meta[0] == 0) {
        std::cerr << "FAIL: the case table is empty\n";
        return 2;
    }
    const unsigned case_count = meta[0];
    const uint64_t meta_words = meta[1];
    const unsigned meta_geoms = meta[4];
    const unsigned meta_stride = meta[5];
    const uint64_t meta_population = meta[7];
    if (cases.size() < static_cast<size_t>(case_count) * kCaseStride) {
        std::cerr << "FAIL: the case image is shorter than the case count\n";
        return 2;
    }

    auto tick = [&]() {
        dut->clk = 1;
        dut->eval();
        dut->clk = 0;
        dut->eval();
    };

    dut->rst_n = 0;
    dut->run = 0;
    dut->run_case = 0;
    dut->case_rd_addr = 0;
    dut->ids_rd_addr = 0;
    dut->expect_rd_addr = 0;
    dut->meta_rd_addr = 0;
    dut->cap_rd_addr = 0;
    for (unsigned i = 0; i < 6; ++i) tick();
    dut->rst_n = 1;
    for (unsigned i = 0; i < 4; ++i) tick();

    auto cap = [&](uint32_t addr) {
        dut->cap_rd_addr = addr;
        dut->eval();
        return static_cast<uint32_t>(dut->cap_rd_data);
    };

    unsigned long checks = 0;
    unsigned failures = 0;
    uint64_t total_words = 0;
    uint64_t total_population = 0;
    checks += 2;
    if (dut->geoms_param != meta_geoms || dut->case_stride_param != meta_stride) {
        std::cerr << "FAIL: the top's geometry count or case stride is not the "
                     "one the images were built for\n";
        return 2;
    }

    for (unsigned index = 0; index < case_count; ++index) {
        const uint32_t* w = cases.data() + static_cast<size_t>(index) * kCaseStride;
        const unsigned geom = w[0];
        const unsigned width = w[2];
        const unsigned id_count = w[3];
        const unsigned max_pop = w[5];
        const unsigned ids_base = w[6];
        const unsigned out_base = w[7];
        const unsigned e_code = w[8];
        const unsigned e_detail = w[9];
        const unsigned e_slot = w[10];
        const uint32_t e_value = w[11];
        const unsigned e_words = w[12];
        const uint32_t e_pop = w[13];
        const uint32_t e_blocks = w[14];
        const unsigned e_base = w[15];
        if (geom >= kGeoms) {
            std::cerr << "FAIL: case " << index << " names geometry " << geom << "\n";
            return 2;
        }
        const unsigned block = kGeom[geom].block;
        const unsigned pin = kGeom[geom].pin;

        // -- run it ---------------------------------------------------------
        dut->run_case = index;
        dut->run = 1;
        tick();
        dut->run = 0;
        unsigned long spins = 0;
        while (dut->busy && spins < kGuard) {
            tick();
            ++spins;
        }
        tick();

        Verdict v;
        v.eq(1, dut->obs_timeout, 0);
        v.eq(2, dut->obs_done_pulses, 1);
        v.eq(3, dut->obs_error_code, e_code);
        v.eq(4, dut->obs_error_detail, e_detail);
        v.eq(5, dut->obs_error_slot, e_slot);
        v.eq(6, dut->obs_error_value, e_value);
        v.eq(7, dut->obs_out_count, e_words);
        v.eq(10, dut->obs_pulses, e_words);
        v.eq(11, dut->obs_addr_errors, 0);
        v.eq(12, dut->obs_write_overflow, 0);
        v.eq(13, dut->obs_param_block, block);
        v.eq(14, dut->obs_param_max_width, kGeom[geom].max_width);
        v.eq(15, dut->obs_param_max_ids, kGeom[geom].max_ids);
        v.eq(16, dut->obs_param_word_bits, kWordBits);
        v.eq(17, dut->obs_param_pin_last, pin);
        v.eq(26, dut->obs_block_busy, 0);
        if (e_pop != kDontCheck) v.eq(8, dut->obs_population, e_pop);
        if (e_blocks != kDontCheck) v.eq(9, dut->obs_blocks, e_blocks);
        if (e_words > 1) {
            v.eq(18, dut->obs_span, e_words - 1);
            v.eq(19, dut->obs_emit_gap_max, 1);
        }
        if (e_code == 0) {
            v.eq(25, dut->obs_ids_consumed, id_count);
            v.eq(27, dut->obs_id_reads, id_count);
        } else if (e_detail == 6) {
            v.eq(25, dut->obs_ids_consumed, e_slot + 1);
        }

        // -- derive the admitted block set ----------------------------------
        // A block-overlap derivation, not a per-position one: the id set, then
        // the runs of positions each admitted block contributes.
        std::vector<uint8_t> admitted;
        unsigned block_count = 0;
        unsigned last_block = 0;
        unsigned tail_len = 0;
        if (width > 0) {
            block_count = (width + block - 1) / block;
            last_block = block_count - 1;
            tail_len = width - last_block * block;
            admitted.assign(block_count, 0);
            bool bad = false;
            for (unsigned slot = 0; slot < id_count && !bad; ++slot) {
                const uint32_t id = (ids_base + slot < ids.size())
                                        ? ids[ids_base + slot] : kAbsentId;
                if (id == kAbsentId) continue;
                if (id >= block_count) { bad = true; break; }
                admitted[id] = 1;
            }
            if (pin != 0) admitted[last_block] = 1;
            uint64_t der_pop = 0;
            uint64_t der_blocks = 0;
            for (unsigned b = 0; b < block_count; ++b) {
                if (!admitted[b]) continue;
                ++der_blocks;
                der_pop += (b == last_block) ? tail_len : block;
            }
            if (e_pop != kDontCheck) v.eq(23, static_cast<long long>(der_pop), e_pop);
            if (e_blocks != kDontCheck)
                v.eq(24, static_cast<long long>(der_blocks), e_blocks);
            if (max_pop != 0 && e_code == 0)
                v.eq(28, der_pop <= max_pop ? 1 : 0, 1);
        }

        // -- every emitted word, three ways ---------------------------------
        if (e_words > 0) {
            v.eq(7, (width + kWordBits - 1) / kWordBits, e_words);
            for (unsigned word = 0; word < e_words; ++word) {
                const uint64_t first = static_cast<uint64_t>(word) * kWordBits;
                const uint64_t limit = first + kWordBits;
                uint32_t der = 0;
                const unsigned b_lo = static_cast<unsigned>(first / block);
                unsigned b_hi = static_cast<unsigned>((limit - 1) / block);
                if (b_hi > last_block) b_hi = last_block;
                for (unsigned b = b_lo; b <= b_hi; ++b) {
                    if (!admitted[b]) continue;
                    uint64_t lo = static_cast<uint64_t>(b) * block;
                    uint64_t hi = lo + block;          // exclusive
                    if (hi > width) hi = width;        // the -inf padded tail
                    if (lo < first) lo = first;
                    if (hi > limit) hi = limit;
                    for (uint64_t p = lo; p < hi; ++p)
                        der |= (1u << static_cast<unsigned>(p - first));
                }
                const uint32_t ref = (e_base + word < expect.size())
                                         ? expect[e_base + word] : 0xdeadbeefu;
                const uint32_t got = cap(out_base + word);
                v.eq(20, got, ref);
                v.eq(21, got, der);
                v.eq(22, ref, der);
            }
        }

        checks += v.checks;
        if (v.code != 0) ++failures;
        total_words += e_words;
        if (e_pop != kDontCheck) total_population += e_pop;
        std::printf("CMCASE %u %s site=%d geom=%u block=%u width=%u ids=%u "
                    "words=%u pop=%u blocks=%u code=%u detail=%u slot=%u "
                    "value=%u pulses=%u span=%u gap=%u cycles=%u consumed=%u\n",
                    index, v.code == 0 ? "OK" : "DIVERGE", v.code, geom, block,
                    width, id_count,
                    static_cast<unsigned>(dut->obs_out_count),
                    static_cast<unsigned>(dut->obs_population),
                    static_cast<unsigned>(dut->obs_blocks),
                    static_cast<unsigned>(dut->obs_error_code),
                    static_cast<unsigned>(dut->obs_error_detail),
                    static_cast<unsigned>(dut->obs_error_slot),
                    static_cast<unsigned>(dut->obs_error_value),
                    static_cast<unsigned>(dut->obs_pulses),
                    static_cast<unsigned>(dut->obs_span),
                    static_cast<unsigned>(dut->obs_emit_gap_max),
                    static_cast<unsigned>(dut->obs_cycles),
                    static_cast<unsigned>(dut->obs_ids_consumed));
    }

    checks += 2;
    if (total_words != meta_words) ++failures;
    if (total_population != meta_population) ++failures;
    std::printf("CHECKS: %lu\n", checks);
    if (failures == 0)
        std::printf("PASS: A3 V41 candidate mask cases=%u words=%llu population=%llu\n",
                    case_count, static_cast<unsigned long long>(total_words),
                    static_cast<unsigned long long>(total_population));
    else
        std::printf("FAIL: A3 V41 candidate mask cases=%u diverged=%u\n",
                    case_count, failures);
    dut->final();
    return failures == 0 ? 0 : 1;
}
