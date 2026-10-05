// Directed opaque-bit fixture for the ACTUAL native provider/archive.
// IO callbacks deliberately stall publication. Not trained payload/full token.
#include "s81_minimum_tp4_gather.hpp"
#include "verilated.h"
#include <map>
#include <set>
#include <iostream>

static void check(bool v,const char* why){if(!v)throw std::runtime_error(why);}
static uint32_t bits(unsigned rank,unsigned address){return 0x3f000000u^(rank<<20)^address;}
int main() {
    VerilatedContext context;
    DsromS81MinimumRuntime runtime{};
    constexpr uint64_t identity=1ull<<31;
    long cycle=0;
    runtime.context=&context;runtime.cycle=[&](){return cycle;};runtime.identity=identity;
    std::array<DsromS81MinimumSourceIo,4> io;
    struct Held {S81EmbeddingOutput output{};long edge=0;bool active=false;};
    std::array<Held,4> held{};
    std::array<unsigned,4> active_pc{};
    std::set<std::tuple<unsigned,unsigned,unsigned>> seen;
    unsigned captured_words=0,published_words=0,accepted_commands=0,refusals=0;
    for(unsigned rank=0;rank<4;rank++) {
        io[rank].span_lease=[&](uint64_t id,uint32_t a,unsigned n){return id==identity&&n&&uint64_t(a)+n<(1u<<19);};
        io[rank].read_word=[&,rank](uint64_t id,uint32_t a)->std::optional<uint32_t> {
            check(id==identity,"foreign read context");
            if(cycle%3==0)return std::nullopt;
            return bits(rank,a);
        };
        io[rank].offer=[&,rank](const S81EmbeddingOutput& out,unsigned n) {
            check(n==16&&out.vm_identity==identity&&!held[rank].active,"overlapping publication fixture");
            if((cycle+rank)%4==0){refusals++;return false;}
            held[rank]={out,cycle,true};return true;
        };
        io[rank].visible=[&,rank](const S81EmbeddingOutput& out,unsigned n) {
            auto& h=held[rank];check(h.active&&n==16&&h.output.vm_address==out.vm_address,"unmatched visibility");
            check(std::equal(std::begin(out.vm_data),std::end(out.vm_data),std::begin(h.output.vm_data)),"held output changed");
            if(cycle<h.edge+5)return false;
            published_words+=16;h.active=false;return true;
        };
    }
    auto provider=dsrom_s81_bind_native_tp4_gather(runtime,identity,io,
        [&](unsigned rank,unsigned pc){check(pc==9||pc==10,"bad accepted literal");active_pc[rank]=pc;accepted_commands++;},
        [&](unsigned rank,unsigned pc,const S81EmbeddingOutput& out) {
            check(active_pc[rank]==pc,"output before real command acceptance");
            const unsigned src=pc==9?419776:420096,dst=pc==9?51648:54208,n=pc==9?320:128;
            for(unsigned lane=0;lane<16;lane++) {
                const unsigned address=out.vm_address+lane,offset=address-dst;
                check(address>=dst&&offset<4*n,"destination extent");
                check(out.vm_data[lane]==bits(offset/n,src+offset%n),"native rank-major payload mismatch");
                check(seen.emplace(pc,rank,address).second,"duplicate native output");
                captured_words++;
            }
        });
    auto tick=[&](bool released){provider.participant.prepare({});provider.participant.rising(released);
                               provider.participant.falling(released);cycle++;};
    tick(false);tick(false);tick(true);
    for(unsigned pc:{9u,10u}) {
        provider.start(pc);
        // Finite fixture completion watchdog: source/callback count is fixed;
        // no build time, memory or host CPU limit is imposed.
        const long begin=cycle;
        while(!provider.complete()) {
            tick(true);
            check(cycle-begin<20000,"finite fixture failed to drain");
            check(!provider.participant.fault(),"native provider fault");
        }
        for(const auto& h:held)check(!h.active,"complete before actual visibility");
    }
    check(captured_words==7168&&published_words==7168&&accepted_commands==8&&refusals,
          "full I9/I10 conservation or publication stalls absent");
    std::cout<<"PASS_NATIVE_TP4_GATHER_FIXTURE words="<<captured_words
             <<" cycles="<<cycle<<" refusals="<<refusals<<"\n";
}
