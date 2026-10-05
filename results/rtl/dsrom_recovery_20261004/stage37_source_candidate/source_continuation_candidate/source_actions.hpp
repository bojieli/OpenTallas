#pragma once
#include "s81_prefix_publication.hpp"
#include "s81_source_selection_restore.hpp"
#include "s81_wavefront_native_result_read.hpp"
#include "s81_typed_completion_request_bind.hpp"
namespace dsrom_s81_emitted_source_actions {
constexpr unsigned source14_catalogue_producer=1792;
constexpr unsigned source_home=28, destination_home=38;
constexpr unsigned selection_address=447360, selection_words=512;
constexpr unsigned copy_entry=113, copy_end_pc=114, copy_writer=2360;
constexpr unsigned handoff_request_kind=1;
constexpr bool l20_restore_required=false;
inline DsromS81PrefixOperation l19_restore_operation() {
 return {copy_writer,2u,"10603c1ac00c9122a5469f7e222b5f919fb2f679fd8c3d443fcaa1881a7bf2db",{0x000000fau,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000004u,0x00000001u,0x00001b4eu,0x00400000u,0x00000000u,0x00000000u,0x00006d38u,0x01000000u,0x00000000u,0x000369c0u,0x08000000u,0x00000000u,0x001b4e00u,0x40000000u,0x00000000u,0x04000000u,0x00006d38u,0x01000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x80000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u,0x00000000u}};
}
// Enrollment is NOT admission or begin; the real provider owns both.
inline void enroll_l19_restore(dsrom_s81_minimum::PrefixPublication& p) {
 p.enroll_literal(copy_writer,{{selection_address,selection_words}});
}
// Bind the ACTUAL owner tuple. Missing source14 is rejected by Epic.
inline std::unique_ptr<dsrom_s81_minimum::SourceSelectionRestore> bind_restore(
 unsigned layer,DsromS81MinimumRuntime& runtime,const DsromC8SourceOffer& destination,
 std::optional<dsrom_s81_minimum::SelectionRestoreSource> retained_source,
 std::optional<DsromS81SourceIoTransferHooks::Binding> native_copy,
 const DsromS81MinimumSourceTags& tags,
 DsromS81SourceIoTransferHooks::Fence positive_context,
 DsromS81SourceIoTransferHooks::Fence input_visible,
 DsromS81SourceIoTransferHooks::Fence remote_drained,
 DsromS81SourceIoTransferHooks::Fence all_copies_drained,bool opt_in=false) {
 if(layer!=19u && layer!=20u)
  throw std::runtime_error("only literal L19/L20 source restore actions are compiled");
 if(layer==19u && (destination.entry!=copy_entry || !native_copy ||
     !native_copy->enrolled_writer || *native_copy->enrolled_writer!=copy_writer))
  throw std::runtime_error("L19 source action requires actual emitted entry113/writer2360");
 const dsrom_s81_minimum::SelectionRestoreAction action{layer,layer==19u?14u:20u,7u,layer==19u};
 return std::make_unique<dsrom_s81_minimum::SourceSelectionRestore>(
  runtime,action,destination,std::move(retained_source),std::move(native_copy),tags,
  std::move(positive_context),std::move(input_visible),std::move(remote_drained),
  std::move(all_copies_drained),opt_in);
}
// Only attach a literal terminal to an ALREADY retained real offer.
// Planck drives saved typed request; Arch supplies coverage/visibility.
inline DsromS81NativeResultTerminal handoff_terminal(unsigned layer,
 const DsromC8SourceOffer& actual_retained_offer) {
 DsromC8SourceDispatch checked(actual_retained_offer);
 if(layer==19u) {
  if(actual_retained_offer.die_id<152 || actual_retained_offer.die_id>155 || actual_retained_offer.entry!=101)
   throw std::runtime_error("source fence does not match retained native terminal offer");
  return {actual_retained_offer,"L19.I114",111u,112u};
 }
 if(layer==20u) {
  if(actual_retained_offer.die_id<160 || actual_retained_offer.die_id>163 || actual_retained_offer.entry!=118)
   throw std::runtime_error("source fence does not match retained native terminal offer");
  return {actual_retained_offer,"L20.I143",128u,129u};
 }
 throw std::runtime_error("only actual L19/L20 source handoff fences are compiled");
}
template<class Top> void drive_source_fence_request(Top& top,unsigned layer,
 const DsromS81WaveRequest& saved_request,
 const DsromC8SourceOffer& saved_accepted_context,
 const DsromC8SourceOffer& actual_retained_terminal_offer,
 int actual_terminal_die_id,bool request_retained) {
 // Rejection cannot leave a stale valid request; accepted RTL debt is untouched.
 top.wf_join_request_v=0; top.wf_join_request_binding_valid=0;
 const auto terminal=handoff_terminal(layer,actual_retained_terminal_offer);
 dsrom_s81_drive_saved_typed_completion_request(top,saved_request,
  saved_accepted_context,terminal,DsromS81CompletionKind::STAGE_HANDOFF,
  actual_terminal_die_id,request_retained);
}
// No restore callback for L20.A0: explicit required=false source action.
// Neither this header nor END grants visibility, completion or an ACK.
}
