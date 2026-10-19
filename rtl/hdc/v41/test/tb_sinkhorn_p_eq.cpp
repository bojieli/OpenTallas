#include "Vtb_sinkhorn_p_eq.h"
#include "verilated.h"
int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_sinkhorn_p_eq *t = new Vtb_sinkhorn_p_eq;
    for (long i = 0; i < 400000000L && !Verilated::gotFinish(); i++) { t->clk = i & 1; t->eval(); }
    t->final(); delete t; return 0;
}
