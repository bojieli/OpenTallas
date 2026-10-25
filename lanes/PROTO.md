# PROTO (virtual prototyping sweep, 2026-10-24 evening; rtx-pro coordinator lane agent)
Branch claude/proto-1024r (worktree rtx-pro:/home/ubuntu/wt/proto-1024r, base origin/main a11334b98). Fleet data: <host>:/srv/opentallas-scratch2/claude/proto/ (ot-run --dir, spills).
Goal: prove every partition type without a SIGNED view is routable / roughly meets timing BEFORE detailed route (no DRT).
Method (tools/die_plan/proto_sweep.py + proto_render.py, on the branch): the G2 partition probe (g2.part_probe: exact
outline + plan pins, one boundary flop per pin bit, ft station flops at regs_um / along the route, hard cores + leaves as
placement blockages + M1..obs_max OBS) + one ideal clock on every flop + plan IO budget 0.2 T + 60/25 ps uncertainty +
repair_design + GRT M2..top with the partition's own logic as capacity adjust 0.5 + STA on GRT RC (TT setup / FF hold).
SKELETON prototype: partition logic not synthesised (B2m and the KV v4 bind have no bound RTL; hard-core views mostly
unrouted), so STA covers the plan wires only (pin->reg, ft hops, repeater pitch). Classes: CLEAN / HOTSPOT / STRUCTURAL.
## Log
2026-10-24 21:48 PDT PROTO: started. Pilot (4 probes: B2m q_b000/q_su00, KV kv3_hg, QC sle_hc0) running via ot-run; then batches HBM B2m -> KV -> QC -> head -> S81.
