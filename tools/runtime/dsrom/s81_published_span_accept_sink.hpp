#pragma once
#include "s81_minimum_macro_ack_adapter.hpp"
#include "s81_minimum_embedding.hpp"
#include <algorithm>
#include <bitset>
#include <vector>
#include "../../native/dsrom_vm_tag227.hpp"

namespace dsrom_s81_minimum {
// Notifications of ACTUAL accept strobes, not reservations or visibility.
// Hubble owns source tag reservation and ledger advancement in these callbacks.
struct ActualVmAcceptObservers {
    using Owner227=std::array<uint32_t,8>;
    using ScalarAccept=std::function<void(unsigned,const MacroWrite&)>;
    using ReadAccept=std::function<void(uint32_t,const Owner227&)>;
    bool source_offer_ledger_selected=false;
    ScalarAccept scalar;
    ReadAccept read;
};
// Additive acceptance-observer successor; historical65e43 and c4bf are
// unchanged. Source callback eligibility is REQUIRED and must represent actual
// native producer spans/versions and matched ACKs, not declarations alone.
// No new RTL/capture seats or a whole-field certificate.
// The source caller supplies its actual tag/provenance encoder. Payloads always
// come from the native embedding reader, and reads from the native target VM.
template<class Model> class PublishedSpanAcceptSink {
public:
    using Record=std::function<MacroWrite(const S81EmbeddingOutput&,unsigned)>;
    using Owner=std::array<uint32_t,8>;
    using SpanLease=std::function<bool(uint64_t,uint32_t,unsigned)>;
    using ScalarAck=std::function<void(const MacroWrite&,const VmReceipt&)>;
    using AcceptObservers=ActualVmAcceptObservers;
    using ScalarAccept=AcceptObservers::ScalarAccept;
    using ReadAccept=AcceptObservers::ReadAccept;
private:
    Model& model;
    AcceptObservers accept_observers;
    const uint64_t identity;
    const uint32_t base;
    Record record;
    SpanLease prefix_source_lease,prefix_write_allowed;
    ScalarAck on_prefix_scalar_ack;
    // Fixed64KiB software receipt witness, NOT a hardware scoreboard price.
    // A source callback alone can NEVER make an unwritten address eligible.
    std::bitset<(1u<<19)> prefix_acked;
    // Software source-version witness; no additional native VM/RTL state.
    std::bitset<20480> mutable_h_addresses;
    unsigned count=16;
    uint16_t required=65535;
    bool prefix_batch=false;
    S81EmbeddingOutput held{};
    std::array<MacroWrite,16> writes{};
    uint16_t accepted=0,acked=0;
    uint32_t published=0;
    bool mutable_h_selected=false;
    std::vector<std::pair<uint32_t,unsigned>> mutable_h_spans;
    bool mutable_h_address(uint32_t address) const {
        for(const auto& span:mutable_h_spans)
            if(address>=span.first&&address-span.first<span.second)return true;
        return false;
    }
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
    uint32_t next_embedding_address() const {
        const uint32_t batch=published/16;
        return base+(batch%4)*5120+(batch/4)*16;
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
            external_scalar_visible(c,receipt); // ONE matched native ACK publication/retirement path
        } else {
            require(!prefix_acked.test(c.source.element_address),"duplicate immutable embedding publication");
            prefix_acked.set(c.source.element_address);
        }
        if(acked==required&&!prefix_batch) {
            require(accepted==required&&held.vm_address==next_embedding_address(),
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
        // Sample only settled PRE-edge native pins; preserve their full tuple
        // before this SAME bank owner's rising evaluation changes any outputs.
        const unsigned write_take=model.wr_accept_v;
        const auto retained=commands();
        require(!(write_take&~unsigned(model.wr_v)),"unsolicited native scalar acceptance");
        for(unsigned b=0;b<4;b++)if(write_take&(1u<<b)) {
            require(bool(retained[b]),"scalar accept lacks retained source command");
            const auto& w=retained[b]->word;
            const auto sampled=dsrom::component_tag227::read_bank_from(model.wr_owner,b);
            require(sampled==w.owner&&
                    ((uint64_t(model.wr_word_addr)>>(15*b))&32767)==w.address&&
                    ((uint64_t(model.wr_lane_mask)>>(16*b))&65535)==w.mask,
                    "accepted native scalar tag/address/mask differs from retained source");
            for(unsigned n=0;n<16;n++)require(model.wr_word_data[b*16+n]==w.data[n],
                                            "accepted native scalar payload differs from source");
        }
        const bool take=model.rd_accept_v;
        Owner sampled_read{};
        if(take) {
            for(unsigned i=0;i<8;i++)sampled_read[i]=model.rd_owner[i];
            require(sampled_read==read_owner&&model.rd_base_word==((read_address>>4)&~3u),
                    "accepted native read owner/address differs from retained request");
            require(read_pending&&!read_accepted&&model.rd_v,"unsolicited native target read acceptance");
            read_accepted=true;read_edge=edge;
        }
        write_ports.rising(true);
        // A callback exception quarantines the enclosing participant and does
        // not roll back actual accepted bank/read debts or recycle identities.
        // Ordering is native BANK ascending then READ; record allocation must
        // reserve retained tags without advancing acceptance at construction.
        for(unsigned b=0;b<4;b++)if((write_take&(1u<<b))&&accept_observers.scalar)
            accept_observers.scalar(b,*retained[b]);
        if(take&&accept_observers.read)accept_observers.read(read_address,sampled_read);
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
    PublishedSpanAcceptSink(Model& m,uint64_t id,uint32_t vm_base,Record r,
                          SpanLease lease,SpanLease write_allowed,ScalarAck ack,
                          AcceptObservers observers={},bool mutable_h=false)
    :model(m),accept_observers(std::move(observers)),identity(id),base(vm_base),record(std::move(r)),
     prefix_source_lease(std::move(lease)),prefix_write_allowed(std::move(write_allowed)),
     on_prefix_scalar_ack(std::move(ack)),
     backend(m,[this](const DsromS81PairResult&){return commands();},
             [this](unsigned b,const MacroWrite& c){took(b,c);},
             [this](unsigned b,const MacroWrite& c,const VmReceipt& a){visible(b,c,a);}),
     write_ports(backend.participant()) {
        mutable_h_selected=mutable_h;
        require(identity<(1ull<<47)&&base<=32768-20480&&bool(record)&&
                bool(prefix_source_lease)&&bool(prefix_write_allowed)&&bool(on_prefix_scalar_ack),
                "embedding target requires source identity/layout/record encoder");
        require(!accept_observers.source_offer_ledger_selected||
                (bool(accept_observers.scalar)&&bool(accept_observers.read)),
                "selected SourceOffer ledger requires actual scalar/read accept observers");
    }
    PublishedSpanAcceptSink(const PublishedSpanAcceptSink&)=delete;
    PublishedSpanAcceptSink& operator=(const PublishedSpanAcceptSink&)=delete;
    bool fault() const {return stopped||backend.fault();}
    uint32_t published_words() const {return published;}
    unsigned accepted_words() const {return __builtin_popcount(accepted);}
    unsigned acknowledged_words() const {return __builtin_popcount(acked);}
    // Concrete same-VM positive receipts AND the source producer's version lease.
    bool source_span_lease(uint64_t id,uint32_t address,unsigned words) const {
        if(fault()||id!=identity||!words||uint64_t(address)+words>(1u<<19))return false;
        if(address>=base&&uint64_t(address)+words<=uint64_t(base)+20480) {
            for(unsigned n=0;n<words;n++) {
                if(!prefix_acked.test(address+n))return false;
                if(mutable_h_address(address+n)&&!prefix_source_lease(id,address+n,1))return false;

            }
            return true;
        }
        for(unsigned n=0;n<words;n++)if(!prefix_acked.test(address+n))return false;
        return prefix_source_lease(id,address,words);
    }
    bool offer(const S81EmbeddingOutput& out) {return offer_batch(out,16,false);}
    bool offer_prefix(const S81EmbeddingOutput& out,unsigned words) {
        return offer_batch(out,words,true);
    }
    // Explicit current publisher route. Initial embedding/offer_prefix guards
    // stay unchanged; this uses the SAME native commands, acceptance and ACK.
    bool offer_mutable_h(const S81EmbeddingOutput& out,unsigned words,const Record& writer) {
        return offer_batch(out,words,true,&writer);
    }
private:
    bool offer_batch(const S81EmbeddingOutput& out,unsigned words,bool prefix,
                     const Record* mutable_record=nullptr) {
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
                for(unsigned n=0;n<words;n++) {
                    const auto address=out.vm_address+n;
                    require(address<base||address>=base+20480||mutable_h_address(address),
                            "prefix writer cannot overwrite unenrolled immutable embedding input");
                }

                require(prefix_write_allowed(identity,out.vm_address,words),
                        "prefix batch not in actual native writer source span");
            }else require(out.vm_address==next_embedding_address()&&published<20480,
                         "embedding target source order/extent mismatch");
            // Validate every captured scalar before changing state or accepting any port.
            std::array<MacroWrite,16> next{};
            for(unsigned n=0;n<words;n++) {
                next[n]=(mutable_record?(*mutable_record)(out,n):record(out,n));const auto& c=next[n];
                const uint32_t address=out.vm_address+n;
                const unsigned k=address&15;
                require(c.source.identity==identity&&c.source.element_address==address&&
                        c.word.address==(address>>4)&&c.word.mask==(uint16_t(1)<<k)&&
                        c.word.data[k]==out.vm_data[n]&&!(c.word.owner[7]&~7u),
                        "embedding target record does not bind actual scalar payload/address/owner");
            }
            if(prefix)for(unsigned n=0;n<words;n++) {
                prefix_acked.reset(out.vm_address+n);
                if(mutable_record)mutable_h_addresses.set(out.vm_address+n-base);
            }
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
    // Source-only opt-in. The bank owner calls this after actual old readers
    // drain, before pub.begin revokes the old version. No port/ACK is created.
    bool mutable_write_drained() const {
        return !fault()&&!read_pending&&backend.drained()&&(!active||(acked==required&&reported));
    }
    void admit_mutable_h_span(uint32_t address,unsigned words) {
        require(mutable_h_selected&&published==20480&&mutable_write_drained()&&words&&
                address>=base&&uint64_t(address)+words<=uint64_t(base)+20480,
                "mutable H requires opt-in, initial ACKs and drained native owners");
        mutable_h_spans.emplace_back(address,words);
        for(unsigned n=0;n<words;n++)prefix_acked.reset(address+n);
        read_done=false; // old cached bits cannot survive a new H version
    }
    // Called by the OTHER selected writer's actual old-head ACK callback.
    // This shares the existing address witness; it does not clock a bank,
    // grant a lease, or treat producer/assignment acceptance as visibility.
    void external_scalar_visible(const MacroWrite& c,const VmReceipt& receipt) {
        try {
            const auto a=c.source.element_address;
            require(!fault()&&!read_pending&&a<(1u<<19)&&c.source.identity==identity&&
                    c.word.address==(a>>4)&&c.word.mask==(uint16_t(1)<<(a&15))&&
                    receipt.address==c.word.address&&receipt.mask==c.word.mask&&
                    receipt.owner==c.word.owner,
                    "external scalar lacks actual matching old-head receipt");
            require(a<base||a>=base+20480||
                    (mutable_h_address(a)&&prefix_write_allowed(identity,a,1)),
                    "external H ACK lacks admitted literal mutable version");
            on_prefix_scalar_ack(c,receipt); // source checks unique admitted tuple/version
            prefix_acked.set(a);
            read_done=false; // never retain a cached read across this write
        }catch(...){stopped=true;throw;}
    }
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
