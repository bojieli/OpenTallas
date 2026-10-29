# DIE-KV-36 KV-022: sys_SD / sys_SD_v1 OT_CLAND groups off the PHY macro (fix-only delta)

Cause (CHECKED): the event26 sidecar `collector.types[T].tree` was composed before the x6 PHY abstract
(ot_qfd_serdes_112g_x6_phy_w522 @ 17.28,54.0 size 1848.96x972) existed: 17 taps, 25 relays on the macro
(e.g. u_cland_collect_rst_n_t10 @ 1702.08,406.08). The current reset tree (`reset_tree.for_type` on the
current plan, macro = blockage) has 69 relays, 15 taps, depth 5, max hop 376.2 um, 0 relays on the macro.

Delta (`mk_sd36.py`, no new check kinds): collector tree := current reset_tree.for_type tree; each local
source re-tapped to the nearest current rst_n_t* (<= 405 um); asserts collector depth <= boot budget.
- Variant A: i_host_fdi -> t13 (279.9 um), i_host_link_rst_n -> t5 (124.2 um); max hop 361.5; depth 6 (was 6).
- Variant B: both sources -> t5 (337.8 / 124.2 um); max hop 354.2; depth 6.

Results (CHECKED): strict bind A/B errors 0 unbound 0 undriven 0 multiply_bound 0; kit-rtl + PHY specialize rc 0;
gen phys rc 0; KIT_PREFLIGHT PASS issues 0 (4 kits); OT_CLAND groups on macro+halo: 0/25 (A), 0/15 (B).
Place: epyc2 kits{A,B}/<T>, `run_kit.sh <T> cts 24 8` via ot-run (port_bind = in-flow face_guard pre-floor).

Not done (UNCHECKED): die_islands_um (46 clock + 105 relay die cells over the macro) are tile blockages only;
siting those die cells off the macro needs the die clock tool rerun with the macro as blockage (die-plan item).
Files: var.sh (bind+kit-rtl), gen.sh (gen phys+preflight), sd36{A,B}_delta.json, recipe_kv27f_sd36{A,B}.json,
bind_report_{A,B}.json, preflight_{A,B}_<T>.json, probe_tree.py.
