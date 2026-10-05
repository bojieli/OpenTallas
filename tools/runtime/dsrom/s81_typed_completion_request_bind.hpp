#pragma once
#include "s81_wavefront_native_result_read.hpp"

// Exactly the finite RTL join's retained request_kind bit; no native ABI change.
enum class DsromS81CompletionKind : uint8_t {
    TOKEN_RESULT=0,
    STAGE_HANDOFF=1
};

// The actual compiler book/factory selects terminal and kind for the parent's
// saved accepted request. Do not pass a candidate's unbound context or derive
// entry/PCs from catalogue IDs, stage37 FIELD END, or live core ports.
//
// Arendt d92 source examples: HANDOFF38 L19.I114/fence entry101/111/112;
// HANDOFF40 L20.I143/fence entry118/128/129. These are selectable BOOK keys,
// not unconditional endpoints or terminal constants in this helper.
// Missing accepted-context/source ownership means leave request_binding_valid
// false and do not invoke this helper. Arch owns that context's lifetime.
template<class Top>
void dsrom_s81_drive_saved_typed_completion_request(
    Top& top,
    const DsromS81WaveRequest& saved_request,
    const DsromC8SourceOffer& saved_accepted_context,
    const DsromS81NativeResultTerminal& compiled_terminal,
    DsromS81CompletionKind compiled_kind,
    int actual_terminal_die_id,
    bool request_retained) {
    // A rejected association cannot leave an old valid input request asserted.
    // This does not clear accepted RTL debt, metadata, or retained result.
    top.wf_join_request_v=0;
    top.wf_join_request_binding_valid=0;
    const auto& offer=compiled_terminal.offer;
    DsromC8SourceDispatch saved_checked(saved_accepted_context);
    DsromC8SourceDispatch checked(offer); // existing ID47 codec, no new epoch
    const bool handoff=compiled_kind==DsromS81CompletionKind::STAGE_HANDOFF;
    const bool token=compiled_kind==DsromS81CompletionKind::TOKEN_RESULT;
    if((!handoff && !token) || actual_terminal_die_id<0 ||
       offer.die_id!=actual_terminal_die_id || compiled_terminal.source_node.empty() ||
       offer.identity!=saved_accepted_context.identity || offer.epoch!=saved_accepted_context.epoch ||
       offer.token!=saved_accepted_context.token || offer.position!=saved_accepted_context.position ||
       offer.user!=saved_accepted_context.user ||
       offer.token!=saved_request.token || offer.position!=saved_request.position ||
       offer.user!=saved_request.user ||
       compiled_terminal.producer_pc>=(1u<<14) || compiled_terminal.end_pc>=(1u<<14) ||
       offer.entry>compiled_terminal.end_pc ||
       (token && (offer.entry>compiled_terminal.producer_pc ||
                  compiled_terminal.producer_pc>=compiled_terminal.end_pc)))
        throw std::runtime_error("typed completion differs from saved request/compiled terminal/physical owner");
    top.wf_join_request_identity=offer.identity;
    top.wf_join_terminal_entry=offer.entry;
    top.wf_join_producer_pc=compiled_terminal.producer_pc;
    top.wf_join_end_pc=compiled_terminal.end_pc;
    top.wf_join_request_kind=handoff ? 1 : 0;
    top.wf_join_request_binding_valid=1;
    top.wf_join_request_v=request_retained;
    // The enclosing caller holds the SAME saved metadata until request_ready
    // is sampled on its actual shared edge. Retire the old accepted result
    // before selecting a simultaneous new saved request. No eval/tick/reset,
    // coverage, visibility, completion, token payload or consumer ACK is driven
    // here. TOKEN_RESULT still requires fresh native AMAX inside the RTL join;
    // STAGE_HANDOFF never asserts token validity or needs a HEAD designation.
}
