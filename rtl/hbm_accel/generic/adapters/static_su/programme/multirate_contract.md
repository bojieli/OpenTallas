# Candidate SU/VM 3:4 static boundary contract

This is a component candidate and compiler model. It does not establish native
whole-SU production execution or physical qualification. The previous proof tying
all clock inputs together remains same-clock evidence only.

The source boundary has serial compute, control, lane-store SRAM and programme
clocks at 900 MHz; the port-group leaf, LG and VM stream clocks run at 1.2 GHz.
One integer quantum is 2500/9 ps. Serial edge n occurs at 4n quanta; stream edge
p at 3p. Both begin at phase-zero epoch 0; the shared phase repeats every12 quanta.
Physical PLL/clock compensation, skew, phase establishment and reset release have
not been proven. There is no asynchronous-clock claim.

The existing pgslice directly holds serial read requests into a stream leaf and
uses a serial delay of10 to sample a response held for one stream cycle. That
can duplicate issue or miss a response. Its serial drain output similarly stays
valid across multiple stream edges. Passing a bench with tied clocks does not
validate these crossings.

The candidate captures a request payload into serial register slot n modulo4 at
serial edge n. Stream register event j=ceil((4n+4)/3) reads that stable slot.
The LG consumes this registered output at stream edge j+1. Register events use
stream phases {0,2,3} modulo4, and LG issue phases {0,1,3}; each fourth stream slot
is idle. Slot selection derives entirely from finite phase counters. No ready,
credits, occupancy decision or response arrival can change issue timing.

| Event for serial source n | Common ticks | Domain edge |
|---|---:|---:|
| Capture serial request | 4n | serial n |
| Register stream request | 3j | stream j |
| LG samples request | 3(j+1) | stream j+1 |
| LG presents read response | 3(j+11) | stream j+11 |
| Capture held read response | 3(j+12) | stream j+12 |
| Present registered serial read response | 4(n+12) | serial n+12 |
| LG presents write acknowledgement | 3(j+8) | stream j+8 |
| Capture acknowledgement | 3(j+9) | stream j+9 |
| Present registered serial acknowledgement | 4(n+10) | serial n+10 |

The read response is captured at the next stream edge, before the LG may change
its output with nonblocking registered updates. This is the declared LG
presentation/hold contract. The model does not sample a narrow stream response
at an arbitrary serial edge. Source-to-opposite-domain setup is at least4 quanta
for requests,6 for read returns and7 for acknowledgements. All are above the
required three-quantum budget; physical setup/hold still needs measured closure.

Four slots in each direction prevent reuse while a crossing is live. The model
checks65,536 consecutive serial events including all phase and slot wraps. It
proves minimum slot-overwrite guard7 quanta, without a same-slot read/write on
coincident edges. The RTL uses four explicit register banks; these are the
actual candidate storage, not a behavioral replacement for an SRAM target.
Payload storage including input/output registers is2780 bits per port,88,960
bits over32ports, plus phase/warmup/valid pipeline and fault registers. This is
an area count, not a routed area or power estimate. The current RTL shares one
serial and one stream clock per port; whole-top integration should expose a
separate compensated pair per actual port-group or hardened boundary leaf.

`su_multirate_compile.py PROG OUT [--expected-writes EXPW]` creates two distinct
planes. `serial_prog.mem` preserves every original serial command. A read's
source event is its VM read command edge. A write's source event is its command
edge+4, because the existing store/RF drain path registers its output after+3,
and the bridge captures it at+4. `stream_cal.mem` reserves read/write VM slots
at each calculated LG issue edge. No observed DUT request determines this
calendar. Optional `stream_expw.mem` moves the independent expected write edge
from its old serial request edge to its computed stream issue edge, preserving
sector, mask and data. Expected arithmetic/scalars and lane-store checks remain
in the serial plane. Generated files and input sources have SHA256 pins.

For the current LAT4/LEAF1 image the model emits7116 serial command edges,
9489 stream calendar edges,32,768 read slots and135,184 write slots. Separate
hardware programme producers must replay these planes in their own domains.
Appending calendar bits to the serial command word cannot replay the stream
plane. Programme memories must be primed before epoch0: the current SRAM
producer starts at serial edge-4 for serial command0 to be sampled at0, and an
equivalent stream producer starts at stream edge-4 for stream calendar0. Bridge,
leaf, LG and top reset/epoch controls must permit that fixed prefetch interval;
the reset release sequence itself remains an integration obligation.

The bridge belongs between the pgslice serial request/return signals and its
existing stream VM bank leaf. The stream leaf keeps READ_RETURN=10 and
WRITE_RETURN=7. The pgslice's serial fill destination/data delay must become12,
requiring a distinct serial-FD parameter rather than reusing its current shared
READ_RETURN parameter. Serial response n+12 is captured by the existing fill
register at n+13; bank pins sample n+14 and commit n+15. This adds2 serial cycles
to fill visibility and3 to the serial acknowledgement interface compared with
the old tied-clock10/7 assumptions. The current last fill command1023 commits at
1038, before op load1040, but a complete compiler dependency/resource check is
still required. Drain source generation remains four serial edges after command;
its LG write expectation moves to the stream schedule above.

This bridge reserves three of every four stream slots, matching one serial
request per edge per port. There is no reduction below the intended900 MHz SU
command rate. A tied-clock1.2 GHz benchmark cannot be treated as a900 MHz
production throughput measurement. No price or clock target is changed here.

The boundary bench uses real3:4 clocks, sparse and dense portions of read/write
traffic over128 source edges, full payload comparisons, fixed return edges and
request counts. Its LG peer is a declared external fixed-latency boundary model,
so this is not proof of actual native VM composition. Mutants change a request
slot, return a response one stream edge early, or violate the epoch phase; all
must fail. The phase mutant is rejected explicitly by the benchmark's clock
contract check. The RTL does not claim to diagnose arbitrary PLL phase failure.

Required next proof: integrate actual bridge instances and the two native SRAM
programme planes with native VM; split pgslice serial-FD from stream latency;
run the whole numerical/store/RF/reduction checks in their declared domains;
prove reset epoch and compensated clock delivery, then route/TT setup/FF hold/
DRC0. Until then production calendar and native whole-SU qualification stay OPEN.

## Two-plane native composition source

`su_programme_compile.py` accepts `--line-bits 64` for a standalone stream
calendar, preserving the default 9688-bit serial command format. Use
`--param-prefix SERIAL` and `--param-prefix STREAM` so each generated include
has distinct constants. On the current image these planes allocate 301 and 76
SRAM macros respectively: 377 total, 12,353,536 payload bits. Provisioning uses
34,420 serial-clock transactions and 9,493 stream-clock transactions. These
counts describe provisioning rather than execution throughput.

`su_multirate_native_run.sh OUT prepare` generates both planes and their native
expected-write calendar. Preparation is the default. The separate `build` and
`run` modes require fleet admission and the coordinator's release of the previous
full-SU job/cache; they must use a new staged tree and output directory. The
runner rejects a cached executable whose RTL or configuration dimensions differ
from its source receipt.

The new `tb_hbm_su_native_multirate_top` connects both actual SRAM programmers to
the native top and 32 actual VM banks. A single half-quantum integer lattice
generates 50 percent duty serial and stream clocks, preserving coincident epochs
without accumulating independent clock rounding. Each programmer starts four of
its own edges before E0; bridge reset releases between the preceding clock edges
and E0. Its ordinary numerical, scalar, lane-write, sector/mask/data, fault and
response checks execute in their declared domains. Negative runs alter external
seed data, command addressing, RF reads, reduction commands, the stream calendar,
or the actual bridge-reset epoch. This source has not yet passed the full native
composition run.

The endpoint receipt measures the last serial lane write, scalar, bridge read
return and bridge acknowledgement, and the last stream LG read issue/return and
write issue/acknowledgement over all ports. Its maximum completion tick includes
both domains. It reports configuration transactions, programme priming, command
and calendar lengths, and the 40-serial-edge checker tail separately. Neither
programme length nor checker tail is reported as measured unit service time;
throughput and physical qualification remain false until the integrated proof
and the required physical/price checks are complete.

`multirate_programmes_tb.sv` is a smaller exact two-programmer component bench.
It checks every command and calendar bit at the common E0-relative consumer
edges using the actual mapped SRAM models. Mutants corrupt either plane's
configuration or shift the stream programmer's start by one stream edge. This
component cannot establish native VM/top arithmetic or physical qualification.

The native endpoint receipt also observes all 512 pinned store-bank `w_pin`
signals at the actual SRAM write edge, and all 256 RF-bank `wv_pin` signals at
their actual register commit edge. These are separate from the lane-write input
strobes. Both commit endpoints enter the maximum completion tick calculation.
