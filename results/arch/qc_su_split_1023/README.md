The current slice plan used undirected SU cut totals as one-way lanes. The
2435-bit core/L0 cut is 1531 core-to-L0 data bits, 903 L0-to-core data bits and
one reset. The 2408-bit core/L1 cut similarly contains 1531 forward data bits,
876 return data bits and one reset. Both lane groups consume the same 500-bit
`gb`, 3-bit `gv` and parent reset. Their 504-bit shared-input overlap is not a
driven L0-to-L1 connection: `u_suvm` drives `gb/gv`, and both groups read them.

`inspect_su.py` parses the actual current `qfd_dv_s8_flat`,
`qfd_dv_s8_suvm_rp1`, `qfd_dv_s5_lrly` and reducer port directions and exact
parent bit slices. It rejects unknown expressions and multiple drivers. Its
source hashes, pin-level witnesses, directed rows, alias sources and static age
contract are stored in `inputs/su_directed.json`. `sc_win0` is specifically
`L_vm_waddr[23:22]`; `sc_wd0` is `L_vm_wdata[31:0]`. These are lane-0 results,
not central SU publications. The 35 previous external SU landing records
become 45 source-correct rows; 57 internal directed census rows cover the three
SU partitions. No inter-lane bundle is invented and no signal is omitted.

The generator aggregates those real directed rows into normal registered plan
lanes, moves external VM/KV/stream/scanner sources to their lane-group origins,
and removes the former hidden SU census group. Existing reset synchronization
handles the shared reset; the data paths do not acquire reset flops. The full
plan latency table must be regenerated and consumed by the binder/compiler;
this packet does not claim the old schedule remains valid or that an assembled
RTL implementation is functionally qualified.

The age notes are static readings of the actual RTL: the lane relay's control,
valid, per-lane address and memory-answer paths have their existing inbound
relay and IREG, the low 256 broadcast-row bits bypass the inbound relay, and
outputs have OREG plus the existing read-request/other-output delays. These
internal registers remain leaf behavior. Added partition boundary/station ages
come only from the regenerated plan. No timing constraints, arithmetic, leaf
RTL, ties or masks are changed.

`check_causals.py` runs the source parser on exact copied sources, then four
actual SV mutations. Removing the core broadcast driver, falsely making the
lane relay a broadcast driver, overlapping lane-4's address slice, or moving
the scanner window to lane 4 must fail. These checks establish connectivity
identity, not RTL numerical correctness, measured timing or physical closure.
The independent G1 review is owned by the coordinator; this author does not
approve its own geometry and launches no P&R.
