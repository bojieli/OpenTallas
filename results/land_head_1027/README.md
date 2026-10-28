# LAND-HEAD-1 (2026-10-27): s81_head LANDED form on the current plan (METHODOLOGY 12.11)

Plan: main `physical/die_plan/s81_head/die_plan.json` sha256 7af81995 (= R20/R21 plan used by HEAD-R22/R23). Tools: main 133d979e4c, unchanged.
Labels: CHECKED = tool output produced in this lane. Nothing here is NUMBER-CHECKed.

## 1 Token window (run first)
- `fallback_land.py plan --granularity part` on 7af81995: 326 regions, 427 crossings / 211,813 bits, 327 lanes, head pass 37 serial crossings (rowpair 5 W: spine 6 down + chain 25 + spine 6 up) + gather round trip 2 x 10 -> **+171 cycles per head pass** (CHECKED, `summary_part.json`; same as the R17 packet).
- HEAD 9,282 cyc/token (TOK-16) + 171 = **9,453 vs window 10,357, slack 904** (composition UNCHECKED). Upper bound if host_tx/rx (7 crossings each way) also sit on the token path: +42 -> 9,495, slack 862. FITS; no coarsening needed. rowpair (50 regions) would give +102 but breaks the landed-regions standard (17-mm strips).

## 2 Compose on the current plan
`compose --monitor dataflow` (observer OPEN, fails closed): OK, **types 16 -> 16, 0 splits, 0 placement failures**, landing_contract 0 errors (414 pins, 1,281 edges, max hop 18.3 um), boot ready 327 cyc (CHECKED `compose_report.json`).
`gen.py latency --inplace` (327 lanes) + `check.py --completeness`: **G0C PASS 0E/6W, 16/16 types** (CHECKED `g0_landed_lat_report.json`).

## 3 Die clock + GEN + GRT (sl300 recipe on the FB1 variant: one entry per partition)
`die_trial kit --leaf-um 300 --htree-full-depth --tree-site-slide` -> 1,667 buffers + 708 repeaters, 0 on core / 0 in PHY / 0 outside (report site check). Render `sl300/clock_tree.png` viewed.
Combined die GRT (signals M4-M7 + ctree M8-M9, ONE global_route, 50 congestion iterations): **overflow 0 on every layer TT and FF**, 0 GRT-0113/0114 (CHECKED logs `sl300/grt_{TT,FF}.txt`).
Landed window (native OpenSTA on GRT RC, `landed_report.json`): |d| max **201.2 TT / 182.9 FF** vs 416.5, margin 215 TT, 0 over budget; insertion TT 5,775-6,164 (spread 389), FF 5,000-5,343; entry slew max 81 ps; drift max 21.3 ps. Worst: sp5<->host (host_tx/rx, m0S/m7S).

## 4 Equal-length analysis (not adopted)
Root->entry Manhattan (own analysis): ideal H-tree spread 250 um (all from leaf->entry legs, nodes exactly equal); slide tree 917 um. Cause = leaf slides (a leaf slid back by e along its leg changes the leaf->entry leg by up to 2e), not the 90 nearest-site fallbacks (leaf 600: 6 fallbacks, still 903 um).
A zero-skew DME embedding (`dme_embed_not_adopted.py`) needed 3-67 elongations (up to 12.9 mm meander) and 147-207 off-segment moves, because the zero-skew merge points sit on hard cores: spread 1.9-2.2 mm, worse. Not adopted.
Next structural step: leaf buffer AT the entry (already a legal channel site) + lattice-aligned last two bisection levels, so every entry has the same tile-relative leaf offset.

## 5 Not done
Die STA (12.11c intra-region pairs): every region is one partition, so the intra-region pairs are inside the partitions; that needs the 16 types rebuilt with rings (binder ring emission, hd_ctl observer, 8-FT adapter: FALLBACK-PLAN-PREP-2 S1/S3/S4). No real views exist for 14/16 types. Nothing launched.
