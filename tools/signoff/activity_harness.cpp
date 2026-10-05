// Verilator driver for sign-off activity capture (tools/signoff_analysis.py).
//
// Toggles `clk` like the campaign harnesses (rtl/test/hdc_core_harness.cpp)
// and, when +VCD=<path> is given, dumps a VCD of the traced model for the
// cycles c with +VCD_BEGIN <= c < +VCD_END and, when +VCD_EVERY=N is given,
// only those with (c - VCD_BEGIN) % N < +VCD_LEN (uniform sampling of a long
// run in windows of VCD_LEN cycles).
//
// Time in the dump is TRACED time: it advances only while a cycle is dumped,
// half_cycle * +HALF_PS ps per half cycle, so the SAIF made from it is in real
// time at the analysis clock (2 * HALF_PS ps per cycle) over the traced cycles
// only.  The first dump of each sampling window carries every change since
// the previous window's last one, which adds at most one toggle per signal
// per window (<= 1/VCD_LEN of a toggle rate).  The path is usually a FIFO read
// by tools/signoff/vcd2saif.
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

static unsigned long long plus_ull(const char* name, unsigned long long dflt) {
    std::string key = std::string(name) + "=";
    const char* p = Verilated::commandArgsPlusMatch(key.c_str());
    return (p && *p) ? strtoull(p + key.size() + 1, nullptr, 10) : dflt;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
    VTOP* top = new VTOP;
    const char* p = Verilated::commandArgsPlusMatch("VCD=");
    std::string vcd = (p && *p) ? std::string(p + 5) : "";
    const unsigned long long vb = plus_ull("VCD_BEGIN", 0), ve = plus_ull("VCD_END", ~0ULL);
    const unsigned long long every = plus_ull("VCD_EVERY", 0), len = plus_ull("VCD_LEN", 0);
    const unsigned long long hp = plus_ull("HALF_PS", 1);
    VerilatedVcdC* tfp = nullptr;
    unsigned long long half = 0;      // simulated half cycles; cycle = half / 2
    unsigned long long traced = 0;    // dumped half cycles
    top->clk = 0;
    top->eval();
    while (!Verilated::gotFinish()) {
        unsigned long long cyc = half / 2;
        bool in = !vcd.empty() && cyc >= vb && cyc < ve && (every == 0 || (cyc - vb) % every < len);
        if (in && !tfp) {
            tfp = new VerilatedVcdC;
            top->trace(tfp, 99);
            tfp->open(vcd.c_str());
            fprintf(stderr, "ACTIVITY dump open at cycle %llu\n", cyc);
        }
        if (tfp && cyc >= ve) {
            tfp->close();
            delete tfp;
            tfp = nullptr;
            vcd.clear();
            fprintf(stderr, "ACTIVITY dump closed at cycle %llu, %llu traced cycles\n", cyc, traced / 2);
        }
        top->clk = !top->clk;
        top->eval();
        half++;
        if (tfp && in) {
            traced++;
            tfp->dump(static_cast<uint64_t>(traced * hp));
        }
    }
    if (tfp) {
        tfp->close();
        delete tfp;
        fprintf(stderr, "ACTIVITY dump closed at finish (cycle %llu), %llu traced cycles\n", half / 2, traced / 2);
    }
    top->final();
    delete top;
    return 0;
}
