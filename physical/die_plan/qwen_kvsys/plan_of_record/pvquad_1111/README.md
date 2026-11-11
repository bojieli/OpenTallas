# KV pv family: pinwheel-quad form (quadw), CPL-KV-PV-3, 2026-11-11

STAGE S2 (type floorplan), DO_NOT_COUNT. COORD ruling 11-11 (a) adopt the pinwheel quad, (b) broadcast = register
stage per group in the centre column. This is for the NEXT KV die event (DIE-KV-99), not the 12:00 cut.

Result plan (not in git, 43 MB):
- epyc8 + epyc7 /srv/opentallas-scratch2/claude/cpl-kv-pv-work/quad3/plan_c_pvquad_1111.json
- epyc4 /srv/opentallas-scratch3/claude/cpl-kv-pv-3/plan_qw1_fin.json
- md5 4ddb637138f804fa2a2a6897057d1909, sha256 1f2cd09a03a334b7da80068beb1e23a40f5222a292a3efead028a7543b2e21a6
- Base: KV cut plan bfe4c242 (epyc4 /srv/opentallas-scratch2/claude/dkv98/kv1200/plan_c.json, see ../kv1200_cut).

## Form
All 16 kv3_pv* types (pv_S x8, pv_N x8, outline unchanged 2160 x 1520.64). Each pair group pK feeds its join face tsK.
The 4 groups are placed as a pinwheel around the join: p0 (0,0) MX, p3 (PW+GAP,0) MX, p1 (0,449.28) R0,
p2 (PW+GAP,449.28) R0, join (JX,233.28) R0. The image is mirrored per group to the base join orient. Clock taps move
rigidly with their core. Parameters (quadw): GAP 103.68, JX 345.6, RQ 1278.72, QY0 43.2, QY1 734.4. The centre
column (spine) is x 872.64 - 1278.72, free of hard cores. Positions and orients only: hard_cores origin/orient change.
The netlist is unchanged except the ft stations/pin cycles below. Delta: evidence/delta_kv_pv_qw1.json.

Why: the 1024-b join ts of the far pair crossed the near pair, and the near pair is M1-M5 blocked (M7 only). That local
bisection cut is the FEAS-AUDIT-2 0.44 failure. Legal moves cannot fix it. In the quad, every pair abuts its own join
face, so no ts crosses a foreign pair (skeleton GRT demand 3.13M -> 1.29M, ts overflow -99.7%; see INTENT_pv_quad.txt).

## Steps (scripts/, run on epyc4 under nice 19)
1. quad_delta.py: quad delta + applied plan (8.64 lattice + overlap check).
2. station_resite (tools/die_plan): re-sites the internal forward stations around the new core sites.
   46 chains need +1 cycle; they are on 24 lanes (parallel chains of one bus share the lane cycle).
3. ft_strip.py: drops ft slot sites/regs within a hard core +4.32 halo. It moves 2 reset local taps per type that
   were blocked ((8.64,544.32) -> (8.64,483.84), (2047.68,544.32) -> (2047.68,483.84)).
4. tools/die_plan/ft_sites_unblock.py re-sites the ft chains. Patch in this branch: when allocation fails within
   20 um, the search widens to 80 um; the existing hop check still rejects an over-reach chain.
5. band_strip.py + bandfill.py + bandmerge.py: landing bands overlapping a moved core are marked FAIL and refilled with
   clock_landing_plan fill_failed_bands (monitor bands slide instead).
6. lat_update.py adds the +1 to fixed_cycles of the 24 lanes (evidence/lat_delta_qw1.tsv), then
   tools/die_plan/gen.py latency --inplace regenerates the table (2404 lanes). G0 check_latency compares both.

## Gates (measured on the result plan)
- G0 (tools/die_plan/check.py): 60 errors vs 130 on the base; 0 NEW, 70 GONE (the old "station cells intersect
  physical macros" errors on pv types are gone). This includes the latency check. evidence/g0_diff_vs_kv1200.txt.
- Pin cycles: 46 chain cycles = +1 on 24 lanes (approved by COORD 11-11). TOK pricing of these 24 lanes: TOK-VERIFY-1
  (owner 12.21: tok/s is not a gate).
- S2 route_supply, all 16 types, with bind-traced core_conns (evidence/core_conns_traced_pv.json.gz, from
  the event28w_c kit bound netlists; kv3_pv_v6 uses kv3_pv_v4, kv3_pv uses kv3_pv_v8, kv3_pv_v5 uses kv3_pv_v5n:
  identical bus sets, no bound netlist on the fleet). Verdict ok on 16/16 (evidence/rs_traced_after_pvquad.tsv).
  - core/street (flag 1.0): max 0.994 (v12 street_H). 0.8-1.0 band: v12 street_H 0.994, v2 core_H 0.861,
    v2n core_H 0.805. WRITTEN REASON: these are the pv2/pe2 face buses of the far pair passing the spine-side pair
    (one 396/652-b vport leg per group). The routed check is the GRT probe of the event.
  - ring (flag 3.0): max 1.61 (v8, v2 1.605). These are the vport/astk landing bands at the top face.
  - Before (kv1200, same traced conns): verdict ok on 16/16 too, core/street max 0.91. route_supply does not see the local
    M7-only bisection cut that fails GRT, so the quad is justified by the cut (above), not by this score.
  - The stock core_conns (every core pin -> every face bus) still FLAG: street_H 2.31-2.39 on the n types, 1.10-1.42 on the others.
    Before the quad, the same stock model gave 4.2-4.3 and 1.57-1.62. The traced conns replace that over-merge.

## (b) Broadcast buses: register stage per group in the centre column
The only true broadcast in the pv type is i_pvw__u_ctl_cmd (32 b, bc/bcx to all 16 pairs). Every other "broadcast"
in the stock conns is face-bus slicing through the existing per-pair delay lines (ot_dp_dly pd<D>_*, D 5..104).
ctl_cmd already goes through pd5/pd6 delay lines per destination. The form: the first stage of the ctl_cmd delay
line is shared per group and sited in the spine at the group's join row (y QY0 / QY1 band, x 872.64 - 1278.72), fanning
out 4 pairs locally. There are 0 new cycles because the delay depth (5/6) already includes it. There is no plan field for a glue
register site, so the kit places it (GPL). DIE-KV-99: if the event needs it pinned, add it as an internal station per
group on bus i_pvw__u_ctl_cmd. There is no serialisation.

## Overlap to watch
COORD (D) K1-K3: the sys_c/hub trunk is routed down the pv spine (DIE-LAYOUT-KVHEAD). The spine has no hard cores. The ctl_cmd
group stage is 32 b x 4. The trunk owner should check that the spine track demand stays below 1.0 with both.

## Views
evidence/explorer_kv3_pv_v{2,4n}_before_after.png (stock conns in the explorer; the heat bar across the old join row is gone).
