// S81-XG4XS: clock driver for tb_s81sl_xs4_equiv.sv
#include "Vxs4eq.h"
#include "verilated.h"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vxs4eq* t = new Vxs4eq;
    for (long i = 0; i < 100000000L && !Verilated::gotFinish(); i++) { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }
    delete t; return 0;
}
