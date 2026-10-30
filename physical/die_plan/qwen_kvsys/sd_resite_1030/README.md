# DIE-KV-47-SD: kv3_sys_SD / kv3_sys_SD_v1 one-block re-site (2026-10-30 16:13 PDT)

One-block delta on plan of record event28w_c (plan_c.json 16980115-based, sidecar eW_sidecar.json):
1. Declares the x6 SerDes PHY macro (DIE-KV-46 delta: physical_inst u_bound.u_core.u_phy.g_native.u_macro,
   masters ot_qfd_serdes_112g_x6_phy_w522 / _w521, origin [17.28,54] outline [1848.96,972] R0, views
   results/kv_serdes_pg_event33) and the two VDDPHY pg domains (serdes_pg_domains.json) bound to that body
   (phy_macro_binding; bump rect = domain rect = body, so no PHY bumps on the core-VDD S/E strips).
2. Moves every blocked local reset tap, collector relay and landing band off the macro onto the legal strips
   (54-um S strip, 34.56-um E strip, W rim) with the existing forms: CL._storage_band (DIE-KV-33),
   head_reset_local_taps.cover_sites 300 um (DIE-KV-33), collector_tree = reset_tree.for_type (DIE-KV-36).
   Pins, outline, origin, orient, neighbours, every other type and the sidecar non-collector data are unchanged
   (asserted fail-closed in mk_sd47.py). Depth 5 unchanged, max hop 376.2 <= reach 405; collector depth 6 <= 6.

Rebuild: python3 mk_sd47.py PLAN_IN SIDECAR_IN serdes_pg_domains.json OUT_DIR (from repo root). Numbers: report.json,
proofs.json; renders render/*.png. Kit-wave KV kit-rtl script: ../kit_wave/kit_rtl.sh (bind kit-rtl, then
specialize_serdes_phy.py for the two SD types only). proof_kits.sh = the kit-rtl -> gen phys -> kit_preflight proof.
Shared tool fix needed for kit_preflight on a physical_inst specialization: tools/die_plan/kit_contract.py
_plan_contents (separate commit; ROOT-MERGE approval).
