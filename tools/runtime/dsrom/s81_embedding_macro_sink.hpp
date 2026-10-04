#pragma once
#include "s81_minimum_macro_ack_adapter.hpp"
#include "s81_minimum_embedding.hpp"
#include <algorithm>

namespace dsrom_s81_minimum {
// Software port binding, not new RTL/capture seats or a whole-field certificate.
// The source caller supplies its actual tag/provenance encoder. Payloads always
// come from the native embedding reader, and reads from the native target VM.
template<class Model> class EmbeddingMacroSink {
public:
    using Record=std::function<MacroWrite(const S81EmbeddingOutput&,unsigned)>;
    using Owner=std::array<uint32_t,8>;
private:
    Model& model;
    const uint64_t identity;
    const uint32_t base;
    Record record;
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
                c.source.element_address<held.vm_address+16,"receipt outside held embedding batch");
        const unsigned n=c.source.element_address-held.vm_address;
        const auto& w=writes[n].word;
        require(c.word.owner==w.owner&&c.word.address==w.address&&c.word.mask==w.mask&&
                c.word.data==w.data,"embedding receipt changed retained native command");
        return n;
    }
    typename MacroAckAdapter<Model>::Commands commands() const {
        typename MacroAckAdapter<Model>::Commands out{};
        if(!active||read_pending)return out;
        for(unsigned n=0;n<16;n++)if(!(accepted&(1u<<n))) {
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
    void visible(unsigned bank,const MacroWrite& c,const VmReceipt&) {
        const unsigned n=lane(c);
        require(bank==(c.word.address&3)&&(accepted&(1u<<n))&&!(acked&(1u<<n)),
                "embedding ACK lacks unique accepted scalar");
        acked|=uint16_t(1)<<n;
        if(acked==65535) {
            require(accepted==65535&&held.vm_address==base+published,
                    "embedding published prefix gap");
            published+=16;
        }
    }
    void prepare(const DsromS81PairResult& result) {
        write_ports.prepare(result);
        if(read_pending&&!read_accepted) {
            model.rd_v=1;
            model.rd_base_word=(read_address>>4)&~3u;
            for(unsigned i=0;i<8;i++)model.rd_owner[i]=read_owner[i];
        }
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
    EmbeddingMacroSink(Model& m,uint64_t id,uint32_t vm_base,Record r)
    :model(m),identity(id),base(vm_base),record(std::move(r)),
     backend(m,[this](const DsromS81PairResult&){return commands();},
             [this](unsigned b,const MacroWrite& c){took(b,c);},
             [this](unsigned b,const MacroWrite& c,const VmReceipt& a){visible(b,c,a);}),
     write_ports(backend.participant()) {
        require(identity<(1ull<<47)&&base<=32768-20480&&bool(record),
                "embedding target requires source identity/layout/record encoder");
    }
    EmbeddingMacroSink(const EmbeddingMacroSink&)=delete;
    EmbeddingMacroSink& operator=(const EmbeddingMacroSink&)=delete;
    bool fault() const {return stopped||backend.fault();}
    uint32_t published_words() const {return published;}
    bool offer(const S81EmbeddingOutput& out) {
        try {
            require(!fault()&&out.vm_valid&&!out.fault&&out.vm_identity==identity,
                    "embedding target offered foreign/faulted source");
            if(active&&!reported) {
                require(same(out,held),"embedding changed unreported held payload");return true;
            }
            if(read_pending)return false;
            require(out.vm_address==base+published&&published<20480,
                    "embedding target source order/extent mismatch");
            // Validate all sixteen before changing state or accepting any port.
            std::array<MacroWrite,16> next;
            for(unsigned n=0;n<16;n++) {
                next[n]=record(out,n);const auto& c=next[n];
                const uint32_t address=out.vm_address+n;
                const unsigned k=address&15;
                require(c.source.identity==identity&&c.source.element_address==address&&
                        c.word.address==(address>>4)&&c.word.mask==(uint16_t(1)<<k)&&
                        c.word.data[k]==out.vm_data[n]&&!(c.word.owner[7]&~7u),
                        "embedding target record does not bind actual scalar payload/address/owner");
            }
            writes=next;held=out;accepted=acked=0;active=true;reported=false;return true;
        }catch(...){stopped=true;throw;}
    }
    bool visible(const S81EmbeddingOutput& out) {
        try {
            require(!fault()&&active&&same(out,held),"embedding visibility lacks same held batch");
            if(accepted!=65535||acked!=65535)return false;
            require(backend.drained(),"embedding visibility has native ACK/callback debt");
            reported=true;return true;
        }catch(...){stopped=true;throw;}
    }
    DsromS81EmbeddingSink sink() {
        return {[this](const auto& o){return offer(o);},
                [this](const auto& o){return visible(o);},[this](){return fault();}};
    }
    DsromS81MinimumParticipant participant() {
        return {"embedding-native-target-16-scalar-ACK",
            [this](const auto& r){try{prepare(r);}catch(...){stopped=true;throw;}},
            [this](bool reset){try{rising(reset);}catch(...){stopped=true;throw;}},
            [this](bool reset){write_ports.falling(reset);},[this](){return fault();}};
    }
    // Poll under runtime.tick(), not a private read/clock loop. This returns
    // actual target SRAM response bits, never the embedding reader's own copy.
    std::optional<uint32_t> target_word(uint32_t address,const Owner& owner) {
        try {
            require(!fault()&&address>=base&&address<base+published&&!(owner[7]&~7u),
                    "target word lacks matched embedding publication range/owner");
            if(read_pending) {
                require(address==read_address&&owner==read_owner,"changed held native target read");
                return std::nullopt;
            }
            if(read_done&&address==read_address&&owner==read_owner)return read_bits;
            require(backend.drained()&&(!active||acked==65535),
                    "target read overlaps uncompleted embedding writes");
            read_address=address;read_owner=owner;
            read_pending=true;read_accepted=read_done=false;return std::nullopt;
        }catch(...){stopped=true;throw;}
    }
};
} // namespace dsrom_s81_minimum
