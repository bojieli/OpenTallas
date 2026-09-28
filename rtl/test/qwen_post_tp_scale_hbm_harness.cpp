#include "Vtb_hdc_qwen_post_tp_scale_hbm.h"
#include "verilated.h"

static vluint64_t main_time = 0;
double sc_time_stamp() { return static_cast<double>(main_time); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_hdc_qwen_post_tp_scale_hbm top;
    for (unsigned cycle = 0; cycle < 20000 && !Verilated::gotFinish(); ++cycle) {
        top.clk = 0;
        top.eval();
        main_time += 5;
        top.clk = 1;
        top.eval();
        main_time += 5;
    }
    top.final();
    return Verilated::gotFinish() ? 0 : 1;
}
