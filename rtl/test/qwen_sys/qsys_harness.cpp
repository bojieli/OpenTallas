// Generic Verilator driver for the Qwen ROM system benches: toggles `clk`
// (period 2 time units) until the bench calls $finish.  The bench's top
// module class is passed as -DTOP=V<top> -DTOPH="V<top>.h".
#include <verilated.h>
#include QSYS_TOPH
#include <cstdio>
double sc_time_stamp() { return 0; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    QSYS_TOP* t = new QSYS_TOP;
    t->clk = 0;
    t->eval();
    unsigned long long n = 0;
    while (!Verilated::gotFinish()) {
        t->clk = !t->clk;
        t->eval();
        if (++n > 4000000000ULL) { std::printf("HARNESS_LIMIT\n"); break; }
    }
    t->final();
    delete t;
    return 0;
}
