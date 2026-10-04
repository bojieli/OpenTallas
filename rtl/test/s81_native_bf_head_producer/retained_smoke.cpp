// C++ orchestration test links unchanged Vpb/Vcut/Vretn/Vroot archives.
// Raw1/2 weights and XN1 are test stimuli; expected roots are assertions only.
#include "s81_native_bf_head_producer.hpp"
#include "Vpb.h"
#include "Vretn.h"
#include "Vroot.h"
#include "svdpi.h"
#include <map>
#include <iostream>
using namespace dsrom_s81_minimum;
NativeBfHeadProducer<Vretn,Vroot>* producer=nullptr;
std::map<const void*,unsigned> banks;
extern "C" void v41rt_rom_register(const char* instance) {
    std::string name=instance?instance:"";
    banks[svGetScope()]=!name.empty()&&name.back()=='b';
}
extern "C" void v41rt_cfg_register() {}
extern "C" long long v41rt_cfg_read(int address) {
    if(!producer)throw std::runtime_error("CFG before actual head producer");
    return producer->cfg_word(address);
}
extern "C" void v41rt_rom_read(int address,svBitVecVal* out) {
    if(!producer)throw std::runtime_error("ROM before actual head producer");
    auto word=producer->raw_word(banks.at(svGetScope()),address);
    std::copy(word.begin(),word.end(),out);
}
int main(int argc,char** argv) {
 try {
    VerilatedContext ctx;ctx.commandArgs(argc,argv);ctx.threads(1);ctx.randReset(0);
    Vpb pair(&ctx,"head_selected_pb");
    DsromS81MinimumRuntime rt{};rt.context=&ctx;rt.stage=0;rt.rank=0;rt.pair=0;rt.bf16=true;
    long cycles=0;uint32_t source=(argc>1)?0x3f800001:0x3f800000;unsigned reads=0,accepted=0,raw_reads=0;
    DsromS81PairDrive driven{};
    rt.result=[&](){return DsromS81PairResult{pair.pv,pair.perr,pair.ppos,pair.pseg,pair.pnseg,
       pair.prow,pair.pval,bool(pair.busy),bool(pair.quiet),bool(pair.fault)};};
    rt.drive=[&](const DsromS81PairDrive& p){driven=p;
      pair.cfg_go=p.cfg_go;pair.cfg_ph=p.cfg_ph;pair.cfg_np=p.cfg_np;
      pair.go=p.go;pair.go_bf=p.go_bf;pair.xs_v=p.xs_v;pair.xs_p=p.xs_p;pair.xs_b=p.xs_b;
      pair.xs_sv=p.xs_sv;pair.xs_e0=p.xs_e0;pair.xs_e1=p.xs_e1;pair.xs_pos=p.xs_pos;
      pair.xb_pos=p.xb_pos;pair.xb_v=p.xb_v;pair.xb_b=p.xb_b;pair.xb_sv=p.xb_sv;pair.xb_u=p.xb_u;
      for(unsigned i=0;i<8;i++){pair.xs_q0[i]=p.xs_q0[i];pair.xs_q1[i]=p.xs_q1[i];}
      for(unsigned i=0;i<32;i++)pair.xb_d[i]=p.xb_d[i];};
    rt.cycle=[&](){return cycles;};rt.drive({});
    Vcut actual_shared_cut(&ctx,"borrowed_head_cut");
    NativeBfHeadProducer<Vretn,Vroot> head(rt,actual_shared_cut,
      [&](uint64_t id,uint32_t a)->std::optional<uint32_t>{
        if(id!=7||a<46464||a>=51584)throw std::runtime_error("source XN bounds");reads++;return source;},
      [&](uint64_t id,uint32_t a,unsigned n){return id==7&&a==46464&&n==5120;},
      [&](unsigned rank,unsigned row,unsigned h,unsigned b){
        if(rank||row>=4||h>=40||b>=8)throw std::runtime_error("raw fixture bounds");
        NativeBfHeadRom::Word w{};unsigned value=(row&1)?0x4000:0x3f80;
        for(unsigned i=0;i<8;i++)w[i]=value|(value<<16);raw_reads++;return w;},
      [&](const NativeBfHeadRoots& out){
        if(out.identity!=7||out.request_sequence!=19||out.rank||out.local_row!=accepted)
            throw std::runtime_error("actual native output source identity");
        uint32_t a=(accepted&1)?0x46000000:0x45800000,b=(accepted&1)?0x45000000:0x44800000;
        if(out.root4096!=a||out.root1024!=b)throw std::runtime_error("actual BF ordered subtree mismatch");
        std::cout<<"NATIVE_HEAD_ROOTS row="<<out.local_row<<" A="<<std::hex<<out.root4096
                 <<" B="<<out.root1024<<std::dec<<" cycle="<<cycles<<"\n";
        source=0x40400000;accepted++;return true;},true);
    producer=&head;
    auto edge=[&](bool released){
      auto old=rt.result();for(auto& p:rt.participants)p.prepare(old);
      pair.clk=1;pair.rst_n=released;pair.eval();for(auto& p:rt.participants)p.rising(released);
      pair.clk=0;pair.eval();for(auto& p:rt.participants)p.falling(released);
      if(released){cycles++;if(pair.fault)throw std::runtime_error("PB native fault");
        for(auto& p:rt.participants)if(p.fault())throw std::runtime_error("native participant fault "+p.name);}
    };
    edge(false);rt.identity=7;head.start(7,19,0);
    // Source cycle watchdog, not an elapsed-time budget. Two native rowpairs.
    while(accepted<4&&cycles<15000){edge(true);head.advance();}
    if(accepted!=4||reads!=5120||raw_reads!=1280||head.all_roots_accepted())
        throw std::runtime_error("native BF snapshot/read counts or premature whole-head completion");
    std::cout<<"RETAINED_BF_HEAD_SMOKE_PASS cycles="<<cycles<<" source_reads="<<reads
             <<" raw274_reads="<<raw_reads<<" roots="<<accepted*2<<"\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<"NATIVE_HEAD_SMOKE_FAIL "<<e.what()<<"\n";return 1;}
}
