#pragma once
#include "s81_minimum_prefix_io.hpp"
#include <deque>
#include <memory>
#include <cstring>
#include <bitset>

// Source-only I44 adapter for the already-built rank scorer. BackendJoin wires
// Maxwell's active NativeIndexHbm B ports; its participant owns those clocks.
// Query/WTS staging is 4128 actual VM words, read under leases before GO. Score
// writes use the native word-address/mask/raw BF16-in-U32 ports and the SAME
// SourceTags/publication bank. No query encoding, score math or HBM response.
template<class Leaf> class DsromS81IndexSourceL20 {
public:
    using Dynamic=std::function<std::optional<uint32_t>(unsigned)>;
    using BackendJoin=std::function<void(Leaf&)>;
private:
    DsromS81MinimumRuntime& runtime;uint64_t identity;
    dsrom_s81_minimum::PrefixPublication& pub;DsromS81MinimumSourceIo io;
    std::shared_ptr<Leaf> leaf;DsromS81PrefixOperation source;
    Dynamic dynamic;BackendJoin backend_join;std::function<bool()> history_current_visible;
    std::array<uint32_t,4128> operands{};unsigned fetched=0;
    uint32_t query=0,weights=0,score_base=0;
    bool prepared=false,accepted=false,stopped=false,offered=false;
    uint32_t captured=0;
    std::bitset<262144> score_seen;
    bool wbase_is_relative;
    std::deque<S81EmbeddingOutput> pending;
    uint64_t request_bytes=0,response_bytes=0;
    static void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
    static uint32_t field(const DsromS81PrefixOperation& o,unsigned off,unsigned width) {
        uint32_t v=0;for(unsigned b=0;b<width;++b)v|=((o.instruction[(off+b)/32]>>((off+b)%32))&1u)<<b;
        return v;
    }
    template<class Wide> static uint32_t bits(const Wide& p,unsigned off,unsigned width) {
        uint32_t v=0;for(unsigned b=0;b<width;++b)v|=((p[(off+b)/32]>>((off+b)%32))&1u)<<b;
        return v;
    }
    bool same(const DsromS81PrefixOperation& o)const {
        return o.index==source.index&&o.unit==source.unit&&o.instruction==source.instruction&&
            o.template_sha256&&source.template_sha256&&!std::strcmp(o.template_sha256,source.template_sha256);
    }
    uint32_t resolved(unsigned off,unsigned width,unsigned selector) {
        uint64_t value=field(source,off,width);const auto d=field(source,selector,6);
        if(d){auto x=dynamic(d);require(bool(x),"index dynamic source not captured");value+=*x;}
        require(value<(1ull<<width),"index actual field narrowing");return uint32_t(value);
    }
    bool input_leases()const{return io.span_lease(identity,query,4096)&&io.span_lease(identity,weights,32);}
    uint32_t read(uint32_t a)const {
        require(input_leases(),"index query/WTS version revoked");
        if(a>=query&&uint64_t(a)-query<4096)return operands[a-query];
        if(a>=weights&&uint64_t(a)-weights<32)return operands[4096+a-weights];
        throw std::runtime_error("native index query read outside actual source spans");
    }
    void capture(uint32_t a,uint32_t value) {
        require(accepted&&a>=score_base&&uint64_t(a)-score_base<262144&&captured<262144&&
                !score_seen.test(a-score_base)&&(value&0xffffu)==0,
                "native index score address/order/count/format mismatch");
        score_seen.set(a-score_base);++captured;S81EmbeddingOutput out{};out.vm_valid=true;out.vm_identity=identity;
        out.vm_address=a;out.vm_data[0]=value;
        auto command=dsrom_s81_reserve_native_scalar_tag(runtime,identity,source.index,a,value);
        pub.native_scalar(source.index,command,true);pending.push_back(out);
    }
public:
    DsromS81IndexSourceL20(DsromS81MinimumRuntime& r,uint64_t id,
        dsrom_s81_minimum::PrefixPublication& publication,DsromS81MinimumSourceIo actual_io,
        std::shared_ptr<Leaf> actual_scorer,DsromS81PrefixOperation actual_I44,
        Dynamic captured_dynamic,BackendJoin actual_backend_join,std::function<bool()> positive_current_key,
        bool source_wbase_is_region_offset)
    :runtime(r),identity(id),pub(publication),io(std::move(actual_io)),leaf(std::move(actual_scorer)),
     source(actual_I44),dynamic(std::move(captured_dynamic)),backend_join(std::move(actual_backend_join)),
     history_current_visible(std::move(positive_current_key)),wbase_is_relative(source_wbase_is_region_offset) {
        require(leaf&&r.context&&leaf->contextp()==r.context&&r.cycle&&id<(1ull<<47)&&
                io.read_word&&io.span_lease&&io.offer&&io.visible&&dynamic&&backend_join&&history_current_visible,
                "index requires actual source VM, positive current key and active 128PC backend");
        leaf->clk=0;leaf->rst_n=0;leaf->go=0;
    }
    bool inputs_ready(const DsromS81PrefixOperation& o) {
        try {
            require(!fault()&&same(o)&&o.unit==1&&field(o,0,3)==1,"index requires exact selected I44");
            if(accepted)return false;
            if(!prepared) {
                leaf->i_nout=resolved(11,21,276);leaf->i_k=resolved(53,21,288);
                const auto actual_wbase=resolved(75,30,258);
                // Canonical IK region-offset zero requires an EXPLICIT source
                // namespace declaration; absolute native ISA is left unchanged.
                require(!wbase_is_relative||actual_wbase==0,"index source region offset changed");
                leaf->i_wbase=wbase_is_relative?0x1000000:actual_wbase;leaf->i_xbase=resolved(195,30,264);
                leaf->i_obase=resolved(226,30,270);leaf->i_wts=field(o,1796,30);
                leaf->i_xks=field(o,294,30);leaf->i_xjs=field(o,324,30);leaf->i_xcs=field(o,420,30);
                leaf->i_hg=field(o,450,2);leaf->i_round=field(o,225,1);
                leaf->i_mmode=field(o,417,1);leaf->i_oen=field(o,256,1);leaf->i_fuse=field(o,1795,1);
                leaf->cfg_ik_base=0x1000000;leaf->i_user_base_sec=0;
                require(leaf->i_nout==262144&&leaf->i_k==128&&leaf->i_wbase==0x1000000&&
                        leaf->i_xbase==98720&&leaf->i_obase==6430&&leaf->i_wts==102848&&
                        leaf->i_xks==1&&leaf->i_xjs==128&&leaf->i_xcs==1024&&leaf->i_hg==2&&
                        leaf->i_round&&leaf->i_mmode&&leaf->i_oen&&leaf->i_fuse,
                        "index effective I44 ports differ from source-selected RING region0");
                query=leaf->i_xbase;weights=leaf->i_wts;score_base=leaf->i_obase*16;
                prepared=true;
            }
            if(!history_current_visible()||!input_leases())return false;
            if(fetched<operands.size()) {
                const auto a=fetched<4096?query+fetched:weights+fetched-4096;
                auto value=io.read_word(identity,a);if(!value)return false;
                operands[fetched++]=*value;
            }
            return fetched==operands.size()&&leaf->ready;
        }catch(...){stopped=true;throw;}
    }
    void drive(const DsromS81PrefixOperation& o,bool go) {
        leaf->go=0;
        try {
        if(go)require(!fault()&&same(o)&&!accepted&&prepared&&fetched==operands.size()&&
            runtime.identity&&*runtime.identity==identity&&input_leases()&&history_current_visible(),
            "index GO before actual query/history/current-key visibility");
        if(go)require(resolved(11,21,276)==leaf->i_nout&&resolved(53,21,288)==leaf->i_k&&
            resolved(195,30,264)==query&&resolved(226,30,270)==leaf->i_obase&&
            resolved(75,30,258)==(wbase_is_relative?0:leaf->i_wbase),
            "index captured dynamic context changed before GO");
        leaf->go=go;
        }catch(...){stopped=true;throw;}
    }
    void prepare(const DsromS81PairResult&) {
        try {
            require(!fault(),"index source/publication fault");backend_join(*leaf);
            if(!pending.empty()) {
                if(!offered)offered=io.offer(pending.front(),1);
                if(offered&&io.visible(pending.front(),1)){pending.pop_front();offered=false;}
            }
            if(accepted&&leaf->idle&&pending.empty()&&pub.complete(identity,source.index)) {
                require(captured==262144,"index drain missing actual source scores");accepted=false;
            }
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(released||(!accepted&&pending.empty()),"index reset would erase source debt");
            std::array<uint32_t,8> q{};for(unsigned j=0;j<8;++j)q[j]=leaf->x_q[j];
            if(released) {
                if(leaf->go&&leaf->ready){require(prepared&&fetched==operands.size(),"index unprepared accept");accepted=true;}
                for(unsigned j=0;j<8;++j)if((leaf->x_re>>j)&1u)q[j]=read(bits(leaf->x_addr,30*j,30));
                for(unsigned pc=0;pc<128;++pc) {
                    if(bits(leaf->h_req_v,pc,1)&&bits(leaf->h_req_rdy,pc,1)) {
                        auto len=bits(leaf->h_req_len,pc*4,4);require(len>0,"index zero-length accepted request");
                        request_bytes+=uint64_t(len)*32;
                    }
                    if(bits(leaf->h_rsp_v,pc,1)&&bits(leaf->h_rsp_rdy,pc,1))response_bytes+=32;
                }
            }
            leaf->rst_n=released;leaf->clk=1;leaf->eval();
            for(unsigned j=0;j<8;++j)leaf->x_q[j]=q[j]; // registered memory response AFTER edge
            if(released) {
                require(!leaf->fault,"actual native index fault");
                for(unsigned port=0;port<8;++port)if((leaf->o_we>>port)&1u) {
                    const auto word=bits(leaf->o_addr,30*port,30);
                    for(unsigned lane=0;lane<16;++lane)if(bits(leaf->o_mask,16*port+lane,1))
                        capture(word*16+lane,leaf->o_data[16*port+lane]);
                }
            }
        }catch(...){stopped=true;throw;}
    }
    void falling(bool r){leaf->rst_n=r;leaf->clk=0;leaf->eval();}
    bool fault()const{return stopped||leaf->fault||pub.fault();}
    bool ready()const{return !fault()&&!accepted&&leaf->ready;}
    bool idle()const{return !fault()&&!accepted&&pending.empty()&&leaf->idle;}
    uint64_t accepted_request_bytes()const{return request_bytes;}
    uint64_t accepted_response_bytes()const{return response_bytes;}
};

template<class Leaf> DsromS81PrefixNativeEngine dsrom_s81_bind_index_source_l20(
    std::shared_ptr<DsromS81IndexSourceL20<Leaf>> p) {
    return {{"native-L20-I44-index-source",[p](const auto& r){p->prepare(r);},
        [p](bool r){p->rising(r);},[p](bool r){p->falling(r);},[p]{return p->fault();}},
        [p]{return p->ready();},[p]{return p->idle();},
        [p](const auto& o){return p->inputs_ready(o);},[p](const auto& o,bool go){p->drive(o,go);}};
}
