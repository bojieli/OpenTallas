# OPUS-FIX-HEAD-LEP0N-R8 (Opus, from 11-21 23:1x PST): HEAD event r17b + hd_lep0N split to sign-off (successor of FABLE-FIX-HEAD-LEP0N-R7)

Predecessor handoffs: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R7.md (split facts, rename map), -R6/-R5/-R4.
Hub dir intel2 ~/opus-fix-head-lep0n-r8/. Lane dir M=/srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r8 (intel2: tmp/, plan/, ev/, planroot_e1b;
epyc10: tmp/). R7 lane dir L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r7 still used (L/src tools tree, L/tmp/recompose_merge.py, L/hc_proof).

## DONE
- HEAD event head_rp21z20NF15f_r17b APPLIED 23:3x (src s81_head_r17b_s0, manifest 67d8b0903f20; e1b START plan 18f3c0c7c0c1 /
  sidecar facc71b93198; in-tree receipt; tools 30b1f11ad5f7). Publish gate PASS c293e888858; marker receipt
  lanes/handoff/s81_head_atomic_apply_1795332633870162806.json (optimistic, holds preserved, review not required).
- ACK FAIL-CLASS 8070467972 posted (hd_host_e DRT-0255; r17b contained tree). Watch the wave hd_host_e relaunch and post RESULT.
- E piece GPL death root cause: yosys kept g_rxm.g_o[*].g_on.g_registered_select.g_bit[k].dm name for merged mrd[k] flops;
  fix tmp/mrdfix.py widens the 4 mrd stage groups. LANDING-BAND-CORE (COORD 23:4x): tmp/bandfix.py slides overlapping stage bands
  (10 on E, 6 on W, max 100 um); landing_band_core --base r16 PASS on both pieces. Both fixes in private tree F (epyc10
  L/trees/s81_head_r7split; plan sha ce3fb5e7ef4d; wave_prepare sha updated; backups in epyc10 M/tmp).
- Cancelled bad-plan kits: oth-ubuntu-371717-1795332613 (E place), oth-ubuntu-231439-1795332206 (W GRT; W CTS setup -875 = landing
  fault/status path coll_i0 -> coll_o2 1.2 mm, no status relays, plus coll_i2 ring -234 in a 13 x 531 um sliver band).
- Split rebased on e1b: tmp/rebase.sh e1 -> M/ev/e1: split + recompose + gen rtl + bind/cohort/LATCHECK 334/334 PASS; G0 14 errors
  (6 faces face_budget_g2, 7 START uses rst_start_raw_0..6, 1 band_capacity reader-start:lepk_i0).

## IN FLIGHT
- Private kits on F (fixed plan, v2-based g9 bind): E spec ~/coord/autopilot/private_specs/OPUS-FIX-HEAD-LEP0N-R8/s81_head_hd_lep0N_1121234406
  (run-item pid 3993424, log ~/opus-fix-head-lep0n-r8/runitem_e7.log); W .../s81_head_hd_lep0N_w_1121234411 (pid 3993434, runitem_w7.log).
- Cut-form LEC (R7 units, epyc10): oth-ubuntu-1452654-1795321534 (CUT_EQUIV_PASS), oth-ubuntu-1610100-1795322008 (CUT_RST_EQUIV_PASS).
- tmp/post2.sh e1 e2 (ot-run pid 4109031 on intel2, log ~/opus-fix-head-lep0n-r8/post2_e2.otrun.log): bandfix + START exports per piece
  (tmp/start_split.py: rows 3, 6 -> lep0N_w, others -> lep0N shifted -820.8; head_reset_exports.py fix picks nearest raw relay) +
  head_sideband_street_rows (status/reader/writer START rows, fixes the W status path) + bind/LATCHECK/G0.

## NEXT
1. e2 G0 to 0 errors: faces need face_budget_g2 (G2 probe = routed private kits of the pieces), band_capacity reader-start:lepk_i0 grow.
2. coll_i2 band on W: channel west of pair 2 is 34.56 - 17.28 = 13 um (pairs at x 34.56). Options: band north of pair 2
   [17.28, 512, 66, 630] (pin hop up to ~407 um) or a different pair x. Decide from W kit result.
3. Split HEAD event r18 on r17b: tree = r17b_s0 + overlay (e2 prep files, published piece wrappers, parts RTL + rgnl sources,
   bind results), src_manifest delta-apply, publish gate, marker; that also clears the uncut LANDING-BAND-CORE overlap.
4. Kits from the r18 manifest tree -> sign-off + export.
