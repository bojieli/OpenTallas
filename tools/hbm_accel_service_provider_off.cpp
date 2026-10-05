#include "Vot_hbm_accel_causal_command_provider.h"
#include <cstdio>
int main() {
    Vot_hbm_accel_causal_command_provider d;
    for (unsigned i=0; i<64; ++i) {
        d.clk=i&1; d.rst_n=i>3; d.req_v=1;
        d.cmd_r=1; d.rsp_v=~i; d.commit_v=~i;
        d.owned_r=1; d.credit_v=1; d.credit_we=i&1;
        d.eval();
        if (d.req_r || d.cmd_v || d.rsp_r || d.commit_r || d.owned_v ||
            d.owned_we || d.owned_credit || d.credit_r || d.fault ||
            d.cycle || d.WRresidents || d.live_tags) return 1;
    }
    std::puts("PASS_DEFAULT_OFF_COMMIT_READY 64 patterns");
    return 0;
}
