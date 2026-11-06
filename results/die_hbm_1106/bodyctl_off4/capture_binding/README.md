# Capture and raw-D source binding

PASS, Fri Nov6 07:37:25 PST2026. Deterministic mechanical audit only; no new heavy tests, production edits, whole-body LEC, or P&R.

Canonical source SHA256 f732f5b5486b744e0480b9de4833d7d5665b94c5a72117c676c445f76998a318. Production source_capture_manifest.json was copied read-only from intel2:/srv/opentallas-scratch2/claude/wt/codex-bodyctl-off4-1106/results/die_hbm_1106/bodyctl_off4/source_capture_manifest.json. Both hashes are recorded in capture_binding_audit.json.

The audit resolves every public it32/b16/c16/d16 bit alias to its original input FF Q bit and scalar capture D. It reconstructs iteration bytes high3..low0 and stride bytes high..low from those actual Ds; all three manifest iteration_D/step_D vectors match token-for-token. Full80 scalar mappings and four original vector capture statements are recorded in the JSON. No selected.json rewind assumptions were needed.

Four original input capture processes,21 native product capture processes, and3 original output processes are literal unconditional posedge clk_control statements with one sequential writer, plain uninitialized reg declarations, no blocking/initialization writer, no reset and no enable. Exact statements are recorded in JSON. Physical BODY top ports clk_control/program/issue connect to root clk, clk_upipe={16{clk}}, clk_qslots={29{clk}}. Intermediate __mc→_x binds these five ports identically by name. All clocks actually used by the28 audited vector capture processes are clk_control, resolving to root clk, equal to helper clk_control. Unused clk_reduce bindings are recorded for transparency but are outside this audit's five-port assertion and capture set.

Scope: functional equality after the original three-capture fill for defined arbitrary D inputs. Native input/product/output FFs have no reset; initial unknown states are not equated. Upstream hold behavior and reset-driven changes remain inside unconstrained D, sampled at the same root clock. The existing universal actual-flat-cone SAT proof and three-edge helper stream proof are unchanged supporting evidence. No added protocol cycles.

Run `python3 -I audit.py`. It reads the private canonical source snapshot in ../flat_binding/source_readonly.sv when present; otherwise it reads the pinned canonical remote tree path. capture_binding_audit.json is the result. Exact copied production manifest is source_capture_manifest.json. Authoritative Intel2 mirror: /srv/opentallas-scratch2/claude/codex-off32-edge3-1106/capture_binding.
