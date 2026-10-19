# Native safe packed136 row-cache candidate

`ot_hbm_svc_static_sm_packed136_native_safe` is a separate opt-in element.
The original packed136 and validated native8 masters are unchanged. Ports
match native8; `PACKED136=0` remains off, and `MUT=0` is the candidate.
Required RTL helpers are `ot_cache_safe_cells.sv` and `newcache_kept_read.sv`.
The five canonical `ot_sram_1r1w_128x256_m1_r2c2` payload macros are unchanged.
No gate, REVIEW or submission was made. Canonical dense-face/PG access and
physical closure remain root-owned.

The model preceded RTL (a500e9961/e8f880b13/7e78ee1dd); final RTL froze at
bb7c14755. The exact asserted bench and analyzer source revision is e3642b697.
Evidence and source hashes are in `rtl/test/hbm_accel/svg_rel/cache_safe_evidence/`.
Top RTL SHA256: `14a8482745e48507123de72a42f54c22b12b3cb3a7994a0fc1a3a8ebba51b3e1`.

## Exact boundary contract

Every non-clock input has a native first Q, then a functional qualified/local
control Q. Every observable operation moves exactly **two streaming edges**
relative to native8: OPEN/owned/busy, sector-driven row commit/ready, READ packet,
retirement and fault. If native8 accepts READ at edge N and exports its SRAM
packet after N, this element exports that packet after N+2. The SRAM outputs
are already actual macro Q; no output data collar is added.

For example, OPEN at N and the first two sector groups at N+1/N+2 produce the
first native8 row at N+3 and the safe row at N+5. A retirement at R clears
ownership after R+2. Fixed 17 sectors/five source edges and four rows/five
commit edges remain unchanged; there is no ready/credit stall mechanism.

The parent's READ issue therefore remains unchanged and its external command
and format gain two edges. Existing retirement issue remains unchanged: its
actual cache effect gains the same two edges. Copy completion/ready gains two
edges. The parent composition model b9c85f2dd owns conservative padding19 and
observed command latency9 while read-admission calibration remains7; simply
replacing every LAT_GO7 with9 can issue READ too early.

Reset asserts asynchronously. Eight real first-stage release FFs feed 180
source second-stage branches, balanced23/22 per first-stage FF. The second
registered level releases on the second common clock edge. Branch D=1 under
an asynchronous clear by first-stage Q is equivalent to sampling that Q:
when it is0 the branch is held0; when it is1 the next edge captures1.
There are no reset distribution buffers in the instantiated element.

## Structural change and measured cost

The 8x256 payload ring remains2048 runtime bits. The ingress pipeline is two
wide native register stages (2550 bits total across all inputs), not a runtime
indexed array or a delay chain of three or more stages. Payload registers are
unreset. Sixteen-bit write leaves own four registered onehot lane selects;
select-Q drives at most 16 data gates plus its local enable logic.

The ring is also32 quarters of 64 bits. Seventeen local read roots advance
17 quarters modulo32 per row. Each root and four 16-bit SOP leaves capture
the same NEXT pointer expression on the same edge. Independent local advance
FFs cover16 pointer bits each. This removes shared binary selectors without
adding an operation edge. Kept hierarchy survives through ABC and is flattened
only afterward, with no opt_merge. Actual Q copies and local predicates remain
separate in the mapped receipt.

Rows commit in strict ordinal order and reads require the whole block ready.
Consequently per-bank epoch/count/tag_base plus a final-row ready bit exactly
replace1280 runtime tag bits and128 row-valid bits. Read identity is the same
10-bit `tag_base+read_row` value the old array stored. Registered packet-valid
uses current read admission AND the complement of next fault. It suppresses a
concurrent valid read/error on the same observable edge as old combinational
`out_valid&&!sticky`, while exposing only a real Q at the output.

The source-pinned ORFS Docker RVT-TT mapped census measures 5751.504um² standard
cells plus five aligned-v2 macros totaling 19469.264um²:25220.768um² per element.
Native8 standard cells were3532.486um²; the increase is2219.018um² per SM,
0.035504mm² over16 SMs. It contains8323 standard FFs and five macro clock pins.
This is a cost, with no unmeasured throughput, power or area credit.

## Qualification

Final fleet Verilator 5.050 passes all 64 legal counts in both banks, changing
epoch/tag patterns including wrap, reference row writes and independent byte
goldens, cross-bank reads, retire/reopen, occupied reset and eight fault cases.
The eighth case is a valid read concurrent with a source identity error.
The bench checks every observable output at exactly+2 edges and explicitly
asserts asynchronous reset and first/second release-edge values.

Measured: 4243 exact reference rows,4323 golden read checks,10445 compared edges,
max live ring occupancy8,10390 same-edge slot recyclings. It observes 4319 safe
valid packets. Golden read checks and safe valid observations count different
boundaries; reset can abort delayed responses. Every surviving response passes
the exact two-edge miter. MUT1 shifts a read quarter and MUT2
shifts registered write-slot qualification; both fail `SAFE_EQUIV packet
cycle=29`, with committed fail witnesses.

The initial mapped prototype had 95 over32 data/control nets (max 3652), reset 1553
and area 3532.486um². Intermediate failures are preserved. The final corrected
analyzer reclassifies the immutable mapped JSON without resynthesis; a
combinational cell input named C cannot create a clock exemption.

Independent structural audit proves:

- Maximum actual non-clock pin fanout 31; over32 count 0; unknown cells 0.
- Reset raw8 / first23 / final25,177 live second-stage branches after pruning.
- Every exported bit reaches only real Q through optional inversions: packet
  1088 SRAM-Q +11 FF-Q; ready2, owned2, busy1, fault1 FF-Q.
- Maximum mapped data cone17 logic cells. This is structural depth, not STA.

## Safe-design review before any physical gate

1. Pins: PASS mapped native input/output Q. Reset profile PASS source/graph
   at8/23/25 and two registered release levels; strict checker/root review
   must use the approved raw<=12 / first<=24 / final<=30 policy.
2. Reach: OPEN physical; every stage must be placed within405um reach.
3. Fanout: PASS source-pinned actual mapped maximum31, including controls.
4. Depth: PASS structural 17 mapped cells; <=600ps actual stage timing OPEN.
5. Storage: PASS runtime payload2048 bits; no long runtime flop delay chain.
6. Floorplan: OPEN. Five actual94.824x41.064um macros need43.2um origins,
   full-width standard-cell bands and synthesis-sized cell regions. Their
   canonical signal-face density410/41.064 is about9.98 pins/um, above6;
   root's canonical macro access repair is required before a legal kit.
7. Clock/reset physical: OPEN CTS spread/neighbor reference, reset-clear
   slew/reach and route hold margin. Clock inventory 8328 pins is measured.
8. Schedule: PASS component exact+2; parent composition owns command/prefetch
   pricing and whole-service proof. No standalone rate claim is made.
