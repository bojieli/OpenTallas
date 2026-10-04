#include "Vot_qwen_nearhbm_sys_tb.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>
struct RestoreContext {
    VerilatedContext* previous = Verilated::threadContextp();
    ~RestoreContext() { Verilated::threadContextp(previous); }
};
int main(int argc,char**argv) {
    bool fixed=argc==2 && !strcmp(argv[1],"fixed");
    RestoreContext restore_main;
    VerilatedContext enclosing;enclosing.threads(1);
    auto before=Verilated::threadContextp();
    for(int rank=0;rank<4;++rank) {
        auto exercise=[] {
            VerilatedContext nc;nc.threads(1);
            Vot_qwen_nearhbm_sys_tb model(&nc,"CONTEXT_CLEANUP");
            model.clk=model.hclk=model.rst_n=model.hrst_n=model.start=model.q_valid=0;
            model.rsp_valid=0;model.T=8192;model.flip_period=0;
            model.eval();model.final();
        };
        if(fixed){RestoreContext restore;exercise();}else{exercise();}
        bool restored=Verilated::threadContextp()==before;
        printf("rank=%d fixed=%d enclosing_context_restored=%d\n",rank,int(fixed),int(restored));fflush(stdout);
        if(!restored) return 3; // detect dangling pointer without dereferencing it
    }
    printf("normal_return0_after_near_model_and_context_destruction\n");fflush(stdout);
    return 0;
}
