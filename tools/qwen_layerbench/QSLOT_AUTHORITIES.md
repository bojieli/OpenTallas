QSLOT booking remains disabled until a complete current source and GEN contract is supplied. The template deliberately has no actual dates. The qbank pin receipt measures source-local edges only; it cannot supply a transport, service, codec or retirement date.

Each of the four other proof files must be JSON with schema `opentallas.qwen.qslot-authority.v1`, its exact `authority` name, and status `QUALIFIED_SOURCE_GEN_EDGES`. It must repeat the contract's source revision, actual die.v and parameter digests, all five source hashes, clock, origin, parameters, endpoint bundle and L-player identity. Every segment must match the contract's context identity, commit identity and concrete epoch/generation/user/layer/token/position tuple.

The following fields must also match exactly:

| Authority | Required segment fields |
| --- | --- |
| commit_identity | begin_pin_edge, q_dd_pin_edges, q_committed_pin_edge, commit_after_last_dd_edges, next_begin_pin_edge |
| sysface_bundle | sysface_to_qbank_edges, l_calendar_start_edge, paired_segment_start_epoch_edge, l_start_decode_edges, l_start_driver_event |
| svc_codec_wire | svc_codec_to_wire_edges, request_capture_edge, d2d_write_capture_edges |
| tx_retire | retire_pin_edge, next_begin_pin_edge |

The service/codec authority's 32 write dates must equal the executing paired programme's Q capture dates. The compiler lowers that contiguous burst through measured wire, qbank read and coherent SF.q_slot transport ages. It checks the final Q commit, request, retirement and next clear against those dates. A file's matching digest alone is insufficient authority.

`l_start_driver_event` is the actual T event `[epoch_edge, class, argument]`. Its class must be STAGE (0), with L flag bit 6 set. Paired segment 1 requires stage 1; paired segment 0 requires stage 2 through 36. MARK-L is refused. The driver edge plus measured decode age must equal the paired epoch origin plus L calendar start. The event must also exist in the executing T programme.

The existing `qfd_sys_face_ovl_fault1` source supports one L pattern. Differing normalized patterns are refused. The opt-in `qfd_sys_face_ovl_lctx1` candidate with `L_CONTEXTS=1` supports two patterns: token paired segment 1 uses source L0; decode paired segment 0 uses source L1. The actual selected source hash, master and parameter must match the contract and GEN. The encoder stores both patterns in the same NE32 store and sets source segment 1's base with target 4 address 0x80. Fourteen compressed entries fit the bounded recipe (one Q burst, four KV slots and two visibility events per pattern). Actual dates may still cause a collision or capacity refusal. Selector component evidence does not qualify this candidate's full calendar or physical parent.

The `SYNTHETIC_COMPILER_TEST` status is accepted only by the explicit unit-test path and is rejected by production loading. The retained local Qbank replays test data, measured pin edges and a deliberately early booked-date negative; their synthetic transport dates are not deployment evidence.
