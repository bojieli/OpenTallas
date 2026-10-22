# Frozen raw-source proof dependencies

This additive artifact packet preserves the exact raw1280 FP32 input, fixture manifests, source CTL, corrected expected quantizer scoreboard, and private model/harness dependencies used by 9463564f4. The 19 payload files are SHA-pinned in manifest.json. These are historical snapshots under results, not production tools or defaults. The original three corrected-model JSON files, 51 RTL sources/files.f/manifest, and result receipts remain in adjacent folders.

Input is only the original q_norm.scale raw FP32 state and real source commands. expected_xq.mem is scoreboard only. source_ctl.txt was unchanged in the corrected-scoreboard run; corrected expected_xq.mem SHA is 0633f6f7faff6b0e8a2b375c115555bd9dc8cbe0636e8348df089a7c567a339b.

The original executable remains remotely at ot-epyc4:/srv/opentallas-scratch/claude/s81-qf-producer-source-1019/qnorm_source_bundle/quant_component_03/obj/Vtb_qnorm_source (SHA819d2575d6c679ddf90ce89b55692a6c350632e3c65426e0e380256bde10910a). It is not a required source dependency. Building requires Verilator5.050 plus a C++ compiler/make; model generation requires Python/numpy and HDC_V41_ARITH=chunk8. The existing runner uses its original frozen remote layout (qnorm_program_model_v1 and v2); reproducing in a new folder must explicitly stage adjacent corrected JSON under that layout rather than silently reading other project state. source_ctl.txt and expected_xq.mem are supplied directly to avoid that ambiguity. No runtime numerical rerun was performed for this packaging.

All15 epoch reads, macro commit timestamps, reset/replay and native physical dates remain outside this component proof. No token or original-deadline PASS is inferred.
