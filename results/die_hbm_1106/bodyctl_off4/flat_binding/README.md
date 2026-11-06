# Actual flattened phase3 source binding

Measured Fri Nov6 07:33:32 PST2026. PASS. No production edits or P&R.

Read-only source: intel2:/srv/opentallas-scratch2/claude/wt/codex-bodyctl-rcp1-1106/rtl/hbm_accel/cores_split/reform_1105s/q3/ot_hfd_coll_q3_body_ctl.sv.
Exact SHA256 f732f5b5486b744e0480b9de4833d7d5665b94c5a72117c676c445f76998a318. extract.py pins this hash and evaluates only OT_Q3CTL_MUL4_RT=false; all other source directives remain untouched. Local source_readonly.sv is a private read-only snapshot used solely for extraction.

actual_refs.sv contains actual_pb / actual_pc / actual_pd standalone combinational modules. Each copies13 original reachable assign statements, original wire widths/names, plus only port bindings to its seven productQ registers and its actual phase3 D expression. Recursive dependency traversal asserts no missing driver, no extra state dependency and no multiple driver. Native productD expressions are checked to be actual multiplications and saved in manifest.json. No multiplication is included in the proof.

| Output FF | Field | Allowed productQ boundaries |
| --- | --- | --- |
| _237566_ | pb | _237584_ through _237590_ |
| _237567_ | pc | _237591_ through _237597_ |
| _237568_ | pd | _237598_ through _237604_ |

miter.sv feeds arbitrary seven16bit product words (112 unconstrained bits) to all three actual cones and compares each to canonical low32 off() expression. Yosys SAT proves correct=1 universally: `SAT proof finished - no model found: SUCCESS!`. A separate control flips bit16 of actual_pb; SAT finds a failing model: `SAT proof finished - model found: FAIL!`. This is the expected mutant result, retained in mutant.log.

Run: python3 -I extract.py; submit bash prove.sh through ot-run. Successful job oth-ubuntu-3421106-1793979178 exited0. Actual proof took0.18s Yosys CPU/wall-reported runtime, peak23.13MB. proof.log, mutant.log, verdict.txt and manifest.json are authoritative results. This supplies only final arithmetic source binding; parent's factorD mechanical manifest covers raw source vectors, clocks, reset and output capture placement.

Authoritative remote artifacts: intel2:/srv/opentallas-scratch2/claude/codex-off32-edge3-1106/flat_binding. Local artifact mirror: /home/ubuntu/coord/tmp/codex-off32-edge3/flat_binding. Existing helper/stream proof files in the parent directory were untouched by this extension.
