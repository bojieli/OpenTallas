// Two-clock Verilator driver for the Qwen ROM system bench (rtl/test/qwen_sys/tb_qwen_rom_sys.sv), after
// rtl/test/two_clock/hdc_core_2clk_harness.cpp.  One tick = one 3.6 GHz VCO period.
//   +CLK=split : sclk every 4 ticks (0.9 GHz), fclk every 3 ticks (1.2 GHz), rising together at tick 0 (one PLL)
//   +CLK=slow  : both clocks on the same edges every 4 ticks (single 0.9 GHz clock) -- the default
//   +FPHASE=k  : split only -- fclk edges at ticks = k (mod 3)
// The top module class is passed as -DTOP=V<top> -DTOPH="V<top>.h".
#include <verilated.h>
#include QSYS_TOPH
#include <cstdio>
#include <cstring>
#include <string>
static double now_ps = 0;
double sc_time_stamp() { return now_ps; }
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::string clk = "slow"; int fph = 0;
    for (int i = 1; i < argc; i++) {
        if (!strncmp(argv[i], "+CLK=", 5)) clk = argv[i] + 5;
        if (!strncmp(argv[i], "+FPHASE=", 8)) fph = atoi(argv[i] + 8);
    }
    int sper = 4, fper = 4, foff = 0;
    if (clk == "split") { fper = 3; foff = fph % 3; }
    else if (clk != "slow") { fprintf(stderr, "bad +CLK\n"); return 2; }
    QSYS_TOP* t = new QSYS_TOP;
    t->sclk = 0; t->fclk = 0; t->tick = 0; t->eval();
    unsigned long long tick = 0;
    while (!Verilated::gotFinish()) {
        t->sclk = 0; t->fclk = 0; t->tick = tick; t->eval();
        bool se = (tick % sper) == 0;
        bool fe = (tick >= (unsigned)foff && ((tick - foff) % fper) == 0);
        if (se || fe) { t->sclk = se; t->fclk = fe; t->eval(); }
        tick++; now_ps = tick * 2500.0 / 9.0;
        if (tick > 40000000000ULL) { printf("HARNESS_LIMIT\n"); break; }
    }
    printf("HARNESS clk=%s fphase=%d ticks=%llu\n", clk.c_str(), foff, tick);
    t->final(); delete t; return 0;
}
