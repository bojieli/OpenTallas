#include "s81_typed_completion_request_bind.hpp"
struct RequestPins {
    uint8_t wf_join_request_v=0,wf_join_request_binding_valid=0,wf_join_request_kind=0;
    uint64_t wf_join_request_identity=0;
    uint16_t wf_join_terminal_entry=0,wf_join_producer_pc=0,wf_join_end_pc=0;
};
void instantiate(RequestPins& pins,const DsromS81WaveRequest& saved,
                 const DsromC8SourceOffer& accepted,const DsromS81NativeResultTerminal& book,int actual_die) {
    dsrom_s81_drive_saved_typed_completion_request(pins,saved,accepted,book,
        DsromS81CompletionKind::STAGE_HANDOFF,actual_die,true);
    dsrom_s81_drive_saved_typed_completion_request(pins,saved,accepted,book,
        DsromS81CompletionKind::TOKEN_RESULT,actual_die,true);
}
