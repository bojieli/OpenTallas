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
## 18:5x update
- r1/r2g cancelled (exact PIDs) before they ran: superseded. Fleet memory-bound; plan queue on epyc9/10.
- fixhops.py (station re-site): every ft slot whose station chain crosses the +129.6 band: exact DP over per-station x offsets in [0,129.6]
  (2.16 grid, bit sites move with their station, macro-free), else equal-arc re-site; 102 slots re-sited with NO cycle change.
  45 slots (hub_Ei 13, hgi_v8 7, hgi_v2 x2 types 4+4, hgi_v3 4, hub_Wi 3, kv3_hgi 3, ...) have no slack (path/stations > 405 um after +129.6):
  +1 station each (inserted mid longest hop, then re-sited) -> 68 lanes +1 cycle (lanes_r3.json); latency rows bumped (stations/cycles/natural +1).
- r3 = plan_r3b.json (sha 0b955b9499a3) full gate queued via ONE ot-run --priority plan --hosts epyc9,epyc10 (intel2 ~/kvhgr/r3.log).
- epyc7 staging (rsync of the whole dir) in progress; do not launch there until tree file counts match epyc9.
## 19:1x update
- COORD asked for kv3_hgi_v2 allow-congestion + M9 forms: NOT launched (12.1a tiles <= M7, never M8/M9); ASK posted 19:0x; launch only on an OWNER M9 exception.
  Allow-congestion-only forms are already TYPE-KVHGI2's (planB routeB2 epyc9, fd04/fdC3/v1a intel1).
- r3 still waiting for memory (plan queue, epyc10). Resume: read run_r3.out on epyc9/epyc10 (out_r3/g0/g0_report.json for G0 errors).
  If G0 flags hops/stations: add the TYPE:SLOT to add_r3.txt, rerun fixhops.py (base.json plan_r1.json ledger_r1.json OUT REPORT --limit 400 --add FILE),
  lanes_of.py for the lanes, bump latency rows (+1 stations/cycles/natural), regate. Other chains crossing the band (collector_tree relays max 380,
  landing reader/writer stages, internal_stations) are NOT re-sited yet: fix them from the G0/bind errors.
- epyc7 copy incomplete (rsync timed out); do not use epyc7 until re-synced.
- On pass: package por/ = plan_c.json (plan_r3b) + sink_bins/*_hgr1.json + README, post to TYPE-KVHGI2 (all 16 column types need new kits).

## 2026-11-14 18:5x PARKED re-floor; Fable GRT-only test
- r3 gate stopped (exact unit). Re-floor parked (FABLE-HARD-KV §3 dead end). Plan r3b kept on epyc9/epyc10.
- Live: GRT-only forms A (M7 region adj 1.0 over 16 cores, centre column open) and C (control), dirs */kv-hgi-refloor/fh/{A,C}/kit on intel1/epyc9/epyc10; logs intel2 ~/kvhgr/fh_A.log fh_C.log. Result: run/logs/asap7/*/base/5_1_grt.log final congestion report + run/reports/.../congestion.rpt; count congested gcells inside core boxes (FH_M7_BLOCK lines list boxes).
