# sfu_ctl bit-level cut map on the d44o plan pins (HBM-CORES-KITS-37/lec2c, 2026-10-31 18:42 PDT)

Failure fixed: `MAP_AMBIGUOUS ot_hgi_sfu_core_split3__ctl: plan bus ro_v_e not in the cut map` (view
ot_hgi_sfu_core_split3__ctl@6d5831d90fa5, plan d44o; DIE-HBM-57 genprobe). The stored whole-bus map
(canonical_ports_split.json sfu_ctl) lists 17 of 108 buses; the RTL top regroups the rest (plan ro_x/ro_v_{n,s,e,w}
vs RTL u_core_ro_x/ro_v_{e,w}, 16 per-lane ro_x[32] = u_core_e_rox[512], ...). Same method as HBM-052
(results/hbm_cores_kits_24/opstore_a).

All CHECKED:
* d44o pins cores/ot_hgi_sfu_core_split3__ctl__669.6x626.4__canon__codex_g21.json (sha 6d5831d9...) = ports_cut.json
  ctl piece: 108 buses, 11819 bits, same names and widths.
* master elab `elab.ys` (= opstore_a elab.ys) in docker openroad/orfs:asap7lock on intel1, 48 GB cap; master json
  sha256 6d8f4455...
* `split_bitmap.py` (cut = ports_cut.json, rest top ot_hgi_sfu_split3_ctl_core): 108/108 buses, 0 problems,
  0 RTL inputs uncovered, 0 outputs open; mapper UNPROVEN on 1 bus: io_word NARROW (470 of 471 master bits).
* `prove_unproven.py` (copy of the opstore_a script) over ALL 108 buses with the cut record
  split/wip_unverified/ot_hgi_sfu_core_split3__ctl.map.json: 107 PROVED by net identity, 11755/11755 bits, 0 differ;
  io_word 470/470 SAME_NET (master io_word[470] is a cut dead bit; RTL ties io_word__full[470]=0).
  u_core_u_vm_stage_mask: cut record 64 x 1, master u_core.u_vm.stage_mask 64 x constant 1, RTL output {64{1}}.
* Sidecar physical/die_plan/hbm/cores/harden/canonical_bitmap_split.json: new type sfu_ctl (mapper_verdict UNPROVEN,
  proofs, check.verdict PASS); sfu_opstore_a entry byte-identical.

Kit (intel2 /srv/opentallas-scratch2/claude/hbm-k37l2c/gen/ot_hgi_sfu_core_split3__ctl_6d5831d90fa5, current src 94634129b96):
`gen_core_kit_hbm.py --views .../d44o/core_views.json --view ot_hgi_sfu_core_split3__ctl@6d5831d90fa5
--clock-pin-entry on --core-macros auto` -> GEN_OK, 11819 pins, face_flops 11807, const_out_bits 64 (stage_mask),
kit_hash cb17d846b9c7f129. kit_gen_lint: GEN_LINT PASS issues 0. kit_preflight --contract --plan-dir d44o_cm:
KIT_PREFLIGHT PASS issues 0 (macro/mesh/island checks NA: no macros). No place/route, no LEC run.
