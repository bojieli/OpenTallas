# S81 VM current-source geometry audit

This package is an **explicit READ_PIPE=4 / CAP_PIPE=2 native candidate**, elaborated from `c3fc1a4a2a9fe2722ba5f9e7bf938a8802c3c381`. The die generator currently supplies no parameter overrides, so its actual defaults are **0 / 0**. `default_vs_native.json` and both frozen elaborated ASTs preserve that distinction. No parameter adoption, RTL change, route submission or die closure is claimed.

The candidate has **640 hard boundaries**, with exact hierarchy identity and parameters in `inventory.json`: 352 memory leaves, 150 write edge leaves, 72 read leaves, 46 CDC halves, 17 capture leaves/control, and three sequencer/scheduler/landing leaves. Their actual kit or source-pin candidate rectangle area sums to **13.5055274832 mm²**. All 640 have source-matched port shapes and physical pin coordinates. Kit existence is geometry evidence only: explicit parameter mismatches and current RTL versus frozen gate snapshot hashes are retained. In particular, the 16 actual scatter instances use PIPE=0 while cb4 kits use PIPE=1. Old F4 x34 source bytes differ from current RTL. Current routed netlist identity remains unverified here.

The independent wire join accounts for all **693 raw clock entries**: 688 reach actual hard boundary pins; four reach inline WFC/XIO control regions, and the legacy core clock has no native hard sink. `clock_root_join.json` records every bit. The inline source state is separately recorded as WFC stream 1,757 / serial 4 bits and XIO stream 1,522 / serial 6 bits. These are declared state bits, not mapped FF or area measurements. Their hardened outlines, pin homes and parent combinational glue remain absent.

The historical 4168.8×3715.2 rectangle does not cover this source. Initial complete-known-hard-rectangle candidates are 5529.6×4903.2 for 2×2, and 3542.4×9828.0 for 1×4 vertical. They preserve 468 exact current local bank/q8 write/payload rectangles and place the other 172 known hard leaves in a side strip. They are neither lower bounds nor complete VM footprints.

Actual free-hole packing places 580/640 known leaves in the 3952.8×4903.2 body with 21.6µm clearance to newly inserted leaves; 60 remain, totaling 1.79532288 mm². A 540µm spill strip accommodates those leaves, giving **4514.4×4903.2**, zero body overlaps and all 640 known rectangles. This is a capacity candidate, with missing parent hardware explicitly retained. It is worse electrically: **205,589 of 441,050 measured internal functional pin legs exceed 500µm**, versus 181,964 in the initial larger side-strip arrangement. Maximum compact-candidate pin distance is 8328.198µm. Rectangle compaction is not a timing or routing improvement.

`pin_producer_join.jsonl.gz` preserves exact bit identities. It resolves 482,632 consumer endpoints to one source, separately identifies 162 constant endpoints, and leaves 31,904 endpoints as parent behavior or unsupported expressions. Internal functional reach covers 441,050 bits with zero missing physical pins. Another 40,254 endpoint legs have external die pin homes missing. Clock/reset legs are excluded from functional reach. `boundary_rank.json` ranks actual producer/consumer ports and clock domains, source pin fanout, crossing net widths and geometric minimum extra stages. The 500µm stage rule is a screening lower bound; actual related-clock timing, uniform compiler ages, new physical relay hardware and the token-cost ledger are mandatory before adoption.

The full 640-leaf pin inventory uses routed LEFs when available, assigned pin Tcl otherwise, and source-bound candidate pins for the 150 write leaves. Every per-bit reach file identifies which source pin supplied the coordinate. Native timing/DRC, whole-die obstacles, clock/PG/reset routing, complete cut capacity and all-source functional calendar proof remain open.

Replay the pinned native candidate elaboration:

```sh
python tools/s81_vm/current_geometry_elaborate.py --manifest results/physical/s81_vm_geometry_1103/source_manifest.json --out /tmp/s81-vm-geometry-replay
python tools/s81_vm/current_physical_inventory.py --ast /tmp/s81-vm-geometry-replay/vm.tree.json --out /tmp/s81-vm-geometry-inventory-replay
```

`--read-pipe 0 --cap-pipe 0` on the elaboration command reproduces the generator default hierarchy. The source manifest validates all consumed source bytes against the pinned git commit. All work was isolated in `/home/ubuntu/wt/s81-vm-geometry-1103`; the original and parent worktrees were not modified.
