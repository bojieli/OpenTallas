# Local SO target: private source implementation contract

This component owns one head beside its real `dsdv_svc_rs` producer. It is
inactive in every public/default parent. It neither closes mu4c's ten open
entries nor supplies the missing SO operands. Its only arithmetic input is
the actual SM write face, after SE division and inverse RoPE.

Source authority: `ot_s81_su_sms` documents 32 SO writes/head, 16 BF16 values
per write, address `obase+8*row+head/2`, mask 00ff/ff00 by head parity. `xs_bf`
assigns eight adjacent heads to each K4096 group. Four consecutive SO rows
therefore form one 1024-bit beat; `idx=8*(head%8)+row/4`. Eight beats/head,
128 unique beats/rank, and eight actual destination slices/group imply 1024
destination deliveries. This component emits unique beats, not the eight
destination copies. Its full 512-bit face is captured; the known head-parity
half is selected only after the complete mask/address/status checks.

Each target contains four genuine historical `ot_sram_1r1w_32x64_m1`
instances, 8192 payload bits total, four clocks and 8 supply terminals before
any actual macro supply/contact audit. The pinned behavioral model is byte
identical to b65718325; it is not a newly qualified master. Across 16 targets:
64 macros/131072 bits; the separate all-quarter FP32 transpose still requires
128 historical banks/262144 bits under bb3262's all-quarter fence. Combined
capacity is 192 banks/393216 bits, before destination replicas or links.
The historical area is 4*552.40704=2209.62816 um2/target and 35354.05056 um2
for 16, conditional on that historical family, not a placement estimate.

One valid write/cycle is 256 useful bits/cycle and four 64-bit writes/cycle.
The scheduled read phase is one row/cycle for 32 edges (four 64-bit reads).
Three held 256-bit portions plus the current row form a four-row 1024-bit
pack: this is an assembly register, not a time-delay chain. It is below 2 kb;
the entire coherent 8192-bit indexed payload lives in SRAM. The registered
output delivers one beat/four read edges, 8 total. Four independent banks
permit writes and reads but the schedule intentionally fences all writes
before any read, with no same-address collision semantics needed.

Independent authority is an explicit new config input, never derived from
received `w_a/w_m/w_st`: full owner {tag8,user10,epoch2}, expected SE jid8,
SO jid8, obase14, SO-write first/last edges, read edge and retire edge (4x16).
The parent must create it from accepted WIN_LOAD/descriptor + static compiler
calendar, and distribute that authority beside the actual SMJ stream with
equal paid data/control ages. Existing WIN_LOAD has user/tag but no epoch2;
the missing allocation-owned epoch producer must be implemented and priced.
This private input does not assert that the production parent already does so.
The actual SE/SO announce input is a separate observation of accepted SMJ
start/kind/jid. The target requires matching independent expected jid, remembers
the real SE `o_den` event, and refuses SO without that denominator lifetime.
The original tap clears status `o_den` at SO announce although its divide
engines retain the denominator. Clearing it must not destroy the target's
valid prior-SE proof. A new config/reset clears row validity and denominator
ownership; SRAM never resets. A second config before booked retirement faults.

Timing convention: config is captured by a pin flop; its following core edge
installs the config and sets relative cycle zero. SM announce and w_* have
separate pin flops. The config's booked write window and read/retire edges
are consumer-core edges. No arrival-dependent start, rescheduling, ready or
credit exists. Missing/late/duplicate/foreign data fault; read and completion
remain on booked edges. A booked retire pulse includes the independent owner
and error flag, and is explicitly NOT an END or proof of destination capture.
No faulty job generates healthy gathered beats. Current-edge failures veto
output, including a failure concurrent with the eighth beat or retire.

State is priced from the actual declarations after implementation. In
particular 16 local targets each pay their own 768-bit assembly and 1024-bit
output registers: bb3262's single shared pack lower bound cannot be reused
as the cost of 16 local targets. The new source adds zero arithmetic MACs,
four SRAM writes and reads per head, and a 1053-bit owned output boundary
including valid/index/data/owner/group. Full mapped area, all-driver fanout,
reset distribution, clock capacitance/spread, lattice/contact/PG checks and
405-um wire reaches are still unavailable. No physical submission is granted.

Integration dependencies remain real: all four P.V quarters and their
transaction identity, transpose read/SMJ serializer, cos/sin ownership, SO
schedule, 16 target placement/clock/reset roots, actual neighbor routes to
eight slices/group, destination BF parity-window issuer, actual arrival-table
acceptance and joined fault/END/WO_A retirement. The original local-P.V END
is too early and cannot be reused as a successful SO completion.
