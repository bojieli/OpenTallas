// Verilator harness of rtl/test/two_clock/tb_hdc_core_2clk.sv.  One tick = one 3.6 GHz VCO period.
// +CLK=split : sclk every 4 ticks (0.9 GHz), fclk every 3 ticks (1.2 GHz), rising together at tick 0 (one PLL)
// +CLK=slow  : both clocks on the same edges every 4 ticks (single 0.9 GHz clock)
// +CLK=fast  : both clocks on the same edges every 3 ticks (single 1.2 GHz clock; pathfinding reference only)
// +FPHASE=k  : split only -- fclk edges at ticks = k (mod 3) (every divider phase is a time shift of phase 0)
#include "Vtb_hdc_core_2clk.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>
#include <string>
static double now_ps = 0;
double sc_time_stamp() { return now_ps; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::string clk = "split"; int fph = 0;
    for (int i = 1; i < argc; i++) {
        if (!strncmp(argv[i], "+CLK=", 5)) clk = argv[i] + 5;
        if (!strncmp(argv[i], "+FPHASE=", 8)) fph = atoi(argv[i] + 8);
    }
    int sper = 4, fper = 3, foff = 0;
    if (clk == "slow") { sper = 4; fper = 4; }
    else if (clk == "fast") { sper = 3; fper = 3; }
    else if (clk == "split") { foff = fph % 3; }
    else { fprintf(stderr, "bad +CLK\n"); return 2; }
    Vtb_hdc_core_2clk* t = new Vtb_hdc_core_2clk;
    t->sclk = 0; t->fclk = 0; t->tick = 0; t->eval();
    unsigned long long tick = 0;
    while (!Verilated::gotFinish()) {
        t->sclk = 0; t->fclk = 0; t->tick = tick; t->eval();
        bool se = (tick % sper) == 0;
        bool fe = (clk == "split") ? (tick >= (unsigned)foff && ((tick - foff) % fper) == 0) : se;
        if (se || fe) { t->sclk = se; t->fclk = fe; t->eval(); }
        tick++; now_ps = tick * 2500.0 / 9.0;
    }
    printf("HARNESS clk=%s fphase=%d ticks=%llu ns=%.3f\n", clk.c_str(), foff, tick, tick * 2500.0 / 9.0 / 1000.0);
    t->final(); delete t; return 0;
}
