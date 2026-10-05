// ---------------------------------------------------------------------------
// Verilator harness for the ABI 3.0 RTL.
//
// This is the second, independent checker of the same campaign: it compiles the
// same RTL through a different elaboration and simulation engine, parses the
// generated vector files itself, and applies its own back-pressure pattern to
// the engine issue port.  It shares no checking code with
// rtl/test/tb_a3_microsequencer.sv -- only the vectors, which come from real
// ABI 3.0 deployments executed by runtime.sim.device.Device.
//
// It requires exact agreement on program-header admission and trap class, the
// retired/fetched/predicated-off/issued/loop/branch/wait/state counters, the
// ordered engine-issue sequence, the ordered stream of resolved operand tensor
// views -- descriptor, operand slot, leading extent, element offset and rank,
// which is where amendments A4 and A13 are checked -- the state
// commit-or-discard decision, and the trap class and first faulting
// instruction.
//
// The harness is the management processor (docs/CHIP_ARCHITECTURE_DESIGN.md
// section 13 item 12): it parses the four device images itself, writes the
// program and descriptor stores through the design's host load path once,
// binds the sixteen request symbols per case through it, and streams the
// program header through the admission beat port.  It is also the engines:
// every accepted issue completes in the cycle after its acceptance, oldest
// first (zero run-ahead; the randomised run-ahead lives in the deployment
// campaign).
// ---------------------------------------------------------------------------
#include "Vot_a3_microsequencer_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr unsigned kCaseStride = 35;
constexpr unsigned kViewStride = 7;
constexpr unsigned kProgramWords = 2048;
constexpr unsigned kDescWords = 4096;
constexpr unsigned kSymbolsPerCase = 16;

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "FAIL: " << message << "\n";
    std::exit(1);
}

std::vector<uint32_t> load_words(const char* path) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint32_t> words;
    std::string token;
    while (stream >> token) {
        words.push_back(static_cast<uint32_t>(std::stoul(token, nullptr, 16)));
    }
    return words;
}

// A wide image: one row per line of `digits` hex digits, as 32-bit lanes in
// little-endian lane order (lane 0 is the last 8 digits of the line).
std::vector<std::vector<uint32_t>> load_rows(const char* path, unsigned digits,
                                             unsigned rows) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<std::vector<uint32_t>> image;
    std::string token;
    while (stream >> token) {
        if (token.size() != digits)
            fail(std::string("malformed row in ") + path);
        std::vector<uint32_t> lanes(digits / 8, 0);
        for (unsigned lane = 0; lane < digits / 8; ++lane) {
            const std::string chunk =
                token.substr(digits - 8 * (lane + 1), 8);
            lanes[lane] = static_cast<uint32_t>(std::stoul(chunk, nullptr, 16));
        }
        image.push_back(lanes);
    }
    if (image.size() < rows) image.resize(rows, std::vector<uint32_t>(digits / 8, 0));
    return image;
}

class Model {
  public:
    Vot_a3_microsequencer_top dut;
    unsigned back_pressure = 0;

    void settle() { dut.eval(); }

    void step() {
        dut.clk = 1;
        dut.eval();
        dut.clk = 0;
        dut.eval();
    }

    void reset() {
        dut.rst_n = 0;
        dut.hdr_in_valid = 0;
        dut.hdr_in_start = 0;
        dut.hdr_in_word = 0;
        dut.host_we = 0;
        dut.host_sel = 0;
        dut.host_row = 0;
        dut.host_lane = 0;
        dut.host_wdata = 0;
        dut.start = 0;
        dut.issue_ready = 1;
        dut.complete_valid = 0;
        dut.complete_slot = 0;
        dut.complete_fault = 0;
        dut.complete_trap_class = 0;
        dut.cfg_program_base = 0;
        dut.cfg_instruction_count = 0;
        dut.cfg_entry_pc = 0;
        dut.cfg_desc_base = 0;
        dut.cfg_desc_count = 0;
        dut.cfg_max_retired_work = 0;
        dut.cfg_state_count = 0;
        dut.predicate_read_valid = 0;
        dut.predicate_read_value = 0;
        dut.predicate_read_trap_class = 0;
        for (unsigned cycle = 0; cycle < 6; ++cycle) step();
        dut.rst_n = 1;
        for (unsigned cycle = 0; cycle < 2; ++cycle) step();
    }

    void host_write(unsigned sel, uint32_t row, unsigned lane, uint32_t data) {
        dut.host_sel = sel;
        dut.host_row = row;
        dut.host_lane = lane;
        dut.host_wdata = data;
        dut.host_we = 1;
        step();
        dut.host_we = 0;
    }

    // A deliberately different stall pattern from the Icarus testbench: the
    // consumer accepts on two cycles out of three, offset by the case index.
    bool ready_now(unsigned tick, unsigned salt) {
        return ((tick + salt) % 3) != 0;
    }
};

struct Check {
    unsigned count = 0;

    void equal(const char* label, unsigned index, uint64_t actual,
               uint64_t expected) {
        ++count;
        if (actual != expected) {
            char buffer[256];
            std::snprintf(buffer, sizeof(buffer),
                          "case %u %s: %llu expected %llu", index, label,
                          static_cast<unsigned long long>(actual),
                          static_cast<unsigned long long>(expected));
            fail(buffer);
        }
    }
};

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const std::vector<uint32_t> cases = load_words("a3_case.hex");
    const std::vector<uint32_t> issues = load_words("a3_issue.hex");
    const std::vector<uint32_t> views = load_words("a3_view.hex");
    const std::vector<uint32_t> meta = load_words("a3_meta.hex");
    if (meta.size() < 5) fail("a3_meta.hex is short");
    const std::vector<std::vector<uint32_t>> image_program =
        load_rows("a3_program.hex", 64, kProgramWords);
    const std::vector<uint32_t> image_header = load_words("a3_header.hex");
    const std::vector<std::vector<uint32_t>> image_desc =
        load_rows("a3_descriptor.hex", 384, kDescWords);
    const std::vector<uint32_t> image_symbol = load_words("a3_symbol.hex");

    const unsigned case_count = meta[0];
    const unsigned expected_issue_total = meta[1];
    const unsigned expected_view_total = meta[4];
    if (cases.size() < case_count * kCaseStride) fail("a3_case.hex is short");

    Model model;
    Check check;
    model.reset();

    // -- load the two control stores through the host path, once ----------
    model.settle();
    if (!model.dut.host_ready) fail("host path not ready before the load");
    unsigned long host_writes = 0;
    for (unsigned row = 0; row < kProgramWords; ++row)
        for (unsigned lane = 0; lane < 8; ++lane) {
            model.host_write(0, row, lane, image_program[row][lane]);
            ++host_writes;
        }
    for (unsigned row = 0; row < kDescWords; ++row)
        for (unsigned lane = 0; lane < 48; ++lane) {
            model.host_write(1, row, lane, image_desc[row][lane]);
            ++host_writes;
        }
    model.step();
    if (model.dut.host_write_refused)
        fail("a control-store write was refused during the load");
    std::printf("HOST_LOAD program_rows=%u descriptor_rows=%u writes=%lu refused=%u\n",
                kProgramWords, kDescWords, host_writes,
                static_cast<unsigned>(model.dut.host_write_refused));

    unsigned total_issues = 0;
    unsigned total_views = 0;
    unsigned total_traps = 0;
    unsigned total_programs = 0;
    unsigned total_headers = 0;

    for (unsigned index = 0; index < case_count; ++index) {
        const uint32_t* word = cases.data() + index * kCaseStride;
        const uint32_t flags = word[10];

        // -- request symbols: sixteen 64-bit entries with bound bits --------
        for (unsigned symbol = 0; symbol < kSymbolsPerCase; ++symbol) {
            const size_t at = static_cast<size_t>(word[4]) + symbol;
            const uint32_t value = at < image_symbol.size() ? image_symbol[at] : 0;
            model.host_write(2, symbol, 0, value);
            model.host_write(2, symbol, 1, 0);
            model.host_write(2, symbol, 2, (word[5] >> symbol) & 1U);
        }
        if (model.dut.host_write_refused) fail("a symbol write was refused");

        // -- program header admission: 64 beats through the port -----------
        for (unsigned beat = 0; beat < 64; ++beat) {
            const size_t at = static_cast<size_t>(word[6]) + beat;
            model.dut.hdr_in_valid = 1;
            model.dut.hdr_in_start = (beat == 0) ? 1 : 0;
            model.dut.hdr_in_word = at < image_header.size() ? image_header[at] : 0;
            model.step();
        }
        model.dut.hdr_in_valid = 0;
        model.dut.hdr_in_start = 0;
        unsigned guard = 0;
        while (!model.dut.header_done && guard < 400) {
            model.step();
            ++guard;
        }
        if (!model.dut.header_done) fail("header admission timeout");
        ++total_headers;
        check.equal("header legal", index, model.dut.header_legal, flags & 1U);
        check.equal("header trap class", index, model.dut.header_trap_class,
                    word[11]);
        if (flags & 1U) {
            check.equal("header instruction count", index,
                        model.dut.header_instruction_count, word[12]);
            check.equal("header entrypoint count", index,
                        model.dut.header_entrypoint_count, word[13]);
        }
        model.step();

        if (!(flags & 2U)) continue;

        // -- transaction ------------------------------------------------
        ++total_programs;
        model.dut.cfg_program_base = word[0];
        model.dut.cfg_instruction_count = word[1];
        model.dut.cfg_desc_base = word[2];
        model.dut.cfg_desc_count = word[3];
        model.dut.cfg_entry_pc = word[7];
        model.dut.cfg_max_retired_work =
            (static_cast<uint64_t>(word[9]) << 32) | word[8];
        model.dut.cfg_state_count = word[34];
        const unsigned issue_base = word[30];
        const unsigned issue_count = word[31];
        if ((issue_base + issue_count) * 2 > issues.size())
            fail("issue image is short");
        const unsigned view_base = word[32];
        const unsigned view_count = word[33];
        if ((view_base + view_count) * kViewStride > views.size())
            fail("view image is short");

        model.dut.start = 1;
        model.step();
        model.dut.start = 0;

        std::deque<uint32_t> pending;
        unsigned seen = 0;
        unsigned views_seen = 0;
        unsigned tick = 0;
        guard = 0;
        while (!model.dut.done && guard < 400000) {
            model.dut.issue_ready = model.ready_now(tick, index) ? 1 : 0;
            // the engines: complete the oldest accepted operation
            model.dut.complete_valid = 0;
            if (!pending.empty()) {
                model.dut.complete_valid = 1;
                model.dut.complete_slot = pending.front();
                pending.pop_front();
            }
            model.settle();
            const bool fire = model.dut.issue_valid && model.dut.issue_ready;
            const uint32_t family = model.dut.issue_family;
            const uint32_t sub = model.dut.issue_sub;
            const uint32_t descriptor = model.dut.issue_descriptor_id;
            const uint32_t slot = model.dut.issue_slot;
            // The view port is an observation pulse, not a handshake: one
            // assertion is one resolved operand view.
            const bool view_fire = model.dut.view_valid;
            const uint32_t view_descriptor = model.dut.view_descriptor_id;
            const uint32_t view_slot = model.dut.view_slot;
            const uint32_t view_extent = model.dut.view_extent;
            const uint32_t view_extent_axis = model.dut.view_extent_axis;
            const uint64_t view_offset = model.dut.view_element_offset;
            const uint32_t view_rank = model.dut.view_rank;
            model.step();
            if (fire) pending.push_back(slot);
            ++tick;
            ++guard;
            if (view_fire) {
                if (views_seen >= view_count) fail("resolved view overflow");
                const uint32_t* expect =
                    views.data() + (view_base + views_seen) * kViewStride;
                check.equal("view descriptor", index, view_descriptor, expect[0]);
                check.equal("view operand slot", index, view_slot, expect[1]);
                // Amendments A13 and A18: the resolved extent of the axis the
                // view declares, and that axis.
                check.equal("view resolved extent", index, view_extent, expect[2]);
                // Amendment A4: the accumulated element offset.
                check.equal("view element offset", index, view_offset,
                            (static_cast<uint64_t>(expect[4]) << 32) | expect[3]);
                check.equal("view rank", index, view_rank, expect[5]);
                check.equal("view extent axis", index, view_extent_axis, expect[6]);
                ++views_seen;
                ++total_views;
            }
            if (!fire) continue;
            if (seen >= issue_count) fail("engine issue overflow");
            const uint32_t expect_opcode = issues[(issue_base + seen) * 2];
            const uint32_t expect_descriptor = issues[(issue_base + seen) * 2 + 1];
            check.equal("issue opcode", index, (family << 8) | sub,
                        expect_opcode & 0xFFFFU);
            check.equal("issue descriptor", index, descriptor, expect_descriptor);
            ++seen;
            ++total_issues;
        }
        model.dut.complete_valid = 0;
        model.dut.issue_ready = 1;
        if (!model.dut.done) fail("transaction timeout");

        check.equal("complete", index, model.dut.complete, (flags >> 2) & 1U);
        check.equal("trap class", index, model.dut.trap_class, word[14]);
        if (model.dut.trapped) {
            ++total_traps;
            check.equal("first fault", index, model.dut.first_fault_instruction,
                        word[15]);
        }
        check.equal("fetched", index, model.dut.count_fetched, word[16]);
        check.equal("retired", index, model.dut.count_retired, word[17]);
        check.equal("predicated off", index, model.dut.count_predicated_off,
                    word[18]);
        check.equal("issued", index, model.dut.count_issued, word[19]);
        check.equal("loop iterations", index, model.dut.count_loop_iterations,
                    word[20]);
        check.equal("branches", index, model.dut.count_branches, word[21]);
        check.equal("wait events", index, model.dut.count_wait_events, word[22]);
        check.equal("state prepares", index, model.dut.count_state_prepares,
                    word[23]);
        check.equal("state commits", index, model.dut.count_state_commits,
                    word[24]);
        check.equal("state discards", index, model.dut.count_state_discards,
                    word[25]);
        check.equal("state reads", index, model.dut.count_state_reads, word[26]);
        check.equal("state generation advances", index,
                    model.dut.count_state_generation_advances, word[27]);
        check.equal("state commits applied", index,
                    model.dut.count_state_commits_applied, word[28]);
        check.equal("state rows committed", index,
                    model.dut.count_state_rows_committed, word[29]);
        check.equal("issue count", index, seen, issue_count);
        check.equal("resolved view count", index, views_seen, view_count);
        check.equal("views resolved counter", index,
                    model.dut.count_views_resolved, view_count);
        check.equal("event single assignment", index,
                    model.dut.event_signal_error, 0U);
        check.equal("irs protocol", index, model.dut.irs_protocol_error, 0U);
        check.equal("outstanding at done", index, model.dut.dbg_outstanding, 0U);
        model.step();
    }

    if (total_issues != expected_issue_total)
        fail("engine issue total differs from the vector set");
    if (total_views != expected_view_total)
        fail("resolved view total differs from the vector set");
    // A comparison that compared nothing is a defect, not a pass.
    if (total_views == 0)
        fail("no operand view was resolved; the A4/A13 comparison is vacuous");
    model.dut.final();
    std::printf(
        "PASS: ABI3 RTL microsequencer cases=%u headers=%u programs=%u "
        "issues=%u views=%u traps=%u checks=%u\n",
        case_count, total_headers, total_programs, total_issues, total_views,
        total_traps, check.count);
    return 0;
}
