# HEAD-KITS-10 (2026-10-29): ft A trial kits (HEAD-017) - results only

Plan COPIES only (base = HEAD-KITS-8 run plan.json = results/die_head_21_1028/hk4/plan_spine_raw_rx_tx.json.gz; md5 07c2ad5a...);
the die plan hk4 (FROZEN 07:26) is not changed. Kits: gen.py phys --trial --hold-ff-margin 10 on main 7a77f0bc61, intel2
/srv/opentallas-scratch2/claude/head-kits-10/{v1,v1c,v1d,v2}. Not regenerated on a FLOW-HOLD-3 tag (none yet): no AP route.

- ft_face_estimate.{py,tsv}: estimate before build. With plan stations k, last stage at the out face => inner hop L/(k-1):
  >405 um on 31/36 slots (415-687). R2 out<=30 + 405 together need k+1 there (+1 cycle per strip crossed).
- ftface.py: plan-copy transform. k' = max(k, ceil(Lmax/(405-4))+1); v1 = per-bit FIRM bit_sites_um (last stage at each
  out pin), --with-regs adds regs_um (so gen's tap planner sees the new station columns = v1c); v2 = regs_um only (spiral).
- plan_hk10_ftv{1,1b,1c,1d,2}.json.gz: the plan copies (v1d = v1c + hd_st_str clock.tap_radius_um 150).
- auto_geom/: AUTO-GEOM (tools/autopilot/geom_check.sh, --all-kits) per kit at 3_place and *_cts (4_cts.odb).
- r2rcls.py: groups r2r>405 captures by launch/capture prefix (hd_spn diagnosis).
