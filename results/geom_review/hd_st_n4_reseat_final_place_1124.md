# HEAD hd_st_n4 START reseat final placement (11-24)

Exact detailed-place ODB `f083223cf516` from epyc2 `/srv/opentallas-scratch2/claude/ot-jobs/head-st-n4-reseat-dpl-1124/hd_st_n4`. Opened native layout, density and physical graph images. Legal DPL and the runner finished rc0. Read-only geometry unit `oth-ubuntu-3524108-1795534493` found zero R2R captures over 405 µm, down from 95 in the original form. Longest R2R is 388.37 µm. Pin capture p90/max are 23.9/86.4 µm and column demand peaks at 0.351. There are zero unregistered pins, relay collapses, partial faces or macro clock entries. Sparse fill and expected landing-strip density remain layout advisories. Native maximum local density is 0.744 and the fanout-spread diagnostic marked 731.4 µm.

E10 had reached DPL before exhausting its scratch filesystem. The incomplete 3_5 ODB was discarded from the recovery input. E2 used complete resized ODB `8deb526e95f5` and its original face-flop sidecars. The first E2 invocation caught the missing sidecar, then unit `oth-ubuntu-3428388-1795534261` recovered using the exact E10 companion files and normal DPL hooks. The preroute LEC completed with rc0.

The seat repair passes the local placed geometry review. No downstream route was launched. Any use of the revised form needs its scope and release decision.

- [Exact layout](hd_st_n4_reseat_final_place_1124/layout.png)
- [Exact density](hd_st_n4_reseat_final_place_1124/density.png)
- [Exact capture and clock geometry](hd_st_n4_reseat_final_place_1124/auto_geom.png)
