# Independent current-source legacy field gate FAIL

One unchanged gate invocation on clean main f06c71a87fc02ff3fb0a7ea9412eac3c0bdc85c0. Exact command, process identities, checkpoint revision/index/header pins, tool hash/version, measured headroom and source hashes are in receipt.json. The original gate, original historical PASS and all RTL remain unchanged. Capture script and raw traces are preserved additively. No source-list completion, retry, corrected control, C++ build or full-token simulation was performed.

Actual result: exit 1 at the flat frontend, MODMISSING ot_hdc_cg from rtl/v41rom/ot_v41_rom_elem.sv:106. Wall 44.01 seconds includes the real checkpoint phase/image preparation. Frontend RSS 80,640 KiB. The frontend exits before composition, golden comparison and wrong-edge negative simulation. The legacy tool does not emit its normal result.json on this path; the independent receipt retains the terminal failure.

Scope: tools/v41_field_rt_gate.py targets legacy rtl/v41die. The separate tools/w17_runtime_v41_field_rt_gate.py includes cg and targets rtl/w17_runtime/v41die; retained native driver lists select runtime spine/pair/retn companions. These static source relationships do not qualify an actual current PHW10 binary or prove this separate runtime gate passes at f06. The current integrated plan requires source/program/geometry identity for G0–G5 and does not allow a historical small-field result to qualify a successor. No selected-product regression, physical failure, throughput or full-token claim follows from this legacy frontend failure.

Historical PASS is retained verbatim: all its source hashes match e9bd212f9. Six source files differ at f06, and the historical NBF8/phase list differs from this current NBF4 invocation. Commits 541ef17eb and 01855c929 changed/restored the legacy source set and isolated runtime companions. The peer b98b report of tick252 o_data mismatch and incorrect flat writes after supplying cg is archived as peer evidence only; this independent invocation never reached that comparison.

Fresh offline check (no compiler, checkpoint read or simulation):

    python3 results/rtl/v41_legacy_field_gate_audit_20261003/verify.py

Actual replay recipe is the exact command array in receipt.json, launched from a fresh clean f06 worktree with a NEW empty workdir. The dba1be0a checkpoint is an external released input; checkpoint_header_metadata.json and generated_input_manifest.json bind this invocation. Payloads are not bundled. Do not use --reuse with unverified prior archives.

Routing: Maxwell should keep this failure outside selected runtime/backend physical conclusions. Claude DSsystem should bind its selected PHW10 source lists and observer enrollment to the runtime companions; any legacy dependency repair and follow-on functional control require a distinct receipt. Existing PHW10 observation and full-token gaps remain separate, unchanged.
