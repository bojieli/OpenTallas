#pragma once
#include "s81_minimum_target_entry.hpp"
#include "s81_minimum_source_tags_component.hpp"
#include "s81_published_span_accept_sink.hpp"
#include "Vnative_vm.h"

// One actual rank's existing bank/entry composition. Construct four owners
// with their actual rank Runtime/VM/tag namespace; this does not replicate or
// copy a rank's VM into the other ranks. Arch owns enclosing registration,
// native source enrollment and shared cold/context admission. Keep this owner
// alive until its participants and every borrowed io/pub/tag reader retire.
// No model construction, eval, clock, tick, new receipt ledger or source ABI.
class DsromS81MinimumL20Bank {
public:
    using Publication=dsrom_s81_minimum::PrefixPublication;
    using Target=dsrom_s81_minimum::PublishedSpanAcceptSink<Vnative_vm>;
    using Visibility=std::function<void(unsigned,const dsrom_s81_minimum::MacroWrite&,
                                       const dsrom_s81_minimum::VmReceipt&)>;
private:
    DsromS81MinimumRuntime& runtime;
    const uint64_t identity;
    std::shared_ptr<Vnative_vm> model;
    Publication pub;
    DsromS81MinimumSourceTags source_tags;
    Visibility visible;
    std::unique_ptr<Target> target;
    DsromS81MinimumSourceIo source_io;
    DsromS81EmbeddingSink h_sink;
    std::unique_ptr<dsrom_s81_minimum::DsromS81MinimumTargetEntry> initial;
    bool bank_handed=false,entry_handed=false,read_pending=false,stopped=false;
    const bool mutable_h_selected;
    uint32_t read_address=0;
    std::array<uint32_t,8> read_owner{};
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    std::optional<uint32_t> read(uint64_t id,uint32_t address) {
        try {
            require(!fault()&&id==identity&&address<(1u<<19),"L20 bank read owner/address/fault");
            if(!read_pending) {
                read_owner=source_tags.read_owner(id,address);
                read_address=address;read_pending=true;
            }
            require(address==read_address,"L20 bank changed outstanding native read");
            auto bits=target->target_word(address,read_owner);
            if(bits) {
                dsrom_s81_retire_source_read_tag(runtime,address,read_owner);
                read_pending=false; // ONLY the actual matched native response
            }
            return bits;
        }catch(...){stopped=true;throw;}
    }
public:
    DsromS81MinimumL20Bank(DsromS81MinimumRuntime& r,uint64_t id,
                          std::shared_ptr<Vnative_vm> actual_vm,
                          DsromS81MinimumSourceTags actual_tags,bool mutable_h=false)
        :runtime(r),identity(id),model(std::move(actual_vm)),pub(id),source_tags(std::move(actual_tags)),mutable_h_selected(mutable_h) {
        require(r.stage==37&&r.rank>=0&&r.rank<4&&id<(1ull<<47)&&r.context&&model&&
                model->contextp()==r.context,"L20 bank requires actual stage37/rank/shared VM context");
        require(source_tags.record&&source_tags.read_owner&&source_tags.root_owner&&
                source_tags.scalar_accept&&source_tags.read_accept,
                "L20 bank requires the actual rank's source reservation/acceptance hooks");
        // Existing qe_join wraps this callback. Every wrapper calls its old
        // callback first, then appends actor notifications; retirement stays
        // here ONCE. The target reads its CURRENT value at each matched ACK.
        visible=[this](unsigned bank,const auto& command,const auto& receipt) {
            pub.on_prefix_scalar_ack(command,receipt);
            dsrom_s81_retire_source_scalar_tag(runtime,bank,command,receipt);
        };
        target=std::make_unique<Target>(*model,id,0,
            [this](const auto& out,unsigned lane) {
                if(out.vm_address<20480&&
                   !(mutable_h_selected&&pub.write_allowed(identity,out.vm_address+lane,1)))
                    return source_tags.record(out,lane);
                return pub.record(out,lane);
            },
            [this](auto owner,auto address,auto count){return pub.source_span_lease(owner,address,count);},
            [this](auto owner,auto address,auto count){return pub.write_allowed(owner,address,count);},
            [this](const auto& command,const auto& receipt) {
                require(bool(visible),"L20 bank matched visibility observer absent");
                visible(command.word.address&3,command,receipt);
            },
            Target::AcceptObservers{true,
                [this](unsigned bank,const auto& command){source_tags.scalar_accept(bank,command);},
                [this](uint32_t address,const auto& owner){source_tags.read_accept(address,owner);}},mutable_h);
        source_io={
            [this](auto owner,auto address){return read(owner,address);},
            [this](auto owner,auto address,auto count){return target->source_span_lease(owner,address,count);},
            [this](const auto& out,unsigned count){return target->offer_prefix(out,count);},
            [this](const auto& out,unsigned count){return target->visible_prefix(out,count);}};
        h_sink=target->sink();
        initial=std::make_unique<dsrom_s81_minimum::DsromS81MinimumTargetEntry>(
            runtime,id,pub,source_tags,source_io,h_sink,true);
    }
    DsromS81MinimumL20Bank(const DsromS81MinimumL20Bank&)=delete;
    DsromS81MinimumL20Bank& operator=(const DsromS81MinimumL20Bank&)=delete;
    Publication& publication(){return pub;}
    DsromS81MinimumSourceTags& tags(){return source_tags;}
    DsromS81MinimumSourceIo& io(){return source_io;}
    DsromS81EmbeddingSink& embedding_sink(){return h_sink;}
    dsrom_s81_minimum::DsromS81MinimumTargetEntry& entry(){return *initial;}
    Visibility& visibility(){return visible;}
    Vnative_vm& native_vm(){return *model;}
    Target& native_target(){return *target;}
    bool fault() const{return stopped||pub.fault()||target->fault()||initial->fault();}
    // Obtain each existing participant once; the enclosing owner registers it.
    DsromS81MinimumParticipant bank_participant() {
        require(!bank_handed,"L20 native bank participant handed out twice");
        bank_handed=true;auto p=target->participant();
        p.name+=" L20 rank"+std::to_string(runtime.rank);return p;
    }
    DsromS81MinimumParticipant entry_participant() {
        require(!entry_handed,"L20 target entry participant handed out twice");
        entry_handed=true;auto p=initial->participant();
        p.name+=" rank"+std::to_string(runtime.rank);return p;
    }
    // Caller invokes ONLY after actual shared cold fence and context binding.
    void initialize() {
        require(bank_handed&&entry_handed&&runtime.identity&&*runtime.identity==identity,
                "L20 entry initialization lacks enrolled participants/admitted context");
        initial->start();
    }
    bool inputs_visible() const{return !fault()&&initial->complete();}
    // At actual later native command acceptance ONLY. Arch retains dispatch
    // and supplies the real old-reader drain fence, not an elapsed-time promise.
    // Later output strobes must still reserve source tags and call native_scalar;
    // source_io.offer/visible use the SAME VM/participant and actual MacroWrite ACK.
    void admit_mutable_h_writer(unsigned producer,
          const std::vector<std::pair<uint32_t,uint32_t>>& ranges,
          bool actual_native_accept,bool old_readers_drained) {
        try {
            require(mutable_h_selected&&inputs_visible()&&actual_native_accept&&
                    old_readers_drained&&!read_pending&&target->mutable_write_drained()&&
                    runtime.identity&&*runtime.identity==identity&&!ranges.empty(),
                    "later H writer lacks opt-in/actual acceptance/drained old readers");
            bool owns_h=false;
            for(const auto& span:ranges) {
                require(span.second&&uint64_t(span.first)+span.second<=(1u<<19)&&
                        (span.first>=20480||uint64_t(span.first)+span.second<=20480),
                        "later H literal exceeds VM19 or straddles the original H extent");
                owns_h=owns_h||span.first<20480;
            }
            require(owns_h,"later H admission has no literal H output");
            // A native H writer also publishes its source reducer (SSX).
            // Enroll all outputs once, but revoke initial H witnesses only.
            pub.enroll_literal(producer,ranges); // descriptors alone create no visibility
            for(const auto& span:ranges)if(span.first<20480)
                target->admit_mutable_h_span(span.first,span.second);
            pub.begin(identity,producer); // old publication version revoked before native writes
        }catch(...){stopped=true;throw;}
    }
    // Other native writer's positive old-head ACK enters the SAME target
    // address witness, mutable callback chain and one retirement. Do not also
    // invoke publication/visibility manually for this same receipt.
    void external_scalar_visible(const dsrom_s81_minimum::MacroWrite& command,
                                 const dsrom_s81_minimum::VmReceipt& receipt) {
        target->external_scalar_visible(command,receipt);
    }
};
