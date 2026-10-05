// Bounded two-state integration check. No host-float arithmetic oracle.
#include "Vgate.h"
#include "verilated.h"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct Pair { uint32_t a, b; int ae, me; };
struct Expected { bool v; int ae, me; };

class Gate {
public:
    Vgate dut;
    uint64_t cycles = 0, samples = 0, valid_samples = 0, bubbles = 0;
    uint64_t reset_edges = 0, async_resets = 0, add_errors[3] = {}, mul_errors[3] = {};
    uint64_t directed_cycles = 0, random_cycles = 0;
    Expected h0 = {false, -1, -1}, h1 = {false, -1, -1};
    std::string phase = "initial", mismatch;

    std::string state(const std::string& property) {
        std::ostringstream s;
        s << "{\"property\":\"" << property << "\",\"phase\":\"" << phase
          << "\",\"cycle\":" << cycles << ",\"rst_n\":" << unsigned(dut.rst_n)
          << ",\"valid_in\":" << unsigned(dut.valid_in) << ",\"a\":" << dut.a << ",\"b\":" << dut.b
          << ",\"reference_add\":[" << dut.ref_add_y << ',' << unsigned(dut.ref_add_err) << ',' << unsigned(dut.ref_add_v)
          << "],\"candidate_add\":[" << dut.sim_add_y << ',' << unsigned(dut.sim_add_err) << ',' << unsigned(dut.sim_add_v)
          << "],\"reference_mul\":[" << dut.ref_mul_y << ',' << unsigned(dut.ref_mul_err) << ',' << unsigned(dut.ref_mul_v)
          << "],\"candidate_mul\":[" << dut.sim_mul_y << ',' << unsigned(dut.sim_mul_err) << ',' << unsigned(dut.sim_mul_v)
          << "],\"reference_wrapper\":[" << dut.ref_qadd_y << ',' << unsigned(dut.ref_qadd_fault)
          << ',' << dut.ref_qmul_y << ',' << unsigned(dut.ref_qmul_fault)
          << "],\"candidate_wrapper\":[" << dut.sim_qadd_y << ',' << unsigned(dut.sim_qadd_fault)
          << ',' << dut.sim_qmul_y << ',' << unsigned(dut.sim_qmul_fault) << "]}";
        return s.str();
    }

    void require(bool condition, const char* property) {
        if (!condition) { mismatch = state(property); throw 1; }
    }

    void check(Expected expected, bool clock_sample) {
        ++samples;
        // UNCONDITIONAL tuples: bubbles, reset-held edges, and reset events too.
        require(dut.ref_add_y == dut.sim_add_y && dut.ref_add_err == dut.sim_add_err
                && dut.ref_add_v == dut.sim_add_v, "add_tuple_every_sample");
        require(dut.ref_mul_y == dut.sim_mul_y && dut.ref_mul_err == dut.sim_mul_err
                && dut.ref_mul_v == dut.sim_mul_v, "mul_tuple_every_sample");
        require(dut.ref_qadd_y == dut.sim_qadd_y && dut.ref_qadd_fault == dut.sim_qadd_fault,
                "qadd_tuple_every_sample");
        require(dut.ref_qmul_y == dut.sim_qmul_y && dut.ref_qmul_fault == dut.sim_qmul_fault,
                "qmul_tuple_every_sample");
        require(dut.ref_add_v == expected.v && dut.ref_mul_v == expected.v
                && dut.sim_add_v == expected.v && dut.sim_mul_v == expected.v, "independent_LAT3_valid");
        require(dut.ref_qadd_y == dut.ref_add_y && dut.sim_qadd_y == dut.sim_add_y
                && dut.ref_qmul_y == dut.ref_mul_y && dut.sim_qmul_y == dut.sim_mul_y, "wrapper_payload");
        require(dut.ref_qadd_fault == (dut.ref_add_v && dut.ref_add_err != 0)
                && dut.sim_qadd_fault == (dut.sim_add_v && dut.sim_add_err != 0)
                && dut.ref_qmul_fault == (dut.ref_mul_v && dut.ref_mul_err != 0)
                && dut.sim_qmul_fault == (dut.sim_mul_v && dut.sim_mul_err != 0), "wrapper_fault_cycle");
        if (!dut.rst_n) {
            require(dut.ref_add_y == 0 && dut.sim_add_y == 0 && dut.ref_add_err == 0 && dut.sim_add_err == 0
                    && dut.ref_mul_y == 0 && dut.sim_mul_y == 0 && dut.ref_mul_err == 0 && dut.sim_mul_err == 0,
                    "asynchronous_reset_payload_error");
        }
        if (expected.v) {
            if (expected.ae >= 0) require(dut.ref_add_err == expected.ae && dut.sim_add_err == expected.ae, "directed_add_error_code");
            if (expected.me >= 0) require(dut.ref_mul_err == expected.me && dut.sim_mul_err == expected.me, "directed_mul_error_code");
            require(dut.ref_add_err <= 2 && dut.ref_mul_err <= 2, "valid_error_aperture");
            if (dut.ref_add_err) require(dut.ref_add_y == 0 && dut.sim_add_y == 0, "add_error_zero_payload");
            if (dut.ref_mul_err) require(dut.ref_mul_y == 0 && dut.sim_mul_y == 0, "mul_error_zero_payload");
            if (clock_sample) {
                ++valid_samples; ++add_errors[dut.ref_add_err]; ++mul_errors[dut.ref_mul_err];
            }
        } else if (clock_sample) ++bubbles;
    }

    void assert_reset(const std::string& label) {
        phase = label;
        dut.clk = 0; dut.rst_n = 1; dut.eval();
        dut.rst_n = 0; dut.eval();  // no rising clock: asynchronous assertion
        h0 = h1 = {false, -1, -1};
        ++async_resets;
        check({false, -1, -1}, false);
    }

    void release() { dut.rst_n = 1; dut.eval(); }

    void tick(Pair p, bool valid, bool random = false) {
        dut.clk = 0; dut.a = p.a; dut.b = p.b; dut.valid_in = valid; dut.eval();
        Expected expected = dut.rst_n ? h1 : Expected{false, -1, -1};
        if (!dut.rst_n) { h0 = h1 = {false, -1, -1}; ++reset_edges; }
        else { h1 = h0; h0 = {valid, p.ae, p.me}; }
        dut.clk = 1; dut.eval(); ++cycles;
        if (random) ++random_cycles; else ++directed_cycles;
        check(expected, true);
        dut.clk = 0; dut.eval();
    }

    void drain() { for (int k = 0; k < 6; ++k) tick({0x7fc00001u, 0x7f7fffffu, 1, 1}, false); }

    void print(uint32_t seed) {
        std::cout << "RESULT {\"status\":\"" << (mismatch.empty() ? "PASS" : "FAIL")
          << "\",\"seed\":" << seed << ",\"clock_cycles\":" << cycles << ",\"checked_samples\":" << samples
          << ",\"valid_output_cycles\":" << valid_samples << ",\"bubble_or_reset_cycles\":" << bubbles
          << ",\"reset_held_clock_edges\":" << reset_edges << ",\"asynchronous_reset_assertions\":" << async_resets
          << ",\"directed_clock_cycles\":" << directed_cycles << ",\"random_clock_cycles\":" << random_cycles
          << ",\"add_err_0_1_2\":[" << add_errors[0] << ',' << add_errors[1] << ',' << add_errors[2]
          << "],\"mul_err_0_1_2\":[" << mul_errors[0] << ',' << mul_errors[1] << ',' << mul_errors[2]
          << "],\"first_mismatch\":" << (mismatch.empty() ? "null" : mismatch) << "}\n";
    }
};

static uint32_t xs(uint32_t& s) { s ^= s << 13; s ^= s >> 17; s ^= s << 5; return s; }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    uint32_t seed = argc > 1 ? uint32_t(std::strtoull(argv[1], nullptr, 10)) : 0x12345678u;
    unsigned n = argc > 2 ? unsigned(std::strtoul(argv[2], nullptr, 10)) : 8192;
    if (seed == 0 || n < 1 || n > 32768) return 2;
    Gate g;
    const Pair normal = {0x3f800000u, 0x40000000u, 0, 0};
    const Pair error = {0x7fc00001u, 0x3f800000u, 1, 1};
    const Pair overflow = {0x7f7fffffu, 0x40000000u, 0, 2};
    const std::vector<Pair> directed = {
        normal, {0x00000000u, 0x80000000u, 0, 0}, {0x80000000u, 0x3f800000u, 0, 0},
        {0x00000001u, 0x00000001u, 0, 0}, {0x007fffffu, 0x00000001u, 0, 0},
        {0x00800000u, 0x3f000000u, 0, 0}, {0x00800001u, 0x3f7fffffu, 0, 0},
        {0x3f800000u, 0xbf800000u, 0, 0}, {0x3f800001u, 0xbf800000u, 0, 0},
        {0x3f800000u, 0xbf7fffffu, 0, 0}, {0x3f800000u, 0x33800000u, 0, 0},
        {0x3f800001u, 0x33800000u, 0, 0}, {0x3fffffffu, 0x33800000u, 0, 0},
        {0x3fffffffu, 0x3f800001u, 0, 0}, {0x7f7fffffu, 0x7f7fffffu, 2, 2}, overflow,
        {0xff7fffffu, 0xff7fffffu, 2, 2}, {0x7f800000u, 0x00000000u, 1, 1},
        {0xff800000u, 0x3f800000u, 1, 1}, {0x3f800000u, 0x7fc00001u, 1, 1},
        {0x7f800001u, 0x3f800000u, 1, 1}, {0x00000000u, 0x7fc00001u, 1, 1},
        {0x00800000u, 0x80800000u, 0, 0}, {0x00000001u, 0x7f7fffffu, 0, 0}
    };
    try {
        g.assert_reset("startup_async_reset");
        for (int k = 0; k < 4; ++k) g.tick(error, true);
        g.release(); g.phase = "directed_II1";
        for (const auto& p : directed) g.tick(p, true);
        g.drain();
        g.phase = "directed_bubbles";
        for (size_t k = 0; k < directed.size(); ++k) {
            g.tick(directed[k], true); g.tick(error, false); g.tick(overflow, false);
        }
        g.drain();
        for (int stage = 0; stage < 3; ++stage) {
            g.assert_reset("reset_prepare_stage_" + std::to_string(stage));
            g.tick(normal, false); g.release();
            g.phase = "fill_stage_" + std::to_string(stage);
            g.tick(error, true);
            for (int k = 0; k < stage; ++k) g.tick(overflow, true);
            g.assert_reset("inflight_async_stage_" + std::to_string(stage));
            // Short reset pulses and reset-held edges are both exercised.
            if (stage != 1) for (int k = 0; k < 3; ++k) g.tick(directed[k+3], true);
            g.release(); g.phase = "immediate_refill_stage_" + std::to_string(stage);
            g.tick(normal, true); g.tick(overflow, true); g.tick(error, true); g.drain();
        }
        g.assert_reset("random_prepare"); g.tick(normal, false); g.release();
        uint32_t rng = seed;
        for (unsigned k = 0; k < n; ++k) {
            g.phase = "seeded_random";
            if (k % 257 == 0) { g.assert_reset("random_async_reset"); g.release(); }
            if (k % 509 == 17) {
                g.assert_reset("random_held_reset");
                g.tick({xs(rng), xs(rng), -1, -1}, true, true);
                g.tick({xs(rng), xs(rng), -1, -1}, false, true); g.release();
            }
            uint32_t av = xs(rng), bv = xs(rng), control = xs(rng);
            if ((control & 7) == 0) { av = directed[control % directed.size()].a; bv = directed[(control >> 8) % directed.size()].b; }
            if ((control & 15) == 1) bv = av ^ 0x80000000u;
            if ((control & 15) == 2) bv = (av ^ 0x80000000u) + (control >> 24);
            g.tick({av, bv, -1, -1}, (control & 3) != 0, true);
        }
        g.phase = "final_drain"; g.drain();
        g.require(g.add_errors[1] && g.add_errors[2] && g.mul_errors[1] && g.mul_errors[2], "exception_coverage");
        g.require(g.valid_samples + g.bubbles == g.cycles, "every_clock_accounted");
        g.require(g.samples == g.cycles + g.async_resets, "every_reset_event_accounted");
    } catch (int) { g.print(seed); return 1; }
    g.print(seed); return 0;
}
