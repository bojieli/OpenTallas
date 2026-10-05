#pragma once
#include "s81_minimum_macro_ack_adapter.hpp"
#include "s81_minimum_embedding.hpp"
#include <algorithm>
#include <bitset>

namespace dsrom_s81_minimum {
// Additive successor to the embedding-only port binder; historical65e43 is
// unchanged. Source callback eligibility is REQUIRED and must represent actual
// native producer spans/versions and matched ACKs, not declarations alone.
// No new RTL/capture seats or a whole-field certificate.
// The source caller supplies its actual tag/provenance encoder. Payloads always
// come from the native embedding reader, and reads from the native target VM.
template<class Model> class PublishedSpanMacroSink {
public:
    using Record=std::function<MacroWrite(const S81EmbeddingOutput&,unsigned)>;
    using Owner=std::array<uint32_t,8>;
    using SpanLease=std::function<bool(uint64_t,uint32_t,unsigned)>;
    using ScalarAck=std::function<void(const MacroWrite&,const VmReceipt&)>;
private:
    Model& model;
    const uint64_t identity;
    const uint32_t base;
    Record record;
    SpanLease prefix_source_lease,prefix_write_allowed;
    ScalarAck on_prefix_scalar_ack;
    // Fixed64KiB software receipt witness, NOT a hardware scoreboard price.
    // A source callback alone can NEVER make an unwritten address eligible.
    std::bitset<(1u<<19)> prefix_acked;
    unsigned count=16;
    uint16_t required=65535;
    bool prefix_batch=false;
    S81EmbeddingOutput held{};
    std::array<MacroWrite,16> writes{};
    uint16_t accepted=0,acked=0;
    uint32_t published=0;
    bool active=false,reported=false,stopped=false;
    MacroAckAdapter<Model> backend;
    DsromS81MinimumParticipant write_ports;
    uint64_t edge=0,read_edge=0;
    bool read_pending=false,read_accepted=false,read_done=false;
    uint32_t read_address=0,read_bits=0;
    Owner read_owner{};
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    static bool same(const S81EmbeddingOutput& a,const S81EmbeddingOutput& b) {
        return a.vm_identity==b.vm_identity&&a.vm_address==b.vm_address&&
            std::equal(std::begin(a.vm_data),std::end(a.vm_data),std::begin(b.vm_data));
    }
    unsigned lane(const MacroWrite& c) const {
        require(active&&c.source.identity==identity&&
                c.source.element_address>=held.vm_address&&
                c.source.element_address<held.vm_address+count,"receipt outside held embedding batch");
        const unsigned n=c.source.element_address-held.vm_address;
        const auto& w=writes[n].word;
        require(c.word.owner==w.owner&&c.word.address==w.address&&c.word.mask==w.mask&&
                c.word.data==w.data,"embedding receipt changed retained native command");
        return n;
    }
    typename MacroAckAdapter<Model>::Commands commands() const {
        typename MacroAckAdapter<Model>::Commands out{};
        if(!active||read_pending)return out;
        for(unsigned n=0;n<count;n++)if(!(accepted&(1u<<n))) {
            const unsigned b=writes[n].word.address&3;
            if(!out[b])out[b]=writes[n]; // one actual bank command per edge
        }
        return out;
    }
    void took(unsigned bank,const MacroWrite& c) {
        const unsigned n=lane(c);
        require(bank==(c.word.address&3)&&!(accepted&(1u<<n)),"duplicate embedding acceptance");
        accepted|=uint16_t(1)<<n;
    }
    void visible(unsigned bank,const MacroWrite& c,const VmReceipt& receipt) {
        const unsigned n=lane(c);
        require(bank==(c.word.address&3)&&(accepted&(1u<<n))&&!(acked&(1u<<n)),
                "embedding ACK lacks unique accepted scalar");
        acked|=uint16_t(1)<<n;
        if(prefix_batch) {
            on_prefix_scalar_ack(c,receipt);
            prefix_acked.set(c.source.element_address);
        }
        if(acked==required&&!prefix_batch) {
            require(accepted==required&&held.vm_address==base+published,
                    "embedding published prefix gap");
            published+=16;
        }
    }
    void prepare(const DsromS81PairResult& result) {
        write_ports.prepare(result);
        if(read_pending)require(read_lease(read_address),"native read lease revoked while outstanding");
        if(read_pending&&!read_accepted) {
            model.rd_v=1;
            model.rd_base_word=(read_address>>4)&~3u;
            for(unsigned i=0;i<8;i++)model.rd_owner[i]=read_owner[i];
        }
    }
    bool read_lease(uint32_t address) const {
        return source_span_lease(identity,address,1);
    }
    void rising(bool released) {
        if(!released) {
            if(active||read_pending){stopped=true;throw std::runtime_error("embedding target reset has retained debt");}
            write_ports.rising(false);return;
        }
        ++edge;
        model.clk=0;model.rst_n=1;model.eval();
        const bool take=model.rd_accept_v;
        if(take) {
            require(read_pending&&!read_accepted&&model.rd_v,"unsolicited native target read acceptance");
            read_accepted=true;read_edge=edge;
        }
        write_ports.rising(true);
        if(model.rd_out_v) {
            require(read_pending&&read_accepted&&!read_done&&edge-read_edge==4,
                    "native target read lacks old accepted E+4 request");
            for(unsigned i=0;i<8;i++)require(model.rd_out_owner[i]==read_owner[i],
                                           "native target read owner mismatch");
            require(model.rd_out_rot==0,"native target aligned read rotation mismatch");
            const unsigned bank=(read_address>>4)&3;
            read_bits=model.rd_out_bank_words[bank*16+(read_address&15)];
            read_done=true;read_pending=false;
        }
    }
public:
    PublishedSpanMacroSink(Model& m,uint64_t id,uint32_t vm_base,Record r,
                          SpanLease lease,SpanLease write_allowed,ScalarAck ack)
    :model(m),identity(id),base(vm_base),record(std::move(r)),
     prefix_source_lease(std::move(lease)),prefix_write_allowed(std::move(write_allowed)),
     on_prefix_scalar_ack(std::move(ack)),
     backend(m,[this](const DsromS81PairResult&){return commands();},
             [this](unsigned b,const MacroWrite& c){took(b,c);},
             [this](unsigned b,const MacroWrite& c,const VmReceipt& a){visible(b,c,a);}),
     write_ports(backend.participant()) {
        require(identity<(1ull<<47)&&base<=32768-20480&&bool(record)&&
                bool(prefix_source_lease)&&bool(prefix_write_allowed)&&bool(on_prefix_scalar_ack),
                "embedding target requires source identity/layout/record encoder");
    }
    PublishedSpanMacroSink(const PublishedSpanMacroSink&)=delete;
    PublishedSpanMacroSink& operator=(const PublishedSpanMacroSink&)=delete;
    bool fault() const {return stopped||backend.fault();}
    uint32_t published_words() const {return published;}
    unsigned accepted_words() const {return __builtin_popcount(accepted);}
    unsigned acknowledged_words() const {return __builtin_popcount(acked);}
    // Concrete same-VM positive receipts AND the source producer's version lease.
    bool source_span_lease(uint64_t id,uint32_t address,unsigned words) const {
        if(fault()||id!=identity||!words||uint64_t(address)+words>(1u<<19))return false;
        if(address>=base&&uint64_t(address)+words<=uint64_t(base)+published)return true;
        for(unsigned n=0;n<words;n++)if(!prefix_acked.test(address+n))return false;
        return prefix_source_lease(id,address,words);
    }
    bool offer(const S81EmbeddingOutput& out) {return offer_batch(out,16,false);}
    bool offer_prefix(const S81EmbeddingOutput& out,unsigned words) {
        return offer_batch(out,words,true);
    }
private:
    bool offer_batch(const S81EmbeddingOutput& out,unsigned words,bool prefix) {
        try {
            require(!fault()&&out.vm_valid&&!out.fault&&out.vm_identity==identity,
                    "embedding target offered foreign/faulted source");
            require(words>=1&&words<=16&&uint64_t(out.vm_address)+words<=(1u<<19),
                    "source batch exceeds native element span");
            if(active&&!reported) {
                require(words==count&&prefix==prefix_batch&&same(out,held),"embedding changed unreported held payload");return true;
            }
            if(read_pending)return false;
            if(prefix) {
                require(uint64_t(out.vm_address)+words<=base||out.vm_address>=base+20480,
                        "prefix writer cannot overwrite immutable embedding input");
                require(prefix_write_allowed(identity,out.vm_address,words),
                        "prefix batch not in actual native writer source span");
            }else require(out.vm_address==base+published&&published<20480,
                         "embedding target source order/extent mismatch");
            // Validate every captured scalar before changing state or accepting any port.
            std::array<MacroWrite,16> next{};
            for(unsigned n=0;n<words;n++) {
                next[n]=record(out,n);const auto& c=next[n];
                const uint32_t address=out.vm_address+n;
                const unsigned k=address&15;
                require(c.source.identity==identity&&c.source.element_address==address&&
                        c.word.address==(address>>4)&&c.word.mask==(uint16_t(1)<<k)&&
                        c.word.data[k]==out.vm_data[n]&&!(c.word.owner[7]&~7u),
                        "embedding target record does not bind actual scalar payload/address/owner");
            }
            if(prefix)for(unsigned n=0;n<words;n++)prefix_acked.reset(out.vm_address+n);
            // Rewrites revoke cached target data before any acceptance. Producer
            // version/generation eligibility remains the source callback's job.
            read_done=false;
            writes=next;held=out;count=words;required=uint16_t((1u<<count)-1);
            prefix_batch=prefix;accepted=acked=0;active=true;reported=false;return true;
        }catch(...){stopped=true;throw;}
    }
public:
    bool visible(const S81EmbeddingOutput& out) {return visible_batch(out,16,false);}
    bool visible_prefix(const S81EmbeddingOutput& out,unsigned words) {
        return visible_batch(out,words,true);
    }
private:
    bool visible_batch(const S81EmbeddingOutput& out,unsigned words,bool prefix) {
        try {
            require(!fault()&&active&&words==count&&prefix==prefix_batch&&same(out,held),"embedding visibility lacks same held batch");
            if(accepted!=required||acked!=required)return false;
            require(backend.drained(),"embedding visibility has native ACK/callback debt");
            reported=true;return true;
        }catch(...){stopped=true;throw;}
    }
public:
    DsromS81EmbeddingSink sink() {
        return {[this](const auto& o){return offer(o);},
                [this](const auto& o){return visible(o);},[this](){return fault();}};
    }
    DsromS81MinimumParticipant participant() {
        return {"source-span-native-target-scalar-ACK",
            [this](const auto& r){try{prepare(r);}catch(...){stopped=true;throw;}},
            [this](bool reset){try{rising(reset);}catch(...){stopped=true;throw;}},
            [this](bool reset){write_ports.falling(reset);},[this](){return fault();}};
    }
    // Poll under runtime.tick(), not a private read/clock loop. This returns
    // actual target SRAM response bits, never the embedding reader's own copy.
    std::optional<uint32_t> target_word(uint32_t address,const Owner& owner) {
        try {
            require(!fault()&&address<(1u<<19)&&read_lease(address)&&!(owner[7]&~7u),
                    "target word lacks matched embedding publication range/owner");
            if(read_pending) {
                require(address==read_address&&owner==read_owner,"changed held native target read");
                return std::nullopt;
            }
            if(read_done&&address==read_address&&owner==read_owner)return read_bits;
            require(backend.drained()&&(!active||acked==required),
                    "target read overlaps uncompleted embedding writes");
            read_address=address;read_owner=owner;
            read_pending=true;read_accepted=read_done=false;return std::nullopt;
        }catch(...){stopped=true;throw;}
    }
};
} // namespace dsrom_s81_minimum
