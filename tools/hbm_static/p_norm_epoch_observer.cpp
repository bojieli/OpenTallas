// Link against the preserved Verilator model archive. This observer changes
// neither RTL nor stimulus; it records actual pin epochs and acknowledged writes.
#include "verilated.h"
#include "Vtb_hbm_p_norm_h16_static.h"
#include "Vtb_hbm_p_norm_h16_static___024root.h"
#include <deque>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <string>

template<class W> unsigned bits(const W& w,unsigned start,unsigned width) {
    unsigned out=0;
    for(unsigned b=0;b<width;b++)out|=((w[(start+b)/32]>>((start+b)%32))&1u)<<b;
    return out;
}
struct Stat { long first=-1,last=-1,count=0,words=0; };
struct Pending {long cycle;unsigned sector;};
static std::string kind(unsigned sector) {
    if(sector>=4608&&sector<5632)return "OUT";
    if(sector>=7904&&sector<8032)return "DEN";
    if(sector>=7840&&sector<7842)return "SINK";
    if(sector>=2304&&sector<3328)return "PV";
    if(sector>=2048&&sector<2128)return "scaled_SC";
    if(sector>=4096&&sector<4176)return "raw_E";
    if(sector>=6000&&sector<7280)return "EB";
    if(sector>=7800&&sector<7802)return "MB";
    if(sector>=7808&&sector<7810)return "SE";
    return "other";
}
#define R(x) r->tb_hbm_p_norm_h16_static__DOT__##x
extern "C" int __wrap_main(int argc,char**argv) {
    const std::unique_ptr<VerilatedContext> context{new VerilatedContext};
    context->threads(1);context->commandArgs(argc,argv);
    const std::unique_ptr<Vtb_hbm_p_norm_h16_static> top{new Vtb_hbm_p_norm_h16_static{context.get(),""}};
    auto*r=top->rootp;
    std::string output;
    for(int i=1;i<argc;i++)if(std::string(argv[i]).rfind("+EPOCH_JSON=",0)==0)output=std::string(argv[i]).substr(12);
    if(output.empty())return 3;
    std::map<std::string,Stat> stats; unsigned head=0;
    auto record=[&](std::string name,long epoch,long words=0){for(auto key:{name,name+"_h"+std::to_string(head)}){auto&s=stats[key];if(s.first<0)s.first=epoch;s.last=epoch;s.count++;s.words+=words;}};
    std::deque<Pending> pending[8];
    bool previous_clk=false,started=false;long cycle=0,base=0,ack_errors=0;
    while(!context->gotFinish()) {
        top->eval();bool clk=R(clk);
        if(clk&&!previous_clk) {
            if(R(running)&&R(io_start_v)&&!started){started=true;base=cycle;}
            if(started) {
                long epoch=cycle-base;head=R(active_head);
                const auto&io=R(dut__DOT__u_core__DOT__u_sfu__DOT__io);
                const auto&aux=R(dut__DOT__u_core__DOT__aux);
                if(bits(io,470,1))record("arithmetic_start_pin",epoch);
                for(unsigned b=0;b<8;b++)if(bits(io,b,1)) {
                    auto k=kind(bits(io,16+16*b,16));
                    record(k+ (bits(io,8+b,1)?"_scalar_prefetch_pin":"_prefetch_pin"),epoch,bits(io,8+b,1)?1:8);
                }
                if(bits(aux,161,1))record(bits(aux,162,16)<4096?"scaled_SC_source_fetch_pin":"E_source_fetch_pin",epoch,64);
                if(bits(aux,0,1)) {
                    unsigned op=bits(aux,12,3);
                    record("reduce_op"+std::to_string(op)+"_precommand_pin",epoch);
                }
                if(bits(aux,109,1))record("scalar_publish_slot_pin",epoch);
                if(R(dut__DOT__u_core__DOT__u_sfu__DOT__stage_v))record("SFU_operand_stage_pin",epoch,__builtin_popcount(R(dut__DOT__u_core__DOT__u_sfu__DOT__stage_v))*8);
                if(R(dut__DOT__u_core__DOT__u_sfu__DOT__scalar_load))record("SFU_scalar_load_pin",epoch);
                if(R(sv))record((R(st)&1)?"SE_scalar_result":"MB_scalar_result",epoch,1);
                for(unsigned b=0;b<8;b++) {
                    if((R(done)>>b)&1) {
                        if(pending[b].empty())ack_errors++;
                        else {auto p=pending[b].front();pending[b].pop_front();if(epoch-p.cycle!=12)ack_errors++;record(kind(p.sector)+"_local_VM_done",epoch);}
                    }
                    if(bits(R(wq),281*b+280,1)) {
                        unsigned sector=bits(R(wq),281*b+264,16),mask=bits(R(wq),281*b,8);
                        record(kind(sector)+"_VM_WQ_pin",epoch,__builtin_popcount(mask));pending[b].push_back({epoch,sector});
                    }
                }
            }
            cycle++;
        }
        previous_clk=clk;
        if(!top->eventsPending())break;
        context->time(top->nextTimeSlot());
    }
    top->final();
    for(auto&q:pending)if(!q.empty())ack_errors++;
    std::ofstream f(output);
    f<<"{\n  \"scope\": \"Actual after-edge pin epochs from preserved source-identical model archive; epoch0 is sampled io_start_v\",\n  \"local_VM_WQ_to_DONE_edges\": 12,\n  \"ack_errors\": "<<ack_errors<<",\n  \"events\": {\n";
    bool first=true;
    for(const auto&[name,s]:stats){if(!first)f<<",\n";first=false;f<<"    \""<<name<<"\": {\"first\": "<<s.first<<", \"last\": "<<s.last<<", \"count\": "<<s.count<<", \"FP32_words\": "<<s.words<<"}";}
    f<<"\n  },\n  \"native_whole_kernel_qualified\": false,\n  \"physical_qualified\": false\n}\n";
    std::cout<<"EPOCH_OBSERVER ack_errors="<<ack_errors<<" events="<<stats.size()<<"\n";
    return ack_errors?1:0;
}
