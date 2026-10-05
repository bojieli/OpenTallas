#pragma once
#include "s81_minimum_prefix.hpp"
#include "s81_published_span_macro_sink.hpp"
#include <unordered_map>
#include <unordered_set>
#include <algorithm>

namespace dsrom_s81_minimum {
// Source-version and raw receipt witness for the minimum stage, NOT new RTL
// queues, a CPU activation producer, or a hardware scoreboard area claim.
// Each command originates at an actual native engine output. Only Popper's
// matched old-head scalar callback establishes publication.
class PrefixPublication {
public:
    static constexpr unsigned SSX=7, PF=8;
private:
    struct Extent {uint32_t base,words;};
    struct Scalar {unsigned producer;MacroWrite command;bool ack=false;};
    uint64_t identity;
    std::unordered_set<unsigned> begun;
    std::unordered_map<unsigned,std::vector<Extent>> literal_extents;
    std::unordered_map<uint32_t,Scalar> scalars;
    std::unordered_map<uint32_t,unsigned> versions;
    bool stopped=false;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    std::vector<Extent> extents(unsigned p) const {
        auto actual=literal_extents.find(p);
        if(actual!=literal_extents.end())return actual->second;
        switch(p) {
        case 0:return {{40992,1}};
        case 1:return {{41024,24}};
        case 2:case 3:return {{20480,5120}};
        case 4:return {{41344,5120},{51584,1}};
        case 5:return {{51616,1}};
        case 6:return {{46464,5120}};
        case SSX:return {{40960,1}};
        case PF:return {{41152,4}};
        default:throw std::runtime_error("unknown native prefix producer");
        }
    }
    bool owns(unsigned p,uint32_t address) const {
        for(auto e:extents(p))if(address>=e.base&&address-e.base<e.words)return true;
        return false;
    }
    static bool same(const MacroWrite& a,const MacroWrite& b) {
        return a.word.address==b.word.address&&a.word.mask==b.word.mask&&
            a.word.owner==b.word.owner&&a.word.data==b.word.data&&
            a.source.identity==b.source.identity&&a.source.phase==b.source.phase&&
            a.source.root==b.source.root&&a.source.position==b.source.position&&
            a.source.row==b.source.row&&a.source.element_address==b.source.element_address;
    }
public:
    explicit PrefixPublication(uint64_t id):identity(id) {
        require(id<(1ull<<47),"prefix publication identity bounds");
    }
    // Literal source-address descriptors only. No payload, acceptance, ACK or
    // authority is created by enrollment; native_scalar still needs an actual
    // admitted writer and complete still requires every matching scalar ACK.
    void enroll_literal(unsigned producer,const std::vector<std::pair<uint32_t,uint32_t>>& ranges) {
        require(!stopped&&producer>=9&&producer<(1u<<14)&&!begun.count(producer)&&
                !literal_extents.count(producer),"duplicate/reserved literal producer index");
        std::vector<Extent> selected;
        for(auto r:ranges) {
            require(r.second&&uint64_t(r.first)+r.second<=(1u<<19),"literal output Address19 extent");
            selected.push_back({r.first,r.second});
        }
        std::sort(selected.begin(),selected.end(),[](auto a,auto b){return a.base<b.base;});
        for(size_t i=1;i<selected.size();++i)
            require(uint64_t(selected[i-1].base)+selected[i-1].words<=selected[i].base,
                    "overlapping literal producer extents");
        literal_extents.emplace(producer,std::move(selected));
    }
    // Call ONLY on real native command acceptance. For I0..I6 the prefix
    // controller invokes this; Peirce invokes SSX/PF on native bootstrap GO.
    // Operand prefetch MUST finish before a rewrite version begins (I3/T).
    void begin(uint64_t id,unsigned producer) {
        try {
            require(!stopped&&id==identity&&producer<(1u<<14)&&!begun.count(producer),
                    "duplicate/foreign prefix producer admission");
            if(producer<7) {
                require(complete(SSX)&&complete(PF),"prefix lacks native bootstrap publication");
                if(producer)require(complete(producer-1),"prefix producer precedes previous publication");
            }
            for(auto e:extents(producer))for(uint32_t a=e.base;a<e.base+e.words;a++) {
                auto old=scalars.find(a);
                require(old==scalars.end()||old->second.ack,"rewrite would erase unacknowledged scalar");
                versions[a]=producer; // old published T version immediately revoked
            }
            begun.insert(producer);
        }catch(...){stopped=true;throw;}
    }
    // The engine bridge samples actual native vm_we/res_we/o_we and supplies
    // its actual source-owned TAG227 command. No declaration creates a scalar.
    void native_scalar(unsigned producer,const MacroWrite& c,bool actual_write) {
        try {
            const auto a=c.source.element_address;const unsigned lane=a&15;
            require(!stopped&&actual_write&&begun.count(producer)&&
                    c.source.identity==identity&&owns(producer,a)&&
                    c.word.address==(a>>4)&&c.word.mask==(uint16_t(1)<<lane)&&
                    !(c.word.owner[7]&~7u)&&c.source.phase<1024&&
                    c.source.root<128&&c.source.position<8,
                    "prefix scalar lacks admitted native writer/address/tag");
            const auto old=scalars.find(a);
            require(old==scalars.end()||
                    (old->second.ack&&old->second.producer!=producer&&
                     old->second.command.word.owner!=c.word.owner),
                    "duplicate native scalar or rewritten address reused old owner");
            scalars.insert_or_assign(a,Scalar{producer,c,false});
        }catch(...){stopped=true;throw;}
    }
    bool write_allowed(uint64_t id,uint32_t address,unsigned words) const {
        if(stopped||id!=identity||!words||words>16||uint64_t(address)+words>(1u<<19))return false;
        std::optional<unsigned> producer;
        for(unsigned n=0;n<words;n++) {
            auto s=scalars.find(address+n);auto v=versions.find(address+n);
            if(s==scalars.end()||v==versions.end()||s->second.ack||
               s->second.producer!=v->second)return false;
            if(producer&&*producer!=s->second.producer)return false;
            producer=s->second.producer;
        }
        return true;
    }
    MacroWrite record(const S81EmbeddingOutput& out,unsigned n) const {
        require(!stopped&&out.vm_valid&&!out.fault&&out.vm_identity==identity&&n<16,
                "prefix record lacks native held payload");
        const auto a=out.vm_address+n;auto s=scalars.find(a);
        require(s!=scalars.end()&&write_allowed(identity,a,1)&&
                s->second.command.word.data[a&15]==out.vm_data[n],
                "prefix payload differs from actual native scalar");
        return s->second.command;
    }
    void on_prefix_scalar_ack(const MacroWrite& c,const VmReceipt& receipt) {
        try {
            auto s=scalars.find(c.source.element_address);
            require(!stopped&&s!=scalars.end()&&!s->second.ack&&same(s->second.command,c)&&
                    c.word.address==receipt.address&&c.word.mask==receipt.mask&&
                    c.word.owner==receipt.owner,
                    "prefix publication lacks unique matched native scalar ACK");
            s->second.ack=true;
        }catch(...){stopped=true;throw;}
    }
    bool source_span_lease(uint64_t id,uint32_t address,unsigned words) const {
        if(stopped||id!=identity||!words||uint64_t(address)+words>(1u<<19))return false;
        for(unsigned n=0;n<words;n++) {
            auto s=scalars.find(address+n);auto v=versions.find(address+n);
            if(s==scalars.end()||v==versions.end()||!s->second.ack||
               s->second.producer!=v->second)return false;
        }
        return true;
    }
    bool complete(unsigned producer) const {
        if(stopped||!begun.count(producer))return false;
        for(auto e:extents(producer))for(uint32_t a=e.base;a<e.base+e.words;a++) {
            auto s=scalars.find(a);
            if(s==scalars.end()||s->second.producer!=producer||!s->second.ack)return false;
        }
        return true;
    }
    bool complete(uint64_t id,unsigned producer) const {
        return id==identity&&complete(producer);
    }
    bool fault() const{return stopped;}
};

// Bind to the ONE PublishedSpanMacroSink used by embedding and native engines.
// Caller constructs it with ledger.source_span_lease/write_allowed/ACK callbacks
// and a Record dispatcher: immutable H record versus ledger.record for prefix.
template<class Model> DsromS81PrefixVm prefix_vm_hooks(
    PrefixPublication& ledger,PublishedSpanMacroSink<Model>& target,
    std::function<std::array<uint32_t,8>(uint64_t,uint32_t)> actual_read_owner) {
    if(!actual_read_owner)throw std::runtime_error("prefix requires actual source read TAG227");
    struct Read {bool active=false;uint64_t id=0;uint32_t address=0,n=0;
                 std::array<uint32_t,16> data{};std::array<uint32_t,8> owner{};};
    auto held=std::make_shared<Read>();
    DsromS81PrefixVm hooks;
    hooks.instruction_accepted=[&ledger](auto id,auto i){ledger.begin(id,i);};
    hooks.cold_inputs_visible=[&ledger,&target](auto id){
        return ledger.complete(PrefixPublication::SSX)&&ledger.complete(PrefixPublication::PF)&&
            target.source_span_lease(id,0,20480)&&target.source_span_lease(id,40960,1)&&
            target.source_span_lease(id,41152,4);
    };
    hooks.outputs_visible=[&ledger](auto id,unsigned i){return ledger.complete(id,i);};
    hooks.fault=[&ledger,&target](){return ledger.fault()||target.fault();};
    hooks.xn_span=[&target,held,actual_read_owner](uint64_t id,uint32_t address)
        ->std::optional<std::array<uint32_t,16>> {
        if(!target.source_span_lease(id,address,16))return std::nullopt;
        if(!held->active) {
            held->active=true;held->id=id;held->address=address;held->n=0;
            held->owner=actual_read_owner(id,address);
        }
        if(id!=held->id||address!=held->address)
            throw std::runtime_error("changed outstanding prefix read span");
        auto word=target.target_word(address+held->n,held->owner);
        if(!word)return std::nullopt;
        held->data[held->n++]=*word; // only actual native target response bits
        if(held->n<16){held->owner=actual_read_owner(id,address+held->n);return std::nullopt;}
        held->active=false;return held->data;
    };
    return hooks;
}
} // namespace dsrom_s81_minimum
