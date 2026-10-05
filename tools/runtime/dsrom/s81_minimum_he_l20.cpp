#include "s81_minimum_he_l20.hpp"
#include "s81_minimum_prefix_io.hpp"
#include "s81_native_he_bootstrap_abi.h"
#include <deque>
#include <string>

namespace {
using namespace dsrom_s81_minimum;
constexpr const char* PIN="b0e6f7c4c4dcb6229b36c29e46d9e1a0b9e898d60f34cf07117fef857b41c319";
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
uint32_t field(const DsromS81PrefixOperation& op,unsigned start,unsigned width) {
    uint32_t value=0;
    for(unsigned b=0;b<width;++b)
        value|=((op.instruction[(start+b)/32]>>((start+b)%32))&1u)<<b;
    return value;
}
struct Source {
    DsromS81MinimumRuntime& runtime;uint64_t identity;
    PrefixPublication& publication;DsromS81MinimumSourceIo io;
    std::function<bool()> entry_complete;
    std::array<DsromS81PrefixOperation,2> ops;
    DsromS81MinimumL20HeWordRead weights;
    DsromS81MinimumOperandSpan<256> span;
    DsromS81MinimumPrefixOutputBatch batch;
    void* leaf=nullptr;
    S81NativeHeBootstrapInput input{};
    S81NativeHeBootstrapOutput output{};
    std::array<uint32_t,20480> h{};
    std::array<uint32_t,64> w_delay{};
    std::array<uint32_t,8> x_delay{};
    struct Pending {S81EmbeddingOutput out{};bool captured=false;};
    std::deque<Pending> pending;
    int selected=-1;
    unsigned h_count=0,outputs=0;
    bool reset_seen=false,accepted=false,stopped=false;
    Source(DsromS81MinimumRuntime& r,uint64_t id,PrefixPublication& p,
           const DsromS81MinimumSourceIo& i,const DsromS81MinimumSourceTags& t,
           std::function<bool()> entry,const std::array<DsromS81PrefixOperation,2>& actual,
           DsromS81MinimumL20HeWordRead read):runtime(r),identity(id),publication(p),io(i),
           entry_complete(std::move(entry)),ops(actual),weights(std::move(read)),
           span(id,i),batch(r,id,p,i,t) {
        require(id<(1ull<<47)&&entry_complete&&weights&&ops[0].index!=ops[1].index,
                "L20 HE requires actual entry, distinct source producers and released reader");
        for(auto& op:ops) {
            require(op.unit==5&&op.template_sha256&&std::string(op.template_sha256)==PIN&&
                    op.index<(1u<<14)&&field(op,1563,21)==24&&field(op,1584,21)==2560&&
                    field(op,1605,30)==0&&field(op,1635,30)==0&&field(op,1665,30)==41024&&
                    field(op,1723,3)==0&&field(op,1726,30)==0&&field(op,1756,30)==0,
                    "L20 HE literal/source binding differs from I1/I78 recipe");
            op.template_sha256=PIN; // retain the validated pin beyond caller lifetime
        }
        leaf=s81_native_he_bootstrap_create();
        require(leaf!=nullptr,"existing native HE leaf unavailable");
    }
    ~Source(){if(leaf)s81_native_he_bootstrap_destroy(leaf);}
    bool fault() const {
        return stopped||output.he_fault||output.ssx_fault||publication.fault()||span.fault()||batch.fault();
    }
    bool cold() const {
        return runtime.identity&&*runtime.identity==identity&&entry_complete()&&
            io.span_lease(identity,0,20480)&&io.span_lease(identity,40960,1)&&
            io.span_lease(identity,41152,4);
    }
    bool idle() const {
        return !fault()&&output.he_idle&&pending.empty()&&!batch.pending()&&
            (selected<0||(accepted&&outputs==24&&publication.complete(identity,ops[selected].index)));
    }
    bool ready() const {
        return !fault()&&reset_seen&&cold()&&selected>=0&&!accepted&&h_count==20480&&
            output.he_ready&&pending.empty()&&!batch.pending();
    }
    unsigned select(const DsromS81PrefixOperation& op) const {
        for(unsigned n=0;n<2;++n)
            if(op.unit==ops[n].unit&&op.index==ops[n].index&&op.template_sha256&&
               std::string(op.template_sha256)==PIN&&op.instruction==ops[n].instruction)return n;
        throw std::runtime_error("L20 HE request not source-mapped I1/I78");
    }
    bool inputs(const DsromS81PrefixOperation& op) {
        try {
            require(!fault(),"L20 HE operand admission quarantined");
            const unsigned next=select(op);
            if(!reset_seen||!cold())return false;
            if(selected>=0&&accepted) {
                if(!idle())return false;
                require(next!=unsigned(selected),"L20 HE producer reissued without source retirement");
                selected=-1;h_count=0;outputs=0;accepted=false;
            }
            if(selected<0){selected=int(next);h_count=0;outputs=0;}
            require(unsigned(selected)==next,"changed held L20 HE operation");
            if(h_count<20480) {
                auto raw=span.poll(identity,h_count);
                if(raw){std::copy(raw->begin(),raw->end(),h.begin()+h_count);h_count+=256;}
            }
            return h_count==20480;
        }catch(...){stopped=true;throw;}
    }
    void drive(const DsromS81PrefixOperation& op,bool go) {
        try {
            input.he_go=go;
            if(!go)return; // Prefix withdraws every engine GO before selection
            require(ready()&&select(op)==unsigned(selected),"L20 HE GO lacks actual operands/native readiness");
            input.he_nout=field(op,1563,21);input.he_k=field(op,1584,21);
            input.he_wbase=field(op,1605,30);input.he_xbase=field(op,1635,30);
            input.he_obase=field(op,1665,30);input.he_m=field(op,1723,3);
            input.he_xps=field(op,1726,30);input.he_ops=field(op,1756,30);
        }catch(...){stopped=true;throw;}
    }
    void prepare() {
        try {
            require(!fault(),"L20 HE publication/source quarantined");
            if(output.he_o_we) {
                require(accepted&&selected>=0&&output.he_o_mask==1&&outputs<24&&
                        output.he_o_addr==41024+outputs&&pending.size()<32,
                        "L20 HE native output lacks admitted ordered writer");
                Pending p;p.out.vm_valid=1;p.out.vm_identity=identity;
                p.out.vm_address=output.he_o_addr;p.out.vm_data[0]=output.he_o_data[0];
                pending.push_back(p);++outputs;
            }
            if(!pending.empty()) {
                auto& p=pending.front();
                if(!p.captured){batch.capture(ops[selected].index,p.out,1,true);p.captured=true;}
                if(batch.progress())pending.pop_front(); // SAME matching VM ACK only
            }
            std::copy(w_delay.begin(),w_delay.end(),input.he_w_data);
            std::copy(x_delay.begin(),x_delay.end(),input.he_x_q);
            // Original fixed pipeline: registered request -> staging -> input,
            // two source edges. Refresh H before EACH GO; no cached L0/L20 H.
            for(unsigned bank=0;bank<8;++bank) {
                if(output.he_w_re&(1u<<bank)) {
                    require(selected>=0&&accepted,"L20 HE weight request without accepted op");
                    const uint64_t line=uint64_t(output.he_w_addr[bank])*8+bank;
                    require(line<61440,"L20 HE weight word outside released tensor");
                    auto word=weights(selected==1,line);
                    std::copy(word.begin(),word.end(),w_delay.begin()+bank*8);
                }
                if(output.he_x_re&(1u<<bank)) {
                    const auto a=output.he_x_addr[bank];
                    require(accepted&&h_count==20480&&a<h_count&&io.span_lease(identity,a,1),
                            "L20 HE native input lacks current H lease");
                    x_delay[bank]=h[a];
                }
            }
        }catch(...){stopped=true;throw;}
    }
    void rise(bool released) {
        try {
            if(!released) {
                require(!runtime.identity&&selected<0&&pending.empty()&&!accepted,
                        "L20 HE reset would erase admitted source/publication debt");
                reset_seen=true;
            }else if(input.he_go) {
                require(ready(),"L20 HE old-edge GO lacks native ready");
                accepted=true;
            }
            input.reset_n=released;
            s81_native_he_bootstrap_rise(leaf,&input,&output);
        }catch(...){stopped=true;throw;}
    }
    void fall(bool released) {
        try {
            require(!fault()&&(released||!runtime.identity),"L20 HE fall/reset violates accepted context");
            input.reset_n=released;s81_native_he_bootstrap_fall(leaf,&input,&output);
        }catch(...){stopped=true;throw;}
    }
};
}

DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_he_l20(
    DsromS81MinimumRuntime& runtime,uint64_t id,PrefixPublication& publication,
    const DsromS81MinimumSourceIo& io,const DsromS81MinimumSourceTags& tags,
    std::function<bool()> entry,const std::array<DsromS81PrefixOperation,2>& ops,
    DsromS81MinimumL20HeWordRead weights) {
    auto s=std::make_shared<Source>(runtime,id,publication,io,tags,std::move(entry),ops,std::move(weights));
    DsromS81PrefixNativeEngine e;
    e.participant={"native L20 HE I1/I78 existing ABI",
        [s](const auto&){s->prepare();},[s](bool r){s->rise(r);},[s](bool r){s->fall(r);},[s](){return s->fault();}};
    e.ready=[s](){return s->ready();};e.idle=[s](){return s->idle();};
    e.inputs_ready=[s](const auto& op){return s->inputs(op);};
    e.drive=[s](const auto& op,bool go){s->drive(op,go);};
    return e;
}
