// Verilator driver for sign-off activity capture (tools/signoff_analysis.py).
//
// Toggles `clk` like the campaign harnesses (rtl/test/hdc_core_harness.cpp)
// and, when +VCD=<path> is given, dumps a VCD of the whole model for the
// cycles [+VCD_BEGIN, +VCD_END).  Value changes are stamped at
// half_cycle * +HALF_PS, so with the bench's 1 ps time precision the VCD (and
// the SAIF made from it) is in real time at the analysis clock
// (2 * HALF_PS ps per cycle).  The path is usually a FIFO read by
// tools/signoff/vcd2saif.
//
// Compile with -DVTOP=<Vclass> -DVTOP_H=\"<Vclass>.h\".
#include VTOP_H
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
    VTOP* top = new VTOP;
    const char* p = Verilated::commandArgsPlusMatch("VCD=");
    std::string vcd = (p && *p) ? std::string(p + 5) : "";
    unsigned long long vb = 0, ve = ~0ULL;
    if ((p = Verilated::commandArgsPlusMatch("VCD_BEGIN=")) && *p) vb = strtoull(p + 11, nullptr, 10);
    if ((p = Verilated::commandArgsPlusMatch("VCD_END=")) && *p) ve = strtoull(p + 9, nullptr, 10);
    unsigned long long hp = 1;
    if ((p = Verilated::commandArgsPlusMatch("HALF_PS=")) && *p) hp = strtoull(p + 9, nullptr, 10);
    VerilatedVcdC* tfp = nullptr;
    unsigned long long half = 0;   // half-cycle counter; cycle = half / 2
    top->clk = 0;
    top->eval();
    while (!Verilated::gotFinish()) {
        unsigned long long cyc = half / 2;
        if (!vcd.empty() && !tfp && cyc >= vb && cyc < ve) {
            tfp = new VerilatedVcdC;
            top->trace(tfp, 99);
            tfp->open(vcd.c_str());
            fprintf(stderr, "ACTIVITY window open at cycle %llu\n", cyc);
        }
        if (tfp && cyc >= ve) {
            tfp->close();
            delete tfp;
            tfp = nullptr;
            vcd.clear();
            fprintf(stderr, "ACTIVITY window closed at cycle %llu\n", cyc);
        }
        top->clk = !top->clk;
        top->eval();
        half++;
        if (tfp) tfp->dump(static_cast<uint64_t>(half * hp));
    }
    if (tfp) {
        tfp->close();
        delete tfp;
        fprintf(stderr, "ACTIVITY window closed at finish, half-cycle %llu\n", half);
    }
    top->final();
    delete top;
    return 0;
}
