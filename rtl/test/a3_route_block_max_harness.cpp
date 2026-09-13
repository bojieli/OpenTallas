// ---------------------------------------------------------------------------
// Verilator checker for ROUTE.BLOCK_MAX (rtl/abi3/ot_a3_route_block_max.sv,
// record results/rtl/a3_v41_block_max_campaign.json).
//
// The second of the two independently written checkers over the same RTL and the
// same generated images.  It shares no code with
// rtl/test/tb_a3_route_block_max.sv: it parses the four hex images with its own
// reader, sequences the block itself, counts what it actually checked, and
// prints the marker only if its own tallies equal the totals the image declares.
// The image layout, the sequencing protocol and the check accounting are
// documented in the Icarus checker; the two must agree on those, on the marker
// and on the RATE line, and on nothing else.
//
// The images are found in the directory given by the +bmdir= plusarg, default
// ".".  The plusarg is read from the VerilatedContext that OWNS the model --
// ctx.commandArgs(argc, argv) is called BEFORE the model is constructed --
// because a plusarg given to the global Verilated::commandArgs would not be
// visible to a model built on a local context.
// ---------------------------------------------------------------------------
#include "Vot_a3_route_block_max_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {

constexpr int kCaseStride = 10;
constexpr int kExpStride = 4;
constexpr int kLanesMax = 16;
constexpr int kVecStride = 4 + kLanesMax;
constexpr uint32_t kCaseFlagRate = 0x1u;
constexpr uint32_t kCaseFlagFault = 0x2u;
constexpr uint32_t kVecFlagRowLast = 0x1u;
constexpr uint32_t kMagic = 0x424d4158u;

long checks = 0;
long failures = 0;
long reported = 0;
long current_case = -1;

void report(const char* label, long got, long want) {
    ++checks;
    if (got == want) return;
    ++failures;
    if (reported < 40) {
        ++reported;
        std::printf("FAIL: case %ld %s got %ld want %ld\n", current_case, label, got, want);
    }
}

std::vector<uint32_t> load_hex32(const std::string& path) {
    std::ifstream stream(path);
    if (!stream) {
        std::printf("FAIL: cannot open %s\n", path.c_str());
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

uint32_t at(const std::vector<uint32_t>& image, size_t index) {
    if (index >= image.size()) {
        std::printf("FAIL: image index %zu beyond %zu words\n", index, image.size());
        std::exit(1);
    }
    return image[index];
}

struct Collector {
    const std::vector<uint32_t>* expects = nullptr;
    uint32_t exp_base = 0;
    long exp_ptr = 0;
    long outputs = 0;
    long first_cycle = -1;
    long last_cycle = -1;
    long latency = 0;
    std::vector<long> accepted;   // cycle of each accepted block, in order
    size_t accepted_read = 0;
};

Collector collector;
long cycle = 0;
long outputs_seen = 0;
long faults_seen = 0;

void collect(Vot_a3_route_block_max_top& top) {
    if (!top.out_valid) return;
    const size_t base = static_cast<size_t>(collector.exp_base)
                      + static_cast<size_t>(collector.exp_ptr) * kExpStride;
    report("out_score", top.out_score_w, at(*collector.expects, base + 0));
    report("out_block_id", top.out_block_id_w, at(*collector.expects, base + 1));
    report("out_row_last", top.out_row_last, at(*collector.expects, base + 2));
    report("out_tag", top.out_tag_w, at(*collector.expects, base + 3));
    long accept_cycle = -1;
    if (collector.accepted_read < collector.accepted.size()) {
        accept_cycle = collector.accepted[collector.accepted_read++];
    }
    report("latency", cycle - accept_cycle, collector.latency);
    ++collector.exp_ptr;
    ++collector.outputs;
    ++outputs_seen;
    if (collector.first_cycle < 0) collector.first_cycle = cycle;
    collector.last_cycle = cycle;
}

// A tick: the inputs are already applied, this drives the rising edge that
// samples them, and the outputs read afterwards are that edge's registered
// values.
void tick(Vot_a3_route_block_max_top& top) {
    top.clk = 0;
    top.eval();
    top.clk = 1;
    top.eval();
    ++cycle;
    collect(top);
}

void idle_tick(Vot_a3_route_block_max_top& top) {
    top.in_valid = 0;
    top.clear = 0;
    tick(top);
}

}  // namespace

int main(int argc, char** argv) {
    VerilatedContext ctx;
    // The context that owns the model must be the one the arguments reach.
    ctx.commandArgs(argc, argv);
    std::string dir = ".";
    const char* match = ctx.commandArgsPlusMatch("bmdir=");
    if (match && match[0] != '\0') {
        const std::string text(match);
        const size_t equals = text.find('=');
        if (equals != std::string::npos && equals + 1 < text.size()) {
            dir = text.substr(equals + 1);
        }
    }
    const std::string prefix = dir + "/";

    const std::vector<uint32_t> meta = load_hex32(prefix + "bm_meta.hex");
    const std::vector<uint32_t> cases = load_hex32(prefix + "bm_case.hex");
    const std::vector<uint32_t> vectors = load_hex32(prefix + "bm_vec.hex");
    const std::vector<uint32_t> expects = load_hex32(prefix + "bm_expect.hex");

    const uint32_t m_magic = at(meta, 0);
    const uint32_t m_version = at(meta, 1);
    const uint32_t m_block = at(meta, 2);
    const uint32_t m_score_w = at(meta, 3);
    const uint32_t m_exp_w = at(meta, 4);
    const uint32_t m_mant_w = at(meta, 5);
    const uint32_t m_cmp_stages = at(meta, 6);
    const uint32_t m_max_blocks = at(meta, 7);
    const uint32_t m_depth = at(meta, 8);
    const uint32_t m_cases = at(meta, 9);
    const uint32_t m_expect_count = at(meta, 11);
    const uint32_t m_blocks = at(meta, 12);
    const uint32_t m_positions = at(meta, 13);
    const uint32_t m_rows = at(meta, 14);
    const uint32_t m_faults = at(meta, 15);
    const uint32_t m_lanes_max = at(meta, 19);
    const uint32_t m_latency = at(meta, 21);

    Vot_a3_route_block_max_top top(&ctx);
    collector.expects = &expects;
    collector.latency = static_cast<long>(m_latency);

    top.clk = 0;
    top.rst_n = 0;
    top.in_valid = 0;
    top.clear = 0;
    top.in_valid_count_w = 0;
    top.in_row_last = 0;
    top.in_tag_w = 0;
    for (int lane = 0; lane < kLanesMax; ++lane) top.in_score_words[lane] = 0;
    for (int k = 0; k < 4; ++k) {
        top.clk = 0;
        top.eval();
        top.clk = 1;
        top.eval();
    }
    top.rst_n = 1;

    for (uint32_t c = 0; c < m_cases; ++c) {
        current_case = static_cast<long>(c);
        const size_t base = static_cast<size_t>(c) * kCaseStride;
        const uint32_t flags = at(cases, base + 1);
        const uint32_t vec_base = at(cases, base + 2);
        const uint32_t vec_count = at(cases, base + 3);
        const uint32_t exp_base = at(cases, base + 4);
        const uint32_t exp_count = at(cases, base + 5);
        const uint32_t err_code = at(cases, base + 6);
        const uint32_t err_detail = at(cases, base + 7);
        const uint32_t err_block_id = at(cases, base + 8);
        const uint32_t err_tag = at(cases, base + 9);

        collector.exp_base = exp_base * kExpStride;
        collector.exp_ptr = 0;
        collector.outputs = 0;
        collector.first_cycle = -1;
        collector.last_cycle = -1;
        collector.accepted.clear();
        collector.accepted_read = 0;
        cycle = 0;

        top.in_valid = 0;
        top.clear = 1;
        tick(top);
        top.clear = 0;

        for (uint32_t v = 0; v < vec_count; ++v) {
            const size_t record = (static_cast<size_t>(vec_base) + v) * kVecStride;
            const uint32_t idle_before = at(vectors, record + 3);
            for (uint32_t k = 0; k < idle_before; ++k) idle_tick(top);
            top.in_valid_count_w = at(vectors, record + 0);
            top.in_row_last = (at(vectors, record + 1) & kVecFlagRowLast) ? 1 : 0;
            top.in_tag_w = at(vectors, record + 2);
            for (int lane = 0; lane < kLanesMax; ++lane) {
                top.in_score_words[lane] = at(vectors, record + 4 + lane);
            }
            top.in_valid = 1;
            collector.accepted.push_back(cycle + 1);
            tick(top);
            top.in_valid = 0;
        }

        const long drain = static_cast<long>(top.pipeline_depth) + 4;
        for (long k = 0; k < drain; ++k) idle_tick(top);

        report("case_outputs", collector.outputs, exp_count);
        report("error_code", top.error_code, err_code);
        report("error_detail", top.error_detail, err_detail);
        report("error_block_id", top.error_block_id_w, err_block_id);
        report("error_tag", top.error_tag_w, err_tag);
        report("busy", top.busy, 0);
        if (flags & kCaseFlagFault) ++faults_seen;
        if (flags & kCaseFlagRate) {
            const long window = (collector.first_cycle < 0)
                                  ? 0
                                  : (collector.last_cycle - collector.first_cycle + 1);
            std::printf("RATE: case=%u outputs=%ld window=%ld first=%ld last=%ld\n",
                        c, collector.outputs, window, collector.first_cycle,
                        collector.last_cycle);
            report("rate_window", window, collector.outputs);
        }
    }

    current_case = -1;
    report("magic", m_magic, kMagic);
    report("layout_version", m_version, 1);
    report("param_block", top.param_block, m_block);
    report("param_score_w", top.param_score_w, m_score_w);
    report("param_exp_w", top.param_exp_w, m_exp_w);
    report("param_mant_w", top.param_mant_w, m_mant_w);
    report("param_max_blocks", top.param_max_blocks, m_max_blocks);
    report("param_cmp_stages", top.param_cmp_stages, m_cmp_stages);
    report("param_lanes_max", top.param_lanes_max, m_lanes_max);
    report("pipeline_depth", top.pipeline_depth, m_depth);
    report("blocks_count", top.blocks_count_w, m_blocks);
    report("positions_count", top.positions_count_w, m_positions);
    report("rows_count", top.rows_count_w, m_rows);
    report("total_outputs", outputs_seen, m_expect_count);
    report("refusal_cases", faults_seen, m_faults);

    top.final();

    if (failures == 0 && outputs_seen == static_cast<long>(m_blocks)
        && faults_seen == static_cast<long>(m_faults)) {
        std::printf("PASS: A3 V41 BLOCK_MAX block=%u cmp_stages=%u cases=%u outputs=%ld "
                    "faults=%ld checks=%ld\n",
                    m_block, m_cmp_stages, m_cases, outputs_seen, faults_seen, checks);
        return 0;
    }
    std::printf("FAILURES: %ld of %ld checks (outputs=%ld expected=%u)\n", failures, checks,
                outputs_seen, m_blocks);
    return 1;
}
