# S81-STRIP-O handoff (Opus successor of FABLE-FIX-S81-STRIP; Fable weekly limit to 11-21)

Updated 2026-11-16 ~04:00 PST.

## Scope
Leaf t43/t47/t75/t28/t8 (STRIP boxed), t72 (ff key), FABLE-PD-S81-0117 levers 5-7 (t62 STRIP row, t34 one kit, re-judge on ring_place ff kits).

## Kits
A. Base ff kits (Fable launch): epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/kit/b_<t>, plan epyc7 fable-fix-s81-strip/fx0.json (B6gE composed + ring_place ff on 988 bands; t34 = strip+y-slot row, t62 = y-slot row). No early stop. Logs intel2 ~/fable-fix-s81-strip/run_b_<t>_grt*.log.
B. Row kits (this lane): epyc7 /srv/opentallas-scratch2/claude/s81-strip-o/kit/c_<t> (plan fx_<t>.json = fx0 + <t>_rows.json), launched by intel2 ~/s81-strip-o/launch.sh TAG TYPE (replicates to epyc8/9/10, ot-run unpinned). Logs intel2 ~/s81-strip-o/run_c_<t>_grt.log.
Status: epyc8 `bash -s < st3.sh` (scratch copy); split: epyc8 /tmp/s81o_cong.py KIT IT, /tmp/s81o_ft.py KIT IT.

## Measured (GRT, ring_place ff, no early stop; congestion-N totals)
| type | it5 | it10 | it15 | class |
|---|---|---|---|---|
| t34 (strip+y-slot one kit) | 13,160 | 618 | 63 | converging -> no extra row (lever 6) |
| t43 base | 56,655 | 457 | | converging -> base may need no row |
| t47 base | 62,674 | 18,997 | | ft S-strip at ve_s/ve_m junction (ft3, ft6 lead) |
| t62 base | 74,410 | 54,818 | | ft S strip x 440-520 (ft0, ft1, ft7) = lever 5 |
| t75 base | 147,564 | | | ft W + S strips |
| t28 base | 188,013 | | | ft S strip H (ft4/ft5 1104-bit S->W) |
| t8 | pending | | | |
| t72 | GPL now PASSES (lever 4 confirmed); CTS stopped on old-tree R-CAP cell gate (882k movable: ~400k max-wire buffers); resumed from CTS with OT_CELL_BUDGET_GATE=0 (owner deleted the cap) | | | |
Lesson: it5 totals overstate; judge at it15+ or end.

## Rows built (epyc7 /srv/opentallas-scratch2/claude/s81-strip-o/)
- Tool corr2.py: re-path chosen ft slots on ft_corridor station DP + row allocator; straight band or explicit Manhattan centre polyline through M7-free space (M5-only cores crossed on M7/M6); checks M7-core legs, sites in M7 cores, collisions with kept slots, station count kept, hop budget 394.9.
- t43_rows.json: ft2 band x 428-512, ft5 band x 516-600 (straight, over vq/vsw/rxsf M5). Hops <= 242. Kit c_t43 running.
- t47_rows.json: ft3 band x 425.5-464.5; ft6 path S(614.6) -> y50 -> x1090 -> y630 -> x614.6 -> N (east detour over the M5 lane cores). Hops <= 339. Kit c_t47 running.
- t62_rows.json: ft1 path E -> x1420 -> y750 -> x120 -> W (north of the core field); ft4 band 626-660, ft8 band 664-714. Kit c_t62 generating.
- t28_rows.json: LEAF-PLAN sp2 core push (vn_b +65.88 y, ve_s +53.46 y; hard_cores + ft_slots + clock.taps from sp2/types.json 528df95851f8) on fx0. Kit c_t28 generating.
- t75, t8: no row yet (await GRT).

## Next
Read finals; READY-ROWS to DIE-S81-92 only for rows whose kit reads GRT 0 (or clearly better than base), plus "no row" verdicts for converging types.
