#include "Vot_fp32_rne_differential_top.h"
#include "verilated.h"

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

namespace {

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "FAIL: " << message << "\n";
    std::exit(1);
}

void require(bool condition, const std::string& message) {
    if (!condition) fail(message);
}

void eval_low(Vot_fp32_rne_differential_top& dut) {
    dut.clk = 0;
    dut.eval();
}

void tick(Vot_fp32_rne_differential_top& dut) {
    dut.clk = 1;
    dut.eval();
    dut.clk = 0;
    dut.eval();
}

template <typename Check>
unsigned run_pairs(Vot_fp32_rne_differential_top& dut, const char* path,
                   Check check) {
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    uint64_t left = 0;
    uint64_t right = 0;
    uint64_t expected = 0;
    unsigned index = 0;
    while (stream >> std::hex >> left >> right >> expected) {
        dut.left_code = static_cast<uint32_t>(left);
        dut.right_code = static_cast<uint32_t>(right);
        eval_low(dut);
        check(index, expected);
        ++index;
    }
    return index;
}

std::string at(const char* operation, unsigned index) {
    return std::string(operation) + " differs at " + std::to_string(index);
}

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_fp32_rne_differential_top dut;
    dut.rst_n = 0;
    dut.rsqrt_in_valid = 0;
    dut.rsqrt_out_ready = 0;
    for (unsigned cycle = 0; cycle < 3; ++cycle) tick(dut);

    const unsigned add_count = run_pairs(
        dut, "arithmetic_add_fields.hex",
        [&](unsigned index, uint64_t expected) {
            if (dut.add_result != expected) fail(at("add", index));
        });
    const unsigned multiply_count = run_pairs(
        dut, "arithmetic_mul_fields.hex",
        [&](unsigned index, uint64_t expected) {
            if (dut.mul_result != expected) fail(at("multiply", index));
        });

    std::ifstream bf16_stream("arithmetic_bf16_fields.hex");
    if (!bf16_stream) fail("cannot open arithmetic_bf16_fields.hex");
    uint64_t input = 0;
    uint64_t expected = 0;
    unsigned bf16_count = 0;
    while (bf16_stream >> std::hex >> input >> expected) {
        dut.left_code = static_cast<uint32_t>(input);
        eval_low(dut);
        if (dut.bf16_result != expected) fail(at("BF16 conversion", bf16_count));
        ++bf16_count;
    }

    dut.rst_n = 1;
    dut.rsqrt_out_ready = 1;
    eval_low(dut);
    std::ifstream rsqrt_stream("arithmetic_rsqrt_fields.hex");
    if (!rsqrt_stream) fail("cannot open arithmetic_rsqrt_fields.hex");
    unsigned rsqrt_count = 0;
    while (rsqrt_stream >> std::hex >> input >> expected) {
        for (unsigned wait = 0; !dut.rsqrt_in_ready && wait < 4; ++wait)
            tick(dut);
        require(dut.rsqrt_in_ready, "reciprocal-square-root input not ready");
        dut.argument_code = static_cast<uint32_t>(input);
        dut.rsqrt_in_valid = 1;
        eval_low(dut);
        tick(dut);
        dut.rsqrt_in_valid = 0;
        unsigned cycles = 0;
        while (!dut.rsqrt_out_valid && cycles < 40) {
            tick(dut);
            ++cycles;
        }
        require(dut.rsqrt_out_valid, "reciprocal-square-root timeout");
        const uint64_t actual =
            (static_cast<uint64_t>(dut.rsqrt_result_error) << 32U) |
            dut.rsqrt_result_code;
        if (actual != expected) fail(at("reciprocal square root", rsqrt_count));
        tick(dut);
        ++rsqrt_count;
    }

    require(add_count == 5000U && multiply_count == 5000U &&
                bf16_count == 5000U && rsqrt_count == 2000U,
            "arithmetic vector counts differ");
    dut.final();
    std::cout << "PASS: FP32 RTL differential add=" << add_count
              << " multiply=" << multiply_count << " bf16=" << bf16_count
              << " rsqrt=" << rsqrt_count << " seed=5157454e33524d53\n";
    return 0;
}
