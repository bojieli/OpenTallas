#include "Vot_fp32_signed_add_differential_top.h"
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

}  // namespace

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vot_fp32_signed_add_differential_top dut;
    std::ifstream stream("signed_add_fields.hex");
    if (!stream) fail("cannot open signed_add_fields.hex");

    uint64_t left = 0;
    uint64_t right = 0;
    uint64_t expected = 0;
    unsigned index = 0;
    while (stream >> std::hex >> left >> right >> expected) {
        dut.left_code = static_cast<uint32_t>(left);
        dut.right_code = static_cast<uint32_t>(right);
        dut.eval();
        if (dut.result != expected) {
            fail("signed add differs at " + std::to_string(index));
        }
        ++index;
    }
    if (index != 20000U) fail("signed-add vector count differs");
    dut.final();
    std::cout << "PASS: FP32 signed-add RTL differential cases=" << index
              << " seed=5157454e334d4154\n";
    return 0;
}
