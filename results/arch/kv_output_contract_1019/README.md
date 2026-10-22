# KV output contract checkpoint, 2026-10-19

Source of inventory: old pinned MU GEN219049242, bound die SHA726f9a08bb3bf497ebe778a0b59f4e1746b9bd8bfbce58eeebcf7848bcd71c21. baseline_inventory.json preserves all612unread classes and73open-port types with source hash. Latestrelease GEN3/4 remains owned by KVcoordinator; this evidence is not a release PASS.

Implemented: kv_rly_std.py writes exact PER-INSTANCE input/output pad ranges at replica construction; a17-bit replica cannot waive livebit34 on a35-bit replica of the same36-bit standard. kv_fwd_lanes.py carries those exact bitindexes and verified oldmaster identity when converting a standard to a forwarded station/landing. kv_port_bind_v2.sh uses kv_output_pads.py to recover the same output contracts for existing physical runs.

Recovery admits ONLY source-hashed bit-independent standard/forwarded relay payloads. Each private output bit traces backwards along exact same-index payload edges of those qualified cells to a zero literal, including fullwidth pin-repair relays. Any logic, nonzero/unknown input, cycle, duplicate driver or changed source refuses. No clock/epoch/fault/control output is declared spare. Existing input pad permissions are narrowed to actual zero literals on exact instances. Input/output functional lanes outside these bitranges remain strict. No new tie or timing exception is introduced.

Measured on the old bound die:306920private-pad outputbits /14536replicas qualified (306720were unread;200already had readers). Fleet strict recheck completed: unread600645->293925 (-306720), spare_out306920, input_tied0, undriven0, multi_driven0, unresolved/ambiguouschildren0. The4unconnectedinputs and73openporttypes remainFAIL. It is not a releasePASS. Five synthetic strictportbind testsPASS, including two logicalwidths sharing one master, lostlivebit, tiedhigh/liveinput rejection, transparent fullwidthrepair provenance and forgednonzero input refusal. No synthesis/simulation ran locally.

Inventory classification (counts are separate from permission):

| Class | Bits | Disposition |
|---|---:|---|
| Relayprivatewire classes |306720| Same-bit sourcezero proof above; exact perinstance declarations only |
| Statichead lane8.nb_t |131072| head_st_rtl.py explicitly removes node-beat output and32relays on staticQK timeline; retained closed lane8 nb is roleunused. Needs exact parent/source/instance output contract, not module-wide nb waiver |
| PVWinternalfields |122420| Still strict: source field-level consumers/padding proof needed |
| ASTKinternalwords |23248| Many fixed296-bit chunk tails; source-width/chunk proof needed. Includes other fields; no suffix waiver |
| PVfork/tap words |12560| Still strict: source protocol field proof needed |
| Landingfault wires |335| REAL functional assertion path gap: kv_fwd_lanes.py already records owed receivingblock faultOR. Must be registered, placed and compiler-priced, not called padding |

The73open-port types include real faults: qkd_ctrl_kc.kf is FIFOoverflow sticky OR synchronizedfi (qkd_ctrl_strip.sv:283ff), and staticdie removes its old land_* consumer. dcal.fault/config outputs, host service/package faults and aborts, recovery state require functional wiring/contract. Source ktree/group/PC chain tails may be terminal-role outputs but require exactinstance/terminal proof. No blanket output_open or unread exemption is proposed.

Physical fault-fold brief:335landingfaults +4kc.kf must reach an existing service/unit/host fault consumer through locally registered neighbour folds. Size/pricer must include folds and exact latency before hardening. Existing AFAULT_D/C roots accept only current attention leaves; adding unpriced combinational ORs to them is not valid. Root and KVlead were notified.
