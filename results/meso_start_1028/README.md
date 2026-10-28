# MESO-START-1 (COORD 2026-10-28 02:42): feed-edge start tree, start relays, hop relays

All flags are opt-in. Without them the byte path does not change (a test checks this).

- `count_align_plan.py --feed FEED.json`: the start tree is the region clock feed tree. Every start edge is a feed
  edge (12.13b). Feed nodes that are not crossing regions are contracted out. A feed edge with no candidate leaves its
  child unreached, so the plan fails closed. The bind refuses any plan whose `start_tree=feed` has an off-feed edge
  (mutant test).
- `--start-relay`: a feed edge p->c with no forward crossing gets a start-only relay. The parent's registered start
  is wired beside the feed into c's `ot_dp_landing_origin`, with no data ring. Its phase is taken from the reverse
  crossing's derated interval, negated. Its J range covers +-(sync aperture + |start skew|). die_sta_related times the
  start row from the reverse pair's STA interval and adds no lag row.
- `--hop-relay`: a non-tree crossing that FAILs becomes two CA rings u->x->v, plus one region-x register. x must be a
  region with forward crossings on both legs (12.13c hop chain).
- No new RTL form. The start relay is the existing origin sync (formal_origin exhaustive). A hop is two proven
  `ot_dp_clk_landing_ca` rings and a same-clock register, so the per-ring k-induction proof (MESO-COUNT-2 /
  MESO-RECONCILE-1) applies to each hop. The composition is covered by the plan MC chip check and the bind start-up
  simulation. Mutant tests: an off-feed edge is rejected, and a hop leg K-1 is caught.
- `--parts table` with hop relays is not wired yet: annotate_table needs the leg ports. The strap tie flow
  (MESO-STRAP-1) must also learn start-relay tree ports.

## QC K2 (die-qc4-1028 K2/CA_2w2s, spice x1.0485/x1.0552, same proof/plan, --cppr-lca, HB none). OWN, UNCHECKED by NC

| form | CA plan FAIL | start-skew FAIL TT | FF | worst lo/hi TT ps |
|---|---|---|---|---|
| base (min-ambiguity tree, = DIE-QC-4) | 6 | 31/260 | 21/260 | 121.7/179.9 |
| base + --start-skew 55.2,87.5 | 6 | 31/260 | 21/260 | same |
| base + hop relay | 6 (no x passes) | 31/260 | 21/260 | same |
| feed + start relay (96) + hop (16 relayed) | 22 | 69/288 | 29/288 | 182.7/180.5 |
| feed + relay + hop + --start-skew | 25 | 24/288 | 29/288 | 182.7/288.4 |

STA rows are measured after dropping the plan-FAIL crossings (INFO, as DIE-QC-4 did). The lag/slot/guard rows have
0 FAIL in every form. The "no taps 631" line is the same in every form (it was already in DIE-QC-4).

Finding: the feed tree does NOT fix QC. The 6 base FAILs pass on the feed tree (margin ~856 ps), but 22-25 long
crossings fail instead (sl_*_st_b -> c_*_tn_10 cwn3/cws3: d ~6 ns, derated width ~1.5 ns + ~340 ps wander, path
ambiguity 4-6 cycles). Feed edges are as ambiguous as any edge (101/312 vs 99/312). Ambiguity comes from the derated
d width plus 2 x T/8 against the T/2 rise/fall grid, not from the tree's shape.

Ring bind (ruling 2): not built, and should not be. The 6 base FAILs have old-ring margins of 92.1/92.3/94.1 ps. That
is the lpo margin at x1.00, never re-timed at spice, so they FAIL against 100 on margin alone. The old ring also has
fixed ABSOLUTE latency, while the two count frames differ by up to 6 chip-variable cycles. A static count schedule
through it is therefore unsound wherever path ambiguity is above 0, and where it is 0 the CA ring already has the
wider window.
