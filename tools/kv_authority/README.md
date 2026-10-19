# G7 observation authority (verification only)

The generator accepts only the exact archived G7 WSQK cut SHA eb75139931390368b0c74320092e5221851b6fe8b616f3f62d5b35251caa0c1f, the pinned 18-path frontier manifest and eight frozen source files. It refuses altered source, manifest, primitive, clock or mapping. This is a bounded generator for that cut, not a general HDL elaborator or GEN8 manifest. Source provenance is the independent kv-token-authority-source-1019 packet.

Compile `kva_authority_path.sv` with the bench and include `authority.svh` within its module. Define `KVA_AUTH_DUT` to the actual cut instance (default `dut`). Define `KVA_AUTH_ADMIT` to actual source guard acceptance qualified only by that guard's own monotonic reset-derived source knowledge; raw acceptance before knowledge must be counted separately. An authoritative admission before all 18 frontiers, or unknown authoritative admission, increments `kva_authority_admission_errors`. The owner must include this and every `kva_authority_errors[i]` in the final verdict. These counters never clear.

Known vector order: TX=0, sequence request=1, K0..7=2..9, V0..7=10..17. Depths are 9,5,69,69,67,63,56,47,34,51,6,4,6,4,6,4,6,4 (510 captures). Aliases name actual top-level bit connections and producer reset/qualifier paths; no relay-internal Q references are used. Source known starts zero. Actual asynchronous reset assertion or target edge with effective source reset known low establishes source knowledge; downstream tags use old values at every real capture. Each captured qualifier is checked after NBA at the following negedge. Reset source clearing and source/output aliases are checked independently. Knowledge remains asserted through repeat reset, idle and active traffic. No A0 or trace_on input exists.

Regenerate using:

```
python3 generate.py --cut ARCHIVED_CUT/qwk_stk_WS.sv --frontiers PACKET/frontiers.json --source-dir PACKET --out OUTPUT
```

PACKET contains `g7_frozen_*.sv` and the source-derived frontier manifest. The generated include is committed for review; regenerate and retain hashes before compiling the selected fixture. Arbitrary initial source/relay state is not asserted zero. Four-state unknown authoritative qualifiers are errors.

Fleet-only controls on ep6, unpinned ot-run admission, Verilator 5.050: 18 actual path depths × asynchronous-before-edge versus reset-first-observed-at-edge = 36 healthy cases PASS. Startup transaction guard removal, premature source knowledge and knowledge clearing on repeat reset are causally caught. Supplemental Icarus four-state controls pass all 36 cases with X-initial relays and detect an injected authoritative X. `run_controls.sh` reproduces the combined suite; these intentional mutant failures and their witness logs remain committed. Generator healthy/refusal controls (altered cut, unknown relay, altered clock manifest, altered producer) all pass.

Two supplemental wrapper attempts exited 1: the first tail slice included a preceding unrelated check, and the second required a narrower error phrase than the actual repeat-reset mutant emitted. Neither was a design PASS or infrastructure-hidden rerun; the preserved actual mutant witness is `CONTROL_FAIL old-D frontier ... known=0`, and its accepted parser checks both valid repeat-reset failure phrases. Primary original control logs remain unchanged.

This packet does not fix RTL startup safety, cancel pending source requests, validate STATUS ownership, suppress first-known events, or establish token/SU/MU/physical qualification. Parent integration owns raw evidence, first-authoritative malformed STATUS before A0, request identity, response queues, deadlines, PROGRAMME_EXECUTED and application verdict parsing. Existing failed full-vehicle logs remain failures. No original sim or live fixture was changed.
