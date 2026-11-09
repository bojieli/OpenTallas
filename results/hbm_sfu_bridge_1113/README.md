SFU native cut latency contract, private source, 2026-11-08

Accepted source: p37su4 compose_t9 creates sfucore_{NW,NE}.__cut_ctl,
master ot_hgi_sfu_core_split3__ctl, 34 ports / 57 members. Native closed
source results/hbm_ctl_native_intake_0440/closure_ot_hgi_sfu_core_split3__ctl.sv
sha256 ff736f49006105d4f4cfd092302867f0615d045aafc19277b804e5dd47f52482.
The existing closure proof is not repeated. An exact all-bit census checks
136 local_rq and 2248 local_wq output FF bits, 2056 local_rr and 8 local_w_done
input FF bits. Therefore intrinsic read_k=2/write_k=2. LG_PATH+1 includes
removed external stages and must not be added again to the external loop.

W3 external read125/write122 gives SFU_READ_RETURN127/SFU_WRITE_RETURN124.
The generated ctl top exposes those two parameters and keeps prototype defaults
145/142; no plan is adopted. Its source comes from the unchanged native closure.
The native FR prototype (source ad36a708f370b10a, existing 1108 generator) exposes
SFU_RDX through top -> sfu -> lane -> read-tag pipeline. Default91 is unchanged:
2 retained store-side edges + external request41/return48. The final value must
be recalculated from the final operand-loop table; bridge125 is another loop.

bind.py opt-in substitute_composed_inst runs after composition, before Graph
and param_regen. Rules must name the exact old master and preserve the full ABI.
For ctl: {"inst":"sfucore_N[EW]\\.__cut_ctl", "master":"ot_hgi_sfu_core_split3__ctl",
"module":"ot_hgi_sfu_sp2_ctl"}. Add the generated source to asbuilt files/prefer.
The private plan master must also be changed to the variant for closure. No native
re-elaboration is needed solely to discover new defaults: the source header seeds
the selected variant's param_defaults. No geometry or core pin cycle is changed.

Checks: seven focused source/ABI tests PASS, including wrong master, width,
direction, new input and rotated request-bit mutants. Run:
python3 -I tools/die_plan/test_bind_composed_variant.py

Smallest mechanism: actual embedded native bridge plus the four retained native
boundary FF vectors against independent external125/122 responder, 3000 cycles.
Good127/124: no fault/data mismatch. Read-1 mutant caught cycle136 (1391 bad data),
write-1 caught160; stale145/142 caught129 (5435 bad data). Source and bench retained
here. Full control-core arithmetic, whole-die LEC and physical qualification are
not claimed. This is the concrete component for the parent-owned final LAT bind.
Runtime E4 /srv/opentallas-scratch3/claude/codex-hbm-kcls-1113/sfu_bridge,
unit oth-ubuntu-2880480-1794165907, exit0. No P&R launched.
