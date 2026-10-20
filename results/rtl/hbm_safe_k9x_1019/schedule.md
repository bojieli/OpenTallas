# k9x / k9y static schedule (L2H-SU-FB, 2026-10-19)

No edge changes. Both structural changes are cycle-identical restructurings, proven by the lockstep bench
(tools/hbm_static/run_sfu_split_equiv.sh, CORE3=1 SYNC_RST=1 K9X_BTREE=3 [K9X_BRING=1]; canonical Qswiglu, 6,679 edges):

| change | edges | why identical |
|---|---|---|
| BTREE=3 controller -> lane-mapper broadcast tree (L0 2 / L1 4 / L2 8 / L3 16 kept copies) | 0 | the tree levels ARE the mapper's 4 registered edges (mono: capture e0, select e1, pair add e2, final add e3); the lane index is a constant, so mono's edge-1 select is wiring and its pair add moves to L2 on the same edge |
| BRING=1 bridge metadata (4 x 44 b) and scalar-address (96 b) READ_RETURN+1 = 65-edge delays in SRAM rings | 0 | write every edge at wp, read every edge at wp - 64, registered read = last stage; a fill counter holds the output at 0 until 65 edges after reset release, exactly the synchronously cleared chain |

Reset: unchanged release edges (RST_TREE as k9r: rst_n -1, lg/map/lane +2, one-time). The tree levels clear their emit/ld bits
on their own registered rst_map_n copy; all rst_map_n release on the same edge.
Compiler / die calendar: nothing to re-price. Die slot (k9x only): no port or pin-range change; lanes 5/13 move +43.2 um
inside the tile (N/S lane pin ranges 345.6-1425.6 unchanged).
