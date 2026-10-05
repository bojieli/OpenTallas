#include "Vot_verilator_unit_top.h"
#include "verilated.h"
#include "verilated_cov.h"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <limits>
#include <string>

// Required by this Verilator release when SystemVerilog source locations use
// simulation time in diagnostics.
double sc_time_stamp() { return 0.0; }

namespace {

constexpr uint32_t kSeed = 0x4f54564cU;
uint32_t rng_state = kSeed;
uint64_t cycles = 0;
uint64_t checks = 0;

uint32_t xorshift32() {
    uint32_t x = rng_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    rng_state = x;
    return x;
}

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "FAIL cycle=" << cycles << " check=" << checks << " " << message << "\n";
    std::exit(1);
}

void require(bool condition, const std::string& message) {
    ++checks;
    if (!condition) fail(message);
}

void eval_low(Vot_verilator_unit_top& dut) {
    dut.clk = 0;
    dut.eval();
}

void rise(Vot_verilator_unit_top& dut) {
    dut.clk = 1;
    dut.eval();
    ++cycles;
}

void fall(Vot_verilator_unit_top& dut) {
    dut.clk = 0;
    dut.eval();
}

int8_t byte_at(uint32_t value, unsigned index) {
    return static_cast<int8_t>((value >> (index * 8U)) & 0xffU);
}

struct DotExpected {
    bool valid;
    bool poison;
    int16_t result;
    uint8_t status;
};

DotExpected dot_reference(bool valid, bool poison, uint8_t enable,
                          uint16_t activations, uint32_t weights) {
    int64_t sum = 0;
    for (unsigned expert = 0; expert < 2; ++expert) {
        if (((enable >> expert) & 1U) == 0U) continue;
        for (unsigned lane = 0; lane < 2; ++lane) {
            const int64_t activation = byte_at(activations, lane);
            const int64_t weight = byte_at(weights, expert * 2U + lane);
            sum += activation * weight;
        }
    }
    bool saturated = false;
    if (sum > std::numeric_limits<int16_t>::max()) {
        sum = std::numeric_limits<int16_t>::max();
        saturated = true;
    } else if (sum < std::numeric_limits<int16_t>::min()) {
        sum = std::numeric_limits<int16_t>::min();
        saturated = true;
    }
    DotExpected expected{};
    expected.valid = valid;
    expected.poison = poison;
    expected.result = valid ? (poison ? 0 : static_cast<int16_t>(sum)) : 0;
    expected.status = valid ? static_cast<uint8_t>((poison ? 8U : 0U) |
                                                    (saturated ? 4U : 0U))
                            : 0U;
    return expected;
}

void clear_inputs(Vot_verilator_unit_top& dut) {
    dut.dot_valid = 0;
    dut.dot_poison = 0;
    dut.dot_enable = 0;
    dut.dot_activations = 0;
    dut.dot_weights = 0;
    dut.skid_in_valid = 0;
    dut.skid_in_data = 0;
    dut.skid_out_ready = 0;
    dut.credit_reserve_valid = 0;
    dut.credit_reserve_mask = 0;
    dut.credit_release_valid = 0;
    dut.credit_release_mask = 0;
}

void reset(Vot_verilator_unit_top& dut) {
    clear_inputs(dut);
    dut.rst_n = 0;
    for (unsigned i = 0; i < 4; ++i) {
        eval_low(dut);
        rise(dut);
        fall(dut);
    }
    dut.rst_n = 1;
    eval_low(dut);
}

void check_dot_cycle(Vot_verilator_unit_top& dut, bool valid, bool poison,
                     uint8_t enable, uint16_t activations, uint32_t weights) {
    dut.dot_valid = valid;
    dut.dot_poison = poison;
    dut.dot_enable = enable;
    dut.dot_activations = activations;
    dut.dot_weights = weights;
    const DotExpected expected = dot_reference(valid, poison, enable, activations, weights);
    eval_low(dut);
    rise(dut);
    require(static_cast<bool>(dut.dot_out_valid) == expected.valid, "dot valid mismatch");
    require(static_cast<bool>(dut.dot_out_poison) == expected.poison, "dot poison mismatch");
    require(static_cast<uint16_t>(dut.dot_result) == static_cast<uint16_t>(expected.result),
            "dot result mismatch");
    require(static_cast<uint8_t>(dut.dot_status) == expected.status, "dot status mismatch");
    fall(dut);
}

void test_dot(Vot_verilator_unit_top& dut) {
    check_dot_cycle(dut, true, false, 3, 0x0201U, 0x02ff0403U);
    check_dot_cycle(dut, true, false, 3, 0x7f7fU, 0x7f7f7f7fU);
    check_dot_cycle(dut, true, false, 3, 0x8080U, 0x7f7f7f7fU);
    check_dot_cycle(dut, true, true, 3, 0x7f7fU, 0x7f7f7f7fU);
    check_dot_cycle(dut, false, false, 0, 0, 0);
    for (unsigned i = 0; i < 4096; ++i) {
        const uint32_t r0 = xorshift32();
        const uint32_t r1 = xorshift32();
        check_dot_cycle(dut, (r0 & 3U) != 0U, (r0 & 0x40U) != 0U,
                        static_cast<uint8_t>((r0 >> 8U) & 3U),
                        static_cast<uint16_t>(r0 >> 16U), r1);
    }
}

void test_skid(Vot_verilator_unit_top& dut) {
    std::deque<uint16_t> model;
    bool saw_full_stall = false;
    bool saw_full_recycle = false;
    for (unsigned i = 0; i < 8192; ++i) {
        uint32_t r = xorshift32();
        bool in_valid = (r & 3U) != 0U;
        bool out_ready = (r & 0x10U) != 0U;
        uint16_t data = static_cast<uint16_t>(r >> 16U);
        if (i < 3) {
            in_valid = true;
            out_ready = false;
            data = static_cast<uint16_t>(0x100U + i);
        }
        dut.skid_in_valid = in_valid;
        dut.skid_in_data = data;
        dut.skid_out_ready = out_ready;
        eval_low(dut);

        const bool out_valid = dut.skid_out_valid;
        const bool in_ready = dut.skid_in_ready;
        require(out_valid == !model.empty(), "skid valid/occupancy mismatch");
        if (out_valid) require(dut.skid_out_data == model.front(), "skid ordering mismatch");
        const bool push = in_valid && in_ready;
        const bool pop = out_valid && out_ready;
        saw_full_stall |= model.size() == 2 && in_valid && !out_ready && !in_ready;
        saw_full_recycle |= model.size() == 2 && push && pop;
        rise(dut);
        if (pop) model.pop_front();
        if (push) model.push_back(data);
        require(model.size() <= 2, "skid model overflow");
        require(!dut.skid_overflow && !dut.skid_underflow, "skid diagnostic asserted");
        fall(dut);
    }
    require(saw_full_stall, "skid full-stall scenario not exercised");
    require(saw_full_recycle, "skid full recycle scenario not exercised");
}

uint8_t free_lane(uint16_t packed, unsigned sink) {
    return static_cast<uint8_t>((packed >> (3U * sink)) & 7U);
}

void test_credits(Vot_verilator_unit_top& dut) {
    std::array<unsigned, 3> free = {4U, 4U, 4U};
    bool saw_exhaustion = false;
    bool saw_atomic_recycle = false;
    for (unsigned i = 0; i < 8192; ++i) {
        const uint32_t r = xorshift32();
        uint8_t release_mask = 0;
        for (unsigned sink = 0; sink < 3; ++sink) {
            const unsigned outstanding = 4U - free[sink];
            if (outstanding != 0U && ((r >> sink) & 1U)) release_mask |= 1U << sink;
        }
        uint8_t reserve_mask = static_cast<uint8_t>((r >> 8U) & 7U);
        bool reserve_valid = ((r >> 16U) & 3U) != 0U;
        bool release_valid = release_mask != 0U;
        if (i < 4) {
            reserve_valid = true;
            reserve_mask = 7U;
            release_valid = false;
            release_mask = 0;
        } else if (i == 4) {
            reserve_valid = true;
            reserve_mask = 7U;
            release_valid = true;
            release_mask = 7U;
        }
        dut.credit_reserve_valid = reserve_valid;
        dut.credit_reserve_mask = reserve_mask;
        dut.credit_release_valid = release_valid;
        dut.credit_release_mask = release_mask;
        eval_low(dut);
        for (unsigned sink = 0; sink < 3; ++sink)
            require(free_lane(dut.credit_free_count, sink) == free[sink],
                    "credit free-count mismatch before edge");
        bool expected_ready = true;
        for (unsigned sink = 0; sink < 3; ++sink) {
            if (((reserve_mask >> sink) & 1U) && free[sink] == 0U &&
                !(release_valid && ((release_mask >> sink) & 1U)))
                expected_ready = false;
        }
        require(static_cast<bool>(dut.credit_reserve_ready) == expected_ready,
                "credit atomic ready mismatch");
        const bool reserve_fire = reserve_valid && expected_ready;
        saw_exhaustion |= !expected_ready;
        saw_atomic_recycle |= reserve_fire && release_valid && free[0] == 0U &&
                              ((release_mask & reserve_mask & 1U) != 0U);
        rise(dut);
        for (unsigned sink = 0; sink < 3; ++sink) {
            if (release_valid && ((release_mask >> sink) & 1U)) {
                require(free[sink] < 4U, "credit model illegal release");
                ++free[sink];
            }
            if (reserve_fire && ((reserve_mask >> sink) & 1U)) {
                require(free[sink] > 0U, "credit model illegal reserve");
                --free[sink];
            }
            require(free_lane(dut.credit_free_count, sink) == free[sink],
                    "credit free-count mismatch after edge");
        }
        require(!dut.credit_overflow_error && !dut.credit_underflow_error &&
                    !dut.credit_conservation_error,
                "credit manager reported an error under legal traffic");
        fall(dut);
    }
    require(saw_exhaustion, "credit exhaustion not exercised");
    require(saw_atomic_recycle, "credit atomic recycle not exercised");

    // release_valid has no ready return; releasing an already-free sink is a
    // protocol violation and must be detected without wrapping the counter.
    reset(dut);
    dut.credit_reserve_valid = 0;
    dut.credit_reserve_mask = 0;
    dut.credit_release_valid = 1;
    dut.credit_release_mask = 1;
    eval_low(dut);
    require(free_lane(dut.credit_free_count, 0) == 4U,
            "credit overflow precondition mismatch");
    rise(dut);
    require(dut.credit_overflow_error && dut.credit_conservation_error,
            "credit illegal release was not diagnosed");
    require(!dut.credit_underflow_error,
            "credit ready/valid stall was misclassified as underflow");
    require(free_lane(dut.credit_free_count, 0) == 4U,
            "credit illegal release wrapped free count");
    fall(dut);
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_verilator_unit_top dut;
    reset(dut);
    test_dot(dut);
    reset(dut);
    test_skid(dut);
    reset(dut);
    test_credits(dut);
    dut.final();
    VerilatedCov::write("build/verilator_unit/coverage.dat");
    std::cout << "PASS: independent Verilator randomized scoreboard seed=0x" << std::hex
              << kSeed << std::dec << " cycles=" << cycles << " checks=" << checks << "\n";
    return 0;
}
