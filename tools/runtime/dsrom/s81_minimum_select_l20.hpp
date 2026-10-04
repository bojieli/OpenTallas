#pragma once
#include "s81_minimum_prefix_io.hpp"
#include <deque>
#include <memory>
#include <cstring>
#include <set>

// Source-selected I45/I50/I93; the arithmetic and comparisons remain entirely
// in the existing xu_adapt model. Staging contains ONLY actual SourceIo reads
// under retained producer leases, including native scorer outputs. It supports
// the source's replay reads; no reference values, FP decoding or host top-k.
// Instantiate against the actual SK512 or SK2048 generated library, once per
// rank, and let PrefixNativeEngine own its clock (never register twice).
template<class Leaf,unsigned Capacity> class DsromS81SelectL20 {
    static_assert(Capacity==512||Capacity==2048,"source-selected native capacity");
public:
    using Dynamic=std::function<std::optional<uint32_t>(const DsromS81PrefixOperation&,unsigned)>;
    using Published=std::function<void(const DsromS81PrefixOperation&,const std::vector<uint32_t>&)>;
private:
    DsromS81MinimumRuntime& runtime;
    uint64_t identity;
    dsrom_s81_minimum::PrefixPublication& publication;
    DsromS81MinimumSourceIo io;
    std::shared_ptr<Leaf> leaf;
    std::array<DsromS81PrefixOperation,3> selected;
    Dynamic dynamic;
    Published published;
    std::optional<DsromS81PrefixOperation> op;
    uint32_t src=0,dst=0,n=0,k=0;
    bool bf16=false,accepted=false,stopped=false,offered=false,notified=false;
    size_t fetched=0;
    std::vector<uint32_t> operands,ids;
    std::set<uint32_t> unique;
    std::deque<S81EmbeddingOutput> pending;
    static void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
    static uint32_t field(const DsromS81PrefixOperation& o,unsigned off,unsigned count) {
        uint32_t v=0;for(unsigned b=0;b<count;++b)
            v|=((o.instruction[(off+b)/32]>>((off+b)%32))&1u)<<b;
        return v;
    }
    template<class Wide> static uint32_t bits(const Wide& p,unsigned off,unsigned width) {
        uint32_t v=0;for(unsigned b=0;b<width;++b)
            v|=((p[(off+b)/32]>>((off+b)%32))&1u)<<b;
        return v;
    }
    static bool same(const DsromS81PrefixOperation& a,const DsromS81PrefixOperation& b) {
        return a.index==b.index&&a.unit==b.unit&&a.instruction==b.instruction&&
            a.template_sha256&&b.template_sha256&&!std::strcmp(a.template_sha256,b.template_sha256);
    }
    uint32_t effective(const DsromS81PrefixOperation& o,unsigned literal,unsigned width,unsigned selector) {
        uint64_t v=field(o,literal,width);const auto d=field(o,selector,6);
        if(d){auto x=dynamic(o,d);require(bool(x),"SELECT dynamic source not captured");v+=*x;}
        require(v<(1ull<<width),"SELECT effective native field truncation");return uint32_t(v);
    }
    uint32_t read(uint32_t a)const {
        require(op&&io.span_lease(identity,src,n),"SELECT actual input version revoked");
        require(a>=src&&uint64_t(a)-src<operands.size(),"SELECT read outside actual operand lease");
        return operands[a-src];
    }
    void capture(uint32_t a,uint32_t raw_id) {
        require(accepted&&op&&a==dst+ids.size()&&ids.size()<k&&raw_id<n,
                "SELECT native raw ID/address/count outside source contract");
        require(unique.insert(raw_id).second,"duplicate native SELECT ID");
        ids.push_back(raw_id);
        S81EmbeddingOutput value{};value.vm_valid=true;value.vm_identity=identity;
        value.vm_address=a;value.vm_data[0]=raw_id;
        auto command=dsrom_s81_reserve_native_scalar_tag(runtime,identity,op->index,a,raw_id);
        publication.native_scalar(op->index,command,true);pending.push_back(value);
    }
public:
    DsromS81SelectL20(DsromS81MinimumRuntime& r,uint64_t id,
        dsrom_s81_minimum::PrefixPublication& pub,DsromS81MinimumSourceIo source,
        std::shared_ptr<Leaf> native,std::array<DsromS81PrefixOperation,3> actual_ops,
        Dynamic captured_dynamic,Published positive_published={})
    :runtime(r),identity(id),publication(pub),io(std::move(source)),leaf(std::move(native)),
     selected(std::move(actual_ops)),dynamic(std::move(captured_dynamic)),published(std::move(positive_published)) {
        require(leaf&&r.context&&leaf->contextp()==r.context&&r.cycle&&id<(1ull<<47)&&
                io.read_word&&io.span_lease&&io.offer&&io.visible&&dynamic,
                "SELECT requires actual native model, captured source and same VM publication");
        leaf->clk=0;leaf->rst_n=0;leaf->go=0;leaf->rst_v=0;leaf->prime_v=0;
        leaf->rst_slot=0;leaf->prime_first=0;leaf->prime_cid=0;
        leaf->token=0;leaf->first=0;leaf->i_hslot=0;
        leaf->vr_q=0;leaf->cr_q=0;
        for(unsigned j=0;j<32;++j)leaf->xr_q[j]=0;
        for(unsigned j=0;j<64;++j)leaf->vsl_q[j]=0;
        for(unsigned j=0;j<9;++j)leaf->er_q[j]=0;
    }
    bool inputs_ready(const DsromS81PrefixOperation& o) {
        try {
            require(!fault(),"SELECT quarantined; source debt retained");
            if(accepted)return false;
            if(!op||!same(*op,o)) {
                require(leaf->idle&&pending.empty(),"SELECT source switch before drain");
                unsigned which=3;for(unsigned j=0;j<3;++j)if(same(selected[j],o))which=j;
                require(which<3&&o.unit==4&&field(o,0,3)==4&&field(o,1455,2)==0,
                        "SELECT requires exact source-selected I45/I50/I93");
                src=field(o,1457,30);dst=field(o,1487,30);
                n=effective(o,1517,21,1538);k=effective(o,1544,12,1556);
                bf16=field(o,1538,6)!=0; // exact core xu_bf16 predicate
                require((which==0&&src==102880&&dst==365024&&n==262144&&k==512&&bf16)||
                        (which==1&&src==447872&&dst==480672&&n==32768&&k==2048&&bf16)||
                        (which==2&&src==366304&&dst==366688&&n==384&&k==6&&!bf16),
                        "SELECT effective operands differ from actual L20 source");
                require(!bf16||k<=Capacity,"SELECT native SK capacity would truncate runtime K");
                require(uint64_t(src)+n<=(1u<<19)&&uint64_t(dst)+k<=(1u<<19),
                        "SELECT VM19 operand/output alias");
                if(!io.span_lease(identity,src,n))return false;
                op=o;operands.assign(n,0);fetched=0;ids.clear();unique.clear();notified=false;
                leaf->i_op=0;leaf->i_src=src;leaf->i_dst=dst;leaf->i_n=n;leaf->i_k=k;
                leaf->i_layer=field(o,1562,1);leaf->i_bf16=bf16;
            }
            require(io.span_lease(identity,src,n),"SELECT prefetch lost actual source lease");
            if(fetched<operands.size()) {
                auto value=io.read_word(identity,src+fetched);if(!value)return false;
                operands[fetched++]=*value;
            }
            return fetched==operands.size();
        }catch(...){stopped=true;throw;}
    }
    void drive(const DsromS81PrefixOperation& o,bool go) {
        leaf->go=0;
        try {
        if(go)require(!fault()&&op&&same(*op,o)&&!accepted&&fetched==operands.size()&&
                runtime.identity&&*runtime.identity==identity&&io.span_lease(identity,src,n),
                "SELECT GO before actual source readiness");
        if(go)require(effective(o,1517,21,1538)==n&&effective(o,1544,12,1556)==k,
                "SELECT captured dynamic context changed before GO");
        leaf->go=go;
        }catch(...){stopped=true;throw;}
    }
    void prepare(const DsromS81PairResult&) {
        try {
            require(!fault(),"SELECT native/publication fault");
            if(!pending.empty()) {
                if(!offered)offered=io.offer(pending.front(),1);
                if(offered&&io.visible(pending.front(),1)){pending.pop_front();offered=false;}
            }
            if(accepted&&leaf->idle&&pending.empty()) {
                require(ids.size()==k,"SELECT native drain lacks its exact output count");
                if(publication.complete(identity,op->index)) {
                    if(published&&!notified){published(*op,ids);notified=true;}
                    accepted=false;
                }
            }
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(released||(!accepted&&pending.empty()),"SELECT reset would erase actual debt");
            const bool accept=released&&leaf->go&&leaf->ready;
            uint32_t scalar=leaf->vr_q;std::array<uint32_t,64> vector{};
            for(unsigned j=0;j<64;++j)vector[j]=leaf->vsl_q[j];
            if(released) {
                if(leaf->vr_re)scalar=read(leaf->vr_addr);
                for(unsigned q=0;q<4;++q)if((leaf->vsl_re>>q)&1u) {
                    const uint32_t a=bits(leaf->vsl_addr,30*q,30);
                    require(a>=src&&uint64_t(a)<uint64_t(src)+n&&((a-src)%16)==0,
                            "SELECT native vector read outside source-aligned span");
                    for(unsigned lane=0;lane<16;++lane) {
                        // Only source-masked tail lanes may be absent. No active
                        // operand is substituted with zero or an expected value.
                        const uint64_t x=uint64_t(a)+lane;
                        vector[16*q+lane]=x<uint64_t(src)+n?read(uint32_t(x)):0;
                    }
                }
                require(!leaf->xr_re&&!leaf->cr_re&&!leaf->er_re,
                        "SELECT requested unbound non-SELECT memory");
            }
            if(accept){require(op&&fetched==operands.size(),"SELECT unprepared actual accept");accepted=true;}
            leaf->rst_n=released;leaf->clk=1;leaf->eval(); // OLD memory Q at this edge
            leaf->vr_q=scalar;for(unsigned j=0;j<64;++j)leaf->vsl_q[j]=vector[j];
            if(released) {
                require(!leaf->fault,"actual SELECT native fault");
                if(leaf->vw_we)capture(leaf->vw_addr,leaf->vw_data); // RAW U32 IDs, never FP decode
                if(leaf->w_we)for(unsigned lane=0;lane<32;++lane)
                    if((leaf->w_mask>>lane)&1u)capture(leaf->w_addr+lane,leaf->w_data[lane]);
            }
        }catch(...){stopped=true;throw;}
    }
    void falling(bool released){leaf->rst_n=released;leaf->clk=0;leaf->eval();}
    bool fault()const{return stopped||leaf->fault||publication.fault();}
    bool ready()const{return !fault()&&!accepted&&leaf->ready;}
    bool idle()const{return !fault()&&!accepted&&pending.empty()&&leaf->idle;}
};

template<class Leaf,unsigned Capacity>
DsromS81PrefixNativeEngine dsrom_s81_bind_select_l20(
    std::shared_ptr<DsromS81SelectL20<Leaf,Capacity>> p) {
    return {{"native-L20-source-SELECT",[p](const auto& r){p->prepare(r);},
        [p](bool r){p->rising(r);},[p](bool r){p->falling(r);},[p]{return p->fault();}},
        [p]{return p->ready();},[p]{return p->idle();},
        [p](const auto& o){return p->inputs_ready(o);},[p](const auto& o,bool go){p->drive(o,go);}};
}
