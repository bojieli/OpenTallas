PVFIN source output cycles in native KV programme preparation

The selected D5 IN_STAGE1 + output-PIN form adds two cycles at all final
PVFIN output pins. The older result-trunk calendar moves P0/P1 before that
arithmetic, so adding the two source cycles to its scalar would change the
wrong dependency. The v2 calendar keeps trunk and output-pin components
separate. Programme prep adds output-pin cycles only to the bound fin path,
which generates the matching boot F_DLY. The compiler consumes that same
generated F_DLY through the selected v2 ages record.

The bridge checks the actual selected plan/asbuilt wrapper, all five output
ports, CPC TSV, canonical D5 source and latency proof. Final mode requires a
matching coherent bind and exact trunk calendar/bus-group/producer identity.
The known stale-pair-image error may remain because regenerating that image
is the next consumer; other bind failures are rejected. Reapplying a v2 CPC
component is rejected. Old tools reject the v2 schema instead of silently
discarding source cycles. Default and positive-cost v1 preparation each
reproduce all ten original output files byte for byte.

Actual D5 source component tests prove fin/F_DLY55->57 with PV, first-input,
arithmetic and vport ages preserved. Wrong cost, duplicate rule/component,
bad total, changed source, stale final bind and CPC reapplication controls are
caught. The old compiler profile fell back to F_DLY1 because old prep did not
attach its generated F_DLY55 as boot_ages. That pre-existing mismatch remains
visible. The selected v2 record supplies the real generated F_DLY57; the new
source adds two cycles, not fifty-six. Legacy defaults are preserved.

The old ns7 bind is only a compatibility fixture. The existing trunk producer
rejects its real node9->12 +3 path, and later source inspection found suspect
selector/data count relationships. That failure is preserved. The source-only
calendar used by the tool proof is an explicit unit input, not an aggregate
physical calendar or a hardware provider. Actual trunk extension and a final
coherent bind remain required before emitting a final aggregate calendar or
compiling the adopted programme. No native programme, physical signoff, POR
or source-freeze qualification is claimed here.

Fleet proof: E7 /srv/opentallas-scratch2/claude/tok-verify-2/kv_cpc_bridge.
Original proof, followup, source-identity guards and v1 compatibility logs are
retained separately. The actual source selection is hubc_pair_1113/native1,
not the obsolete native_pair3 prototype.
