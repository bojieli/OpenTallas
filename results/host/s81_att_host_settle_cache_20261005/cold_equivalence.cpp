#include "s81_minimum_attention_cut.hpp"
#include "VDsromAttention.h"
#include "VDsromAttEngine.h"
#include "verilated.h"
#include <chrono>
#include <cstring>
#include <iostream>

struct Trial {
    VerilatedContext& context;
    DsromS81MinimumRuntime runtime{};
    long cycle=0;
    std::shared_ptr<VDsromAttention> adapter;
    std::shared_ptr<VDsromAttEngine> endpoint;
    std::shared_ptr<DsromS81MinimumAttentionCut<VDsromAttention,VDsromAttEngine>> cut;
    DsromS81MinimumParticipant participant;
    double seconds=0;
    Trial(VerilatedContext& shared,bool cache,const char* name):context(shared) {
        runtime.stage=37;runtime.rank=0;runtime.pair=11;
        runtime.context=&context;runtime.cycle=[this](){return cycle;};
        const std::string a_name=std::string(name)+"_adapter";
        const std::string e_name=std::string(name)+"_endpoint";
        adapter=std::make_shared<VDsromAttention>(&context,a_name.c_str());
        endpoint=std::make_shared<VDsromAttEngine>(&context,e_name.c_str());
        adapter->go=0;adapter->clk=0;adapter->rst_n=0;
        endpoint->clk=0;endpoint->rst_n=0;
        setenv("DSROM_S81_ATT_HOST_SETTLE_CACHE",cache?"1":"0",1);
        cut=std::make_shared<DsromS81MinimumAttentionCut<VDsromAttention,VDsromAttEngine>>(
            runtime,*adapter,*endpoint);
        participant=cut->participant();
    }
    void step(bool released) {
        const auto start=std::chrono::steady_clock::now();
        adapter->clk=0;adapter->rst_n=released;adapter->eval();
        // Repeated enclosing LOW joins, then the ordinary participant prepare.
        for(unsigned j=0;j<3;++j)cut->join();
        participant.prepare(DsromS81PairResult{});
        adapter->clk=1;adapter->eval();participant.rising(released);
        adapter->clk=0;adapter->eval();participant.falling(released);
        seconds+=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        ++cycle;
    }
};
int main() {
    VerilatedContext context;context.threads(1);
    Trial baseline(context,false,"cache_baseline"),cached(context,true,"cache_candidate");
    for(unsigned i=0;i<130;++i) {
        const bool released=i>=2;
        baseline.step(released);cached.step(released);
        if(std::memcmp(&baseline.adapter->att_from[0],&cached.adapter->att_from[0],
                       sizeof(baseline.adapter->att_from)) ||
           baseline.adapter->ready!=cached.adapter->ready ||
           baseline.adapter->idle!=cached.adapter->idle ||
           baseline.adapter->fault!=cached.adapter->fault) {
            std::cerr<<"FIRST_MISMATCH cycle="<<i<<std::endl;std::_Exit(1);
        }
    }
    std::cout<<"{\"scope\":\"actual unadmitted ATT same-input LOW settle only; no operator/token or hardware timing credit\","
             <<"\"cycles_each\":130,\"cold_cycles_each\":2,\"released_cycles_each\":128,"
             <<"\"bus_words_compared_per_cycle\":1124,\"mismatches\":0,"
             <<"\"baseline_seconds\":"<<baseline.seconds
             <<",\"cached_seconds\":"<<cached.seconds<<"}"<<std::endl;
    // No job was admitted. Close/flush the result before process teardown;
    // protect-library scope destruction is outside this eval equivalence test.
    std::_Exit(0);
}
