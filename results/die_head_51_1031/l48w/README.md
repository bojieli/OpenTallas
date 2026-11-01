# HEAD plan event l48w (DIE-HEAD-51, COORD 16:2x 2026-10-31 APPROVED)

l48w = l48c (results/die_head_50_1031/l48c, merged ROOT-MERGE-AK) + three value-only changes in clock:
1. ring_hold.write_edge fall + write_fall_types [hd_turn_a, hd_st_turn, hd_st_k5, hd_st_n4]
   (HEAD count-aligned ring writer on the falling fclk edge; tools origin/claude/head-ringhold-2-1031@5eeeccdc50c).
2. tap_window.per_type_ps (23 types, 20-130 ps; hd_tile 130): DIE-KV-56 formula W_t = ceil10(measured nominal
   single-arrival related-pair kit-contract damage of the type regions + 10), cap T/4; need_by_type.json / per_type_ps.json.
3. seam_hold {seam_ps 90, sender_ps 0}: ceil10(seam damage 72.71 (sp2_bw_i_shim->sp2) + 10).
RTL: unchanged from l48c except .WFALL(1) on the CA rings of the 4 fall types (rekit p1 unchanged RTL on l48w vs l48g).

Checks (intel2 /srv/opentallas-scratch2/claude/die-head-48, tools 5eeeccdc50c):
- G0C --completeness: 1 ERROR = pre-existing SerDes native release PENDING (same as l48c), 0 new.
- strict die port-bind HEAD_DIE_PORTBIND_SOURCE PASS (bind/run_l48w.log).
- die STA 12.25 form, --nominal-arrival single (HBM-CLKLOC-5 default), proof sta/proof_l48c, bind_l47k:
  TT setup +257.36, intra kit contract PASS (worst need 49.93 within its type window), seam PASS,
  CA lo TT +211.9 / FF +241.6; remaining gate items = CA start-skew 1607/1607 x TT/FF no taps
  (bind start tree on legacy unicode paths of an older clock tree; DIE-HEAD-51 fix in progress).
  Before (l48c, same tool): 263419 contract violations.
