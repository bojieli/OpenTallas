// S81-XG3: clock driver for tb_s81sl_rs_equiv.sv
#include "Vrseq.h"
#include "verilated.h"
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vrseq* t = new Vrseq;
    for (long i = 0; i < 100000000L && !Verilated::gotFinish(); i++) { t->clk = 0; t->eval(); t->clk = 1; t->eval(); }
    delete t; return 0;
}
