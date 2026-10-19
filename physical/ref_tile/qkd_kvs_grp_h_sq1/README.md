# qkd_kvs_grp_h_sq1: safe-square DOMSPLIT group

Replaces the 220.32 x 1185.84 strip with 388.8 x 388.8 um (pin-bound waiver approved by KV coordinator). Four SRAM origins are at (43.2,43.2), (172.8,43.2), (43.2,129.6), (172.8,129.6); a full-width standard-cell band is available above the compact bank. Macro halos are 5.4 um; horizontal SRAM pin channels have >35 um clearance. The die lead must reserve the square slot before binding. No RTL latency change beyond the existing DOMSPLIT +2 ck status observation and relayed group path.

Safe-design checklist before gate:

1. Landing: existing per-domain two-stage reset landing + kept child copies retained. Boundary registers/relay paths inherited from TW2-KVGRP; gate must check any unlanded path.
2. Reach: redesigned long 1186-um frame into 388.8-um square; check worst routed reach in gate. Existing group leg/lcal relay edges retained.
3. Fanout: existing per-child reset relay copies retained; confirm textbook high-fanout and retained copies at gate.
4. Depth: structural data/control relay stages retained; measured synthesis/CTS must confirm no >600ps critical stage.
5. Storage: four real SRAM macros; no new flop storage or delay lines.
6. Floorplan: SRAM origins on 43.2 lattice, 1:1 outline, lower macro bank and full-width upper standard-cell band. E face ~2171/388.8 = 5.59 pins/um; W split core/HBM words share full face. Util waiver: prior synth ~24.7k std +15.6k SRAM /151k =27%; pin density sets minimum face height. Inspect actual gate PNGs before route.
7. Clock: existing per-domain measured spine; ck/hck entry on W beside register band; require pin-flop spread <=80ps TT/FF, neighbour-matched boundaries and io_hold_margin0.03. No measured new-outline clock evidence yet.
8. Schedule: static, DOMSPLIT words isolated by launch domain, existing +2ck hck-status landing retained. Geometry adds no cycles.

Bench/gate state lives in pending_results.txt. No REVIEW.json or submit until coordinator inspects the final PNG/checklist.
