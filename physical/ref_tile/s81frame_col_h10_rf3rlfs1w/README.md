# h10 wide-channel structural fallback (SOURCE candidate)

The unchanged fs1 gate is still progressing but its global placement has oscillated around0.30–0.35 overflow for thousands of iterations. Preserve the existing fs1 and fs1e snapshots. The fs1 EP6 run is subject to the scheduled14:15 retirement; classify any mapped retirement terminal as infrastructure and do not blanket retry. This separate candidate takes Claude's generated fs1w geometry and widens the centre and right routing columns by172.8um each, moving every one of235 fixed child/memory blocks only by0/172.8/345.6um. Every original child, orientation, source, pinface/y-range, clock and pipeline age is retained. The independent model and inherited-file hashes are under results/arch/s81_frame_h10w_1340_1021.

## SAFE review before gate

1. PASS source/pins: exact21b97190e frameRTL, same OT_S81_RLY_RSSLICE and8 output-hop profile; no new port or serializer. Translations preserve existing pin tracks. Reset lands at the existing faces.
2. FIXED reach structure: existing relay chains, landed regional crossings and8 registered output hops retained (8×405=3240um budget exceeds1782.432um width). Placed internal reach and timing remain required gate checks; no wire or cycle waiver. Added relays, if actually needed, must be implemented and repriced before adoption.
3. PASS source native: unchanged RTL/profile from existing exact fs1 native<=32. Geometry introduces no control replication, mux, arithmetic or new cell load. The actual gate still runs its own mapped census.
4. PASS depth: no logic/stage change. Physical timing and hard-child boundary checks are unchanged.
5. PASS storage: same fixed rawROM and real hard-child views; no new indexed FF storage.235 planned fixed block placements retained.
6. FIXED floorplan:1782.432×3672um versus1436.832×3672. Centre and right channels each+172.8; all shifts4/8×43.2.235blocks on track/in bounds. Exact fixed cell boxes2647893.047um² plus actual progressing fs1 GPL movable1240658.477um² predict59.41% gross cell fill (blocked-row accounting61.95%); final gate measures. Regional hierarchical frame aspect2.06, improved from2.56, retains its fixed12-row child organization. No squeeze or extra pin layer.
7. PASS proposed clock contract: three related landed CTS roots plus four source-synchronous xk clocks; same phase and constraints. Existing FRAME forwarded-metadata initialization fix must be published and used before the gate; every within-region TT/FF spread must still pass. io_hold_margin0.03 unchanged.
8. PASS schedule identity: source has0 additional edges and unchanged memory/boundary items per cycle. Physical fit remains unqualified. No performance credit or token-anchor claim.

## Measured cost and adoption limits

The standalone area grows1.2690432mm²/frame, or15.2285184mm² for the12 h10 frames. Two added vertical channels provide22200 raw M3/M5/M7 track positions before PG/access/derating; this is a capacity bound, not route proof. The current die already occupies a33×26mm reticle: actual G9 packing/reprojection and all hop/cell-body corridors must be demonstrated, preserving72frame capacity or explicitly pricing a legal die addition. This candidate cannot inherit the old die slot. A source/layout view closure is not parent adoption.

No current job/snapshot was edited or canceled. The old generated fs1w source files are preserved by hash. Gate this independent source only after the shared forwarded preCTS helper is published; rootintegration owns that helper publication. The narrower FB/fs1e continues independently; the fs1 EP6 retirement mapping is pending.
