// Compile/link check of the native hook against a Vdie stub with the combined die's exact row-port
// widths and the real Vhbm (ot_qwen_hbm_stream4_tagged): one wiring pass must report changed pins,
// a second pass on unchanged values must report none.
#include "Vdie.h"
#include "Vhbm.h"
#include "verilated.h"
#include <cstdio>
bool qwen_stream4_wire_native_tagged_rows(Vdie&, Vhbm&);
int main(int argc, char** argv) {
    VerilatedContext ctx; ctx.commandArgs(argc, argv);
    Vdie d(&ctx, "die"); Vhbm m(&ctx, "stream4");
    d.hclk = 1; d.hrst_n = 1; d.h_rsp_ready[0] = 0;
    bool first = qwen_stream4_wire_native_tagged_rows(d, m);
    bool second = qwen_stream4_wire_native_tagged_rows(d, m);
    bool ok = first && !second && m.t_clk == 1 && m.t_rst_n == 1;
    printf("STREAM4_TAGGED_HOOK %s first_changed=%d second_changed=%d\n", ok ? "PASS" : "FAIL", int(first), int(second));
    return ok ? 0 : 1;
}
