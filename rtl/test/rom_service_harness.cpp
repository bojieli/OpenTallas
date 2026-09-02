// ---------------------------------------------------------------------------
// Verilator checker for the ROM read service.
//
// This is the second, independent checker of the same campaign.  It compiles
// the same RTL through a different elaboration and simulation engine, parses
// the generated images itself, and applies its own back-pressure pattern to the
// operand bus and the sense port.  It shares no checking code with
// rtl/test/tb_rom_service.sv; the two agree only on the images, which come from
// real ABI 3.0 ROM deployments and from the ROM reads the deployed program
// actually issues.
//
// Per request it requires exact agreement on completion status, fault class,
// beat count, byte count, row-activation count, the first and last beat record,
// the beat-stream digest and the operand-data digest.  Across the run it
// requires the service's counters to reconcile with the sum of the per-request
// results, the array's own activation and sense counts to match, and the window
// model never to miss.
// ---------------------------------------------------------------------------
#include "Vrom_service_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

constexpr unsigned kExpectStride = 32;

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

uint64_t pair64(const std::vector<uint32_t>& words, size_t base) {
    return static_cast<uint64_t>(words[base]) |
           (static_cast<uint64_t>(words[base + 1]) << 32);
}

class Model {
  public:
    Vrom_service_top dut;

    void step() {
        dut.clk = 1;
        dut.eval();
        dut.clk = 0;
        dut.eval();
    }

    void reset() {
        dut.rst_n = 0;
        dut.cfg_start = 0;
        dut.case_start = 0;
        dut.case_index = 0;
        dut.out_ready_in = 1;
        dut.sense_ready_in = 1;
        for (unsigned cycle = 0; cycle < 6; ++cycle) step();
        dut.rst_n = 1;
        for (unsigned cycle = 0; cycle < 2; ++cycle) step();
    }
};

struct Check {
    uint64_t count = 0;

    void equal(const char* label, long index, uint64_t actual, uint64_t want) {
        ++count;
        if (actual != want) {
            char buffer[256];
            std::snprintf(buffer, sizeof(buffer),
                          "request %ld %s: %llu expected %llu", index, label,
                          static_cast<unsigned long long>(actual),
                          static_cast<unsigned long long>(want));
            fail(buffer);
        }
    }

    template <typename Wide>
    void equal_wide(const char* label, long index, const Wide& actual,
                    const std::vector<uint32_t>& words, size_t base) {
        // Match the independently written SV checker's accounting unit: one
        // semantic 256-bit comparison is one check, even though this harness
        // performs it lane by lane to report the exact failing word.
        ++count;
        for (unsigned lane = 0; lane < 8; ++lane) {
            if (actual[lane] != words[base + lane]) {
                char buffer[256];
                std::snprintf(buffer, sizeof(buffer),
                              "request %ld %s word %u: %08x expected %08x",
                              index, label, lane, actual[lane],
                              words[base + lane]);
                fail(buffer);
            }
        }
    }
};

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const std::vector<uint32_t> expect = load_words("rom_expect.hex");
    const std::vector<uint32_t> meta = load_words("rom_meta.hex");
    if (meta.size() < 18) fail("rom_meta.hex is too short");

    Model model;
    Check check;
    model.reset();

    model.dut.cfg_start = 1;
    unsigned guard = 0;
    while (!model.dut.cfg_done) {
        model.step();
        if (++guard > 20000000u) fail("configuration never completed");
    }
    model.step();
    model.dut.cfg_start = 0;
    for (unsigned cycle = 0; cycle < 4; ++cycle) model.step();

    const uint32_t requests = meta[4];
    if (requests == 0) fail("the vector set carries no requests");
    if (model.dut.meta_request_count != requests)
        fail("the top and the harness disagree about the request count");

    // Refuse a vector set that outgrew a table depth rather than let it alias
    // onto a legal wrong entry.
    const struct {
        const char* name;
        uint32_t need;
        uint32_t have;
    } capacities[] = {
        {"objects", model.dut.req_objects, model.dut.cap_objects},
        {"shards", model.dut.req_shards, model.dut.cap_shards},
        {"regions", model.dut.req_regions, model.dut.cap_regions},
        {"quarantine entries", model.dut.req_quarantine_entries, model.dut.cap_quarantine_entries},
        {"repair_entries", model.dut.req_repair_entries,
         model.dut.cap_repair_entries},
        {"requests", model.dut.req_requests, model.dut.cap_requests},
        {"window_entries", model.dut.req_window_entries,
         model.dut.cap_window_entries},
        {"masks", model.dut.req_masks, model.dut.cap_masks},
    };
    for (const auto& capacity : capacities) {
        ++check.count;
        if (capacity.need > capacity.have) {
            char buffer[192];
            std::snprintf(buffer, sizeof(buffer),
                          "vector set needs %u %s but the top holds %u",
                          capacity.need, capacity.name, capacity.have);
            fail(buffer);
        }
    }
    // Every real plan write must be admitted.  Four subsequent probes make
    // the independent slot, descriptor, descriptor/plan-binding and plan-
    // structure guards sticky; reproducing the marker then proves none of the
    // rejected writes changed a populated entry.
    check.equal("cfg_error_after_plan", -1, model.dut.cfg_error_plan, 0);
    check.equal("cfg_flags_after_plan", -1,
                model.dut.cfg_error_plan_flags, 0);
    check.equal("cfg_error_after_probe", -1, model.dut.cfg_error, 1);
    check.equal("cfg_flags_after_probes", -1,
                model.dut.cfg_error_flags, 0xf);

    uint64_t sum_beats = 0, sum_bytes = 0, sum_acts = 0;
    uint64_t sum_masked = 0, sum_faults = 0;

    for (uint32_t index = 0; index < requests; ++index) {
        const size_t base = static_cast<size_t>(index) * kExpectStride;
        const uint64_t want_beats = pair64(expect, base + 2);
        // A deliberately different stall pattern from the Icarus testbench:
        // the operand bus accepts on three cycles out of four and the sense
        // port on four out of five, both offset by the request index.  The very
        // long requests run at full rate for the same reason the other checker
        // gives.
        const bool stall = want_beats <= 65536;
        uint64_t tick = index;
        model.dut.out_ready_in = stall ? ((index % 4) != 2) : 1;
        model.dut.sense_ready_in = stall ? ((index % 5) != 3) : 1;
        model.dut.case_index = index;
        model.dut.case_start = 1;
        model.step();
        guard = 0;
        while (!model.dut.case_busy) {
            model.step();
            if (++guard > 1000u) fail("the top never accepted the request");
        }
        model.dut.case_start = 0;
        uint64_t cycles = 0;
        while (!model.dut.case_done) {
            model.step();
            ++tick;
            if (stall) {
                model.dut.out_ready_in = ((tick % 4) != 2);
                model.dut.sense_ready_in = ((tick % 5) != 3);
            }
            if (++cycles > 4000000000ull) fail("a request never completed");
        }
        model.dut.out_ready_in = 1;
        model.dut.sense_ready_in = 1;

        check.equal("status", index, model.dut.cmp_status, expect[base + 0]);
        check.equal("fault", index, model.dut.cmp_fault, expect[base + 1]);
        check.equal("beats", index, model.dut.cmp_beats, want_beats);
        check.equal("bytes", index, model.dut.cmp_bytes, pair64(expect, base + 4));
        check.equal("activations", index, model.dut.cmp_activations,
                    pair64(expect, base + 6));
        check.equal("beat_digest", index, model.dut.cmp_beat_digest,
                    pair64(expect, base + 8));
        check.equal("data_digest", index, model.dut.cmp_data_digest,
                    pair64(expect, base + 10));
        check.equal_wide("first_beat", index, model.dut.cmp_first_beat, expect,
                         base + 12);
        check.equal_wide("last_beat", index, model.dut.cmp_last_beat, expect,
                         base + 20);
        check.equal("tag", index, model.dut.cmp_tag, expect[base + 28]);

        sum_beats += model.dut.cmp_beats;
        sum_bytes += model.dut.cmp_bytes;
        sum_acts += model.dut.cmp_activations;
        if (model.dut.cmp_status == 1) ++sum_masked;
        if (model.dut.cmp_status == 2) ++sum_faults;
    }

    check.equal("count_requests", -1, model.dut.count_requests, requests);
    check.equal("count_beats", -1, model.dut.count_beats, sum_beats);
    check.equal("count_bytes", -1, model.dut.count_bytes, sum_bytes);
    check.equal("count_activations", -1, model.dut.count_activations, sum_acts);
    check.equal("count_masked", -1, model.dut.count_masked, sum_masked);
    check.equal("count_faults", -1, model.dut.count_faults, sum_faults);
    check.equal("array_activations", -1, model.dut.array_act_count, sum_acts);
    check.equal("array_senses", -1, model.dut.array_sense_count, sum_beats);
    check.equal("window_miss", -1, model.dut.window_miss, 0);
    // What actually crossed the operand bus, counted by this harness's own
    // observer inside the top rather than by the service.
    check.equal("bus_bytes", -1, model.dut.bus_bytes, sum_bytes);
    check.equal("bus_beats", -1, model.dut.bus_beats, sum_beats);
    check.equal("bus_last_beats", -1, model.dut.bus_last_beats,
                requests - sum_masked - sum_faults);
    check.equal("total_beats", -1, sum_beats, pair64(meta, 8));
    check.equal("total_bytes", -1, sum_bytes, pair64(meta, 10));
    check.equal("total_activations", -1, sum_acts, pair64(meta, 12));
    check.equal("total_masked", -1, sum_masked, pair64(meta, 14));
    check.equal("total_faults", -1, sum_faults, pair64(meta, 16));

    std::printf(
        "ROM-SERVICE-OK requests=%u beats=%llu bytes=%llu activations=%llu "
        "masked=%llu faults=%llu marker=%08x%08x\n",
        requests, static_cast<unsigned long long>(sum_beats),
        static_cast<unsigned long long>(sum_bytes),
        static_cast<unsigned long long>(sum_acts),
        static_cast<unsigned long long>(sum_masked),
        static_cast<unsigned long long>(sum_faults), meta[7], meta[6]);
    std::printf("checks=%llu\n", static_cast<unsigned long long>(check.count));
    return 0;
}
