// Read-only accepted-byte collector for the retained Opt4 service model.
// Same eval/nextTimeSlot/reset/argv; no Verilator regeneration or DUT writes.
#include "verilated.h"
#include "Vtb_hbm_accel_wg_service.h"
#include "Vtb_hbm_accel_wg_service___024root.h"
#include <array>
#include <cstdio>
#include <memory>
#include <string>

int main(int argc, char** argv) {
    std::string dir;
    for (int i=1;i<argc;++i) if (std::string(argv[i]).rfind("+DIR=",0)==0) dir=argv[i]+5;
    if(dir.empty()) return 2;
    std::array<FILE*,8> raw{};
    for(int m=0;m<8;++m) {
        raw[m]=std::fopen((dir+"/accepted_w2_sm"+std::to_string(m)+".bin").c_str(),"wb");
        if(!raw[m]) return 2;
    }
    FILE* log=std::fopen((dir+"/accepted_w2.log").c_str(),"w");
    if(!log) return 2;
    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> ctx{new VerilatedContext};
    ctx->commandArgs(argc,argv);
    const std::unique_ptr<Vtb_hbm_accel_wg_service> top{new Vtb_hbm_accel_wg_service{ctx.get(),""}};
    auto* r=top->rootp;
    unsigned words[256], before[8], captured[8]={};
    bool initial=true;
    while(!ctx->gotFinish()) {
        // The SV sink's counters change ONLY on s_valid && s_ready.
        // Snapshot OLD payload before eval, attribute only that accepted edge.
        for(int m=0;m<8;++m) before[m]=r->tb_hbm_accel_wg_service__DOT__cnt[m];
        for(int j=0;j<256;++j) words[j]=r->tb_hbm_accel_wg_service__DOT__s_data[j];
        top->eval();
        if(!initial) for(int m=0;m<8;++m) {
            unsigned after=r->tb_hbm_accel_wg_service__DOT__cnt[m];
            if(after==before[m]) continue;
            if(after!=before[m]+1) return 3;
            unsigned offset=m<6?256:0;
            if(before[m]>=offset) {
                // Explicit little-endian; never substitute an input array.
                for(int j=0;j<32;++j) {
                    unsigned w=words[m*32+j];
                    unsigned char b[4]={static_cast<unsigned char>(w),static_cast<unsigned char>(w>>8),
                        static_cast<unsigned char>(w>>16),static_cast<unsigned char>(w>>24)};
                    if(std::fwrite(b,1,4,raw[m])!=4) return 2;
                }
                std::fprintf(log,"%llu %d %u\n",static_cast<unsigned long long>(ctx->time()),m,before[m]-offset);
                ++captured[m];
            }
        }
        initial=false;
        if(!top->eventsPending()) break;
        ctx->time(top->nextTimeSlot());
    }
    top->final();
    const unsigned counts[8]={10,10,0,0,29,29,29,29};
    for(int m=0;m<8;++m) {
        std::fclose(raw[m]);
        if(captured[m]!=6*counts[m]) return 4;
    }
    std::fclose(log);
    if(!ctx->gotFinish()) return 5;
    std::puts("ACCEPTED_W2_CAPTURE_PASS lines=816");
    return 0;
}
