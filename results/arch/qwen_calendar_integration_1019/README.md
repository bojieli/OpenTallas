Finite calendar integration is opt-in CALENDAR_ROM=0 by default. The actual
cal_mu now reads two native266-bit ROMs, accounts for one additional capture
edge through in-flight FIFO state, accepts CALR10 counts, and retains exact
scheduled output edges. Legacy CALD9 and TLOAD paths remain the default.
The immutable path rejects old TLOAD commands; native table loading is separate.

The fresh source lowerer emits406decode commands,320head commands,64embedding
commands, plus3 source-extracted cap0 token-start commands. The aligned image,
one BOOT command and67-entry INIT copy total867 entries/217 rows. INIT replaces
only the ordinary AMAX emit by NOP and exports FIRST800/CNT67 for this image.
Those values are an image receipt, not production CTLM parameters.
The prior390decode/774body summary is not the count for this exact lowerer.

Native5.050 playback through actual cal_mu passes3920 exact output events with
fault=0. MUT1 shifts issue edges and fails3920 comparisons; MUT11 changes user
ownership and fails3904. BOOT SETID and DONE are also checked. This tests command
playback; it does not execute numerical engines or qualify a whole token.

Source body parameters embed/head word0=300 are explicitly diagnostic. Public
cap0 prefix is hash-pinned (canonical DW5/6 mask0/tag4D43), not a production
cap1 manifest. Phase source is unbound; head/finalnorm payload is absent.
BOUNDARY_RELOC remains0. Physical source, clock, preload/lifetime joins and
actual production receiver/body installation remain open.

All four users play all four segments on exact edges; count1024 and invalid explicit ranges reject. Legacy NU1 lockstep/NU4 regression passes with zero mismatches and1536 landed words.

The next source step adds TABLE_ROM=0 by default and a registered LOCALkind4
load event carrying explicit stage1..36/user. The emitted image has36 aligned
one-entry ranges (first868 through1008),1009 total entries. Callers select a
range explicitly; ordinary stage starts do not infer a table installation.
The registered event is sampled by the loader one edge later. Loader output
is first+3/last+90 from that input sample. The bench waits a fixed103 edges
from explicit range start and then reads the native SRAMs, independent of done.

Actual calendar→four-ROM loader→22-SRAM VM at slice0 passes149640 native reads
in465155 cycles,36stages×4users. Every installation re-reads all resident
users, plus the clearly synthetic common-head sentinel. Exact sample traces
produce144 source-bound windows:93 reserved edges each,13392 total.
The manifest c63242abc11b880c741bd7556138529dab331b21579231b7ba9b53c7435cee92
is the same compact manifest checked against the full released checkpoint.
Compiler collision/lifetime/early-window mutations all reject.
Native loader wrong-userMUT2 fails a PROG read; actual overlapping loads fault;
reading the last CROM row before the fixed window completes fails against the
same target SRAM. No credits, dynamic ready or waiting for done is added.
This proves the minimum source-bound table transport/retention mechanism.
Numerical consumers, full cap1 host metadata/receiver acceptance, whole-frame
admission and provider/clock binding remain separate obligations.

The shared timing source is tools/qwen_layerbench/table_load_contract.py;
both finite-calendar emitter and table-window validator import it.
witness/fixed_load_pricing.json enumerates all144 affected loads with range
start, command output, loader input, payload interval, final VM write,
read bound, actual read/retirement edges and both reservation intervals.
The103-edge interval has range-start origin; the93-edge interval has loader
input origin nine edges later. The larger caller interval adds9 front edges
and1 tail edge. Thus aggregate caller reservation is14832 vs13392 loader-port
edges:1440 origin-expansion edges,360 per user across36 loads. Actual table
write-port occupancy delta is0. This is not a measured token slowdown.
Production critical-path delta is explicitly null until an actual dependency/
overlap schedule binds. In this diagnostic sweep, user0 first read is loader+96
(range+105), including two bench driver edges after the103-edge reservation.
Other first-owned-user read offsets732/1368/2004 include the deliberate native
resident-bank reread sweep. Those testbench reads are not the production layer.

The cap1 follow-up emits the actual25-word fused ME programme (400PW), its
source-generated ME/XPF control rows and the cap1 footer. Only the obsolete
SRAM-calendar interval [400,976) is cleared; the full calendar is in two ROMs.
The input compiler checks native capability against the sole PC11 native59
template. Source programme, complete PW metadata, ROMs, descriptor and digest
are pinned. This does not complete the ME/XPF versus relocated SU-X namespace
join, head/finalnorm payloads, or all physical receiver copies.

The actual calendar-copy receiver passes epoch7/digestb8de77b060896115/cap1,
observing actual calendar SRAM PW write interfaces and registered DW receipt.
Commit1044 precedes BOOT SETID1050, INIT clear1212, LOCAL EMB1261 and all other
command outputs. The receiver execution_active input uses a real NE32 L player,
matching existing FACE recordport.execution_active(l_run), with l_go=ev_lay.
Its one-END L image is a declared diagnostic component fixture, not production
L timing. SYSFACE owner confirmed current source07174adb1 retains that binding.
An assertion rejects any command/LOCAL pulse before receiver commitment.
Payload digest, cap-cleared footer, wrong authorization, early L execution and
missing final DW/drain controls all fail. No cal.running mask/BOOT hold is added.
The failed alternative execution_active=cal.running is preserved: BOOT prefetch
starts before the final observer drain even though its SETID output is later.
BOOT calendar running and the source-bound execution_active signal are distinct.

The current1009-entry capsule leaves14 entries under the1023-entry ABI ceiling.
Future lifecycle/production commands must be counted again and fail closed if
they exceed capacity. Source phase, all ME/XPF receiver copies, actual head,
global programme/stream allocation, full F16 admission and physical closure
are open. production_bound remainsfalse. INIT FIRST800/CNT67 is still only
this capsule's exported range; public F16 timing and CTLM defaults are unchanged.
