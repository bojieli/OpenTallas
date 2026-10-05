// Generic Verilator driver for a self-checking bench `module TB (input wire clk)`:
// toggles the clock until $finish.  Build with -CFLAGS -DVTOP=V<bench>.
#include "verilated.h"
#define HDC_STR2(x) #x
#define HDC_STR(x) HDC_STR2(x)
#define HDC_HDR(x) HDC_STR(x.h)
#include HDC_HDR(VTOP)

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    VTOP* top = new VTOP;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    top->final();
    delete top;
    return 0;
}
