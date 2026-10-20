# Original coupled diagnostic: exact interval coverage, illegal tree calendar

The original first execution ended normally (unit `oth-ubuntu-627409-1792450818`, native PID627426, executable SHA256 `53da2c56f8c3881b9e9c6935eec46fe7179ecadce7779fd3e8d1821e461f1cc1`). Its original11900 horizon, ORIGIN32,834ps clock,15epochs,387 source commands, zero target3 commands, inputs and weights were unchanged. The complete73790690-byte raw log is preserved remotely and in deterministic gzip here; raw SHA256 `1a179dcd9682fb0fec691948c5fe145931355c1f0cc13675db46e76a564f78ee`. This is a failing preparatory diagnostic, not a numerical or token qualification. No second execution or programme correction was performed.

## Source-complete interval result

`source_interval_audit.json` joins all actual pair PV outputs to the original90 plans and810 configured placements. All1536 original row/segment leaves appear exactly once with correct pair/macro ownership and no PV error, unknown, missing or extra leaf. All624 actual frame return words match the actual CAP arrival pins bit for bit at exactly+6 measured logical edges, without extra arrivals.

The original unchanged tags are400 `(lo=0,k=2,nseg=3)`,112 `(2,1,3)` and112 `(0,1,3)`. For every tag the audit retains the complete encoded interval `[lo,lo+2**k)` and explicitly reports both occupied source segments and implicit padding. The occupied union matches the actual1536 PV leaves exactly once. The512 padding positions are reported separately and receive no source-leaf credit. No lo/k clamping, deduplication, fabricated gold leaf or filled payload is used. The preliminary classifier's112 repeated row IDs therefore represent complementary partials, not duplicated occupied segments. Numerical FP32 partial sums and golden rounding remain unqualified.

## Exact source padding equation and actual consumption

The relevant original hardware is `ot_s81_retn_static.sv:67..100` (snapshot pinned adjacent), repeated in the actual specialized n6 source at `ot_s81sl_cap_rt.sv:499..531`. Its normalization predicate is `C(j) = !(lo==0 && 2**j>=nseg) && lo[j]==0 && lo+2**j>=nseg`, for j<5; it advances k through each consecutive true predicate. The singleton actual segment2 starts `(lo=2,k=0,nseg=3)`: C(0) is true because2+1>=3 and lo[0]=0; C(1) is false because lo[1]=1. Therefore its *same data word* is normalized to `(2,1,3)` without an add or any fourth input. The actual three configured/PV leaves per row have segments0,1,2 and nseg3; no segment3 PV exists. The left real leaves0 and1 merge to `(0,1,3)`; the source sibling rule permits its merge with `(2,1,3)` only when row,nseg,k match and lo XOR equals2. Their source parent is `(0,2,3)`, which `complete` accepts because lo==0 and4>=3. The abstract fourth interval position is thus normalization ancestry, not a source operand. The audit's occupied/padding partition reports that original source fact; it does not edit a tag or discard actual segment3 data.

At the first offending actual child inputs, the `(2,1,3)` word remains a real valid partial. The hardware does NOT suppress it for being partly padding: it enters P1/P2 and the WIN2 window and exits normally. Its different row identity prevents a sibling match with the other input, causing the F1 double exit described below. Consequently the512 reported padding positions neither waive upper payload bits nor mask the first tree fault. Complete-word transport equality includes all bits of each partial's data, tag, valid, error and fault fields. It proves no numerical relation between different partials or against gold.

## First tree-leaf fault: concrete original schedule collision

The immutable selected source is `ceaed19c4`; exact source snapshots and SHA256 identities are adjacent. The raw monitor timestamps below are pre-edge logical source observations; internal uninstrumented stages are labelled **derived from source**, not measured native clock phases.

At frame edge1784 the following actual words return simultaneously:

| Actual CAP child | A source owner | B source owner | Actual CAP pins | P1 sample | Derived F1 assertion |
|---|---|---|---|---|---|
| W `g_l1[0].u_n` | lane0 L01 row3076,lo0/k2/n3 | lane1 L02 row3162,lo0/k2/n3 |1790|1791|1795|
| W `g_l1[1].u_n` | lane2 L03 row3247,lo2/k1/n3 | lane3 R01 row3333,lo0/k2/n3 |1790|1791|1795|
| E `g_l1[0].u_n` | lane4 R02 row3418,lo0/k2/n3 | lane5 R03 row3502,lo2/k1/n3 |1790|1791|1795|

Actual pin word joins are independently checked for all624 returns. `ot_s81sl_cap_tr.sv:39..74` registers the CAP input lanes, then connects adjacent lanes directly to the two actual child nodes. R01 is W child lane3 in this wiring. These are different row identities, so no sibling match can merge them. Earlier inputs at these nodes cannot consume these distinct rows. The node source P1/P2 stages, WIN2 windows, and `fa && fb` at `ot_s81_retn_static.sv:176..180` consequently produce two unmerged exit-slot owners at derived edge1795. This violates F1. The existing forward selection gives A priority; it does not queue both words. The source sticky-fault path is node fault after1795 → CAP tree fault after1796 → root `lf_p` after1797 → `fcause[1]` after1798. The first actual monitor observation is **1799 causes0002**, exactly matching this path. Internal F1 was not directly instrumented, so this is source-derived causal attribution rather than an additional measured signal claim.

## First n6 fault is independently caused before any child loss contaminates it

The earliest actual returns at frame1776 are W lane1 row3160 and E lane4 row3416, each lo2/k1/n3. They reach actual CAP pins1782 and child P1 samples1783. With the source's constant13-edge node sample latency, their W/E child results are sampled at1796 and the respective column-root results at1809. They therefore enter n6 together at1809 with different row owners. The same P1/P2/WIN2 F1 path asserts at derived1813; root `fcause[3]` is set after1814 and first **observed1815 causes000a**. These particular words precede the outputs from the first illegal child exit (sample edge1804), so this first n6 explanation does not depend on choosing either lost child word or on extrapolating a healthy model after collision. The specialized n6 source is `ot_s81sl_cap_rt.sv:485..700`, with the same F1 rule (`610`) and sticky fault (`696`).

## Expected F9 is later and separate

First complete actual row3158 enters the frame return at1779, actual CAP pins1785, child P1 at1786; source-derived child/column/n6 samples are1799/1812/1825. The actual FIN A observation is1826 (`fa=1/0b0ac043`). D1/D2 source stages decode this complete word against original reset `rcnt=0`, suppress D3/CW and assert F9. The actual monitor first shows F9 at1829 and combined sticky **010a at1830**. Thus the first tree faults precede the expected reset-CAP range rejection. Zero CW is consistent with reset configuration; it does not prove healthy tree completion or VP drain.

## Decision boundary

The source and measured chronology identify a genuine original global return-calendar/ownership conflict, not a missing CAP base address. A target3/rbase-only programme cannot recover words already rejected by child/n6 F1. A healthy fixed CAP programme is HOLD until an authorized source calendar/placement correction or explicitly priced structural alternative proves all actual tree exit-slot obligations at the original dates. Current authority permits this read-only audit only: no schedule retiming, source patch, profile adoption, deadline extension or second run. Original native physical phase, numerical gold correctness, deadline PASS, healthy CAP/VP drain and token PASS remain NULL/unqualified.
