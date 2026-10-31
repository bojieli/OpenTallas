# DIE-HBM-42 d41v: V-A hop-chain lanes for the SFU/IDX pairs (COORD 16:0x), base d41c (fa542d5c0871)

Results only (no shared tool change). `va_build.py` = DIE-HBM-41 lane_e.py pattern: lane_add.Builder (unchanged tool) builds
the NW lanes on the DIE-HBM-37 V-A chains (`va_route_lengths.tsv` NW paths; Builder.path if absent), NE = exact die
mirror (`L<n>m`). The script patches two Builder methods locally: station resite = per-crossed-partition
station_resite.route (layered reachability, macro-free 4.32 lattice + halo, hop <= 0.9 x 405) from the previous FF
to the next partition's entry with >= ceil(route / ft_station_max) FFs per partition (check R3), instead of the
tool's straight-line whole-chain ideal (that one failed on every L-shaped chain: "no macro-free station chain").
Wide pairs split over k <= 6 parallel lanes, shorter parts padded to the slowest (R8 latency group).

Three builds (gates in gates.txt, all vs d41c G0 6 / G0C 14 errors, bind 66 pairs / 46,952 b):
- all 26 NW pairs (va_build_all26.log): 16 built, 10 failed (no free window on b111|b003, su01|b010, b012|b113;
  no station chain hub->b113, b113->hub/b110/su11/su31, su11->b113). bind 66 -> 34 pairs / 30,580 b, but
  G0 +21 / G0C +62 new: hops 540-959 um on L730-732 (b100->b102 via sm3/spb1/sm2, 51 cyc), L735/L739/L741/L746
  (long su/spu chains); cuts NE_b003 0.73 (b113->b111 1662 b) and NE_b103 0.61; NE_b101|hub L744m shares a
  track with L12m; street_reach on sm2/sm3/su20/su31 cores. NOT usable.
- 9 clean-candidate pairs (va_build_9.log): G0 0 new, G0C +2 street_reach NW/NE_su20 core u_su_Q2_lanes8_11
  (467 um) from the b111<->hub stations in su20. Bind 48 pairs / 41,276 b.
- d41v = 7 pairs (va_build_d41v.log, plan_of_record/d41v, sha 3bccac4b3860): G0 6 -> 6, G0C 14 -> 14 (0 new);
  bind 66 -> 52 pairs, 46,952 -> 42,416 b.
  Lanes (NW / NE mirror, cycles): L730/m b113->b112 1662 b 42 cyc; L731/m b113->su20 596 b 17; L732/m b002->hub 4 b 12;
  L733/m b011->hub 3 b 10; L734/m b013->hub 1 b 20; L735/m su11->su20 1 b 35; L736/m su20->su31 1 b 20.
All numbers CHECKED by this lane's own G0/G0C/bind runs (intel1 /srv/opentallas-scratch2/claude/die-hbm-42/va);
cycle numbers are plan arithmetic (lane_natural), TOK pricing pending.
