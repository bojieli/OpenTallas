# DIE-HBM-25 (HBM die owner, 2026-10-29 19:23- PDT)

Run dirs intel1:/srv/opentallas-scratch2/claude/die-hbm-25/{plan/d25a,plan/d25b,g4,b_ids,b_046a,b_all,chk}.
Strict bind = `bind.py bind --strict --all-gaps` with the HBM-BIND-13 g3 elaboration cache (no re-elaboration).

## Plan d25a = d24a + Codex d23c_ids (HBM-045) (CHECKED)
d24a die_plan is byte-identical to d23c (77d613ccd600), so Codex `source_ids.py` output 128ad3093cb4 (52 SU lane
`lane_lane_id` straps set to the as-built literal terminals, 0 RTL, 0 cycles) applies unchanged; core_macros = d24a
5047d56dac7e. G0 PASS 0 err; G0C 8 errors, message-identical to d24a. Strict bind (g3 compose): 163 -> **103** =
92 UNPLANNED + 11 EMIT; the 60 parent-ID errors are gone, 0 new (b_ids).

## HBM-046 (A) compose cut exposes the leaf: SU pretree (CHECKED)
The 8 SU pretree cuts (`su_*.__cut_pretree`) named their one reset port `pretree_rst_n`; its only terminal is
`u_slice.g_pretree.u_pt.rst_n` = slice `rst_n` (ot_hbm_su_static_pgslice_s.sv:390), the plan pin `rst_n`.
`mk_compose_pretree_rst.py` renames that port (module ot_hnx_su_pretree__rst), nothing tied/moved -> g4 compose
(`mk_g4_manifest.py`). Bind d25a + g4: 103 -> **95** (8 pretree EMIT gone, 0 new) (b_046a). (B) not needed: the
source has the same structure as the plan.

## HBM-047/048 (B) plan follows source: root split pieces of whole-bound reuse masters (CHECKED)
u_tkm_SW (ot_hgi_coll_tkm_m_tp192_p) and u_hc_eng (ot_hbm_hc_root_static_s) are reuse contents bound as ONE leaf; the
plan hard cores are their split pieces. Source:
- tkm: master rst_n feeds only the root logic flops + u_buffer (ot_hgi_coll_tkm_static_p.sv:116/127/178); the 32
  tiles are reset-free -> piece u_tkm_SW_root.rst_n IS the master port (kind `port`).
- hc: master rst_n -> ot_rst_relay u_rst -> rst_c = rn[0] (ot_hbm_hc_root_static_s.sv:109-110) -> tail units -> sinkhorn
  u_ss rst_n -> the sk_steady piece resets are master-INTERNAL relayed nets, not die wavefront consumers (kind `internal`).
(A) (compose cut) is wrong for hc (the cut input would get a second driver) and needs a dissolve + re-elaboration
for tkm, so (B) is adopted. Tool change (shared, needs ROOT-MERGE): hard-core field `reset_from_master
{kind port|internal, content, pin, source}` (schema.py + die_plan.schema.json; reset_tree.core_reset_targets skips
`internal`, fails closed on an unknown content; bind drives the master leaf port from the piece tap for `port`, one
unshared leaf). Plan d25b 77fb5f395968 = d25a + 3 declarations (`mk_d25b.py`), no geometry/pins/cycles.
G0 PASS 0; G0C 8 errors message-identical to d24a. Bind d25b + g4: **92 = 92 UNPLANNED (82,285 b) + 0 EMIT**
(b_all), tied/undriven/multiply_bound 0/0/0; root RTL: u_u_tkm_SW.rst_n(rst_n_t108), u_u_hc_eng.rst_n(rst_n).
Tests: test_reset_wavefront (+1 new) / test_bind_wavefront / test_bind_all_gaps PASS (python:3.11 docker).

## Far pairs: Codex L7c_alloc_v4 G0C (collect only) (CHECKED)
intel1 codex-hbm-ft-1849/check_l7c_alloc_v4: G0C FAIL 12 errors, all message-identical to the L7c base (0 new), but
L7c base itself has 12 vs d24a 8 core_faces (q_hub_ne 22 vs 13 face-away ports). Decision: NOT adopted yet; adopt
L7c+FT only after Codex facefix1861 (qctl/query re-pin, re-kit owed) brings G0C core_faces back to <= the d24a set.

## HBM-052 opstore_a MAP_AMBIGUOUS (analysis, CHECKED)
canonical_ports_split.json type sfu_opstore_a / ot_hgi_sfu_core_split3__opstore_a__388.8x345.6 cut_pins has 8 buses;
the current plan pin table (c20g 390.528x436.32) has 29 -> 21 missing, 0 extra (first alphabetic miss
g_operand_0_u_group_sw_mask). Fix = regenerate the canonical cut map for the current pin table (harden/kit tool).
