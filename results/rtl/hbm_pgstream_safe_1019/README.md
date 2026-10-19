# Actual PGSTREAM regional bridge source experiment

**Overall source safety FAIL. No placement, CTS, route, adoption, token or die
qualification.** Frozen source/gate53cbcc9a8/95463 is untouched; legacy files
remain byte-identical. New top `ot_hbm_su_static_pg_stream_split_regional` has
SAFE_COPY=0 by default. The candidate uses SAFE_COPY=1, QID1/G2, RR18/WR15,
STRAP1, FAULT_REG1. Model was committed before implementation (b22240738).

Actual source state is regionally replicated with keep_hierarchy paramodules;
serial request regions7bits, stream and return regions15bits. No new data,
valid, fault, reset or return-bank edge is charged by this bounded step. The
request4q/2q, return2q/4q and inject3q/7q windows are measured unchanged by the
original actual-parent lockstep/window checker. No buffer-only source copies.

Verilator5.050 qualification `qualified/results.json`: **four positives PASS**
(18/15, legacy10/7, QID0 and default-off) and **eight causal mutants FAIL**
(wrong return bank, wrong request bank, no return staging, wrong write bank,
wrong inject bank, early request read, wrong fault publication, cross-reset
fault clearing). Each has its committed actual bench log; shell returns1 on
FAIL because the inherited bench itself prints FAIL then uses $finish. The
earlier status-only harness mismatch is preserved, not counted as a source
failure or an ineffective mutant. Main18/15 PASS7194 checks/9228 windows.

Actual TT-library source map (`r3/binding.json`, `r3/yosys.log`) has8710FF,
27526 physical cells,3856.205880um2 native library area, zero Yosys check
problems. These are source-map numbers, not placed footprint/native clock STA.
The full flat BUF/INV-transparent census has21391 roots and **14 above32**;
raw bridge reset1726, inherited tap controls564/36, tap/leaf resets92/73 and
inject/select logic83/82/81/41/35 remain unsafe. Control replication increases
reset pressure; no global fanout PASS claim. The baseline full census has25
above32/worst1707. Revision2's15bit serial request regions incorrectly
predicted31 but measured61 because four physical loads/bit; failed evidence
is preserved and the model was corrected before7bit source revision3.

Physical8point checklist: pins OPEN (dynamic pos/inject unregistered decode),
reach OPEN, fanout FAIL14, depth boundary10levels OPEN, storage audit in MODEL
but no SRAM conversion needed for the individual small data banks, sizing/
pin-bound exception OPEN, native clocks OPEN, schedule bridge edges PASS only.
Inherited3edge serial reset landing is external to this bare source map; final
new reset source must preserve that release age and existing leaf/tap ages.

All jobs from this agent are terminal. Fleet outputs/binaries stay at
`ot-epyc5:/srv/opentallas-scratch/claude/pgstream-safe-source-1019`.
