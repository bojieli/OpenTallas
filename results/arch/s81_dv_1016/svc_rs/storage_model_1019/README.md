# Whole SVC storage and real SM exit: source-bound MODEL ONLY

Source `claude/s81-svc-land-1019@53ccd5927`, landing implementation `5d9c4ecaa`.
No RTL changed, new simulation, synthesis, gate or route launched. Original three diagnostic
gates and full/skew/ST benches remain with their existing owners. `model.py` reproduces
the arithmetic and actual LEF contact census; `model.json` records five RTL hashes and
all seven view hashes for each compared family. This is not a fit or timing certificate.

## Actual stores per slice

All attention stores below use streaming `clk`, nominal 1.2 GHz. The landed parent puts
attention in `ck_c`, SM in `ck_sm`. Reset invalidates pointers/presence/valid state;
payload memories are not cleared. Every first functional read must remain gated by
source presence/job/lifetime checks; zero initialization is not an admissible proof.

| Store | Actual shape / useful bits | Access and lifetime | Necessary change |
|---|---:|---|---|
| `land` | 640x256 logical; three writer copies =491520 physical data bits | PC0,PC1 and ROWS can write concurrently; 4 consecutive rows/edge release. 640x2 LVT selects last writer, source order ROWS wins same-row collision; per-job `pres` reset | Current 12x256x256 SRAM; replace real views, preserve concurrent writers, old-read and LVT edge |
| `pmem` | 512x512=262144 | PMEM1 only, one 512b write/edge, two 512b words/edge read (even/odd banks), wrap depth512; prefetch `pr_n`, `pw_q` enforces availability | Current four256x256; native replacement and same prefetch age |
| Engine stage | 2x4x160x265=339200 | Front/back job buffers; one row/lane write, synchronous old read per lane; filled/reuse guards own lifetime | Current sixteen256x256; full265 bits (not256) must survive |
| `wq` | 3 classes x2 PCs x8x341=16368 | Up to3 registered pushes/edge, one request/PC/edge selected with HBM credit; depth8 pointer overflow fault | Six independent1R1W rings,36 shallow64b banks. Prefetch/empty bypass and priority must be proved, not changed to on-die backpressure |
| `sw` | 32x(512+10+5)=16864 | Q SEL_IDS burst writes, serial 16-ID scan may wait only at elastic HBM fetch boundary; retains row base/count | One527b ring,9 shallow banks; keep metadata aligned and exact final-row count |
| `pvq` | 8x2120=16960 | Eight consecutive result beats, one whole2120b write/edge; each drains header+four512b words,40-edge owner window | 34 shallow banks. Cannot serialize producer writes to fit a narrow macro; prefetch before first drain |
| `qmem` | 16x512=8192 | One selected head row write/edge; `eq_w <= qmem[4'(rc-1)]` every edge,16 valid reads after GO | Eight32x64 macros can replace existing read register at same edge |
| `fq` | 2x16x26=832 | Fetch descriptor queues; HBM-only elastic lifetime | Real circular pointers already exist; below2kb, keep bounded local state and uncapped source census |
| Other validity | `pres`640, LVT1280, `wsc`1024, selected-held512; small per-PC counters | Independently selected validity/scale state and job epochs; LVT is not reset but presence must dominate | Real source fanout, reset tree and mux-depth proof required; no aggregate-size fiction |

The three-writer landing raises capacity over the logical640x256; it does not remove
the original engine's double staging. PMEM1 therefore instantiates **32 legacy256x256**
macros (12 landing+16 staging+4 probability), PMEM0 28. Legacy LEF172.8x41.04 has
W411/E410 actual signal/clock contacts, **10.015/9.990 contacts/um**: fails the6/um
rule. A successful diagnostic gate cannot qualify those faces.

## Distributed arithmetic state and honest banking alternatives

There is no blanket rule that summing thousands of independent multiplier registers
turns them into one SRAM. Actual simultaneous access is the limiting constraint:

* Stationary operands: 4 tiles x16 heads x32 dimension lanes x5 banks x16b =163840b.
  Each multiplier has an independent80b banked operand. `sk_bank[gk%8]` supplies eight
  distinct read addresses per head, each shared by dimensions gk={j,j+8,j+16,j+24}.
  Keep distributed80b compute state as a candidate, with same-edge writes, exact
  bank-held guards and all control copies charged. A literal SRAM alternative groups
  four same-address dimensions into64b words and costs512 macros, not64.
* Transposers: four tiles x64 rows x8 dims x18b =36864b. Each row has288b local state,
  four independent row writes/edge and all32 output-row reads/edge. Source is indexed
  selection, not a shift pipeline. Distributed bounded row state is a candidate only
  after write-enable/read-onehot fanout and depth proof. SRAM banking preserving these
  parallel ports costs128 native macros; one packed macro cannot deliver the bandwidth.
* Merge: four tiles x5 levels x16 heads x8 entries x33b =84480b. Current code shifts
  eight-deep arrays on every valid and **must change**. A true pointer ring per head
  holds264b (320 rings), changes no rounding/tree order, and advances only on the
  original valid. Local FF pointer rings are a priced alternative to180 native SRAMs;
  prove head OLD value, store-or-recirculate, all bubbles and same-edge pointer wrap.
  This is an actual algorithmic ring conversion, not relabeling the old shift chain.
  Exact declaration is `reg [32:0] ring [0:DPT-1]` inside the existing per-head loop:
  264b is the **total eight-word ring**, not the word width. Combining sixteen heads
  gives one528x8=4224b ring; the comparison above charges180 macros for that grouping.
  ROOT must choose the coherent storage grouping before source implementation;
  if SRAM merge is selected, hybrid totals rise to475 macros/340904.12544um2 raw/
  683 clock contacts, with shared read prefetch/OLD semantics still open.

The hybrid native-memory model covers the seven large stores in the table, and keeps
the above285184b distributed state explicit. Using the existing128x64 two-clock family
for deep stores and32x64 single-clock for shallow ones gives **295 macros,241470.858um2
raw area,1882112 physical bits and503 actual clock contacts** per PMEM1 slice. Deep
macros each pay both clocks even when tied to the same region. This is conditional:
the128x64 behavioral model has separate blocking read/write processes and **does not
define same-edge same-address OLD semantics**. A no-collision proof or an independently
reviewed exact macro behavior contract is required; a tied-clock invocation alone
does not repair the model. Existing academic abstracts are not transistor/SPICE macros.

The fully single-clock alternative uses **655 existing32x64 macros** and preserves the
native same-process OLD read/write behavior; inspect JSON for physical bits/area.
It costs361825.38816um2 raw and655 clock contacts before any merge SRAM selection.
Its pointer/address prefetch still needs source proof. Both candidates require genuine
mask64 mapping; padded bits have mask0. Replacement non-repair32/128 families do not
silently inherit the old r2c2 spare/repair contract. Production currently ties repair
controls off; any repair-enabled build must reject this replacement or supply a
separately priced implementation. No new ECC is added under the academic policy.

32x64 actual31.968x17.28 has W103/E102 (5.961/5.903 per full face);
128x64 actual33.720x27.576 has105 each side (3.808/um). Full-face density passing does
not prove PG, OBS, access track, pin span, route, per-pin clock, or parent fit. Width
and height include real compiler geometry, not stretched LEF without timing cost.

The naive all-SRAM alternative also replaces distributed operands/transposer/merge
state:1115 macros/raw694444.631um2/1323 clock contacts. Its43.2-lattice cell sum is
2.0808mm2 before logic/escape, incompatible with a nominal1.491mm2 compact slot under
that packing. This is an expensive alternative, **not a mandatory global-array rule**.
The295-bank hybrid lattice-cell sum0.55054mm2 likewise is not a placed floorplan:
full-width std band, channels, orientation, all macro origins and runtime logic area
are unknown. The655-bank choice has less space remaining. Synthesis area, source
fanout and actual legal packing must decide; no current slot or L20 fit approval.

## Real SM producer and required consumer

`ot_s81_su_sms` wires the registered `ot_s81_su_smq` output. It emits a555b bundle
`{w_v1,w_a14,w_m16,w_d512,w_st12}` per head, not spare pins. SE writes512b exponent
rows at `obase +16*oc +g`, maskFFFF; SO writes256b normalized inverse-RoPE/BF16 data
at `obase +8*oc +g/2`, mask00FF orFF00. `oc` resets at job start; `w_st` retains jid
and den/alive/fault status. In the landed parent this output is already **+3 SM edges**
relative to flat; return travel is additional and cannot be treated as zero.

Current GENmu3 all16 `u_rsv` w_* outputs are OPEN. Current-main `lower_svc.py` G9/G9b
confirms there is no existing die VM target. A general16384x512 memory inferred from
the14-bit address would invent8Mbit/head and would not establish a producer/consumer
path. The real graph needs: SE sixteen-head gather→BF16 probability-frame words→P
store, then owner-quarter P.V gather→SO operand SMJ frames, then SO masked half-row
gather→real Wo input/V memory ingress. Other three output quarters require the
cross-die G10 exchange. The actual destinations, address lifetime, two-half merge,
clock roots, generation/jid validity and static slots must be selected and modeled
before target RTL. No tied sink, diagnostic-only new output, artificial address
alias, unpriced write serialization or omitted SO status is permitted.

The QF producer source lane owns the actual slice SEND→q headers/payload programme;
it is upstream of this graph. Existing endpoint injection does not close it. Keep
G9/G9b/G10 separate pending dependencies until real producer and consumer programmes
exist. Single-user and multi-user token qualification remain open.

## Minimal next source work, pending ROOT review

First implement an opt-in **qmem eight-bank32x64** replacement, retaining generic
default byte identity. Registered macro outputs replace `eq_w` at the existing
sampling edge, so intended added data edges0, clock contacts8/raw4419.25632um2;
compiler GO16-head availability and per-word write age stay exact. Prove all16
nonzero heads, arbitrary payload initialization, same-edge OLD collision, pointer
wrap, occupied reset and two consecutive jobs, plus wrong-head/early-read mutants.
Do this on the minimum component rather than another whole arithmetic build.
Then source-bind merge pointer-ring conversion and queue prefetch proofs. No new
physical kit/gate until whole-block uncapped fanout, actual synthesis depth/area,
reset ownership, clock/registered-pin census and a legal lattice floorplan are ready.

Added latency in the whole candidate is **UNKNOWN**, not zero: SRAM queue prefetch,
pointer-ring conversion, true SM exit and inter-region/cross-die transport have not
been implemented or measured. Compiler/die event ages and token price must consume
the resulting exact edges before adoption. No credits or cancel path is introduced.
