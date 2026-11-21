# FAM-KV-IOPC-R2 handoff (11-21 11:4x PST)
Work dir epyc7 /srv/opentallas-scratch2/claude/fam-kv-iopc-r2 (repo = lane clone on main, tmp/, views_d27b/ = 4 fixed pc views, tree_pc = cp -al of D26 src + those views, diag_ioc/ = io_cor_v1 diag). Predecessor dirs: epyc7 /srv/opentallas-scratch2/claude/fam-kv-iopc (proof_A, tree_d26, br2 = 41 bank_taps rows).
No jobs running.

## Done
- PDN-0006 FIXED: pc_v3 kit (private spec ~/coord/autopilot/private_specs/FAM-KV-IOPC-R2/qwen_kvsys_kv3_pc_v3_1121101204, kit epyc7 kw43-wave-1109/.../KV-D26/private/FAM-KV-IOPC-R2/kv3_pc_v3_1121101204/gen/kv3_pc_v3) floorplans rc 0 with the D27b exact-OBS views; PDN-0007 3.1 % only. Views pcc 1883d59424fe, pcc_h_head_p dab80c4090c2, pcf dc76858fb9ed, pcf_h_head_p 872a9e5361a1 are in the D27b/c/d trees.
- main b49b697c40: view_export PG M5:M6+M7 crossing preflight + exact_pg fallback + finalize gate (lever 7).
- main 4f638b4e9f: kit_wave E2BIG fix; 8 rows retried (kit_wave.json d3b9b01082), 6 relaunched by the wave.
- main a137683011: tools/die_plan/kit_pin_site_check.py (face pins inside reserved die clock-site obstructions).

## io_cor_v1 (rep)
- Variant A (hand env, non-manifest) FAIL_route: 6 shorts = ft11_i[2..7] inside the east-seam reserved die clock site (1276.99-1278.72 x 517.86-518.94); DPL-0033 overlap u_cland_ft5_i ring flops sd_c[219] vs sd_c[81] at (1120.34,434.70). Setup was fine (CTS +23.89, GRT +8.24, GRT hold +38.5).
- Kit predates obs_gcell_cap: next build must be a D27d wave kit via private-spec on current rt, after (a) the 41 bank_taps rows and (b) a seam row moving ft11 E-face bits (or the site) are in the plan (KV-PLAN-R6). Run kit_pin_site_check on the new kit before launching place.

## pc family
- pc_v3: PDN fixed; open items: 2 seam pins (i_vport_Q_N_vqN[14..15]), tap density (TAP-GRID-R4), efault -1,492 path (D27 r6 efault_stage), R8 strap pad/type split rows (D27d). Run on D27d via private-spec.
- epyc7 is DRAINING (cap 9999): private specs must name another --host (epyc8/epyc10).

## KV-wide seam class (posted 11:4x): hg family ft1_o 2, hgi_v3 17, hub_Eo/Wo 24, pv family 20-55, sys_c 6, io_cor_v1 6, pc_v3 2 -> KV-PLAN-R6 rows.
## Leftovers to ot-delete when done: epyc7 fam-kv-iopc-r2/tree_pc, views_d27b, diag_ioc; predecessor tree_a1, tree_s1, proof_a1 (epyc8), tree_d26b.
