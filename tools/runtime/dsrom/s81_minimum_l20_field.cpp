// Bounded stage37 I7/I8 consumer of produced SIM_ONLY I0..I6 XN.
// Generated binding header supplies canonical literals/CFG, never activations.
#include "s81_minimum_l20_bank.hpp"
#include "s81_minimum_qe_join.hpp"
#include "l20_field_binding.hpp"
#include <fstream>
#include <filesystem>
#include <cstdio>

namespace {
const char* required(const char* name) {
    auto value=std::getenv(name);
    if(!value||!*value)throw std::runtime_error(std::string("field input missing: ")+name);
    return value;
}
void require(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
}
extern "C" int dsrom_s81_minimum_source_main(DsromS81MinimumRuntime& r,const char* output) {
    using namespace dsrom_s81_minimum;
    require(r.stage==37&&r.rank>=0&&r.rank<4&&r.context,"selected L20 field stage/rank/context");
    constexpr uint64_t id=1ull<<31;
    std::ifstream input(required("DSROM_S81_FIELD_XN"),std::ios::binary);
    std::array<uint32_t,5120> xn{};
    input.read(reinterpret_cast<char*>(xn.data()),sizeof(xn));
    require(input.gcount()==sizeof(xn)&&input.peek()==EOF,"produced I6 XN raw extent");
    auto vm=std::make_shared<Vnative_vm>(r.context,"field_native_vm");
    auto cut=std::make_shared<Vcut>(r.context,"field_static_cut");
    auto actualbank=std::make_shared<DsromS81MinimumL20Bank>(r,id,vm,dsrom_s81_bind_minimum_source_tags(r,id));
    auto& bank=*actualbank;
    auto& pub=bank.publication();auto& io=bank.io();
    pub.enroll_literal(2476,{{46464,5120}});
    struct Dispatch {
        std::array<DsromS81PrefixOperation,2> ops=s81_l20_field_operations();
        unsigned next=0;bool inflight=false,go=false;
    };
    auto dispatch=std::make_shared<Dispatch>();
    const auto& ops=dispatch->ops;
    for(unsigned n=0;n<2;n++)pub.enroll_literal(ops[n].index,{{n?420096u:419776u,n?128u:320u}});
    auto actualactors=std::make_shared<std::vector<std::shared_ptr<DsromS81NativeQe>>>();
    auto& actors=*actualactors;
    std::weak_ptr<DsromS81MinimumL20Bank> prior_bank=actualbank;
    std::weak_ptr<std::vector<std::shared_ptr<DsromS81NativeQe>>> prior_actors=actualactors;
    for(unsigned n=0;n<2;n++) {
        const auto dir=std::string(required("DSROM_S81_FIELD_CONTROLS"))+"/rank"+std::to_string(r.rank)+"/I"+std::to_string(7+n);
        auto bindings=n?s81_native_field_i8_bindings(id,r.rank):s81_native_field_i7_bindings(id,r.rank);
        auto phase=dsrom_s81_qe_load_controls(ops[n],bindings,s81_l20_field_bf_sites(),dir,46464,32768);
        auto reader=dsrom_s81_qe_word_reader(std::stoi(required(n?"DSROM_S81_FIELD_I8_FD":"DSROM_S81_FIELD_I7_FD")));
        actors.push_back(std::make_shared<DsromS81NativeQe>(r,id,pub,io,*cut,std::move(phase),reader,
            [prior_bank,prior_actors,n](){
                auto bank=prior_bank.lock();auto actors=prior_actors.lock();
                require(bool(bank)&&bool(actors),"field prior source owner released");
                return (n?actors->at(0)->complete():bank->publication().complete(2476))&&bank->native_target().mutable_write_drained();}));
    }
    auto actualengine=std::make_shared<DsromS81PrefixNativeEngine>(dsrom_s81_bind_native_qe_field(actors,bank.tags(),bank.visibility()));
    auto& engine=*actualengine;
    auto& next=dispatch->next;auto& inflight=dispatch->inflight;auto& go=dispatch->go;
    r.participants.push_back(bank.bank_participant());
    r.participants.push_back({"canonical full field dispatch",
        [&,dispatch,actualbank,actualactors,actualengine](const auto&){
            r.drive({});go=false;
            if(next==2)return;
            engine.drive(ops[next],false);
            if(inflight&&actors[next]->complete()){inflight=false;++next;}
            if(next<2&&!inflight){go=engine.inputs_ready(ops[next])&&engine.ready();engine.drive(ops[next],go);}
        },
        [&,dispatch,actualbank](bool rn){if(rn&&go){pub.begin(id,ops[next].index);inflight=true;
            printf("FIELD_ACCEPT rank=%d I%u cycle=%ld producer=%u\n",r.rank,7+next,r.cycle(),ops[next].index);fflush(stdout);}},
        [](bool){},[actualbank](){return actualbank->fault();}});
    r.participants.push_back(engine.participant);
    r.participants.push_back({"sole static cut shared clock",
        [cut](const auto&){cut->clk=0;cut->eval();},
        [cut](bool rn){cut->rst_n=rn;cut->clk=1;cut->eval();},
        [cut](bool rn){cut->rst_n=rn;cut->clk=0;cut->eval();},
        [cut](){return bool(cut->fault);}});
    r.publication_ready=[actualbank,id](uint64_t owner){return owner==id&&!actualbank->fault();};
    r.publication_drained=[actualbank,actualengine,cut,id](uint64_t owner){return owner==id&&!actualbank->fault()&&
        actualbank->native_target().mutable_write_drained()&&actualengine->idle()&&cut->idle&&!cut->obs_rows_left;};
    r.cold_start();r.bind_context(id);
    // SIM_ONLY producer import; no native arithmetic/cycle claim for I0..I6.
    // Every imported word still obtains the real source reservation and VM ACK.
    pub.begin(id,2476);
    for(unsigned offset=0;offset<5120;offset+=16){
        S81EmbeddingOutput held{};held.vm_valid=true;held.vm_identity=id;held.vm_address=46464+offset;
        for(unsigned j=0;j<16;j++){
            held.vm_data[j]=xn[offset+j];
            auto command=dsrom_s81_reserve_native_scalar_tag(r,id,2476,held.vm_address+j,held.vm_data[j]);
            pub.native_scalar(2476,command,true);
        }
        while(!io.offer(held,16))r.tick();
        while(!io.visible(held,16))r.tick();
    }
    require(pub.complete(2476)&&io.span_lease(id,46464,5120),"I6 import lacks full native ACK lease");
    printf("FIELD_XN_ACK rank=%d cycle=%ld words=5120 producer=2476\n",r.rank,r.cycle());fflush(stdout);
    while(next<2)r.tick();
    for(unsigned n=0;n<2;n++){
        auto path=std::filesystem::path(output)/(n?"native_L20_I8.u32":"native_L20_I7.u32");
        std::ofstream out(path,std::ios::binary);
        require(bool(out),"native field readback output open");
        const unsigned base=n?420096:419776,count=n?128:320;
        for(unsigned j=0;j<count;j++){
            std::optional<uint32_t> bits;
            while(!(bits=io.read_word(id,base+j)))r.tick();
            out.write(reinterpret_cast<const char*>(&*bits),sizeof(*bits));
        }
        require(bool(out),"native field readback output write");
    }
    require(actors[0]->complete()&&actors[1]->complete()&&r.publication_drained(id),"native full field terminal drain");
    printf("FIELD_COMPLETE rank=%d cycle=%ld I7=320 I8=128 prefix=SIM_ONLY native_readback=448\n",r.rank,r.cycle());fflush(stdout);
    return 0;
}
