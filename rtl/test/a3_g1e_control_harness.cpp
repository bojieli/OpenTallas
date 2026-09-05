// ---------------------------------------------------------------------------
// Rung G1e -- the governed workload's whole CONTROL path, in RTL.
//
// This checker drives rtl/test/a3_shipped_prefix_top.sv elaborated with
// ENABLE_RESULT_INJECTION=1: the design's own control plane
// (rtl/abi3/ot_a3_device_top.sv -- fetch, decode, the symbol file, view
// resolution, predicates, the loop stack, the wait set, the dependence table,
// the event scoreboard and queue acceptance) runs every pass of the governed
// workload, and only the engine RESULT is supplied, at the engine result
// boundary.  Under that parameter the top ties the engine bridge's
// issue_valid low, so no engine is issued to and none can compute: the
// checker requires real_launch_count and engine_work_count to read zero, and
// that is the evidence that what ran was the control plane.
//
// What is injected, and where it can reach.  Three inputs carry model values:
// inj_result_valid / inj_result_fault / inj_result_trap_class, which the top
// muxes into the engine port's completion handshake, and inj_write_en /
// inj_write_addr / inj_write_data, which the top muxes into the result
// memory's write port.  Nothing else in this file drives a design input that
// fetch, decode, view resolution, predicate evaluation, the loop stack, the
// wait set or issue can observe: the per-pass configuration is the request's
// own (program base, instruction count, descriptor base and count, the
// sixteen request symbols with their bound bits, the entry PC, the retired-
// work bound and the state count), which is what a host supplies on every
// machine.  tools/rtl_abi3_g1e_control_campaign.py re-derives that claim from
// the RTL source itself rather than from this comment.
//
// What is compared.  Every issue the RTL makes, in program order, with its
// opcode, descriptor id and program counter, followed by every view its
// resolver produced with slot, descriptor id, extent, extent axis, element
// offset and rank -- flattened to one element vector and compared to the
// golden model's element for element, failing at the FIRST divergence with
// the element index and the field named.  The golden is produced by
// tools/build_abi3_g1e_control_vectors.py from runtime.sim.device.Device
// alone; this file never writes it.
//
// Environment:
//   OT_A3_G1E_DIR        directory holding the vector set (default ".")
//   OT_A3_TRACE_OUT      write the RTL trace out for inspection (optional)
//   OT_A3_CYCLE_GUARD    per-pass cycle watchdog (default 4e9)
// ---------------------------------------------------------------------------
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "Vot_a3_shipped_prefix_top.h"
#include "Vot_a3_shipped_prefix_top__Dpi.h"
#include "verilated.h"

namespace {

const char* env_or_null(const char* name) {
    const char* value = std::getenv(name);
    if (value == nullptr || value[0] == '\0') return nullptr;
    return value;
}

std::uint64_t env_u64(const char* name, std::uint64_t fallback) {
    const char* value = env_or_null(name);
    if (value == nullptr) return fallback;
    return std::strtoull(value, nullptr, 10);
}

std::string vector_dir() {
    const char* dir = env_or_null("OT_A3_G1E_DIR");
    return dir == nullptr ? std::string(".") : std::string(dir);
}

std::string vector_path(const std::string& name) {
    return vector_dir() + "/" + name;
}

std::vector<std::uint32_t> read_hex(const std::string& name) {
    std::ifstream input(vector_path(name));
    if (!input) throw std::runtime_error("cannot read " + name);
    std::vector<std::uint32_t> out;
    std::string token;
    while (input >> token)
        out.push_back(static_cast<std::uint32_t>(std::stoul(token, nullptr, 16)));
    return out;
}

// One row of a wide memory image, little-endian lanes of 32 bits.
std::vector<std::vector<std::uint32_t>> read_rows(const std::string& name,
                                                 unsigned lanes,
                                                 std::size_t rows) {
    std::ifstream input(vector_path(name));
    if (!input) throw std::runtime_error("cannot read " + name);
    std::vector<std::vector<std::uint32_t>> out;
    std::string token;
    while (input >> token) {
        if (token.size() != lanes * 8u)
            throw std::runtime_error("row width mismatch in " + name);
        std::vector<std::uint32_t> row(lanes, 0);
        for (unsigned lane = 0; lane < lanes; ++lane) {
            const std::string slice =
                token.substr(token.size() - (lane + 1) * 8, 8);
            row[lane] = static_cast<std::uint32_t>(std::stoul(slice, nullptr, 16));
        }
        out.push_back(std::move(row));
    }
    if (out.size() != rows)
        throw std::runtime_error(name + " has the wrong number of rows");
    return out;
}

struct Checker {
    std::uint64_t checks = 0;
    std::uint64_t failures = 0;

    void equal(const char* what, std::uint64_t got, std::uint64_t want) {
        ++checks;
        if (got == want) return;
        ++failures;
        if (failures <= 40)
            std::cerr << "FAIL: " << what << " got=" << got << " want=" << want
                      << "\n";
    }
};

// -- the trace ------------------------------------------------------------
struct View {
    std::uint64_t slot = 0;
    std::uint64_t descriptor_id = 0;
    std::uint64_t extent = 0;
    std::uint64_t extent_axis = 0;
    std::uint64_t element_offset = 0;
    std::uint64_t rank = 0;

    std::uint64_t field(const std::string& name) const {
        if (name == "slot") return slot;
        if (name == "descriptor_id") return descriptor_id;
        if (name == "extent") return extent;
        if (name == "extent_axis") return extent_axis;
        if (name == "element_offset") return element_offset;
        if (name == "rank") return rank;
        throw std::runtime_error("unknown VIEW field '" + name + "'");
    }
    void set(const std::string& name, std::uint64_t value) {
        if (name == "slot") slot = value;
        else if (name == "descriptor_id") descriptor_id = value;
        else if (name == "extent") extent = value;
        else if (name == "extent_axis") extent_axis = value;
        else if (name == "element_offset") element_offset = value;
        else if (name == "rank") rank = value;
        else throw std::runtime_error("unknown VIEW field '" + name + "'");
    }
};

struct Issue {
    std::uint64_t family = 0;
    std::uint64_t sub = 0;
    std::uint64_t descriptor_id = 0;
    std::uint64_t pc = 0;
    std::uint64_t queue = 0;
    std::uint64_t serial = 0;
    std::uint64_t irs_slot = 0;
    std::vector<View> views;

    std::uint64_t field(const std::string& name) const {
        if (name == "family") return family;
        if (name == "sub") return sub;
        if (name == "descriptor_id") return descriptor_id;
        if (name == "pc") return pc;
        if (name == "queue") return queue;
        if (name == "serial") return serial;
        if (name == "irs_slot") return irs_slot;
        throw std::runtime_error("unknown ISSUE field '" + name + "'");
    }
    void set(const std::string& name, std::uint64_t value) {
        if (name == "family") family = value;
        else if (name == "sub") sub = value;
        else if (name == "descriptor_id") descriptor_id = value;
        else if (name == "pc") pc = value;
        else if (name == "queue") queue = value;
        else if (name == "serial") serial = value;
        else if (name == "irs_slot") irs_slot = value;
        else throw std::runtime_error("unknown ISSUE field '" + name + "'");
    }
};

struct Record {
    std::vector<Issue> issues;
    std::vector<std::string> issue_fields;
    std::vector<std::string> view_fields;
};

Record read_trace(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot read golden trace " + path);
    Record record;
    bool issue_declared = false;
    bool view_declared = false;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string tag;
        fields >> tag;
        if (tag == "FIELDS") {
            std::string which;
            fields >> which;
            std::vector<std::string> names;
            std::string name;
            while (fields >> name) names.push_back(name);
            if (names.empty())
                throw std::runtime_error("empty FIELDS line in " + path);
            if (which == "ISSUE") {
                record.issue_fields = names;
                issue_declared = true;
            } else if (which == "VIEW") {
                record.view_fields = names;
                view_declared = true;
            } else {
                throw std::runtime_error("unknown FIELDS kind in " + path);
            }
            continue;
        }
        if (!issue_declared || !view_declared)
            throw std::runtime_error(
                "golden trace " + path +
                " has no FIELDS header: the compared field set must be "
                "declared, never assumed");
        std::vector<std::uint64_t> values;
        std::uint64_t value = 0;
        while (fields >> value) values.push_back(value);
        if (tag == "ISSUE") {
            if (values.size() != record.issue_fields.size())
                throw std::runtime_error("ISSUE arity disagrees with FIELDS");
            Issue issue;
            for (std::size_t i = 0; i < values.size(); ++i)
                issue.set(record.issue_fields[i], values[i]);
            record.issues.push_back(std::move(issue));
        } else if (tag == "VIEW") {
            if (record.issues.empty())
                throw std::runtime_error("VIEW before any ISSUE in " + path);
            if (values.size() != record.view_fields.size())
                throw std::runtime_error("VIEW arity disagrees with FIELDS");
            View view;
            for (std::size_t i = 0; i < values.size(); ++i)
                view.set(record.view_fields[i], values[i]);
            record.issues.back().views.push_back(view);
        } else {
            throw std::runtime_error("unknown trace tag '" + tag + "'");
        }
    }
    if (!issue_declared || !view_declared)
        throw std::runtime_error("golden trace " + path + " declares no FIELDS");
    return record;
}

void flatten(const Record& record, const std::vector<std::string>& issue_sel,
             const std::vector<std::string>& view_sel,
             std::vector<std::uint64_t>& values,
             std::vector<std::string>& labels) {
    for (std::size_t i = 0; i < record.issues.size(); ++i) {
        const auto& issue = record.issues[i];
        for (const auto& name : issue_sel) {
            values.push_back(issue.field(name));
            labels.push_back("issue[" + std::to_string(i) + "]." + name);
        }
        for (std::size_t v = 0; v < issue.views.size(); ++v) {
            for (const auto& name : view_sel) {
                values.push_back(issue.views[v].field(name));
                labels.push_back("issue[" + std::to_string(i) + "].view[" +
                                 std::to_string(v) + "]." + name);
            }
        }
    }
}

struct Comparison {
    bool equal = true;
    long long divergence_index = -1;
    std::string label;
    std::uint64_t got = 0;
    std::uint64_t want = 0;
    std::size_t compared = 0;
};

// Element for element.  First divergence wins and its index is recorded.
Comparison compare(const Record& rtl, const Record& golden) {
    Comparison out;
    std::vector<std::uint64_t> rtl_values, golden_values;
    std::vector<std::string> rtl_labels, golden_labels;
    flatten(rtl, golden.issue_fields, golden.view_fields, rtl_values, rtl_labels);
    flatten(golden, golden.issue_fields, golden.view_fields, golden_values,
            golden_labels);
    const std::size_t common = std::min(rtl_values.size(), golden_values.size());
    for (std::size_t i = 0; i < common; ++i) {
        ++out.compared;
        if (rtl_values[i] != golden_values[i]) {
            out.equal = false;
            out.divergence_index = static_cast<long long>(i);
            out.label = rtl_labels[i] + " vs golden " + golden_labels[i];
            out.got = rtl_values[i];
            out.want = golden_values[i];
            return out;
        }
    }
    if (rtl_values.size() != golden_values.size()) {
        out.equal = false;
        out.divergence_index = static_cast<long long>(common);
        out.label = rtl_values.size() < golden_values.size()
                        ? "rtl trace ends early"
                        : "rtl trace runs long";
        out.got = rtl_values.size();
        out.want = golden_values.size();
    }
    return out;
}

// -- the injected engine results -----------------------------------------
struct Result {
    std::uint32_t family = 0;
    std::uint32_t sub = 0;
    std::uint32_t descriptor_id = 0;
    std::uint32_t pc = 0;
    std::uint32_t fault = 0;
    std::uint32_t trap_class = 0;
    std::vector<std::pair<std::uint32_t, std::uint32_t>> words;
};

std::vector<Result> read_results(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot read results " + path);
    std::vector<Result> out;
    std::string line;
    std::uint64_t remaining = 0;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string tag;
        fields >> tag;
        if (tag == "RESULT") {
            if (remaining != 0)
                throw std::runtime_error("truncated result body in " + path);
            Result record;
            std::uint64_t count = 0;
            if (!(fields >> record.family >> record.sub >> record.descriptor_id >>
                  record.pc >> record.fault >> record.trap_class >> count))
                throw std::runtime_error("malformed RESULT line in " + path);
            remaining = count;
            out.push_back(std::move(record));
        } else if (tag == "WORD") {
            if (out.empty() || remaining == 0)
                throw std::runtime_error("stray WORD line in " + path);
            std::uint32_t address = 0;
            std::uint32_t data = 0;
            if (!(fields >> address >> data))
                throw std::runtime_error("malformed WORD line in " + path);
            out.back().words.emplace_back(address, data);
            --remaining;
        } else {
            throw std::runtime_error("unknown result tag '" + tag + "'");
        }
    }
    if (remaining != 0) throw std::runtime_error("truncated result body in " + path);
    return out;
}

// -- the device ------------------------------------------------------------
struct Model {
    VerilatedContext context;
    Vot_a3_shipped_prefix_top dut{&context};

    Model() {
        dut.clk = 0;
        dut.rst_n = 0;
        dut.start = 0;
        dut.host_we = 0;
        dut.host_sel = 0;
        dut.host_row = 0;
        dut.host_lane = 0;
        dut.host_wdata = 0;
        dut.cfg_program_base = 0;
        dut.cfg_instruction_count = 0;
        dut.cfg_entry_pc = 0;
        dut.cfg_desc_base = 0;
        dut.cfg_desc_count = 0;
        dut.cfg_max_retired_work = 0;
        dut.cfg_state_count = 0;
        dut.cfg_index_base = 0;
        dut.cfg_source_base = 0;
        dut.cfg_source_launch_stride = 0;
        dut.cfg_embedding_source_base = 0;
        dut.cfg_rms_input_base = 0;
        dut.cfg_rms_weight_base = 0;
        dut.cfg_transfer_index_base = 0;
        dut.cfg_transfer_source_base = 0;
        dut.cfg_matmul_input_base = 0;
        dut.cfg_matmul_weight_object_0 = UINT32_MAX;
        dut.cfg_matmul_weight_base_0 = 0;
        dut.cfg_matmul_weight_object_1 = UINT32_MAX;
        dut.cfg_matmul_weight_base_1 = 0;
        dut.cfg_matmul_weight_object_2 = UINT32_MAX;
        dut.cfg_matmul_weight_base_2 = 0;
        dut.cfg_head_input_object_0 = UINT32_MAX;
        dut.cfg_head_input_base_0 = 0;
        dut.cfg_head_input_object_1 = UINT32_MAX;
        dut.cfg_head_input_base_1 = 0;
        dut.cfg_head_weight_object_0 = UINT32_MAX;
        dut.cfg_head_weight_base_0 = 0;
        dut.cfg_head_weight_object_1 = UINT32_MAX;
        dut.cfg_head_weight_base_1 = 0;
        dut.cfg_rope_input_object_0 = UINT32_MAX;
        dut.cfg_rope_input_base_0 = 0;
        dut.cfg_rope_input_object_1 = UINT32_MAX;
        dut.cfg_rope_input_base_1 = 0;
        dut.cfg_rope_coefficient_object = UINT32_MAX;
        dut.cfg_rope_coefficient_base = 0;
        dut.cfg_output_base = 0;
        dut.cfg_extended_placement_valid = 0;
        dut.cfg_map_object_0 = UINT32_MAX;
        dut.cfg_map_base_0 = 0;
        dut.cfg_map_object_1 = UINT32_MAX;
        dut.cfg_map_base_1 = 0;
        dut.cfg_map_object_2 = UINT32_MAX;
        dut.cfg_map_base_2 = 0;
        dut.cfg_map_object_3 = UINT32_MAX;
        dut.cfg_map_base_3 = 0;
        dut.cfg_map_object_4 = UINT32_MAX;
        dut.cfg_map_base_4 = 0;
        dut.cfg_map_object_5 = UINT32_MAX;
        dut.cfg_map_base_5 = 0;
        dut.cfg_map_object_6 = UINT32_MAX;
        dut.cfg_map_base_6 = 0;
        dut.cfg_map_object_7 = UINT32_MAX;
        dut.cfg_map_base_7 = 0;
        dut.cfg_context_length = 0;
        dut.cfg_kv_plane_rows = 0;
        dut.cfg_generation_policy_id = UINT32_MAX;
        dut.cfg_request_max_new_tokens = 0;
        dut.cfg_generated_before = 0;
        dut.cfg_matmul_weight_window_base = 0;
        dut.cfg_predicate_object = UINT32_MAX;
        dut.cfg_predicate_base = 0;
        dut.inj_result_valid = 0;
        dut.inj_result_fault = 0;
        dut.inj_result_trap_class = 0;
        dut.inj_write_en = 0;
        dut.inj_write_addr = 0;
        dut.inj_write_data = 0;
        dut.result_read_addr = 0;
        dut.eval();
    }

    template <class Observer>
    void cycle(Observer&& before_rising) {
        dut.clk = 0;
        dut.eval();
        before_rising();
        dut.clk = 1;
        dut.eval();
        context.timeInc(1);
        dut.clk = 0;
        dut.eval();
        context.timeInc(1);
    }

    void reset() {
        for (int i = 0; i < 4; ++i) cycle([] {});
        dut.rst_n = 1;
        for (int i = 0; i < 2; ++i) cycle([] {});
    }

    void host_write(unsigned sel, std::uint32_t row, unsigned lane,
                    std::uint32_t data) {
        dut.host_sel = sel;
        dut.host_row = row;
        dut.host_lane = lane;
        dut.host_wdata = data;
        dut.host_we = 1;
        cycle([] {});
        dut.host_we = 0;
    }
};

constexpr std::size_t kProgramWords = 4096;
constexpr std::size_t kDescWords = 8192;
constexpr unsigned kSymbolsPerCase = 16;
constexpr std::size_t kCaseStride = 32;
constexpr std::size_t kMetaWords = 18;

}  // namespace

// ---------------------------------------------------------------------------
// The three DPI functions rtl/test/a3_shipped_prefix_top.sv imports.  This
// vehicle instantiates no engine and reads no weight, so the window is opened
// over a zero-byte image and a halfword request is a hard error rather than a
// value: an engine that reached for a weight here would be a defect, not a
// miss, and it must not be answered with a plausible number.
// ---------------------------------------------------------------------------
struct Geometry {
    std::uint32_t program_words = 0;
    std::uint32_t desc_words = 0;
    std::uint32_t index_words = 0;
    std::uint32_t source_words = 0;
    std::uint32_t result_words = 0;
    std::uint64_t matmul_weight_bytes = 0;
    std::uint32_t result_injection = 0;
    std::uint32_t exact_multicast = 0;
    bool declared = false;
};

static Geometry g_geometry;
static std::uint64_t g_weight_halfword_requests = 0;

// Signatures are Verilator's own, from Vot_a3_shipped_prefix_top__Dpi.h.
extern "C" void ot_a3_geometry_declare(unsigned int program_words, unsigned int desc_words,
                            unsigned int index_words, unsigned int source_words,
                            unsigned int result_words,
                            unsigned long long matmul_weight_bytes,
                            unsigned int result_injection,
                            unsigned int exact_multicast) {
    g_geometry.program_words = program_words;
    g_geometry.desc_words = desc_words;
    g_geometry.index_words = index_words;
    g_geometry.source_words = source_words;
    g_geometry.result_words = result_words;
    g_geometry.matmul_weight_bytes = matmul_weight_bytes;
    g_geometry.result_injection = result_injection;
    g_geometry.exact_multicast = exact_multicast;
    g_geometry.declared = true;
}

extern "C" unsigned long long ot_a3_weight_window_open(
    unsigned long long declared_bytes) {
    // The rung reads no weight.  Reporting the declared size is what the top
    // requires to elaborate; the halfword path below is what would catch an
    // engine actually reaching for one.
    return declared_bytes;
}

extern "C" unsigned int ot_a3_weight_window_halfword(
    unsigned long long halfword_index) {
    ++g_weight_halfword_requests;
    std::cerr << "FAIL: the G1e vehicle was asked for weight halfword "
              << halfword_index
              << "; under result injection no engine may read a weight\n";
    return 0;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    try {
        const auto meta = read_hex("g1e_meta.hex");
        const auto cases = read_hex("g1e_case.hex");
        if (meta.size() != kMetaWords)
            throw std::runtime_error("g1e_meta.hex has the wrong length");
        const std::size_t passes = meta[0];
        const std::size_t golden_issues = meta[1];
        const std::size_t golden_views = meta[2];
        const std::size_t golden_results = meta[3];
        if (meta[4] != kCaseStride)
            throw std::runtime_error("vector set declares a case stride this "
                                     "checker has not been qualified against");
        const bool probe_present = meta[16] != 0;
        const std::size_t probe_issues = meta[17];
        const std::size_t case_records = passes + (probe_present ? 1u : 0u);
        if (passes == 0 || cases.size() != case_records * kCaseStride)
            throw std::runtime_error("g1e_case.hex geometry mismatch");

        const auto image_program = read_rows("a3_program.hex", 8, kProgramWords);
        const auto image_desc = read_rows("a3_descriptor.hex", 48, kDescWords);
        const auto image_symbol = read_hex("a3_symbol.hex");
        const auto injected = read_results(vector_path("g1e_inject.txt"));
        const auto golden = read_trace(vector_path("g1e_golden_trace.txt"));
        const auto golden_queue =
            read_trace(vector_path("g1e_golden_trace_queue.txt"));
        const auto probe_results =
            probe_present ? read_results(vector_path("g1e_inject_probe.txt"))
                          : std::vector<Result>{};
        const std::uint64_t cycle_guard_limit =
            env_u64("OT_A3_CYCLE_GUARD", 4000000000ULL);

        Checker check;
        Model model;
        if (!g_geometry.declared)
            throw std::runtime_error("the top declared no geometry");
        // The rung's own precondition: this must be the injection build.
        check.equal("result injection elaborated", g_geometry.result_injection, 1);
        check.equal("injection enabled by the top", model.dut.injection_enabled, 1);
        check.equal("no exact multicast in this vehicle",
                    g_geometry.exact_multicast, 0);
        check.equal("golden result stream length", injected.size(),
                    golden_results);
        check.equal("golden trace issue count", golden.issues.size(),
                    golden_issues);
        check.equal("golden queue trace issue count", golden_queue.issues.size(),
                    golden_issues);

        model.reset();
        model.dut.eval();
        check.equal("host ready before load", model.dut.host_ready, 1);
        std::uint64_t host_writes = 0;
        for (std::size_t row = 0; row < kProgramWords; ++row)
            for (unsigned lane = 0; lane < 8; ++lane) {
                model.host_write(0, static_cast<std::uint32_t>(row), lane,
                                 image_program[row][lane]);
                ++host_writes;
            }
        for (std::size_t row = 0; row < kDescWords; ++row)
            for (unsigned lane = 0; lane < 48; ++lane) {
                model.host_write(1, static_cast<std::uint32_t>(row), lane,
                                 image_desc[row][lane]);
                ++host_writes;
            }
        model.cycle([] {});
        check.equal("no write refused during load", model.dut.host_write_refused,
                    0);

        Record rtl_trace;
        rtl_trace.issue_fields = golden.issue_fields;
        rtl_trace.view_fields = golden.view_fields;
        std::vector<View> pending_views;
        std::size_t injected_at = 0;
        std::size_t injected_word_at = 0;
        bool injected_serving = false;
        std::uint64_t injected_words_written = 0;
        std::uint64_t total_cycles = 0;
        std::uint64_t total_views_seen = 0;
        double sim_seconds = 0.0;
        std::uint64_t passes_completed = 0;

        for (std::size_t pass = 0; pass < passes; ++pass) {
            const std::uint32_t* record = &cases[pass * kCaseStride];
            model.dut.cfg_program_base = record[0];
            model.dut.cfg_instruction_count = record[1];
            model.dut.cfg_desc_base = record[2];
            model.dut.cfg_desc_count = record[3];
            for (unsigned symbol = 0; symbol < kSymbolsPerCase; ++symbol) {
                const std::size_t at = record[4] + symbol;
                model.host_write(2, symbol, 0,
                                 at < image_symbol.size() ? image_symbol[at] : 0);
                model.host_write(2, symbol, 1, 0);
                model.host_write(2, symbol, 2, (record[5] >> symbol) & 1U);
            }
            check.equal("no symbol write refused", model.dut.host_write_refused,
                        0);
            model.dut.cfg_entry_pc = record[6];
            model.dut.cfg_max_retired_work =
                (static_cast<std::uint64_t>(record[8]) << 32) | record[7];
            model.dut.cfg_state_count = record[9];

            const std::uint32_t expect_trap = record[10];
            const std::uint32_t expect_complete = record[11];
            const std::uint32_t expect_fetched = record[12];
            const std::uint32_t expect_retired = record[13];
            const std::uint32_t expect_predicated_off = record[14];
            const std::uint32_t expect_issued = record[15];
            const std::uint32_t expect_loops = record[16];
            const std::uint32_t expect_waits = record[17];
            const std::uint32_t expect_issues = record[18];
            const std::uint32_t expect_views = record[19];

            const std::size_t issues_before = rtl_trace.issues.size();
            std::uint64_t views_before = total_views_seen;
            std::uint64_t last_serial = 0;   // the serial restarts per pass
            bool first_issue = true;

            // Drive the injected completion, settle, then observe: the
            // handshake is seen in the cycle it happens, exactly as a real
            // engine's is.
            auto drive_injection = [&]() {
                model.dut.inj_write_en = 0;
                model.dut.inj_result_valid = 0;
                model.dut.inj_result_fault = 0;
                model.dut.inj_result_trap_class = 0;
                if (!model.dut.rst_n || !model.dut.inj_issue_valid) {
                    model.dut.eval();
                    return;
                }
                if (injected_at >= injected.size()) {
                    ++check.failures;
                    std::cerr << "FAIL: RTL issued past the golden result "
                                 "stream at issue "
                              << injected_at << "\n";
                    model.dut.eval();
                    return;
                }
                const auto& answer = injected[injected_at];
                if (!injected_serving) {
                    injected_serving = true;
                    injected_word_at = 0;
                    // The injected result must answer the issue the RTL
                    // actually made.  A mismatch is a divergence, not a fill.
                    check.equal("injected result opcode",
                                (static_cast<std::uint32_t>(
                                     model.dut.inj_issue_family)
                                 << 8) |
                                    model.dut.inj_issue_sub,
                                (answer.family << 8) | answer.sub);
                    check.equal("injected result descriptor",
                                model.dut.inj_issue_descriptor_id,
                                answer.descriptor_id);
                    check.equal("injected result pc", model.dut.inj_issue_index,
                                answer.pc);
                }
                if (injected_word_at < answer.words.size()) {
                    model.dut.inj_write_en = 1;
                    model.dut.inj_write_addr = answer.words[injected_word_at].first;
                    model.dut.inj_write_data =
                        answer.words[injected_word_at].second;
                    ++injected_word_at;
                    ++injected_words_written;
                } else {
                    model.dut.inj_result_valid = 1;
                    model.dut.inj_result_fault = answer.fault;
                    model.dut.inj_result_trap_class = answer.trap_class;
                    injected_serving = false;
                    ++injected_at;
                }
                model.dut.eval();
            };

            auto capture_trace = [&]() {
                if (!model.dut.rst_n) return;
                if (model.dut.trace_view_valid) {
                    View view;
                    view.slot = model.dut.trace_view_slot;
                    view.descriptor_id = model.dut.trace_view_descriptor_id;
                    view.extent = model.dut.trace_view_extent;
                    view.extent_axis = model.dut.trace_view_extent_axis;
                    view.element_offset = model.dut.trace_view_element_offset;
                    view.rank = model.dut.trace_view_rank;
                    pending_views.push_back(view);
                    ++total_views_seen;
                }
                if (!model.dut.trace_issue_valid) return;
                Issue issue;
                issue.family = model.dut.trace_issue_family;
                issue.sub = model.dut.trace_issue_sub;
                issue.descriptor_id = model.dut.trace_issue_descriptor_id;
                issue.pc = model.dut.trace_issue_index;
                issue.queue = model.dut.trace_issue_queue;
                issue.serial = model.dut.trace_issue_serial;
                issue.irs_slot = model.dut.trace_issue_slot;
                // Views belong to the issue they were resolved for and are
                // ordered by slot, so the record is a function of the data and
                // not of RTL timing.
                std::sort(pending_views.begin(), pending_views.end(),
                          [](const View& a, const View& b) {
                              return a.slot < b.slot;
                          });
                issue.views = pending_views;
                pending_views.clear();
                // Fields the golden cannot carry are still not left
                // unexamined: the serial must advance within the pass and the
                // schedule must be a real queue.
                check.equal("issue serial advances",
                            first_issue || issue.serial > last_serial, 1);
                first_issue = false;
                last_serial = issue.serial;
                check.equal("issue queue in range", issue.queue < 32, 1);
                rtl_trace.issues.push_back(std::move(issue));
            };

            auto observe = [&]() {
                drive_injection();
                capture_trace();
            };

            model.dut.start = 1;
            model.cycle(observe);
            model.dut.start = 0;
            std::uint64_t guard = 0;
            const auto started = std::chrono::steady_clock::now();
            while (!model.dut.done && guard < cycle_guard_limit) {
                model.cycle(observe);
                ++guard;
            }
            sim_seconds +=
                std::chrono::duration<double>(std::chrono::steady_clock::now() -
                                              started)
                    .count();
            total_cycles += guard;
            if (!model.dut.done) {
                ++check.failures;
                std::cerr << "FAIL: pass " << pass << " timed out after " << guard
                          << " cycles\n";
                break;
            }
            if (!pending_views.empty()) {
                ++check.failures;
                std::cerr << "FAIL: pass " << pass << " left "
                          << pending_views.size()
                          << " resolved views attached to no issue\n";
                pending_views.clear();
            }
            // The control plane's own accounting, against the golden model's.
            check.equal("pass complete", model.dut.complete, expect_complete);
            check.equal("pass trap class", model.dut.trap_class, expect_trap);
            check.equal("pass instructions fetched", model.dut.count_fetched,
                        expect_fetched);
            check.equal("pass instructions retired", model.dut.count_retired,
                        expect_retired);
            check.equal("pass predicated off", model.dut.count_predicated_off,
                        expect_predicated_off);
            check.equal("pass instructions issued", model.dut.count_issued,
                        expect_issued);
            check.equal("pass loop iterations", model.dut.count_loop_iterations,
                        expect_loops);
            check.equal("pass wait events", model.dut.count_wait_events,
                        expect_waits);
            check.equal("pass views resolved", model.dut.count_views_resolved,
                        expect_views);
            check.equal("pass issues traced",
                        rtl_trace.issues.size() - issues_before, expect_issues);
            check.equal("pass views traced", total_views_seen - views_before,
                        expect_views);
            // No engine was issued to.  This is the evidence that the control
            // plane, not the datapath, is what ran.
            check.equal("no engine launch under injection",
                        model.dut.real_launch_count, 0);
            check.equal("no engine work under injection",
                        model.dut.engine_work_count, 0);
            check.equal("no multicast launch", model.dut.multicast_launch_count,
                        0);
            check.equal("injected completions this pass",
                        model.dut.inj_completion_count, expect_issues);
            check.equal("no predicate refused", model.dut.predicate_read_refused_count,
                        0);
            check.equal("no event signal error", model.dut.event_signal_error, 0);
            check.equal("no state apply overflow", model.dut.state_apply_overflow,
                        0);
            if (model.dut.complete) ++passes_completed;
            std::cout << "PASS-RECORD index=" << pass
                      << " entrypoint=" << record[24]
                      << " generation=" << record[26]
                      << " context=" << record[27]
                      << " issues=" << (rtl_trace.issues.size() - issues_before)
                      << " views=" << (total_views_seen - views_before)
                      << " fetched=" << model.dut.count_fetched
                      << " retired=" << model.dut.count_retired
                      << " loops=" << model.dut.count_loop_iterations
                      << " waits=" << model.dut.count_wait_events
                      << " cycles=" << guard << "\n";
        }

        // -- the post-EOS probe ------------------------------------------
        // The reference model refuses a transaction on a session that has
        // reached EOS.  Whether the RTL control plane refuses one is a
        // question about the RTL, so it is asked rather than reasoned about:
        // the same configuration is driven once more with its own result
        // stream, and what the design does is reported.  Its issues are not
        // added to the compared trace.
        bool probe_ran = false;
        bool probe_admitted = false;
        std::uint32_t probe_trap_class = 0;
        std::uint64_t probe_issue_count = 0;
        std::uint64_t probe_cycles = 0;
        if (probe_present) {
            const std::uint32_t* record = &cases[passes * kCaseStride];
            model.dut.cfg_program_base = record[0];
            model.dut.cfg_instruction_count = record[1];
            model.dut.cfg_desc_base = record[2];
            model.dut.cfg_desc_count = record[3];
            for (unsigned symbol = 0; symbol < kSymbolsPerCase; ++symbol) {
                const std::size_t at = record[4] + symbol;
                model.host_write(2, symbol, 0,
                                 at < image_symbol.size() ? image_symbol[at] : 0);
                model.host_write(2, symbol, 1, 0);
                model.host_write(2, symbol, 2, (record[5] >> symbol) & 1U);
            }
            model.dut.cfg_entry_pc = record[6];
            model.dut.cfg_max_retired_work =
                (static_cast<std::uint64_t>(record[8]) << 32) | record[7];
            model.dut.cfg_state_count = record[9];
            std::size_t probe_at = 0;
            bool probe_serving = false;
            auto probe_observe = [&]() {
                model.dut.inj_write_en = 0;
                model.dut.inj_result_valid = 0;
                model.dut.inj_result_fault = 0;
                model.dut.inj_result_trap_class = 0;
                if (!model.dut.rst_n || !model.dut.inj_issue_valid) {
                    model.dut.eval();
                    return;
                }
                if (probe_at >= probe_results.size()) {
                    model.dut.eval();
                    return;   // the probe refuses to feed past its stream
                }
                if (!probe_serving) probe_serving = true;
                model.dut.inj_result_valid = 1;
                probe_serving = false;
                ++probe_at;
                model.dut.eval();
            };
            model.dut.start = 1;
            model.cycle(probe_observe);
            model.dut.start = 0;
            std::uint64_t guard = 0;
            while (!model.dut.done && guard < cycle_guard_limit) {
                model.cycle(probe_observe);
                ++guard;
            }
            probe_ran = true;
            probe_cycles = guard;
            probe_issue_count = probe_at;
            probe_admitted = model.dut.done && model.dut.complete;
            probe_trap_class = model.dut.trap_class;
            total_cycles += guard;
            check.equal("post-EOS probe reached a definite outcome",
                        model.dut.done ? 1 : 0, 1);
            check.equal("post-EOS probe issue count", probe_at, probe_issues);
        }
        // The EOS observation, measured rather than inferred.  OFFICIAL_EOS
        // is raised by rtl/abi3/ot_a3_selection_token_append.sv, an ENGINE.
        // Under result injection the bridge's issue_valid is tied low, so
        // that engine is never issued to and these outputs must still read
        // their reset values: that is what says the EOS in this run is the
        // model's, not the RTL's, and it is checked instead of asserted.
        std::cout << "EOS selected_token=" << model.dut.selected_token
                  << " selected_tie_multiplicity="
                  << model.dut.selected_tie_multiplicity
                  << " selected_eos_reason="
                  << static_cast<unsigned>(model.dut.selected_eos_reason)
                  << " engine_launches=" << model.dut.real_launch_count << "\n";
        check.equal("no EOS reason published by any engine",
                    model.dut.selected_eos_reason, 0);
        std::cout << "POSTEOS ran=" << (probe_ran ? 1 : 0)
                  << " admitted=" << (probe_admitted ? 1 : 0)
                  << " trapped=" << (model.dut.trapped ? 1 : 0)
                  << " trap_class=" << probe_trap_class
                  << " issues=" << probe_issue_count
                  << " cycles=" << probe_cycles << "\n";

        check.equal("every golden result consumed", injected_at, injected.size());
        check.equal("injected words written", injected_words_written,
                    [&] {
                        std::uint64_t total = 0;
                        for (const auto& r : injected) total += r.words.size();
                        return total;
                    }());
        check.equal("no weight halfword requested", g_weight_halfword_requests, 0);
        check.equal("total issues traced", rtl_trace.issues.size(),
                    golden_issues);
        check.equal("total views traced", total_views_seen, golden_views);
        check.equal("passes completed", passes_completed, passes);

        const auto comparison = compare(rtl_trace, golden);
        const auto comparison_queue = compare(rtl_trace, golden_queue);
        check.equal("issue trace equals golden", comparison.equal ? 1 : 0, 1);
        if (!comparison.equal)
            std::cerr << "FAIL: trace diverges at element "
                      << comparison.divergence_index << " (" << comparison.label
                      << ") got=" << comparison.got << " want=" << comparison.want
                      << "\n";
        if (!comparison_queue.equal)
            std::cerr << "NOTE: the extended (queue) comparison diverges at "
                      << comparison_queue.divergence_index << " ("
                      << comparison_queue.label
                      << ") got=" << comparison_queue.got
                      << " want=" << comparison_queue.want << "\n";

        if (const char* out = env_or_null("OT_A3_TRACE_OUT")) {
            std::ofstream stream(out);
            stream << "FIELDS ISSUE family sub descriptor_id pc queue serial "
                      "irs_slot\nFIELDS VIEW slot descriptor_id extent "
                      "extent_axis element_offset rank\n";
            for (const auto& issue : rtl_trace.issues) {
                stream << "ISSUE " << issue.family << ' ' << issue.sub << ' '
                       << issue.descriptor_id << ' ' << issue.pc << ' '
                       << issue.queue << ' ' << issue.serial << ' '
                       << issue.irs_slot << '\n';
                for (const auto& view : issue.views)
                    stream << "VIEW " << view.slot << ' ' << view.descriptor_id
                           << ' ' << view.extent << ' ' << view.extent_axis << ' '
                           << view.element_offset << ' ' << view.rank << '\n';
            }
        }

        std::cout << "GEOMETRY program_words=" << g_geometry.program_words
                  << " desc_words=" << g_geometry.desc_words
                  << " index_words=" << g_geometry.index_words
                  << " source_words=" << g_geometry.source_words
                  << " result_words=" << g_geometry.result_words
                  << " matmul_weight_bytes=" << g_geometry.matmul_weight_bytes
                  << " result_injection=" << g_geometry.result_injection << "\n";
        std::cout << "TRACE compared=" << comparison.compared
                  << " equal=" << (comparison.equal ? 1 : 0)
                  << " divergence_index=" << comparison.divergence_index
                  << " queue_compared=" << comparison_queue.compared
                  << " queue_equal=" << (comparison_queue.equal ? 1 : 0)
                  << " queue_divergence_index="
                  << comparison_queue.divergence_index << "\n";
        std::cout << "INJECTION results=" << injected_at
                  << " words=" << injected_words_written
                  << " engine_launches=" << model.dut.real_launch_count
                  << " engine_work=" << model.dut.engine_work_count
                  << " weight_halfwords=" << g_weight_halfword_requests << "\n";
        std::cout << "COST passes=" << passes_completed
                  << " cycles=" << total_cycles << " seconds=" << std::fixed
                  << std::setprecision(3) << sim_seconds
                  << " host_writes=" << host_writes << "\n";

        if (check.failures != 0) {
            std::cerr << "FAILURES: " << check.failures
                      << " checks=" << check.checks << "\n";
            return 1;
        }
        std::cout << "PASS: ABI3 G1e control end to end passes="
                  << passes_completed << " issues=" << rtl_trace.issues.size()
                  << " views=" << total_views_seen
                  << " elements=" << comparison.compared
                  << " injected=" << injected_at << " checks=" << check.checks
                  << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "ERROR: " << error.what() << "\n";
        return 2;
    }
}
