# KV-HGI-REFLOOR handoff (Opus) 2026-11-14 18:1x PST
Goal: hgi column re-floor so kv3_hgi_v2__cl2862d491 (and every hgi type on the 4x4 head-core grid) gets a real W logic region; G0 0 / strict bind 0 / LATCHECK pass; hand plan to TYPE-KVHGI2 (cc KV-102).
Work dir: epyc9 + epyc10 /srv/opentallas-scratch2/claude/kv-hgi-refloor (tree/ = cp -al of kv-102/cg3/kv_tree11; base.json = kv-102 plan_band.json = kvgeom5 candidate, sha 8301f154d3b2).
DESIGN (form R1): BOTH hgi columns grow +129.6 um (W col x0 3179.52, die cut 3254.80; E col x0 6618.24, die cut 7821.68).
 - Shared local cut c = 75.28 um from the strip-side face (R0/MX in W col: local x; MY/R180 in E col: local x; hub_Ei R0: 1203.44).
   c sits in a common 1.4-um gap of all 16 column types (no coordinate within 0.7 um), so nothing is split; straddling rects (bands/keepouts) stretch.
 - Everything at local x >= c (the whole macro grid, streets, E face) moves +129.6; the W strip (face pins, landing-band starts, x<75) stays at the face
   -> W logic region 86.4/77.76 -> 216/207.4 um between face and grid. Column channels stay 95 um (plan numbers; GEOM 55 um was render scale).
 - Why both columns: kv3_hgi is shared by hgi_WS_0 (R0) and hgi_ES_0 (MY); growing both columns needs NO type clone (KV-102 A3 clone hit SIDECAR_STALE),
   and the WS/WN hgi types (same grid, same GRT class) get the same fix. Die 11180.16 -> 11439.36 um (+2.3 %).
 - Die map f(x) = x + 129.6*[x>3254.80] + 129.6*[x>7821.68]: partition origins, die.io, pg domains, N/S port windows (1-D x; E/W windows are y, untouched),
   spine root. reset.in_sites per base type follows the type rule. 6 sink_bins files rewritten as sink_bins/<type>_hgr1.json.
 - Tool: refloor.py (self-checks: every type point of every instance lands at f(old); row gaps preserved; N/S windows stay in their partitions).
Runs: r1 = plan_r1.json, run_gate.sh r1 via ot-run --priority plan (launched from intel2 ~/kvhgr/r1.log), output run_r1.out / out_r1/.
Next: read G0 errors (expect ft station spacing / hops across the +129.6 band -> add stations where len/stations > 405), iterate, then package por/ (plan_c.json + sink_bins) and post to TYPE-KVHGI2.
