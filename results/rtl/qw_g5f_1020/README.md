# QW-G5F 10-20 -- g5f fault-OR emission: prerequisites on the actual dv2f20g5 GEN (d502ea9ae)

Base: codex/qw-g5f-fault-1020 @94341cb20 (qfd_fault_capture early-sticky leaf, bench PASS 133 checks, 2 mutants FAIL).
NOT a GEN, NOT a gate. physical_qualification_eligible = false.

## 1. Actual g5 early-sticky proposal regenerated (the Codex 08:12 fail-closed item)
The "missing absolute fwd_lane RTL authority" refusal was only a missing `--src-prefix`: port_bind lists
`/srv/opentallas-scratch/claude/mu-die-qw/dv2f20g5/src/physical/qwen_fwd_lane/qfd_fwd_lane_masters.sv`; with
`--src-prefix /srv/opentallas-scratch/claude/mu-die-qw/dv2f20g5/src/` it resolves to the committed file at d502ea9ae.
`g5_early_sticky_proposal.json`: 498 bits / 425 ports / 340 (clock,reset) groups / 344 nodes / 1,874 FF,
capture_mode early_sticky_optin, actual_sys_face_obs_fault_input = false (unchanged numbers vs the legacy proposal).

## 2. Mapped native census of the leaf (ASAP7 TT RVT, Yosys, tools/ref_tile/native_census.py from main)
fleet ep6 unit oth-ubuntu-3230684-1792509675 (census/run.sh):
| top | status | max dynamic loads | net |
|---|---|---|---|
| qfd_fault_capture N=16 | PASS | 18 | rs (N+2) |
| qfd_fault_capture N=1  | PASS | 3  | rs |
| qfd_fault_or N=16      | PASS | 18 | rl[1] internal (rs 2) |
Area N=16: 9.90 um2 (76.6% sequential).

## 3. Die-level reset-net census (die_rs_census.py on the g5 die.v)
Existing die-top loads per reset net + capture direct rs loads: 332 reset nets, max existing 8.
ONE violation: n_rst_io__t173 = 1 + 80 = 81 > 32 -- all 70 bits are io_collective (closed
qfd_collective_static_io_production view, no such pins). Every other net <= 18. -> the collective bits must be ORed
inside the collective into its existing `fault` pin (RTL + re-close; collective owner), which also removes the
missing-pin problem; or the GEN reset tree gives that group a regional ot_rst_relay leaf.

## 4. Why no g5f GEN / die chain was launched
All die-top instances are hard masters placed by place.tcl (13,766, incl. relays/landings 65x30); there is no soft
die-top logic. Emission therefore needs a GEN-core pass in tools/qwen_rom_fulldie_b3r2.py after _relays and before
_reset_tree: place capture nodes as hard qfd_fault_capture_N masters (LEF/lib/die_glue via gen_relay_rtl INST regex,
die_sta_libs), emit the 383 landing `fault` pins, route the cross-domain tree as landed 1-bit lanes (fault_or_plan:
85 crossings / 450 hops on g4g) through the relay allocator, feed the reset tree / clock regions. And the root has
no sink: the bound sys_face view has no obs_fault (Q.MU.FACE.3, critical n32o/n32oa kits). A chain of an unchanged
g5 would duplicate the live g5/g5b units 3021575/3021574.
