// ---------------------------------------------------------------------------
// Verilator harness: the four deployments this program ships, co-simulated.
//
// The second, independent checker of the deployment campaign.  It elaborates
// and simulates the same RTL through a different engine, parses the generated
// vector files itself, and applies a different back-pressure pattern to the
// engine issue port.  It shares no checking code with
// rtl/test/tb_a3_deployment.sv -- only the vectors, which are the real
// Qwen3-8B ROM and HBM, plus DeepSeek-V4-Flash ROM-wafer and HBM-cluster
// deployments executed by runtime.sim.device.Device.
//
// Required agreement, per case: program-header admission, trap class,
// instruction and entrypoint counts and the declared retired-work bound; every
// engine issue in program order including the instruction index that issued it;
// every resolved operand view in program order then operand order; the
// fourteen transaction counters plus the views-resolved counter; the completion
// decision; the trap class and first faulting instruction.
//
// A divergence does not stop the run: the first disagreement in a case is
// recorded with the same numeric site code the Icarus testbench uses,
// comparison for that case is abandoned, and the next case starts clean.  The
// per-case and per-deployment lines below are formatted identically in both
// checkers, so the campaign can require the two simulators to have seen the
// same thing even when what they saw was a defect.
//
// Engine datapaths are out of scope, as in the sibling campaign: the golden
// model runs recording no-op engines, so this correlates the instruction
// stream and not the arithmetic.
// ---------------------------------------------------------------------------
#include "Vot_a3_microsequencer_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr unsigned kCaseStride = 40;
constexpr unsigned kIssueStride = 3;
constexpr unsigned kViewStride = 7;
constexpr unsigned kPredicateStride = 3;
// A whole DeepSeek prefill is 29,595 fetched instructions; the guard catches a
// hang without mistaking a long real program for one.
constexpr unsigned kRunGuard = 40000000u;

// Divergence site codes.  Transcribed identically in
// rtl/test/tb_a3_deployment.sv; numbers rather than strings so two
// independently written checkers name the same site the same way.
enum Site : int {
    kNone = 0,
    kIssueOpcode = 1,
    kIssueDescriptor = 2,
    kIssueIndex = 3,
    kIssueOverflow = 4,
    kIssueCount = 5,
    kViewDescriptor = 6,
    kViewSlot = 7,
    kViewExtent = 8,
    kViewOffset = 9,
    kViewRank = 10,
    kViewAxis = 11,
    kViewOverflow = 12,
    kViewCount = 13,
    kViewCounter = 14,
    kPredicateObject = 15,
    kPredicateElement = 16,
    kPredicateOverflow = 17,
    kPredicateCount = 18,
    kHeaderLegal = 20,
    kHeaderTrap = 21,
    kHeaderInstructions = 22,
    kHeaderEntrypoints = 23,
    kHeaderWork = 24,
    kComplete = 30,
    kTrapClass = 31,
    kFirstFault = 32,
    kFetched = 33,
    kRetired = 34,
    kPredicatedOff = 35,
    kIssued = 36,
    kLoopIterations = 37,
    kBranches = 38,
    kWaitEvents = 39,
    kStatePrepares = 40,
    kStateCommits = 41,
    kStateDiscards = 42,
    kStateReads = 43,
    kStateAdvances = 44,
    kStateApplied = 45,
    kStateRows = 46,
    kSignalError = 47,
    kStateApplyOverflow = 48,
};

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "FAIL: " << message << "\n";
    std::exit(2);
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

class Model {
  public:
    Vot_a3_microsequencer_top dut;

    void settle() { dut.eval(); }

    void step() {
        dut.clk = 1;
        dut.eval();
        dut.clk = 0;
        dut.eval();
    }

    void reset() {
        dut.rst_n = 0;
        dut.header_start = 0;
        dut.start = 0;
        dut.issue_ready = 1;
        dut.cfg_header_base = 0;
        dut.cfg_program_base = 0;
        dut.cfg_instruction_count = 0;
        dut.cfg_entry_pc = 0;
        dut.cfg_desc_base = 0;
        dut.cfg_desc_count = 0;
        dut.cfg_symbol_base = 0;
        dut.cfg_symbol_mask = 0;
        dut.cfg_max_retired_work = 0;
        dut.cfg_state_count = 0;
        dut.predicate_read_valid = 0;
        dut.predicate_read_value = 0;
        dut.predicate_read_trap_class = 0;
        for (unsigned cycle = 0; cycle < 6; ++cycle) step();
        dut.rst_n = 1;
        for (unsigned cycle = 0; cycle < 2; ++cycle) step();
    }

    // Deliberately unlike the Icarus LFSR: the consumer accepts on three cycles
    // out of five, offset by the case index, so neither simulator's issue
    // stream is checked under the other's stall pattern.
    bool ready_now(unsigned tick, unsigned salt) {
        return ((tick + salt) % 5) < 3;
    }
};

// One case's first disagreement, and nothing after it: everything downstream of
// a divergence is a consequence of it, not a second finding.
struct CaseResult {
    int code = kNone;
    uint64_t rtl = 0;
    uint64_t golden = 0;
    unsigned long checks = 0;

    void record(int site, uint64_t actual, uint64_t expected) {
        if (code == kNone) {
            code = site;
            rtl = actual;
            golden = expected;
        }
    }

    void equal(int site, uint64_t actual, uint64_t expected) {
        ++checks;
        if (actual != expected) record(site, actual, expected);
    }

    bool agreeing() const { return code == kNone; }
};

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const std::vector<uint32_t> cases = load_words("a3_deployment_case.hex");
    const std::vector<uint32_t> issues = load_words("a3_deployment_issue.hex");
    const std::vector<uint32_t> views = load_words("a3_deployment_view.hex");
    const std::vector<uint32_t> predicates =
        load_words("a3_deployment_predicate.hex");
    const std::vector<uint32_t> meta = load_words("a3_deployment_meta.hex");
    if (meta.size() < 6) fail("a3_deployment_meta.hex is short");

    const unsigned case_count = meta[0];
    const unsigned expected_issue_total = meta[1];
    const unsigned expected_view_total = meta[2];
    const unsigned expected_completions = meta[3];
    const unsigned deployment_count = meta[4];
    const unsigned expected_predicate_total = meta[5];
    if (cases.size() < case_count * kCaseStride)
        fail("a3_deployment_case.hex is short");

    Model model;
    model.reset();

    // Production-profile admission: any legacy state-resource count is
    // rejected before the first instruction fetch.  This is independent of
    // the eight real-deployment cases, all of which correctly declare zero.
    model.dut.cfg_instruction_count = 1;
    model.dut.cfg_max_retired_work = 1;
    model.dut.cfg_state_count = 1;
    model.dut.start = 1;
    model.step();
    model.dut.start = 0;
    unsigned profile_guard = 0;
    while (!model.dut.done && profile_guard < 20) {
        model.step();
        ++profile_guard;
    }
    if (!model.dut.done || !model.dut.trapped || model.dut.complete ||
        model.dut.trap_class != 4 ||
        model.dut.first_fault_instruction != 0xffffffffU ||
        model.dut.count_fetched != 0 ||
        model.dut.count_state_prepares != 0 ||
        model.dut.state_apply_overflow)
        fail("STATE_COMPAT=0 did not reject state resources before fetch");
    std::printf("PROFILE: ABI3 live-buffer state exclusion PASS\n");
    model.reset();

    unsigned total_issues = 0;
    unsigned total_views = 0;
    unsigned total_predicates = 0;
    unsigned total_completions = 0;
    unsigned diverged_cases = 0;
    unsigned signal_flag_cases = 0;
    unsigned apply_overflow_cases = 0;
    unsigned long checks = 0;

    long deploy_index = -1;
    unsigned deploy_cases = 0;
    unsigned deploy_issues = 0;
    unsigned deploy_views = 0;
    unsigned deploy_predicates = 0;
    unsigned deploy_diverged = 0;

    auto close_deployment = [&]() {
        if (deploy_cases > 0) {
            std::printf(
                "DEPLOY %ld cases=%u diverged=%u issues=%u views=%u predicates=%u\n",
                        deploy_index, deploy_cases, deploy_diverged,
                        deploy_issues, deploy_views, deploy_predicates);
        }
    };

    for (unsigned index = 0; index < case_count; ++index) {
        const uint32_t* word = cases.data() + index * kCaseStride;
        const uint32_t flags = word[10];
        const uint32_t tag = word[35];
        // word[8..9] is the bound the transaction is configured with; the
        // header must publish word[36..37], the bound the program declares.
        // They differ only when the vector set lowered the co-simulation bound.
        const uint64_t work = (static_cast<uint64_t>(word[9]) << 32) | word[8];
        const uint64_t declared_work =
            (static_cast<uint64_t>(word[37]) << 32) | word[36];
        const long this_deploy = static_cast<long>(tag >> 8);
        if (this_deploy != deploy_index) {
            close_deployment();
            deploy_index = this_deploy;
            deploy_cases = 0;
            deploy_issues = 0;
            deploy_views = 0;
            deploy_predicates = 0;
            deploy_diverged = 0;
        }
        ++deploy_cases;
        CaseResult result;

        // -- program header admission ---------------------------------
        model.dut.cfg_header_base = word[6];
        model.dut.header_start = 1;
        model.step();
        model.dut.header_start = 0;
        unsigned guard = 0;
        while (!model.dut.header_done && guard < 400) {
            model.step();
            ++guard;
        }
        if (!model.dut.header_done) fail("header admission timeout");
        result.equal(kHeaderLegal, model.dut.header_legal, flags & 1U);
        result.equal(kHeaderTrap, model.dut.header_trap_class, word[11]);
        result.equal(kHeaderInstructions, model.dut.header_instruction_count,
                     word[12]);
        result.equal(kHeaderEntrypoints, model.dut.header_entrypoint_count,
                     word[13]);
        result.equal(kHeaderWork, model.dut.header_max_retired_work,
                     declared_work);
        model.step();

        // -- transaction ------------------------------------------------
        model.dut.cfg_program_base = word[0];
        model.dut.cfg_instruction_count = word[1];
        model.dut.cfg_desc_base = word[2];
        model.dut.cfg_desc_count = word[3];
        model.dut.cfg_symbol_base = word[4];
        model.dut.cfg_symbol_mask = word[5];
        model.dut.cfg_entry_pc = word[7];
        model.dut.cfg_max_retired_work = work;
        model.dut.cfg_state_count = word[34];
        const unsigned issue_base = word[30];
        const unsigned issue_count = word[31];
        if (static_cast<size_t>(issue_base + issue_count) * kIssueStride >
            issues.size())
            fail("issue image is short");
        const unsigned view_base = word[32];
        const unsigned view_count = word[33];
        if (static_cast<size_t>(view_base + view_count) * kViewStride >
            views.size())
            fail("view image is short");
        const unsigned predicate_base = word[38];
        const unsigned predicate_count = word[39];
        if (static_cast<size_t>(predicate_base + predicate_count) *
                kPredicateStride >
            predicates.size())
            fail("predicate image is short");

        model.dut.start = 1;
        model.step();
        model.dut.start = 0;

        unsigned seen = 0;
        unsigned views_seen = 0;
        unsigned predicates_seen = 0;
        unsigned tick = 0;
        guard = 0;
        while (!model.dut.done && guard < kRunGuard) {
            model.dut.issue_ready = model.ready_now(tick, index) ? 1 : 0;
            model.dut.predicate_read_valid = 0;
            model.dut.predicate_read_trap_class = 0;
            model.settle();
            if (model.dut.predicate_read_req) {
                if (predicates_seen >= predicate_count) {
                    result.record(kPredicateOverflow, predicates_seen,
                                  predicate_count);
                    model.dut.predicate_read_value = 0;
                } else {
                    const uint32_t* expect =
                        predicates.data() +
                        static_cast<size_t>(predicate_base + predicates_seen) *
                            kPredicateStride;
                    result.equal(kPredicateObject,
                                 model.dut.predicate_read_object_id, expect[0]);
                    result.equal(kPredicateElement,
                                 model.dut.predicate_read_element_index,
                                 expect[1]);
                    model.dut.predicate_read_value = expect[2] & 1U;
                    ++predicates_seen;
                    ++total_predicates;
                    ++deploy_predicates;
                }
                model.dut.predicate_read_valid = 1;
            }
            const bool fire = model.dut.issue_valid && model.dut.issue_ready;
            const uint32_t family = model.dut.issue_family;
            const uint32_t sub = model.dut.issue_sub;
            const uint32_t descriptor = model.dut.issue_descriptor_id;
            const uint32_t issue_index = model.dut.issue_index;
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
            ++tick;
            ++guard;
            if (view_fire && result.agreeing()) {
                if (views_seen >= view_count) {
                    result.record(kViewOverflow, views_seen, view_count);
                } else {
                    const uint32_t* expect =
                        views.data() +
                        static_cast<size_t>(view_base + views_seen) * kViewStride;
                    result.equal(kViewDescriptor, view_descriptor, expect[0]);
                    result.equal(kViewSlot, view_slot, expect[1]);
                    // Amendments A13 and A18: the resolved extent of the axis
                    // the view declares, and that axis.
                    result.equal(kViewExtent, view_extent, expect[2]);
                    // Amendment A4: the accumulated element offset.
                    result.equal(kViewOffset, view_offset,
                                 (static_cast<uint64_t>(expect[4]) << 32) |
                                     expect[3]);
                    result.equal(kViewRank, view_rank, expect[5]);
                    result.equal(kViewAxis, view_extent_axis, expect[6]);
                    ++views_seen;
                    ++total_views;
                    ++deploy_views;
                }
            }
            if (!fire || !result.agreeing()) continue;
            if (seen >= issue_count) {
                result.record(kIssueOverflow, seen, issue_count);
                continue;
            }
            const uint32_t* expect =
                issues.data() +
                static_cast<size_t>(issue_base + seen) * kIssueStride;
            result.equal(kIssueOpcode, (family << 8) | sub, expect[0] & 0xFFFFU);
            result.equal(kIssueDescriptor, descriptor, expect[1]);
            // The program counter that issued it.
            result.equal(kIssueIndex, issue_index, expect[2]);
            ++seen;
            ++total_issues;
            ++deploy_issues;
        }
        if (!model.dut.done) fail("transaction timeout");

        // Trap class first: when the RTL stops a program the golden model runs
        // to completion, "trap class 4 where 0 was expected" names the
        // divergence and "complete 0 where 1 was expected" only restates it.
        result.equal(kTrapClass, model.dut.trap_class, word[14]);
        if (model.dut.trapped)
            result.equal(kFirstFault, model.dut.first_fault_instruction, word[15]);
        result.equal(kComplete, model.dut.complete, (flags >> 2) & 1U);
        if (model.dut.complete) ++total_completions;
        result.equal(kFetched, model.dut.count_fetched, word[16]);
        result.equal(kRetired, model.dut.count_retired, word[17]);
        result.equal(kPredicatedOff, model.dut.count_predicated_off, word[18]);
        result.equal(kIssued, model.dut.count_issued, word[19]);
        result.equal(kLoopIterations, model.dut.count_loop_iterations, word[20]);
        result.equal(kBranches, model.dut.count_branches, word[21]);
        result.equal(kWaitEvents, model.dut.count_wait_events, word[22]);
        result.equal(kStatePrepares, model.dut.count_state_prepares, word[23]);
        result.equal(kStateCommits, model.dut.count_state_commits, word[24]);
        result.equal(kStateDiscards, model.dut.count_state_discards, word[25]);
        result.equal(kStateReads, model.dut.count_state_reads, word[26]);
        result.equal(kStateAdvances, model.dut.count_state_generation_advances,
                     word[27]);
        result.equal(kStateApplied, model.dut.count_state_commits_applied,
                     word[28]);
        result.equal(kStateRows, model.dut.count_state_rows_committed, word[29]);
        result.equal(kIssueCount, seen, issue_count);
        result.equal(kViewCount, views_seen, view_count);
        result.equal(kViewCounter, model.dut.count_views_resolved, view_count);
        result.equal(kPredicateCount, predicates_seen, predicate_count);

        // RTL status bits.  See the note in rtl/test/tb_a3_deployment.sv:
        // after amendment A24 event_signal_error reports only an event ID
        // outside the scoreboard's space, and amendment A23 makes that a
        // refusal at admission, so zero is the ABI's expectation for any
        // admitted program rather than a hand-written constant.
        // STATE_COMPAT is zero in this production-profile elaboration and all
        // four certified deployments contain zero state records.  The
        // compatibility apply-overflow output is therefore tied to zero.
        result.equal(kSignalError, model.dut.event_signal_error, 0U);
        result.equal(kStateApplyOverflow,
                     model.dut.state_apply_overflow, 0U);
        if (model.dut.event_signal_error) ++signal_flag_cases;
        if (model.dut.state_apply_overflow) ++apply_overflow_cases;

        checks += result.checks;
        if (!result.agreeing()) {
            ++diverged_cases;
            ++deploy_diverged;
        }
        std::printf(
            "CASE %u tag=%04x %s code=%d rtl=%llu golden=%llu issues=%u/%u "
            "views=%u/%u predicates=%u/%u fetched=%u retired=%u trap=%u "
            "fault=%u sigerr=%u applyovf=%u\n",
            index, tag, result.agreeing() ? "OK" : "DIVERGE", result.code,
            static_cast<unsigned long long>(result.rtl),
            static_cast<unsigned long long>(result.golden), seen, issue_count,
            views_seen, view_count, predicates_seen, predicate_count,
            model.dut.count_fetched,
            model.dut.count_retired, model.dut.trap_class,
            model.dut.first_fault_instruction, model.dut.event_signal_error,
            model.dut.state_apply_overflow);
        model.step();
    }
    close_deployment();
    model.dut.final();

    if (diverged_cases == 0) {
        if (total_issues != expected_issue_total)
            fail("engine issue total differs from the vector set");
        if (total_views != expected_view_total)
            fail("resolved view total differs from the vector set");
        if (total_completions != expected_completions)
            fail("completion total differs from the vector set");
        if (total_predicates != expected_predicate_total)
            fail("predicate total differs from the vector set");
        // A comparison that compared nothing is a defect, not a pass.
        if (total_views == 0)
            fail("no operand view was resolved; the comparison is vacuous");
        std::printf(
            "PASS: ABI3 RTL deployment co-simulation deployments=%u cases=%u "
            "completions=%u issues=%u views=%u predicates=%u "
            "signal_flag_cases=%u apply_overflow_cases=%u checks=%lu\n",
            deployment_count, case_count, total_completions, total_issues,
            total_views, total_predicates, signal_flag_cases,
            apply_overflow_cases, checks);
        return 0;
    }
    std::printf(
        "FAIL: ABI3 RTL deployment co-simulation diverged_cases=%u of %u "
        "deployments=%u issues=%u views=%u predicates=%u "
        "signal_flag_cases=%u apply_overflow_cases=%u checks=%lu\n",
        diverged_cases, case_count, deployment_count, total_issues, total_views,
        total_predicates, signal_flag_cases, apply_overflow_cases, checks);
    std::cerr << "FAIL: the RTL and runtime.sim.device.Device disagree on a "
                 "shipped program\n";
    return 1;
}
