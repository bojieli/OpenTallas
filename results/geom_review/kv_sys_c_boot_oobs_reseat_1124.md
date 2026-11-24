# SYS C boot and OOBS seat trial (11-24)

The exact A5t3 SYS C place view remains **BAD**. A private placement-only trial on E11 uses source plan `cbee82715bca` and the exact original synthesis ODB `6a62a419ac15`. Unit `kv-sys-c-boot-oobs-place-1124` runs in existing KV-ALLFIX scratch scope at `kv3_sys_c_boot_oobs_reseat_1124`. The original kit and full-die plan remain the comparison inputs.

The boot configuration crosses from the east landing around the central ROM toward the Dcal consumers on the west. The existing four pad stages bunch in the east and north, leaving a final 1,076 µm configuration capture jump. The draft places five existing 40-flop banks (BIN and four pads) at centers (1883.52, 889.92), (1736.64, 946.08), (1352.16, 946.08), (972.00, 937.44) and (652.32, 872.64) µm. It preserves all 32 data bits, six address bits, and both write-enable bits in stable order. The six leg maxima across all 240 mapped capture edges are 230.796, 203.040, 384.480, 388.800, 384.480 and 352.512 µm. The modeled cap crossing turns above the SRAMs and around the ROM's northwestern corner.

OOBS active and flush each move two existing flops. Projected longest hops through every incident capture on these flops change from 774.549 to 314.847 µm and 634.014 to 210.681 µm. The trial adds zero cells and zero cycles. A placement hook checks row/site occupancy for all 204 target instances and fails on any reservation collision or missing cell. Fresh placed images, actual clock capture routes, connectivity and resulting capture reach are still due.

The attention TX valid path remains a broader D2D region problem. The max exact hop from its existing BIN register is 1,258.34 µm. Its FIRM face ring at (2001.834, 760.725) is 1,531.872 µm from one downstream EFC capture at (565.812, 664.875), across three existing hops with a total 1,215 µm budget. Re-seating the two intermediate flops by themselves cannot satisfy the bound. A candidate must move parts of the existing downstream TX error cone or relocate its exact launch while preserving valid/payload age. Other D2D POR fanout, RX/TX calibration, and KVI reaches remain held.

- [Viewed draft seat sketch](kv_sys_c_reseat_1124.png)
- [Exact moved instance list and predicted graph bounds](kv_sys_c_perbit_reseat_1124.json)
- [Original placed evidence](kv_a5t3_pv_v3ne_sys_c_1124.md)

The E11 trial waited on CPU admission and started no payload. Its queue entry was stopped and checked for an active scope. Intel1 unit `oth-ubuntu-4161057-1795533417` is the active placement-only trial under `/srv/opentallas-scratch3/claude/ot-jobs/kv-sys-c-boot-oobs-1124`; the copied source plan and synth ODB hashes match, and initial kit preflight passed.

Device-level check showed Intel1 scratch3 shared the root filesystem. Its floorplan-only unit was stopped and the interrupted log preserved. The current retry is epyc2 service `kv-sys-c-boot-oobs-place-e2-1124` at `/srv/opentallas-scratch2/claude/ot-jobs/kv-sys-c-boot-oobs-1124`. This destination is on device 66304 and the root is on 66307. It uses the same verified original plan and synthesis checkpoint.
