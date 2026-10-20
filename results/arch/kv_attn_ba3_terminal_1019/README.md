# Terminal native ATTN ba3 gate failure

Exact immutable gate source a43438ceed67b16af7fb599cd8dced0b10fd29c5. Finished08:37 PDT on ot-epyc8. This failure cannot qualify a release or be rerouted unchanged.

TT reg-to-reg WNS -185.6ps, endpoint codec_tx_payload[91] DFFE. Pin-flop spread TT89.5ps / FF83.6ps (both exceed80ps), insertion462.5/393.4ps,5840 clock sinks. TrialGRT overflow0. The RX zero-flag optimization leaves a global fault/event enable on548 TX payload flops. A new owner is proving same-edge unconditional TX payload capture with unchanged valid/fault semantics, plus balanced physical clock grouping.

Original receipt: /home/ubuntu/wt/codex-kv-relaygen-attn-recovery-1019/physical/ref_tile/qkd_kvs_attn_ba3/gate_result.json
Uncompressed SHA256: ea76ee8a60484d2e8867ebb22163c3628f93dd0d58bfbe67d74f2eb23cee9eee

The compressed receipt preserves the original staged source manifest. Layout images remain alongside the original kit. No REVIEW/submission claimed.
