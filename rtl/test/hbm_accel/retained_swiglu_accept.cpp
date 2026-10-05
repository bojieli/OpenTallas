// Read-only output collector for retained W64 ROUTED1 RTL-only SwiGLU.
// Unchanged SV stimulus/clock/eval/reset; turn the original printed FAIL into
// a nonzero process exit. No arithmetic, context rewrite or ideal ready.
#include "verilated.h"
#include "Vtb_dsrom_su_swiglu.h"
#include "Vtb_dsrom_su_swiglu___024root.h"
#include <cstdio>
#include <memory>
static void little(FILE* f,unsigned w,int bytes) {
    for(int i=0;i<bytes;++i) if(std::fputc((w>>(8*i))&255,f)==EOF) std::abort();
}
int main(int argc,char** argv) {
    auto ab=std::fopen("native_a.u32","wb");
    auto qp=std::fopen("native_q.bin","wb");
    if(!ab||!qp)return 2;
    const std::unique_ptr<VerilatedContext> ctx{new VerilatedContext};ctx->commandArgs(argc,argv);
    const std::unique_ptr<Vtb_dsrom_su_swiglu> top{new Vtb_dsrom_su_swiglu{ctx.get(),""}};
    auto* r=top->rootp;unsigned av[64],q[16];bool initial=true;
    while(!ctx->gotFinish()) {
        unsigned oa=r->tb_dsrom_su_swiglu__DOT__oa,ov=r->tb_dsrom_su_swiglu__DOT__ov;
        for(int i=0;i<64;++i)av[i]=r->tb_dsrom_su_swiglu__DOT__dut__DOT__ab[i];
        for(int i=0;i<16;++i)q[i]=r->tb_dsrom_su_swiglu__DOT__q[i];
        // Actual native oq={fault,q,e,y}, low y1024, then e20. NOUT23.
        const auto& line=r->tb_dsrom_su_swiglu__DOT__dut__DOT__u_out__DOT__g_line__DOT__line;
        const unsigned bit=22*1557+1024,word=bit/32,shift=bit%32;
        unsigned exp=(line[word]>>shift)|(line[word+1]<<(32-shift));
        top->eval();
        if(!initial) {
            if(r->tb_dsrom_su_swiglu__DOT__oa!=oa) {
                if(r->tb_dsrom_su_swiglu__DOT__oa!=oa+1)return 3;
                for(auto w:av)little(ab,w,4);
            }
            if(r->tb_dsrom_su_swiglu__DOT__ov!=ov) {
                if(r->tb_dsrom_su_swiglu__DOT__ov!=ov+1)return 3;
                for(int b=0;b<2;++b) {
                    little(qp,(exp>>(10*b))&1023,2);
                    for(int i=0;i<8;++i)little(qp,q[b*8+i],4);
                }
            }
        }
        initial=false;
        if(!top->eventsPending())break;
        ctx->time(top->nextTimeSlot());
    }
    top->final();std::fclose(ab);std::fclose(qp);
    if(!ctx->gotFinish()||r->tb_dsrom_su_swiglu__DOT__ea||r->tb_dsrom_su_swiglu__DOT__eq||
       r->tb_dsrom_su_swiglu__DOT__nchk!=r->tb_dsrom_su_swiglu__DOT__nblk||
       r->tb_dsrom_su_swiglu__DOT__oa*64!=r->tb_dsrom_su_swiglu__DOT__n||
       r->tb_dsrom_su_swiglu__DOT__ov*64!=r->tb_dsrom_su_swiglu__DOT__n)return 1;
    std::puts("NATIVE_SWIGLU_CAPTURE_PASS");return 0;
}
