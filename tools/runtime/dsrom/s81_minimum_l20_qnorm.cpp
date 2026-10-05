// Native I11..I13 consumer of actual I9 QA. Stops before field I14;
// never imports a reference intermediate or repeats the gather/field.
#include "s81_minimum_l20_bank.hpp"
#include "s81_minimum_prefix_providers.hpp"
#include "verilated.h"
#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>

namespace {
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
// Exact demand-r5 canonical L20.I11/I12/I13 literal bodies and catalogue IDs.
const std::array<DsromS81PrefixOperation,3> operations{{
{2482,2,"7970d8c8ed842e252fb2e521efe11b8a08bd96cff55e74c67c25e0786b6da4bb",{0x00000002u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x50000020u,0x00000000u,0xa0000327u,0x00400000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x50000000u,0x00019300u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000003u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u}},
{2483,2,"9c9a074dd15af26528c76fe99944bdf97df4cf9056b632b296bb40e862df1444",{0x00000012u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00800004u,0x00000000u,0x00000326u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x04050140u,0x00000c9au,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x08940000u,0x03c79ca1u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u}},
{2484,2,"2788192194b6f874bfadf950d51d01853a0b54388a4ce449d3d0d74a774029a0",{0x00000012u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x80000004u,0x00000002u,0x00000327u,0x00400000u,0x00000000u,0x00000000u,0x00000c9au,0x00000000u,0x20000000u,0x00000000u,0x08000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x06100040u,0x00000cecu,0x01000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x80000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u}}
}};
}

int main(int argc,char** argv) try {
    require(argc==8,"usage: minimum_qnorm OUTPUT ACTUAL_ID47 QA_RANK0 QA_RANK1 QA_RANK2 QA_RANK3 INITIAL_H_RAW32");
    std::size_t used=0;const uint64_t id=std::stoull(argv[2],&used,0);
    require(used==std::string(argv[2]).size()&&id==(1ull<<31),"actual frozen component identity required");
    const char* crom=std::getenv("DSROM_S81_MINIMUM_CROM_HEX");
    require(crom&&*crom,"actual released L20 CROM required for native I13 q_norm");
    std::array<std::array<uint32_t,1280>,4> qa{};
    for(unsigned rank=0;rank<4;++rank){
        for(unsigned p=0;p<rank;++p)require(!std::filesystem::equivalent(argv[3+rank],argv[3+p]),"four actual rank QA files required");
        std::ifstream file(argv[3+rank],std::ios::binary);require(bool(file),"actual I9 QA missing");
        file.read(reinterpret_cast<char*>(qa[rank].data()),sizeof(qa[rank]));
        require(file.gcount()==sizeof(qa[rank])&&file.peek()==EOF,"QA must contain exactly 1280 raw32 words");
    }
    // Real seeded entering H supplies native SU's unused default VM operands;
    // no constructor zero, derived activation or expected norm is accepted.
    std::array<uint32_t,16> h{};std::ifstream seed(argv[7],std::ios::binary);
    require(bool(seed),"actual initial H fixture missing");
    seed.read(reinterpret_cast<char*>(h.data()),sizeof(h));require(seed.gcount()==sizeof(h),"initial H first16 words missing");
    const std::filesystem::path output(argv[1]);
    require(!std::filesystem::exists(output)||std::filesystem::is_empty(output),"fresh qnorm output required");
    std::filesystem::create_directories(output);
    VerilatedContext context;long cycle=0;
    std::array<DsromS81MinimumRuntime,4> ranks{};
    std::array<std::shared_ptr<Vnative_vm>,4> models;
    std::array<std::shared_ptr<DsromS81MinimumL20Bank>,4> banks;
    std::array<DsromS81PrefixNativeEngine,4> engines;
    std::vector<DsromS81MinimumParticipant> participants;
    require(setenv("DSROM_S81_NATIVE_L20_NORM","1",1)==0,"native norm source enrollment");
    for(unsigned rank=0;rank<4;++rank){
        auto& r=ranks[rank];r.stage=37;r.rank=rank;r.pair=11;r.bf16=true;r.context=&context;
        r.cycle=[&](){return cycle;};r.identity=id;
        models[rank]=std::make_shared<Vnative_vm>(&context,("qnorm_vm_rank"+std::to_string(rank)).c_str());
        banks[rank]=std::make_shared<DsromS81MinimumL20Bank>(r,id,models[rank],dsrom_s81_bind_minimum_source_tags(r,id));
        auto& pub=banks[rank]->publication();pub.enroll_literal(2480,{{51648,1280}});
        pub.enroll_literal(2482,{{51584,8}});pub.enroll_literal(2483,{{51616,1}});pub.enroll_literal(2484,{{52928,1280}});
        participants.push_back(banks[rank]->bank_participant());
        engines[rank]=dsrom_s81_bind_minimum_su256(r,id,pub,banks[rank]->io(),banks[rank]->tags());
        participants.push_back(engines[rank].participant);
    }
    auto tick=[&](bool released){
        for(auto& p:participants)p.prepare({});
        for(auto& p:participants)p.rising(released);
        for(auto& p:participants)p.falling(released);
        ++cycle;for(auto& p:participants)require(!p.fault(),"native qnorm participant fault; no debt clear");
    };
    for(unsigned i=0;i<3;++i)tick(false);
    for(unsigned rank=0;rank<4;++rank){
        auto& bank=*banks[rank];auto& io=bank.io();auto& pub=bank.publication();
        S81EmbeddingOutput seed_batch{};seed_batch.vm_valid=1;seed_batch.vm_identity=id;seed_batch.vm_address=0;
        std::copy(h.begin(),h.end(),seed_batch.vm_data);
        while(!bank.embedding_sink().offer(seed_batch))tick(true);
        while(!bank.embedding_sink().visible(seed_batch))tick(true);
        pub.begin(id,2480);
        for(unsigned offset=0;offset<1280;offset+=16){
            S81EmbeddingOutput batch{};batch.vm_valid=1;batch.vm_identity=id;batch.vm_address=51648+offset;
            for(unsigned lane=0;lane<16;++lane){
                batch.vm_data[lane]=qa[rank][offset+lane];
                auto command=dsrom_s81_reserve_native_scalar_tag(ranks[rank],id,2480,batch.vm_address+lane,batch.vm_data[lane]);
                pub.native_scalar(2480,command,true);
            }
            while(!io.offer(batch,16))tick(true);while(!io.visible(batch,16))tick(true);
        }
        require(pub.complete(id,2480)&&io.span_lease(id,51648,1280),"actual QA import publication incomplete");
        std::cout<<"QA_IMPORT_ACK rank="<<rank<<" cycle="<<cycle<<'\n';
    }
    const std::array<unsigned,3> addresses{51584,51616,52928},counts{8,1,1280};
    for(unsigned stage=0;stage<3;++stage){
        std::array<bool,4> admitted{};
        while(!std::all_of(admitted.begin(),admitted.end(),[](bool v){return v;})){
            for(unsigned rank=0;rank<4;++rank)if(!admitted[rank]&&engines[rank].inputs_ready(operations[stage])&&engines[rank].ready()){
                banks[rank]->publication().begin(id,operations[stage].index);
                engines[rank].drive(operations[stage],true);admitted[rank]=true;
                std::cout<<"SU_ACCEPT I"<<11+stage<<" rank="<<rank<<" cycle="<<cycle<<'\n';
            }
            tick(true);for(auto& engine:engines)engine.drive(operations[stage],false);
        }
        while(!std::all_of(engines.begin(),engines.end(),[](const auto& e){return e.idle();}))tick(true);
        const long drain_cycle=cycle;
        for(unsigned rank=0;rank<4;++rank){
            auto& bank=*banks[rank];require(bank.publication().complete(id,operations[stage].index)&&
                bank.io().span_lease(id,addresses[stage],counts[stage]),"native SU boundary lacks full matched write ACK");
            std::ofstream file(output/("native_L20_I"+std::to_string(11+stage)+"_rank"+std::to_string(rank)+".u32"),std::ios::binary);
            require(bool(file),"native SU readback open");
            for(unsigned word=0;word<counts[stage];++word){
                std::optional<uint32_t> value;while(!(value=bank.io().read_word(id,addresses[stage]+word)))tick(true);
                file.write(reinterpret_cast<const char*>(&*value),4);
            }
            require(bool(file),"native SU readback write");
        }
        std::cout<<"SU_BOUNDARY I"<<11+stage<<" native_drain_cycle="<<drain_cycle<<" readback_cycle="<<cycle<<'\n';
    }
    std::cout<<"QNORM_COMPLETE actual_QA_to_native_I11_I12_I13 ranks=4 QR_words=1280 scope=component_NO_field_I14_or_fulltoken_or_physical_timing\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"QNORM_ERROR "<<e.what()<<'\n';return 1;}
