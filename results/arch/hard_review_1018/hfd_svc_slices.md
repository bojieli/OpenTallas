# Hard review: hfd_svc_SW_s0..s8 / hfd_svc_SE_s0..s8 (HBM service slices)

Reviewed 2026-10-18 (read only).

## Verdict: NOT on the current HBM die (d4g GEN2). Retired. No redesign owed.

Evidence:
- The current HBM die is `results/fleet_viz/die_sources.json` (origin/main) -> "GEN2 d4g, strict die port-bind PASS",
  `/home/ubuntu/artifacts/hdie-d4/d4g_gen2/pb0/port_bind.json` (97 masters, 1,214 instances, verdict PASS, 0 stubs, 0 ties).
  It has **no `hfd_svc*` master or instance**: `grep -c hfd_svc /home/ubuntu/artifacts/hdie-d4/d4g_gen2/pb0/die.v` = 0.
- Lineage: `hfd_svc_{SW,SE}_s0..s8` = v14-era stream-service band (first routes 10-08..10-12). They were
  superseded by the v15.1 band `hfd_svc_v15_*` (ELEMENTS.md rows 1613-1616: "superseded"; HANDOFF 10-16 00:43
  "hfd_svc_v15_* are superseded (not in v16 die.v)"). The v15 band was then retired in turn:
  `/home/ubuntu/artifacts/hdie-d4/d4g_gen1/compose/pre_relay.json.gz` -> `retired_v15`: "v15 service band (hfd_svc_v15_*):
  replaced by the SM-specific 4-PC service engine (ctl_<q>_pNN + svg_<q><k>), Codex DECISION 14:40, H-DIE 1705
  (exposed 816 band inputs retired with it)"; HANDOFF line ~47 (10-15 17:05: "Codex candidates adopted as primary:
  HBM SM-specific 4-PC service engine (13 SRAM/SM)").

## What replaced them (in GEN2)
| GEN2 master | instances | role |
|---|---|---|
| `ot_hbm_svc_pc_ctrl_leaf_cfg_h9b` | 64 (`ctl_SW_p00`...) | one per HBM pseudo-channel, beside its SM |
| `ot_hbm_svc_sm_group_id` | 16 (`svg_SW0`...) | per-SM group (4 PCs) |
| `ot_hbm_svc_sm_xcal_t`, `ot_hbm_svc_vm_kshare_splitstrap` | 16 each | per-SM calendar / VM key share |
| `ot_hbm_svc_vmdel_lane_n` | 32 | VM delivery lanes |
| `ot_hbm_svc_stack_fault`, `ot_hbm_svc_wb_kport_q`, `ot_hbm_svc_wbw_copy` | 4 each | per-quadrant services |

So the "18 near-identical slices" question is already answered by the design: the replacement is ONE hardened PC
leaf replicated x64 plus one SM group leaf x16 (dedup done; single param set each per port_bind `param_sets`).

## Post-mortem (short): why so many routes (26-42 each) and why not bindable
Route counts (ELEMENTS.md rows 2043-2059, "x/y/routes"): SE s0 36, s1 36, s2 33, s3 39, s4 34, s5 38, s6 26, s7 35,
s8 22; SW s0 34, s1 34, s2 36, s3 42, s4 28, s5 34, s6 41, s7 36. Failure classes from
`/home/ubuntu/claude-takeover-20261007/setup-triage.md` (rows 50-59, 150-153, 202-317):
- **D (high fanout)**, most common: one select/queue register driving 131-280 endpoints across 400-900 um
  (SE_s1 gq[1] 131 ep -189 ps; SE_s2 gq[4] 280 ep; SE_s4 / SW_s7 sv_q -> 228/254 ep, 730-905 um; SW_s6).
- **A (clock skew / IO reference)**: SW_s2 0-logic input path +517 ps internal skew; SE_s5 launch/capture +305..+531;
  SW_s5 unbuffered 235 ps clock wire.
- **F (wire)**: SW_s3 430 um to u_wa.
- **B (constraint)**: SE_s3 -1,258 = input budget against a negedge capture; SE_s1 forwarded-clock false path (fixed c4ffc4f9d).
- Several "closed" records later REVOKED under a consistent clock split (SE_s6/s7/s8, SW_s4), and NEEDS_RTL reset paths
  (`u_rs.rst_s[1] -> ...rv`, SE_s7/SW_s5/SE_s2).
- "Not die-bindable (native)": the routed native audit judged the views against the later die standard
  (registered pins, regional reset, neighbour-relative clock); the d4f/d4g contracts never had slots for these slices,
  and the 10-18 0gf note says the table's native column was a static 10-16 file (stale). Moot either way: no current die binds them.

**Root cause (historical):** wrong partition. Each slice was a long band segment that held several PCs plus a shared
distribution register mass (gq / sv_q select and queue registers) fanning across the segment, with one balanced
clock tree over 0.5-1 mm and unregistered band pins. The retries chased fanout buffering, IO budgets and skew
(symptoms) on 17 hand-built, slightly different slices. The fix was structural and has been made: per-PC leaf beside
its SM + per-SM group, replicated, inside quadrant clock regions (d4g).

**Verdict:** ABANDON (already abandoned/retired; do not reroute or dedupe these). Risk: LOW (to the current die).
Redesign cost: zero new. The replacements are already in GEN2.
Action: mark the 17 `hfd_svc_{SW,SE}_s*` rows superseded -> `ot_hbm_svc_pc_ctrl_leaf_cfg_h9b` / `ot_hbm_svc_sm_group_id`
in the die_sources.json `supersede` map, so the element table stops listing them as "closed, not die-bindable".
(Note: the table lists SW s0..s7 + SE s0..s8 = 17 slices, not 18; SW_s8 has no row.)

PNGs: none viewed. The slices are not on the current die, and their job dirs were trimmed/offloaded 10-15/16 (ELEMENTS.md last-status column).
