# qkd_hr_cluster_p10a — KV host root parent REPACK (CRITICAL qkd_host_root; DIAGNOSTIC pathfinding gate, no REVIEW.json / submit)
KV-HROOT10 10-20. Parent of qkd_host_root_admission (die frame qkd_host_rt). MAIN variant (peer die buses on E face).
- Outline 1382.4 x 1382.4 um (1.91 mm2; 1339.2 placement + 43.2 E/N margin, child fill 51 %, aspect 1.0) — replaces the 777.6 x 518.4 frame (0.40 mm2, E face 5.90 pins/um PINBOUND).
- Children: 16 CLOSED views (adp128 x8, rx_rr, pad5, cdc_pc, tx, guard, order, queue, cdc_host; rx_rr + queue LEFs re-stubbed by the current
  abstract_pin_stub.py under childfix/, libs unchanged) + 3 DIAGNOSTIC stand-ins under standin/ (STANDIN_NOT_A_VIEW): peer 518.4 sq (the slot
  KV-HOST9A needs), prompt 475.2 x 432 (m33a/mu4p3a geometry), ingest_qm 345.6 sq. Stand-in pins are PARENT-ASSIGNED (standin/*/pins.json):
  the leaf kits must adopt them (top-down rule for unclosed tiles).
- Placement: tools/qwen_kv_die/host_cluster/repack_1020 (hr_anneal: lattice anneal on closed-view pin centroids; hr_refine: greedy on the
  realistic stand-in pin model). Pre-gate lane estimate: bits > 405 um = 759 (mostly 1-bit fault/status lanes to guard + peer-queue 100 b).
- RTL: rtl/qwen_sys/host_cluster_hroot10_1020/qkd_hr_cluster_e.v = qkd_hr_cluster with one clock entry port per child clock pin (23), exact.
## Safe-design checklist (parent)
1 pins: wires-only parent, every child registers its pins; no parent pin regs (owner 09:05). 2 reach: see lane estimate; gate measures. 3 fanout:
no parent logic (resets fan to every child, each lands it). 4 depth: wires only. 5 storage: none in parent. 6 floorplan: children on the 43.2
lattice (mirrored children +0.024 track offset WARN), gaps >= 21.6, parent pins <= 2.5/um, aspect 1.0. 7 clock: entries mode, die delivers
each entry; families async but timed at 833.333 (tool gap, clock_domain_note). 8 schedule: wires-only, 0 added cycles vs the flat root.
