# Actual OFF4 hook parser

PASS, Fri Nov6 07:41:35 PST2026. Exact command: `iverilog -g2012 -Wall -DOT_Q3CTL_OFF4_RT -s hook_only -tnull hook_only.sv ot_bodyctl_off32_split_d.sv`. Exit0, zero diagnostics.

hook_only.sv copies the actual production OFF4 helper wire declarations and three instantiations literally, retains the actual flag condition, and copies the three actual enabled phase3 always statements literally. It declares clk_control, all80 exact rawD scalar identifiers from capture_binding_audit.json, and three original32bit output registers. default_nettype none rejects unexpected undeclared namespace dependencies. extraction_manifest.json records exact production source hash and literal snippets. Helper was copied directly from production reform_1106/ot_bodyctl_off32_split_d.sv and hashes identically to the proven helper: e44fe63f42fc3568eede51e70e4cd6006ff6fed48dcf2e7e7f9a8d8ec3e86d6b.

This check covers actual hook grammar, ports, widths and namespace only. No simulation or full31MB source parse was performed. Existing default-off token identity, actual flat-cone SAT, three-edge helper stream, and rawD/clock/capture audit remain the functional evidence. Full GEN and kit LEC are still required before any future P&R.

Files: extract_hook.py, hook_only.sv, exact production helper, extraction_manifest.json, empty compile.log, verdict.json. Authoritative remote mirror: intel2:/srv/opentallas-scratch2/claude/codex-off32-edge3-1106/hook_parse. Production source was never edited.
