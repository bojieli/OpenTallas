// Minimum I9 continuation: four produced native I7 boundaries, fresh real
// import ACKs, then the unchanged native TP4 gather and real destination ACKs.
// No field, pair, expected activation, or head is executed by this vehicle.
#include "s81_minimum_l20_bank.hpp"
#include "s81_minimum_l20_collective.hpp"
#include "verilated.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>

namespace {
void require(bool ok,const char* why) {if(!ok)throw std::runtime_error(why);}
constexpr unsigned source_writer=2478, gather_writer=2480;
constexpr unsigned source_address=419776, destination_address=51648;
constexpr unsigned source_words=320, destination_words=1280;
}

int main(int argc,char** argv) try {
    require(argc==7,"usage: minimum_gather OUTPUT ACTUAL_ID47 I7_RANK0 I7_RANK1 I7_RANK2 I7_RANK3");
    std::size_t used=0;
    const uint64_t identity=std::stoull(argv[2],&used,0);
    require(used==std::string(argv[2]).size()&&identity==(1ull<<31),
            "gather requires the frozen native field component identity, not a fabricated source context");
    std::array<std::array<uint32_t,source_words>,4> input{};
    for(unsigned rank=0;rank<4;++rank) {
        for(unsigned prior=0;prior<rank;++prior)
            require(!std::filesystem::equivalent(argv[3+rank],argv[3+prior]),
                    "gather requires distinct produced rank files");
        std::ifstream file(argv[3+rank],std::ios::binary);
        require(bool(file),"produced native I7 input missing");
        file.read(reinterpret_cast<char*>(input[rank].data()),sizeof(input[rank]));
        require(file.gcount()==sizeof(input[rank])&&file.peek()==EOF,
                "produced native I7 must contain exactly 320 raw32 words");
    }
    const std::filesystem::path output(argv[1]);
    require(!std::filesystem::exists(output)||std::filesystem::is_empty(output),
            "fresh gather output required; retain prior failure outputs");
    std::filesystem::create_directories(output);
    VerilatedContext context;
    long cycle=0;
    std::array<DsromS81MinimumRuntime,4> ranks{};
    std::array<std::shared_ptr<Vnative_vm>,4> models;
    std::array<std::shared_ptr<DsromS81MinimumL20Bank>,4> banks;
    std::array<DsromS81MinimumSourceIo,4> io;
    std::vector<DsromS81MinimumParticipant> participants;
    // No cfg/field phase is pretended here. The tag provider selects its
    // source-bound nonfield component path for actual imported/native writers.
    require(setenv("DSROM_S81_NATIVE_L20_GATHER","1",1)==0,"gather source enrollment environment");
    for(unsigned rank=0;rank<4;++rank) {
        auto& r=ranks[rank];
        r.stage=37;r.rank=rank;r.pair=11;r.bf16=true;r.context=&context;
        r.cycle=[&](){return cycle;};r.identity=identity;
        models[rank]=std::make_shared<Vnative_vm>(&context,("gather_vm_rank"+std::to_string(rank)).c_str());
        banks[rank]=std::make_shared<DsromS81MinimumL20Bank>(r,identity,models[rank],
            dsrom_s81_bind_minimum_source_tags(r,identity));
        io[rank]=banks[rank]->io();
        banks[rank]->publication().enroll_literal(source_writer,{{source_address,source_words}});
        banks[rank]->publication().enroll_literal(gather_writer,{{destination_address,destination_words}});
        participants.push_back(banks[rank]->bank_participant());
    }
    const auto operation=dsrom_s81_l20_collective_literals().front().operation;
    require(operation.index==9&&operation.unit==6&&operation.template_sha256&&
            std::string(operation.template_sha256)=="71936363a5862e0eee46beb9bc7b365611e47ef7dc983204e86e2351c03e1f16",
            "gather requires canonical L20.I9 literal");
    bool accepted=false;
    auto source_ready=[&](){
        for(unsigned rank=0;rank<4;++rank)
            if(!banks[rank]->publication().complete(identity,source_writer)||
               !io[rank].span_lease(identity,source_address,source_words)||
               !banks[rank]->native_target().mutable_write_drained())return false;
        return true;
    };
    auto engine=dsrom_s81_bind_native_l20_collective(ranks[0],identity,io,
        [&](unsigned rank,unsigned pc){
            require(pc==9&&rank<4&&source_ready(),"I9 acceptance lacks four actual wait31 source publications");
            banks[rank]->publication().begin(identity,gather_writer);
            std::cout<<"GATHER_ACCEPT rank="<<rank<<" pc=9 producer=2480 cycle="<<cycle<<'\n';
            accepted=true;
        },
        [&](unsigned rank,unsigned pc,const S81EmbeddingOutput& out){
            require(accepted&&pc==9&&rank<4,"gather output lacks accepted PC9 association");
            for(unsigned lane=0;lane<16;++lane)
                dsrom_s81_capture_minimum_prefix_scalar(ranks[rank],banks[rank]->publication(),
                    gather_writer,out,lane,true);
        },true);
    participants.push_back(engine.participant);
    auto tick=[&](bool released){
        for(auto& p:participants)p.prepare({});
        for(auto& p:participants)p.rising(released);
        for(auto& p:participants)p.falling(released);
        ++cycle;
        for(auto& p:participants)require(!p.fault(),"gather native participant fault; retained debt not cleared");
    };
    for(unsigned n=0;n<3;++n)tick(false);
    // Files carry actual native-produced words, not surviving old leases.
    // The new component obtains its OWN real tagged import writes and ACKs.
    for(unsigned rank=0;rank<4;++rank) {
        auto& pub=banks[rank]->publication();pub.begin(identity,source_writer);
        for(unsigned offset=0;offset<source_words;offset+=16) {
            S81EmbeddingOutput batch{};batch.vm_valid=1;batch.vm_identity=identity;
            batch.vm_address=source_address+offset;
            for(unsigned lane=0;lane<16;++lane) {
                batch.vm_data[lane]=input[rank][offset+lane];
                auto command=dsrom_s81_reserve_native_scalar_tag(ranks[rank],identity,
                    source_writer,batch.vm_address+lane,batch.vm_data[lane]);
                pub.native_scalar(source_writer,command,true);
            }
            while(!io[rank].offer(batch,16))tick(true);
            while(!io[rank].visible(batch,16))tick(true);
        }
        require(pub.complete(identity,source_writer)&&io[rank].span_lease(identity,source_address,source_words),
                "rank I7 import lacks actual full matched ACK lease");
        std::cout<<"IMPORT_ACK rank="<<rank<<" producer=2478 words=320 cycle="<<cycle<<'\n';
    }
    require(source_ready(),"I9 wait31 unavailable");
    while(!engine.inputs_ready(operation)||!engine.ready())tick(true);
    engine.drive(operation,true);tick(true);engine.drive(operation,false);
    require(accepted,"native I9 did not accept GO");
    while(!engine.idle())tick(true);
    const long drain_cycle=cycle;
    for(unsigned rank=0;rank<4;++rank)
        require(banks[rank]->publication().complete(identity,gather_writer)&&
                io[rank].span_lease(identity,destination_address,destination_words),
                "I9 terminal lacks all-rank native gather ACKs");
    unsigned mismatches=0;
    for(unsigned rank=0;rank<4;++rank) {
        std::ofstream file(output/("native_L20_I9_rank"+std::to_string(rank)+".u32"),std::ios::binary);
        require(bool(file),"gather readback open");
        for(unsigned index=0;index<destination_words;++index) {
            std::optional<uint32_t> word;
            while(!(word=io[rank].read_word(identity,destination_address+index)))tick(true);
            file.write(reinterpret_cast<const char*>(&*word),4);
            // Gather semantics only: compare against the SAME actual operands.
            mismatches+=*word!=input[index/source_words][index%source_words];
        }
        require(bool(file),"gather readback write");
    }
    std::cout<<"GATHER_COMPLETE native_drain_cycle="<<drain_cycle<<" readback_terminal_cycle="<<cycle
             <<" rank_words=1280 mismatches="<<mismatches
             <<" scope=native_I9_native_produced_boundary_imports_NO_fulltoken_or_physical_timing\n";
    require(mismatches==0,"native gather differs from actual four rank source words");
    return 0;
}catch(const std::exception& e){std::cerr<<"GATHER_ERROR "<<e.what()<<'\n';return 1;}
