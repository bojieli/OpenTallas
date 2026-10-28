# CLK-LOCAL-EST-1 (estimate-only, 2026-10-28)
Full write-up: coord lanes/CLK-LOCAL.md. Per die: <die>_local_fish_feed.tsv = proposed clock-forwarding graph (child <- parent, feed tap),
<die>_local_fish_crossings.tsv = per crossing class (tree-edge / short-loop / long-loop), tree node region (LCA), unshared per side,
OCV, DEPTH, L window, margins (locality.py fish on the die's current region map; count_align_plan unchanged). ESTIMATE / UNCHECKED.
scripts/: cur.py (current topology on gate inputs with the CA-OCV-1 die_sta_related model), topo.py (region tree from tree_path),
amb.py (start-tree ambiguity emulation), loc.py (locality.py driver), startedge.py (fork start-port width), cmp.py/summ.py/tsv.py.
HBM uses the LOCALITY-SCORE-3 map tree_s3.5c5 (no built clock).
