// QC-PG-2 (10-27): tb_qfd_dv2 driver = rtl/test/qwen_dv/main2.cpp + VCD (Verilator --trace; what is traced is set by the .vlt).
// VCD written next to the +LOG= file (<log>.vcd), one per simulation.
#include "Vtb.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <string>
static double g_t = 0;
double sc_time_stamp() { return g_t; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
    Vtb* t = new Vtb;
    VerilatedVcdC* tf = new VerilatedVcdC;
    t->trace(tf, 99);
    std::string lg = Verilated::commandArgsPlusMatch("LOG=");
    std::string vcd = (lg.size() > 5 ? lg.substr(5) : std::string("sim")) + ".vcd";
    tf->open(vcd.c_str());
    vluint64_t k = 0;
    t->ck = 0;
    while (!Verilated::gotFinish()) { t->ck = !t->ck; t->eval(); tf->dump(k++); g_t += 0.5; }
    t->final(); tf->close();
    delete tf; delete t;
    return 0;
}
