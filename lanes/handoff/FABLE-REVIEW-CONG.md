# FABLE-REVIEW-CONG (Fable) 2026-11-14 - S81 routing-congestion families (PRELIMINARY, proofs running)

Work dirs: epyc8/epyc9/epyc10 /srv/opentallas-scratch2/claude/fable-review-cong (scripts, d/<type> dumps + GRT proofs, k/<type> private kit copies); column work epyc7 /srv/opentallas-scratch2/claude/fable-review-col (wallx.py, */wallx.txt).

## Findings so far (measured on wave 7073a6b4a59 / B3v kits and DBs)
- LEAF is not leaf-wide congestion. 71 leaf GRT reports: routing use is 3-12 percent of capacity; 80 percent of each type's overflow sits in 1-24 bins of 40 um. Three local structures own it:
  L1 clock-landing rings (u_cland_*_i): t2 61k, t11 51k, t12 28k, t47 32k, t55 19k, t53 31k, t59, t32 (fails on 1-4 gcells), t6, t15, t57. The plan band is 5 um2 per bit while the ring cells need 3.1-5.3 um2 per bit (band 60-100 percent full), and in 13 types the band is a 24-30 um column inside a core-core slot or beside its window.
  L2 ft output stations at a pin face with a core 34.6-50 um behind it: t75 83k, t34 35k, t52 31k, t62 54k, t61 41k, t13, t71, t24, t58.
  L3 glue logic in 8.6-24 um slots between cores (vn_a/vn_b against the ln column): t56 61k, t68, t42, t74, t10, t5, t45.
- R-STREET is NOT applied to leaf: wave kits still have the generator gaps (face 34.56-50, core-core 8.64-23.8). S81-FORMS-1 A5 (full rule, 0 growth) applied 16 of 79 types; band-only at 43.2 (fam43B) moved 0 cores on t2, t11, t32, t68. Macros cover 34 percent of the leaf outline, so the room is inside the type.
- First proof: t68 with ln_12/ln_13 moved off the vn_a face (in place, GRT only): overflow 0 after extra iterations. More proofs running (t11, t75 in-place; t32 band under its pins and t68 gutter blockage as private re-place + GRT).
