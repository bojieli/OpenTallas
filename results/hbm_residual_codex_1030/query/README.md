Query fixed-calendar source preparation, 2026-10-30

UNADOPTED. Generic physical view be0b530febe5 remains HOLD: its single recipe value173 cannot qualify the actual three171/one173 native roles. These source wrappers add no flops, arithmetic or cycles. Existing pin shell and VM calendars are preserved.

Authoritative native source: intel1:/srv/opentallas-scratch2/claude/die-hbm-31/b31t/out/asbuilt.json, modules.hbm_current_native_top; direct cell parameters and all16 port connections checked by query_compose_aliases.py. Actual role map from map_d29c.json and bind owner:

| Native instance | Part / plan descriptor | Fixed master |
| --- | --- | --- |
| hb_idx__op_NE | NE_hub / u_hb_idx__op_Q__q1 | ot_hbm_idx_vm_query_static_n12__rt171 |
| hb_idx__op_NW | NW_hub / u_hb_idx__op_Q__q1 | ot_hbm_idx_vm_query_static_n12__rt173 |
| hb_idx__op_SE | NE_hub / u_hb_idx__op_Q__q0 | ot_hbm_idx_vm_query_static_n12__rt171 |
| hb_idx__op_SW | NW_hub / u_hb_idx__op_Q__q0 | ot_hbm_idx_vm_query_static_n12__rt171 |

The constructor emits a separate native-compose candidate, clones the original blackbox port module twice, replaces only the four exact cell types/parameters, and proves reversing these declared changes restores every original cell. Every other module and cell remains the original object. It rejects all four wrong-RT native mutants. The output is a cache preparation artifact, not an elaborated RTL netlist or an adopted die plan. RTL meaning comes from the two direct-wire fixed-parameter wrappers and recipes. No master-match rule is weakened. The original four source files are byte-identical at current source HEAD and the old recipe's d34578d6f commit.

Run under ot-run4GB/1thread on intel1: both171 and173 wrappers match all1185 output bits, four-state, for650cycles against their exact native parameter module. Each probe loads weights, completes3queries and14request/return beats, and checks reference fault stays0. The wrong-calendar mutant171↔173 raises fault for each probe. Results are lockstep.log; testbench and runnable command preserved here. Native alias actual-cache proof ran under ot-run8GB/1thread; manifest records4wrong-RT mutants rejected.

Physical next step is a batched parent-approved plan/compose alias event assigning each descriptor the matching master while preserving outline, all ports, clocks and calendars. Only then may role-specific centre/shallow-clock kits be prepared and independently rendered/reviewed before P&R. No P&R, signed count, calendar composition or adopted-plan claim is made by this source preparation.
