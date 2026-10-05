#pragma once
#include "s81_minimum_prefix_providers.hpp"

// Native provider port adapters for Cicero's canonical SourceIo. These create
// no VM, clock, numerical operations, read-accept pulse or synthetic ACK.
// Staging capacity/transfer cost belongs in the owners' existing model rows.
// Call poll/progress from ONE shared participant prepare callback per tick.
template<size_t Words> class DsromS81MinimumOperandSpan {
    static_assert(Words>0&&Words<=20480,"operand span exceeds selected H staging");
    DsromS81MinimumSourceIo io;
    uint64_t identity;
    bool active=false,stopped=false;
    uint32_t base=0,next=0;
    std::array<uint32_t,Words> bits{};
public:
    DsromS81MinimumOperandSpan(uint64_t id,const DsromS81MinimumSourceIo& source)
    :io(source),identity(id) {
        if(id>=(1ull<<47)||!io.read_word||!io.span_lease)
            throw std::runtime_error("actual source read and version lease required");
    }
    std::optional<std::array<uint32_t,Words>> poll(uint64_t id,uint32_t address) {
        try {
            if(stopped||id!=identity||uint64_t(address)+Words>(1u<<19))
                throw std::runtime_error("native operand span wrong owner/extent/quarantine");
            if(!active) {
                if(!io.span_lease(id,address,Words))return std::nullopt;
                active=true;base=address;next=0;
            }
            if(base!=address||!io.span_lease(id,base,Words))
                throw std::runtime_error("native operand read changed or source version revoked");
            auto word=io.read_word(id,base+next);
            if(!word)return std::nullopt;
            bits[next++]=*word; // exact qualified target VM response, no FP work
            if(next<Words)return std::nullopt;
            if(!io.span_lease(id,base,Words))
                throw std::runtime_error("operand source lease lost at final native response");
            active=false;return bits;
        }catch(...){stopped=true;throw;}
    }
    bool pending()const{return active;}
    bool fault()const{return stopped;}
};

class DsromS81MinimumPrefixOutputBatch {
    DsromS81MinimumRuntime& runtime;
    DsromS81MinimumSourceIo io;
    dsrom_s81_minimum::PrefixPublication& publication;
    uint64_t identity;
    S81EmbeddingOutput held{};
    unsigned count=0;
    bool active=false,offered=false,stopped=false;
public:
    DsromS81MinimumPrefixOutputBatch(DsromS81MinimumRuntime& r,uint64_t id,
        dsrom_s81_minimum::PrefixPublication& pub,
        const DsromS81MinimumSourceIo& source,const DsromS81MinimumSourceTags& source_tags)
    :runtime(r),io(source),publication(pub),identity(id) {
        if(id>=(1ull<<47)||!io.offer||!io.visible||!source_tags.record)
            throw std::runtime_error("actual native publication IO and source reservation required");
    }
    // Once per actual native output. A provider's priced output stage retains
    // later outputs while this one is outstanding. Never recapture on poll.
    void capture(unsigned producer,const S81EmbeddingOutput& output,
                 unsigned words,bool actual_write) {
        try {
            if(stopped||active||!actual_write||words<1||words>16||
               output.vm_identity!=identity||!output.vm_valid||output.fault||
               uint64_t(output.vm_address)+words>(1u<<19))
                throw std::runtime_error("native output batch absent/overlapping/foreign");
            // Versioned tags come from the same registered provider as H/root.
            // A partial exception retains reservations and quarantines this adapter.
            for(unsigned n=0;n<words;n++)
                dsrom_s81_capture_minimum_prefix_scalar(
                    runtime,publication,producer,output,n,true);
            held=output;count=words;active=true;offered=false;
        }catch(...){stopped=true;throw;}
    }
    // Completion means the SAME retained batch received ALL actual matched
    // scalar ACKs through Popper; neither admission nor native idle is enough.
    bool progress() {
        try {
            if(stopped||publication.fault())
                throw std::runtime_error("native output publication quarantined");
            if(!active)return false;
            if(!offered)offered=io.offer(held,count);
            if(!offered||!io.visible(held,count))return false;
            active=false;offered=false;return true;
        }catch(...){stopped=true;throw;}
    }
    // Caller keeps a native output stable while the existing stage waits for
    // its matched ACK; a changed producer output must not retire the old one.
    bool retains(const S81EmbeddingOutput& output,unsigned words)const {
        if(!active||count!=words||held.vm_identity!=output.vm_identity||
           held.vm_address!=output.vm_address||!output.vm_valid||output.fault)return false;
        for(unsigned n=0;n<words;++n)if(held.vm_data[n]!=output.vm_data[n])return false;
        return true;
    }
    bool pending()const{return active;}
    bool fault()const{return stopped||publication.fault();}
};
