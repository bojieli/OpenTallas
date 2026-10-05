#include "VDsromAttention.h"
#include "s81_minimum_attention_cut.hpp"
#include "s81_sim_only_attention_endpoint.hpp"
#include <fstream>
#include <iostream>
#include <vector>
#include <array>
#include <filesystem>
#include "adapter_config.hpp"

template<class B> uint32_t bits(const B& b,unsigned o,unsigned n) {
    uint32_t v=0;for(unsigned j=0;j<n;++j){
        if constexpr(std::is_integral<B>::value)v|=((uint64_t(b)>>(o+j))&1u)<<j;
        else v|=((b[(o+j)/32]>>((o+j)%32))&1u)<<j;
    }return v;
}
std::vector<uint32_t> load(const std::string& p,size_t n) {
    std::ifstream f(p,std::ios::binary);std::vector<uint32_t> v(n);
    f.read(reinterpret_cast<char*>(v.data()),n*4);
    if(!f||f.peek()!=EOF)throw std::runtime_error("input extent: "+p);return v;
}
template<class B> void write(std::ofstream& f,const B& b,unsigned words) {
    for(unsigned i=0;i<words;++i){uint32_t v=b[i];
        unsigned char x[4]={uint8_t(v),uint8_t(v>>8),uint8_t(v>>16),uint8_t(v>>24)};
        f.write(reinterpret_cast<char*>(x),4);
    }if(!f)throw std::runtime_error("capture write");
}
int main(int argc,char** argv) {try {
    if(argc!=3)throw std::runtime_error("capture INPUT_DIR FRESH_OUTPUT_DIR");
    const std::string input=argv[1],output=argv[2];
    if(!std::filesystem::create_directory(output))throw std::runtime_error("fresh output required");
    auto p=load(input+"/I63.S_rank0.u32",10240);
    auto k=load(input+"/source_kv_beats.u32",160*530);
    VerilatedContext context;VDsromAttention a(&context,"I63_minimum_adapter");
    DsromS81SimOnlyAttentionEndpoint e(&context,"I63_sim_math");
    long cycle=0;DsromS81MinimumRuntime r{};r.stage=37;r.rank=0;r.pair=11;r.bf16=true;
    r.context=&context;r.cycle=[&](){return cycle;};
    auto cut=std::make_shared<DsromS81MinimumAttentionCut<VDsromAttention,DsromS81SimOnlyAttentionEndpoint>>(r,a,e);
    auto ep=cut->participant();configure(a);
    a.clk=0;a.rst_n=0;a.go=0;a.packed_kv_v=0;a.packed_kv_fault=0;a.packed_kv_m=15;
    for(unsigned j=0;j<4;++j)a.x_q[j]=0;
    unsigned nk=0,np=0,nq=0,ny=0,jobs=0;bool admitted=false;
    std::array<uint32_t,8192> sink{};std::array<bool,8192> seen{};
    std::ofstream pf(output+"/accepted_p.u32",std::ios::binary),kf(output+"/accepted_kv.u32",std::ios::binary),
        qf(output+"/accepted_q.u32",std::ios::binary),yf(output+"/old_pv_bus.u32",std::ios::binary),
        events(output+"/events.tsv");
    events<<"cycle\tevent\tordinal\tjob_identity47\tproducer\tphase\n";
    for(;;++cycle){
        const bool released=cycle>=3;
        a.rst_n=released;a.go=released&&!admitted&&a.ready;
        a.packed_kv_v=released&&nk<160;
        if(nk<160)for(unsigned j=0;j<530;++j)a.packed_kv_w[j]=k[nk*530+j];
        a.clk=0;cut->join();ep.prepare({});
        const bool takego=a.go&&a.ready;
        std::array<uint32_t,4> nextq{};
        for(unsigned j=0;j<4;++j)if((a.x_re>>j)&1){
            auto address=bits(a.x_addr,j*30,30);
            if(address<63936||address>=63936+10240)throw std::runtime_error("source P address");
            nextq[j]=p[address-63936];
        }
        auto event=[&](const char* what,unsigned ordinal){events<<cycle<<'\t'<<what<<'\t'<<ordinal<<"\t2147483648\t2534\tI63\n";};
        if(released&&e.job_v&&e.job_ready){if(jobs++)throw std::runtime_error("second job");event("JOB",0);}
        if(released&&e.p_v&&e.p_ready){if(np>=320)throw std::runtime_error("extra P");write(pf,e.p_w,16);event("P",np++);}
        if(released&&e.kv_v&&e.kv_ready){if(nk>=160||e.kv_m!=15)throw std::runtime_error("KV extent/mask");write(kf,e.kv_w,530);event("KV",nk++);}
        if(released&&e.q_v&&e.q_ready){write(qf,e.q_w,256);event("Q",nq++);}
        if(released&&e.pv_v){if(ny>=8||e.pv_c!=ny)throw std::runtime_error("PV order");write(yf,e.pv_y,1024);event("PV",ny++);}
        if(released)for(unsigned port=0;port<4;++port)if((a.o_we>>port)&1){
            auto address=bits(a.o_addr,port*30,30)*16;
            for(unsigned lane=0;lane<16;++lane)if((a.o_mask>>(port*16+lane))&1){
                if(address+lane<74272||address+lane>=74272+8192)throw std::runtime_error("PV writer address");
                unsigned i=address+lane-74272;if(seen[i])throw std::runtime_error("duplicate PV writer");
                seen[i]=true;sink[i]=a.o_data[port*16+lane];
            }
        }
        // Freeze all OLD inputs before either model's rising evaluation.
        ep.rising(released);a.clk=1;a.eval();
        for(unsigned j=0;j<4;++j)a.x_q[j]=nextq[j];
        a.clk=0;a.eval();ep.falling(released);
        if(takego)admitted=true;
        if(admitted&&a.idle&&np==320&&nk==160&&ny==8){
            for(bool x:seen)if(!x)throw std::runtime_error("missing PV writer");break;
        }
        if(a.fault||ep.fault())throw std::runtime_error("native adapter/cut fault");
    }
    std::ofstream out(output+"/adapter_PV.u32",std::ios::binary);write(out,sink,8192);
    std::cout<<"MINIMUM_I63_CAPTURE jobs="<<jobs<<" P="<<np<<" KV="<<nk<<" Q="<<nq<<" PV="<<ny
        <<" cycles="<<cycle<<" scope=controlled-source SIM_ONLY-math/native-adapter; no original-input attribution/timing\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"MINIMUM_I63_ERROR "<<e.what()<<'\n';return 1;}}
