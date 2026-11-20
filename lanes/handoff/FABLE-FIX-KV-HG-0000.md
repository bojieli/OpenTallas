# FABLE-FIX-KV-HG-0000 handoff (Fable, owner of KV hg / hgi routing + timing since 2026-11-19 23:24 PST)

Posts: lanes/posts/FABLE-FIX-KV-HG.md (OWNER 23:24, STATE 00:1x). Predecessor: the Opus successor of FABLE-FIX-KV-HG (k8-k12).
Work dir: epyc9 /srv/opentallas-scratch2/claude/fable-kv-hg0 (sc/ = tools, kR kS kSR = kits). Hub logs: intel2 ~/tmp/fablekvhg0.

## STATE 11-20 00:2x PST (read first)

Four private kits run on epyc9, type kv3_hgi_v1__cl141fc26e, d25d4 bind, same RTL (k12 RTL: M2 D=3 pads, both t2 splits, reset copies),
route goal, 64 GB / 8 thr, DO_NOT_COUNT, no export:

| kit | dir | what differs | launcher log (intel2) |
|---|---|---|---|
| k12 | opus-kv-hg/k12 | Opus: M2 re-sited stations, hst3 leg x 627 | ~/tmp/opuskvhg/k12_route.log |
| kR | fable-kv-hg0/kR | k12 + reserved die clock sites obstruct M1-M3 only | ~/tmp/fablekvhg0/kR_route.log |
| kS | fable-kv-hg0/kS | S-form sites (below), obstructions as generated | ~/tmp/fablekvhg0/kS_route.log |
| kSR | fable-kv-hg0/kSR | kS + M1-M3 only | ~/tmp/fablekvhg0/kSR_route.log |

Stop one only with `ot-run --cancel <unit>`; the unit name is the "RAN on / admitted as" line of its launcher log.
Read: `ssh epyc9 bash fable-kv-hg0/sc/st.sh` (stage per kit), `python3 -I sc/zones.py <congestion-N.rpt>` (overflow by zone, capacity-0
share), `sc/capmap.py` (capacity histogram by zone). TT: `tt_setup_repair.log`, FF: `pregrt_ff_hold.log`, `4_cts_post_hook.rpt` in the kit run dir.

## Measured facts (hgi_v1; all M, tools in sc/)

1. Walls, not capacity. HG6 wave kit (epyc7 ot-jobs/kv3_hgi_v1__cl141fc26e-route-loved-redfish-556033-*): 30 GRT iterations, final overflow
   106,508 at 9.9 % total usage (M7 4.9 %, M8 1.9 %). Overflow grew with iterations (congestion-5 ... -30). Iteration 5 is a screen only.
2. Over the head cores: LEF OBS M1-M5 full, M6 / M7 3 %. GRT: H capacity 0, V 6-8 per 0.57-um gcell (M7). So about 1,900 M7 tracks per core
   for straight N-S shots between the bands above and below a core; an H jog inside a core is capacity 0 (k10: 6,414 of the 8,356 on e6).
3. Pin faces (sc/lefpins.py): front pins of the even cores are on the LEF S face, M5: e6 master (e4, e6) 807 pins; e2 551 S + 256 row_in N;
   e0 (placed MX, so its pins are at y 233.28) 1,283 incl. kp_in 448. Type-frame y: e6 1002.24, e4 682.56, e2 336.96 / 552.96, e0 233.28.
   f_t2 / f_t3 outputs are E, M4. Odd cores take dr_i / cr_i on W, M4. Landing core q[j] on E at y 1100.5 + 0.192 j.
   The rls rows (FABLE-FIX-KV-HG-rls-rows-all.json) put the copies in the V channel west of the column: wrong face. Copies belong in
   the H channel under their cores. This also takes the 807 bits out of the 8.64-um krsp gap on the 7 hg_v1 types (to verify per type).
4. Reserved die clock sites (sc/geo.py): 151 rects, M1-M7. V-channel width blocked: middle gap 46 of 95 um at y 1187, 23 at y 1060,
   20 at y 977, 36 at y 677; h2/h3 channel 41 at y 760, 28-42 at y 925-975; h3mid channel 95 of 95 at y 644 and y 1255.
   Strips also sit 8-25 um in front of S-face pins (y 328 x 689-792 under head3_e2; y 977 x 214-312 under head2_e6; y 950 x 672-802).
5. The ft2 slot runs 1,056 bits north in the middle gap (x 355, y 601 -> 1289). tN there (M2) doubles a loaded gap.
6. hst trunk content: 1,575 bits = 4 x 256 row bits (one group per even core) + 551 common. Copy c (e6) needs 807.

## S-form (kS; sc/mk_ks.py is the generator and the clearance / hop check)

- tN lpad D=3 placed per bit range (is_place globs on r[0][j], r[1][j], q[j]):
  B j 0-399: r0 (48,1070) r1 (60,962) q (250,930); A1/A2/A3 j 400-599 / 600-799 / 800-999: r0 (128|161|194, 1262) r1 (same x, 975)
  q (250,930); C j 1000-1559: r0 (250,1300) r1 (366,1140) q (385,935).
- eN D=3: (40,383) (40,775) (270,912). Polylines: hst2 `250 930 40 930 40 660` (g (40,900), t1 (40,660)); hst3
  `250 930 640 930 640 655 760 655` (g (640,927.5), ftg (760,655)).
- Copies: hst2 a (40,285) b (40,600) c (40,980) as k12; hst3 a (800,300) b (820,620) c (770,978).
- Cycles: same as k12 (eN +2, tN +2 against D25d). No RTL difference to k12.

## Decision table for the first read (GRT iteration 5, then later iterations)

| result | next |
|---|---|
| kS capacity-0 overflow gone outside strips, total < about 3,000 | rows = S-form; let kS run to DRT; port copies-under-cores to the other 16 types |
| kS still walls at strips, kSR clean | S-form rows + route_layers on reserved sites (ask DIE-CORETAP-1119 for the stack columns); gen_phys already has per-site route_layers |
| kR clean, kS not better than kR | k12 sites + route_layers only |
| none clean | column shift (head2 west column +43.2 um) with the tN trunk in the west margin; needs the plan build, ask KV-D23-COMPOSE |

## Open

1. Read the four kits (above). Post RESULT with the zone table and TT / FF.
2. Rows for D25f to KV-D23-COMPOSE: internal station rows per bit range (plan form: internal_stations bit ranges or relay_sites keys),
   polylines, copy sites, D=3 pads. The per-range is_place is a kit edit today; the generator form is relay_sites keys per flop
   (rs_place_all exists) or a new `bit_ranges` field on internal_stations.
3. Other 16 hg / hgi types: check core orientation and S-face pins per type (lefpins.py + macro_place.tcl), move rls copy sites under the cores.
4. Sign-off builds wait for a bound event that carries the rows; then export signed records to rtx-pro ~/signed-export-1114 and AGIdock /archive.
