// Native stage37 I14 consumer of produced native I13 QR.
// Independent caller snapshot; the live I7/I8 caller remains unchanged.
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
    std::ifstream input(required("DSROM_S81_FIELD_QR"),std::ios::binary);
    std::array<uint32_t,1280> xn{};
    input.read(reinterpret_cast<char*>(xn.data()),sizeof(xn));
    require(input.gcount()==sizeof(xn)&&input.peek()==EOF,"produced native I13 QR raw extent");
    require(setenv("DSROM_S81_NATIVE_L20_QFIELD","1",1)==0,"QFIELD source enrollment");
    auto vm=std::make_shared<Vnative_vm>(r.context,"field_native_vm");
    auto cut=std::make_shared<Vcut>(r.context,"field_static_cut");
    auto actualbank=std::make_shared<DsromS81MinimumL20Bank>(r,id,vm,dsrom_s81_bind_minimum_source_tags(r,id));
    auto& bank=*actualbank;
    auto& pub=bank.publication();auto& io=bank.io();
    pub.enroll_literal(2484,{{52928,1280}});
    struct Dispatch {
        std::array<DsromS81PrefixOperation,1> ops=s81_l20_field_operations();
        unsigned next=0;bool inflight=false,go=false;
    };
    auto dispatch=std::make_shared<Dispatch>();
    const auto& ops=dispatch->ops;
    pub.enroll_literal(ops[0].index,{{s81_qfield_output_base,s81_qfield_output_rows}});
    auto actualactors=std::make_shared<std::vector<std::shared_ptr<DsromS81NativeQe>>>();
    auto& actors=*actualactors;
    std::weak_ptr<DsromS81MinimumL20Bank> prior_bank=actualbank;
    std::weak_ptr<std::vector<std::shared_ptr<DsromS81NativeQe>>> prior_actors=actualactors;
    for(unsigned n=0;n<1;n++) {
        const auto dir=std::string(required("DSROM_S81_FIELD_CONTROLS"))+"/rank"+std::to_string(r.rank)+"/I"+std::to_string(14+n);
        auto bindings=s81_native_field_i14_bindings(id,r.rank);
        auto phase=dsrom_s81_qe_load_controls(ops[n],bindings,s81_l20_field_bf_sites(),dir,52928,32768);
        auto reader=dsrom_s81_qe_word_reader(std::stoi(required("DSROM_S81_FIELD_I14_FD")));
        actors.push_back(std::make_shared<DsromS81NativeQe>(r,id,pub,io,*cut,std::move(phase),reader,
            [prior_bank,prior_actors,n](){
                auto bank=prior_bank.lock();auto actors=prior_actors.lock();
                require(bool(bank)&&bool(actors),"field prior source owner released");
                return bank->publication().complete(2484)&&bank->native_target().mutable_write_drained();}));
    }
    auto actualengine=std::make_shared<DsromS81PrefixNativeEngine>(dsrom_s81_bind_native_qe_field(actors,bank.tags(),bank.visibility()));
    auto& engine=*actualengine;
    auto& next=dispatch->next;auto& inflight=dispatch->inflight;auto& go=dispatch->go;
    r.participants.push_back(bank.bank_participant());
    r.participants.push_back({"canonical full field dispatch",
        [&,dispatch,actualbank,actualactors,actualengine](const auto&){
            r.drive({});go=false;
            if(next==1)return;
            engine.drive(ops[next],false);
            if(inflight&&actors[next]->complete()){inflight=false;++next;}
            if(next<1&&!inflight){go=engine.inputs_ready(ops[next])&&engine.ready();engine.drive(ops[next],go);}
        },
        [&,dispatch,actualbank](bool rn){if(rn&&go){pub.begin(id,ops[next].index);inflight=true;
            printf("FIELD_ACCEPT rank=%d I%u cycle=%ld producer=%u\n",r.rank,14+next,r.cycle(),ops[next].index);fflush(stdout);}},
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
    // Import produced native QR through new actual matched VM ACKs.
    // This boundary import is not a surviving whole-parent source lease.
    // Every imported word still obtains the real source reservation and VM ACK.
    pub.begin(id,2484);
    for(unsigned offset=0;offset<1280;offset+=16){
        S81EmbeddingOutput held{};held.vm_valid=true;held.vm_identity=id;held.vm_address=52928+offset;
        for(unsigned j=0;j<16;j++){
            held.vm_data[j]=xn[offset+j];
            auto command=dsrom_s81_reserve_native_scalar_tag(r,id,2484,held.vm_address+j,held.vm_data[j]);
            pub.native_scalar(2484,command,true);
        }
        while(!io.offer(held,16))r.tick();
        while(!io.visible(held,16))r.tick();
    }
    require(pub.complete(2484)&&io.span_lease(id,52928,1280),"I13 QR import lacks full native ACK lease");
    printf("FIELD_QR_ACK rank=%d cycle=%ld words=1280 producer=2484\n",r.rank,r.cycle());fflush(stdout);
    while(next<1)r.tick();
    for(unsigned n=0;n<1;n++){
        auto path=std::filesystem::path(output)/("native_L20_I14_fragment"+std::to_string(s81_qfield_fragment)+".u32");
        std::ofstream out(path,std::ios::binary);
        require(bool(out),"native field readback output open");
        const unsigned base=s81_qfield_output_base,count=s81_qfield_output_rows;
        for(unsigned j=0;j<count;j++){
            std::optional<uint32_t> bits;
            while(!(bits=io.read_word(id,base+j)))r.tick();
            out.write(reinterpret_cast<const char*>(&*bits),sizeof(*bits));
        }
        require(bool(out),"native field readback output write");
    }
    require(actors[0]->complete()&&r.publication_drained(id),"native full field terminal drain");
    printf("FIELD_COMPLETE rank=%d cycle=%ld I14_fragment=%u output_base=%u words=%u input=native_I13_QR component_not_fulltoken\n",r.rank,r.cycle(),s81_qfield_fragment,s81_qfield_output_base,s81_qfield_output_rows);fflush(stdout);
    return 0;
}
