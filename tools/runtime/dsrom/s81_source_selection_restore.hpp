#pragma once
#include "s81_source_caller_hooks.hpp"
#include <optional>
#include <string>

namespace dsrom_s81_minimum {

// Narrow source action, not a context-ready, publication or retirement grant.
// Inactive is deliberately distinct from Published: L20.A0 has no copy/ACK.
enum class SelectionRestoreResult { Inactive, Waiting, Published };

struct SelectionRestoreAction {
    unsigned layer;
    unsigned source_layer;
    unsigned before_instruction;
    bool required;
};

struct SelectionRestoreSource {
    // Actual retained accepted offer and compiled native writer association.
    // Catalogue producer1792 is NOT this writer or a guessed program entry.
    DsromC8SourceOffer offer;
    unsigned native_writer;
    std::string source_node,template_sha256; // actual compiled source descriptor
    std::function<bool(const DsromC8SourceOffer&,unsigned)> publication_retained;
};

// Existing NativeSu M1_BYP remains the ONLY payload/capture/publication owner.
// This adapter allocates no payload array, writer, tags, native model or clock.
// Arch binds its real saved producer, source/destination SourceIo and all
// accepted-edge/publication/reverse callbacks; Arendt binds the literal action.
// Drive poll_restore/poll_drain from the existing caller, never a private tick.
class SourceSelectionRestore {
public:
    using Binding = DsromS81SourceIoTransferHooks::Binding;
    using Fence = DsromS81SourceIoTransferHooks::Fence;
    static constexpr uint32_t selection_address = 447360;
    static constexpr unsigned selection_words = 512;
private:
    DsromC8SourceOffer destination;
    std::unique_ptr<DsromS81SourceIoTransferHooks> transfer;
    bool stopped = false;
    static void require(bool ok,const char* reason) {
        if(!ok)throw std::runtime_error(reason);
    }
    void matching(const DsromC8SourceOffer& o) const {
        require(o.die_id==destination.die_id && o.identity==destination.identity &&
                o.token==destination.token && o.position==destination.position &&
                o.user==destination.user && o.epoch==destination.epoch &&
                o.entry==destination.entry,
                "selection restore changed accepted destination");
    }
public:
    // opt_in is off by default. An absent required source offer is a refusal,
    // never bootstrap identity, checkpoint data, memory alias or host setup.
    SourceSelectionRestore(DsromS81MinimumRuntime& runtime,
        const SelectionRestoreAction& action,DsromC8SourceOffer target,
        std::optional<SelectionRestoreSource> retained_source,
        std::optional<Binding> actual_copy,
        const DsromS81MinimumSourceTags& tags,
        Fence positive_context,Fence input_visible,Fence remote_drained,
        Fence all_copies_drained,bool opt_in=false)
        :destination(target) {
        require(opt_in,"selection restore provider is opt-in");
        DsromC8SourceDispatch checked_destination(destination);
        require(action.before_instruction==7,
                "selection restore is only the source action before I7");
        if(action.layer==20) {
            require(!action.required && action.source_layer==20 &&
                    !retained_source && !actual_copy,
                    "L20.A0 is inactive: no fictitious restore/copy/ACK");
            return;
        }
        require(action.layer==19 && action.required && action.source_layer==14,
                "selection restore requires exact L19.A0 SOURCE14 contract");
        require(retained_source && actual_copy,
                "L19.A0 requires actual retained source offer and native copy binding");
        const auto& source=*retained_source;
        DsromC8SourceDispatch checked_source(source.offer);
        require(source.source_node=="L14.I63" && source.template_sha256==
                "d0ca14372349ed80e998c5140108eaf4796bb1ed121c3b5529e9729abd4e6c79",
                "selection restore requires actual released L14.I63 TOPK publication");
        auto b=std::move(*actual_copy);
        const auto& s=b.span;
        const auto rank=unsigned(destination.die_id)%4;
        require(destination.die_id==int(152+rank) &&
                source.offer.die_id==int(112+rank) &&
                s.producer_die==source.offer.die_id &&
                s.producer_identity==source.offer.identity &&
                s.producer_address==selection_address &&
                s.destination_address==selection_address &&
                s.words==selection_words,
                "selection restore source28/destination38 rank or exact SELG extent changed");
        require(source.offer.user==destination.user &&
                source.offer.position==destination.position &&
                source.offer.token==destination.token,
                "selection restore source token/position/user differs");
        // Source and destination IDs/epochs are retained independently. The
        // actual source publication callback validates its saved generation;
        // copying into a new destination does not re-label the source version.
        require(source.native_writer>=9 && source.native_writer<(1u<<14) &&
                source.publication_retained && b.source.span_lease &&
                b.native_copy_visible && !b.transfer_accepted,
                "selection restore requires actual source writer and NativeSu copy visibility only");
        // Gate the original live source lease by its actual native publication
        // association. Inherited transfer checks keep this lease through BOTH
        // destination publication and real remote/allcopy reverse drain.
        auto source_lease=b.source.span_lease;
        b.source.span_lease=[source,source_lease](uint64_t id,uint32_t address,unsigned n) {
            require(id==source.offer.identity && address==selection_address &&
                    n==selection_words,"selection restore changed held source extent");
            return source.publication_retained(source.offer,source.native_writer) &&
                   source_lease(id,address,n);
        };
        std::vector<Binding> bindings;
        bindings.push_back(std::move(b));
        transfer.reset(new DsromS81SourceIoTransferHooks(runtime,destination,
            std::move(bindings),tags,std::move(positive_context),
            std::move(input_visible),std::move(remote_drained),
            std::move(all_copies_drained)));
    }

    SelectionRestoreResult poll_restore(const DsromC8SourceOffer& accepted) {
        try {
            require(!stopped,"selection restore quarantined");
            matching(accepted);
            if(!transfer)return SelectionRestoreResult::Inactive;
            return transfer->restore(accepted) ? SelectionRestoreResult::Published
                                               : SelectionRestoreResult::Waiting;
        }catch(...){stopped=true;throw;}
    }
    SelectionRestoreResult poll_drain(const DsromC8SourceOffer& accepted) {
        try {
            require(!stopped,"selection restore quarantined");
            matching(accepted);
            if(!transfer)return SelectionRestoreResult::Inactive;
            return transfer->drain(accepted) ? SelectionRestoreResult::Published
                                             : SelectionRestoreResult::Waiting;
        }catch(...){stopped=true;throw;}
    }
};
} // namespace dsrom_s81_minimum
