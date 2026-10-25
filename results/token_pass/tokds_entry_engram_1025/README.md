L14 Engram attention-entry H, from genuine inputs

PASS: checkpoint-derived 24 selected embedding rows, full TP4 wkv weights, and fixture input H/pre/q/k weights
reproduce decoded rows (6144), wkv (25600), gates (4), updated H (20480), and attention hc_pre (5120), all bit exact.
The expected ops files are assertions only. Flipping bit6 of the first checkpoint embedding code is CAUGHT:
1 decoded row word,17460 wkv words,4 gates,4940 H words,1039 attention hc_pre words mismatch.

Use `entry_engram.entry_h(fixture, sidecar_directory)` to obtain the updated BF16 H for the norm compiler.
No RTL or schedule cycles change: this supplies the Engram-produced layer-entry state that attention consumes.
This is a golden input reconstruction, not a full layer token-pass verdict or an Engram RTL qualification.

Source helper: tools/s81_dv/layer_prog/entry_engram.py. Sidecars (157 MB; never committed) live at:
epyc3:/srv/opentallas-scratch2/claude/codex-entry-engram-1025/inputs_L14.
They can be regenerated using the helper's export command and the released checkpoint, then checked via its check command.
Arithmetic ran through ot-run on epyc3,16 GB/4 threads; units oth-ubuntu-2155367-1792922252 baseline and
oth-ubuntu-2164754-1792922304 input corruption. Small tensor-byte staging from the checkpoint host took <1 s.
