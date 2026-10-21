#!/bin/bash
# S81 DIE72 G8 (S81-G8 10-21, OWNER: full 33 x 26 mm reticle, 0.5 mm margin dropped, ~0.1 mm seal ring inside the outline;
#   72 frames + the qualified 241-stage map 483869b91 unchanged): G7 chain on plan g8 + the newest RTL:
#   floorplan dv_floorplan72_g8.py (results/arch/s81_die72_1021/g8): die 33000 x 26000, blocks >= 100 from the outline;
#   extra room = closure margin, not density: slice-row streets 86.4 -> 172.8 (relay channels for <= 405 um hops + landing
#   rings at every region crossing), service-group column streets 86.4 -> 129.6 + svc->slice street 106.8, all four MU end
#   slots 2851.2 (s_0S was 2505.6), Engram eng streets widen with the row; SerDes 10 real + copy-A/B reserve pair as G7.
#   plan dv_plan72_g8.py (G7 constructor, 161 blocks / 819 links) + facts.stage_map = the qualified 241-stage map.
#   Bind overlays: G7 set + release72/apply_ep_clock_g8.py (per-region clock trees: each of the 12 end-parent clock ports
#   its own die-top root ck_ep_<inst>_<region>, as the frames' ck_r0/1/2).
#   RTL: G7 + u_sl.u_xg -> ot_s81sl_xgt_xo (S81-FIX2/XG 6aac44322, ONE combined xg_xo + rstopt + xs4 master) + Engram L14
#   lookup dsfd_engram_lkp_ra640 RETURN_AGE 640 (S81-FIX2/ENG d5e45464e; G7 response age ~575 > 512) + lepmu bench e033c77e0.
#   tools/die_port_bind.py: child-closure scan no longer re-masks the module body per #( (was quadratic: G3..G7 binds 2-4 h).
#   UNBOUND / stand-in (no CLOSED view yet): u_lep lep_mu_ab, safe8_ntf lanes, u_sl.u_xg xgt_xo, u_sl.u_xr xrt1, eng/etap +
#   ra640 lookup, ctrl rg3, hwin, bk_sel hk2l.  MAIN = SRC = claude/s81-die72-g8-1021.  G1..G7 untouched.  G7 header follows.
# S81 DIE72 G7 (S81-LINK5B L5B-G7 10-21): G6 chain on plan g7 + the G6 leftovers:
#   floorplan dv_floorplan72_g7.py (results/arch/s81_die72_1021/g7): die 32648 x 25952.4 (everything above the ctrl row
#   +907.2); COORD 4.4: the 8 L2 index readers in the two south pockets beside the PHY (reader <-> ctrl lanes 70-75 -> <= 11
#   stations a segment), E column-B reserves to rows 2/3; iqf in the W pocket; bk_sel 907.2 x 4190.4 (L20 +10 SRAM).
#   S81-RTLGAP/eng ccefda9d5 + S81-COLLECT ra512 lookup 0bf2e17b4: eng (dsdv_eng_rr) above s_6S + 16 taps etap_00..15 in the
#   ctrl/service strip, reader links through the taps, tap chains, s_7N f_ks second sink, column-6 rung via eng
#   (dv_plan72_g7.py; bind rows release72/apply_eng_overlay_g7.py after the MU72 overlay).
#   S81-RTLGAP/l20 7cac7629d: l20split_1021/apply_overlay.py after the IDX reset fix (bk_sel -> dsdv_bk_sel_vmtx TX_SRAM 1,
#   die ports bk_sel_tl_o / bk_sel_tx_st, iqf_uid).
#   S81-RTLGAP/ffn 59a8155d3 partial: end-slice u_xr -> ot_s81sl_xrt1 (u_xg stays xg_xo: combined master owed, S81-RTLGAP).
#   s_0N u_lep #(RX_SRAM 1, IN_PIPE 1, NATIVE32 1) (lead; lepmu t5c/t5d params; IN_PIPE +1 on ro / mu_c).
#   Land plan: release72/mk_land_plan_g7.py = G4 rows + MODEL rows (routed station count) for the IDX cluster and Engram
#   links (the 67 IDX placeholders of G3..G6); die STA re-derives.
#   UNBOUND: u_lep lep_mu_ab (t5c/t5d gates live), safe8_ntf lanes, u_sl.u_xg xg_xo, u_sl.u_xr xrt1, eng/etap (no kits).
#   MAIN = SRC = claude/s81-die72-g7-1021.  G1..G6 untouched.  G6 header follows.
# S81 DIE72 G6 (S81-LINK5B L5B-G6 10-21): run_die72_g5.sh unchanged plan g5 (--wb-rows 2 3, stage hop 17 mm) + RTL
#   L5-RTL e484cff47 (6 missing safe8_ntf lane sources @445e6c74c: the MU72 end-slice tops never elaborated on G2..G5)
#   + CLOSED ot_s81sl_capc5r view (closure s81sl_capc5r-163d31541, record 4a4d275ee: physical/ref_tile/s81sl_capc5r on this
#   branch -> u_sl.u_cap binds by master; source blobs identical; old capc5c view no longer carried in the assembly).
#   + S81-RTLGAP/idx bfdb07fa7: native-fixed dsdv_idx_rg3.sv + apply_rst_fix.py (reader/qf rst active-low: the 9 rinv_*
#   inverters vanish).  IDX L2 readers stay at the north edge (~25 mm hrrq/hrrd lanes, ~151 cycles priced; move = G7).
#   UNBOUND: s_0N u_lep ot_s81sl_lep_mu_ab (lepmu, binds in G7), safe8_ntf lanes, u_sl.u_xg xg_xo.
#   MAIN = SRC = claude/s81-die72-g6-1021.  G1..G5 untouched.  G5 header follows.
# S81 DIE72 G5 (S81-LINK5B L5B-G4 10-21): run_die72_g4.sh on plan g5 (dv_floorplan72_g4.py --wb-rows 2 3: W column-B real
#   SerDes lk_WN2/lk_WN3 beside lk_WN0/1, s_0N<->lk_WN2/3 links ~7.9 mm shorter, = pair A length) + RTL L5-RTL e93685328
#   (u_land #(SRAM 1) = CLOSED dsdv_mu_land 263e13fc3) + S81-RTLGAP/head 589110357 (end-slice u_xg -> ot_s81sl_xg_xo).
#   UNBOUND (no CLOSED view yet): s_0N u_lep ot_s81sl_lep_mu_ab (kit s81sl_lepmu, binds in G6), safe8_ntf lanes, u_sl.u_xg
#   xg_xo.  MAIN = SRC = claude/s81-die72-g5-1021.  G1..G4 untouched.  G4 header follows.
# S81 DIE72 G4 (S81-LINK5 L5-G4 10-21): G3 chain + the owner-approved 5th lane pair (10-21 06:00) -- plan G4
#   (results/arch/s81_die72_1021/g4: die 32648 x 25200; W column B link_0_4/0_5 = REAL ot_pdie_serdes lk_WN2/lk_WN3 with
#   links s_0N tx2/tx3 -> lk_WN2/3 tx, lk_WN2/3 rx -> s_0N rx2/rx3; E column B link_1_4/1_5 stay copy-A/B blockage reserves;
#   s_0N = ot_s81sl_slice_lepw_mab_mu_72 2851.2 x 6825.6 (L5-RTL claude/s81-link5-rtl-1021, overlay key dsdv_slice_lepw_mu)),
#   routed HERE on the fleet (dv_route72 + dv_station_dirs72, 0 failures required); land plan = p4l3 + 4 sibling rows
#   (release72/mk_land_plan_g4.py).  Everything else exactly as run_die72_g3.sh.  MAIN = SRC = claude/s81-die72-g5-1021.
#   G1/G2/G3 untouched.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
MAIN=${1:?main}; SRC=${2:?plan_source}; FRAME=f04198934d9a1fdacc81b9501a9ccb5c632ba2ea; LPREF=21b97190eba0b3b306026f23a2408867cd099726
CREF=12c132d60a8f0300056abb216d48ff9588e7f620
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
W=$D/die72-g8; mkdir -p "$W/src"; S=$W/steps.log
for r in "$MAIN" "$SRC" "$FRAME" "$LPREF" "$CREF"; do git --git-dir="$G" cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin "$r"; done
BASE=results/arch/s81_dv_1016
printf 'MAIN %s\nPLAN %s\nFRAME %s\nLP %s\nVIEWS %s\n' "$MAIN" "$SRC" "$FRAME" "$LPREF" "$CREF" > "$W/snapshot.refs"
git --git-dir="$G" archive "$MAIN" tools rtl "$BASE" physical/rom_host_ingest results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 | tar -xf - -C "$W/src"
git --git-dir="$G" ls-tree -r --name-only "$MAIN" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$W/phys.lst"
mapfile -t PF < "$W/phys.lst"; git --git-dir="$G" archive "$MAIN" -- "${PF[@]}" | tar -xf - -C "$W/src"
git --git-dir="$G" archive "$SRC" results/arch/s81_die72_1021 tools/s81_dv/release72 physical/ref_tile/s81_mu72_assembly | tar -xf - -C "$W/src"
git --git-dir="$G" show "$FRAME:tools/s81_dv/frame_bind.py" > "$W/src/tools/s81_dv/frame_bind.py"
cd "$W/src"
if ! grep -q 'from frame_bind import' tools/s81_dv/dv_bind.py; then patch --batch -p1 < tools/s81_dv/release72/frame_bind.patch; fi
grep -q "station_dirs" tools/s81_dv/dv_diecase.py
export GIT_DIR=$G
R72=results/arch/s81_die72_1021
python3 tools/s81_dv/dv_route72.py "$R72/g8/plan_unrouted_g8.json" "$W/plan_routed_g8_raw.json" > "$W/route72.log" 2>&1
python3 - "$W/plan_routed_g8_raw.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));f=p['facts']['physical72']
assert not f['routing_failures'],f['routing_failures'][:5]
print('ROUTE72_OK links',len(p['links']),'stations',f['relay_station_count'],'bit_mm',round(p['facts']['bit_mm'],1))
PY
printf 'ROUTE_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed_g8_raw.json" "$R72/relay_bodies.json" "$W/plan_routed_g8.json" > "$W/station_dirs.log" 2>&1
printf 'STATION_DIRS_RC 0 %s\n' "$(date)" >> "$S"
P=$W/plan_routed_g8.json
T=$W/bind_table72.json; LAND=$W/land_plan_g8.json
python3 tools/s81_dv/release72/mk_land_plan_g7.py "$BASE/landing/p4l3/land_plan.json" "$P" "$LAND" > "$W/land_plan_g8.log" 2>&1
python3 tools/s81_dv/frame_bind.py --plan "$P" --table "$BASE/bind/bind_table_p4l3_mu.json" --out "$T" --source-ref "$LPREF" > "$W/frame_table.log" 2>&1
printf 'FRAME_TABLE_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/recovery_idx4_1021/apply_overlay.py "$T"
printf 'IDX_OVERLAY_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/rtlgap_idx_1021/apply_rst_fix.py "$T" > "$W/idx_rst_fix.log" 2>&1
printf 'IDX_RST_FIX_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/l20split_1021/apply_overlay.py "$T" > "$W/l20_overlay.log" 2>&1
printf 'L20_OVERLAY_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/release72/apply_mu72_overlay.py "$T" > "$W/mu72_overlay.log" 2>&1
printf 'MU72_OVERLAY_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/release72/apply_eng_overlay_g7.py "$T" > "$W/eng_overlay.log" 2>&1
printf 'ENG_OVERLAY_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/release72/apply_ep_clock_g8.py "$T" "$P" > "$W/ep_clock.log" 2>&1
printf 'EP_CLOCK_RC 0 %s\n' "$(date)" >> "$S"
python3 tools/s81_dv/release72/apply_spare_faces_g8.py "$T" "$P" > "$W/spare_faces.log" 2>&1
printf 'SPARE_FACES_RC 0 %s\n' "$(date)" >> "$S"
set +e
python3 tools/s81_dv/dv_diecase.py --plan "$P" --out "$W/bind" --bind real --bind-table "$T" --land-plan "$LAND" > "$W/bind.log" 2>&1
RC=$?; echo "BIND_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs "$CREF" "$MAIN" "$SRC" --die-repair --dieflow-ref "$MAIN" --dcc-ref "$MAIN" --corners tt ff ss --macro-views --signal-top-layer M8 --gen-safety-diag 'selected72 g8 diagnostic: G8 = G7 on the full reticle 33000 x 26000 (seal ring 100; slice-row streets 172.8, svc streets 129.6, svc->slice 106.8, end slots 2851.2 x4, per-region end-parent clock roots) + u_xg xgt_xo + Engram ra640 + qualified 241-stage map facts; G7 = G6 + readers beside ctrls (south pockets, die 32648 x 25952.4) + Engram eng/16 taps (RTLGAP eng + ra512) + L20 bk_sel_vmtx (+10 SRAM, slot 907.2 x 4190.4) + end-slice u_xr xrt1 + s_0N lep RX_SRAM/IN_PIPE/NATIVE32 + IDX/Engram model land rows; G6 = G5 + L5-RTL e484cff47 safe8_ntf lane sources + CLOSED capc5r u_cap + IDX reader/qf reset polarity fix (rtlgap idx bfdb07fa7); G5 = G4 + W column-B real SerDes beside lk_WN0/1 + u_land CLOSED dsdv_mu_land SRAM1 + head XB egress u_xg xg_xo (6 real W SerDes, 2 E reserves, s_0N lepw_mab_mu_72 2851.2; svc 3801.6, lepe 2851.2, idx 1209.6, seqhost 475.2x993.6) + MU72 tops on capc5r slice successor; declared unclosed frame/MU/service parents and source-view scope; no production closure claim' > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC $(date)" >> "$S"
[ $RC -eq 0 ] || exit "$RC"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
RC=$?; echo "CHAIN_RC $RC $(date)" >> "$S"; exit "$RC"
