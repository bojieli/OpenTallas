HBM TX feed-forward parity stage candidate

Source branch: codex/hbm-tx-feed. Source implementation commit: dc98564b80a.
This is a dormant source proposal. No recipe, plan, timing constraint or canonical
parameter default is activated. No physical closure result is claimed.

The routed tall ELA2 form failed on ch_q -> pp0: an eight-level feed-forward
matrix whose source bits each feed an average of 150.57 parity rows. EFF=1 on
ot_pdie_serdes_tx selects FF=1 on its LA2 encoder. Each 260-bit half matrix is
split into four 65-bit slices and eight 300-bit partials are registered. The next
edge combines four partials per half into pp0/pp1; the downstream LA2 recurrence
is unchanged. Four 520-bit copies of the selected chunk each own 75 parity bits.
The canonical keep-reg-cell synthesis hook preserves those copied source flops.

All 600 original half-matrix rows reconstruct exactly from the 2400 sliced masks.
The original row has 110..152 nonzero inputs (balanced XOR depth 8); each new
partial has 20..44 (depth 6), followed by a four-input combine (depth 2). Source
incidence per input is 119..175 uses before copying (mean 150.569), and 25..52
per copy after (mean 37.642). These are source estimates before logic sharing.

Timing contract: ELA2 FF0 port -> p_d latency 8 edges becomes 9 with FF1.
Both valid and all 544 output bits are delayed exactly one further edge. The
input-side sticky fault keeps its original cycle. PMA_LAT and frame cadence
remain unchanged: ten 544-bit PMA words per RS544 frame, one word per edge.
At 833 ps this adds 0.833 ns to each TX traversal. Parent TOK owner must charge
that edge per traversal before enabling EFF in a production recipe.

Control f0/f9/fe and replicated f0w/fv/f0v retain their corresponding parity
stages. Par-load moves one edge; the PMA phase and beat window move together
from {d6,d5} to {d7,d6}. h0s remains the approved constant-header source fix.
FF0 keeps the existing LA1/LA2 behavior and old parameter order; FF/EFF are
trailing default-zero parameters. LA1 ignores FF.

Native proof: results/rtl/hbm_tx_ff_1106 contains exact tested source snapshots,
source hashes, raw logs, and the source-normalization comparison to the pinned
candidate. The tested and pinned encoder differ only in comments and two unused
genvar names. Native default LA1/LA2, enabled full-word/valid refinement including
stall/restart, PMA composition, parity-flip, partial-bit-flip and par-load-skew
mutants are required. See actual logs for completed verdicts.

Physical readiness requires mapped count <= 150000 and standard utilization
<= 0.45 in the existing 285.12x207.36 outline, then parent source/geometry adoption
and an actual generated-image review before any P&R. Native exactness and an
area estimate do not prove TT/FF timing, DRC or sign-off. A separate admitted
candidate netlist LEC remains required after synthesis; the prior tall kit LEC
was an infrastructure OOM and does not qualify this candidate.

Measured mapping: conservative Yosys count 111,698 standard cells, 16,882 DFF,
18,245.73276 um2, and 33.209% utilization of the actual 54,942.1056 um2 core.
OpenROAD synthesis ODB after dead logic removal has 110,078 standard cells
and 18,173.9 um2 (33.078%). All 2,080 copied chunk DFFs survive mapping.
Old synth-to-placed growth ratios predict 118,073.79 placed cells and
18,524.151 um2 (33.7158%); this is an estimate, not an actual placement result.
Yosys peak RSS was 627 MB. Source-pinned logs and counts are under
results/rtl/hbm_tx_ff_1106/size. No placement or route was launched.

Completed native proof: LA1/LA2 default regressions passed 3,981/3,980 full
words. FF continuous refinement passed 4,979 full words including 497 parity
words; stall/reset passed 4,952 full words including 494 parity words across
two reset epochs. All had zero mismatches. Native PMA composition passed
3,914 words with zero mismatches. Each mutant (parity flip, partial-bit flip,
par-load-edge error) was caught with 117 mismatches over 1,179 words. Data and
valid add exactly one edge; fault adds zero. Final admitted unit
oth-ubuntu-3575005-1793962989 completed exit zero; peak RSS was 199,876 KB.
