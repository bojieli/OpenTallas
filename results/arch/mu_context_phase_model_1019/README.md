# Cyclic admission representation: concrete model options

Authoritative inputs here are Calpipe's lifecycle_F8_P2.json and
lifecycle_F16_P2.json (EMB61, one root-capture edge, three-edge leaf prefetch).
These are compiler/model evidence with production_bound=false. They include
absolute active units, leaf INIT/RETIRE masks, explicit paired context slots,
retirement windows and expanded link starts. The earlier F8.json/F16.json and
EXPLORATORY_EMB60.md are historical capacity exploration, superseded for the
current lifecycle rates and counts.

Run tools/qwen_static_schedule/compare_lifecycle_storage.py on the two lifecycle
files to reproduce lifecycle_comparison.json. The comparison records input
SHA256 values. It checks load-before-INIT and retirement-before-next-load from
the supplied manifest; it does not certify the still-unimplemented phase RTL.

| Option | Leaf words / ROMs | OVL words per direction / total ROMs | Total list+leaf ROM area | Lifecycle model tok/s | Existing leaf22-bit time? |
|---|---:|---:|---:|---:|---|
| F8 expanded leaf + expanded legacy OVL |3300 /1|1484 /4|11957.93um2|11920.09|yes|
| F8 masked leaf + expanded legacy OVL |2063 /1|1484 /4|11957.93um2|11920.09|yes|
| F8 masked leaf + masked OVL |2063 /1|815 /4|11957.93um2|11920.09|yes|
| F16 expanded leaf + expanded legacy OVL |8216 /3|3260 /4|16741.11um2|13112.10|no,23-bit period|
| F16 masked leaf + expanded legacy OVL |4521 /2|3260 /4|14349.52um2|13112.10|yes,H+phase state|
| F16 masked leaf + masked OVL |4521 /2|1703 /4|14349.52um2|13112.10|yes,H+phase state|

The fixed one4096x72 macro area is2391.58656um2,38.016x62.91um. The table
excludes the unchanged sys_face configuration ROM. Full tile/std-cell overhead
and new banking/clock implementation remain to be synthesized and gated.
F8 has H2013408 and superframe4026816; F16 H4026816 and superframe8053632.
Calpipe's revised lifecycle keeps fillers active from their first admissible
head to their last head in the second phase. It supersedes the earlier
half-duty illustration. F16 lifecycle output is10% above F8; this is a model
comparison, not measured full-token throughput.

The direct OVL conclusion is independent of the leaf choice: expanded legacy
32-bit lists fit a single existing4096x72 ROM in every direction for BOTH
bounded two-phase candidates. F8 fits existing11-bit list addresses; F16 needs
AW12 wired to the same ROM's full address. Adding OVL phase masks saves no
physical list ROM in either case. It introduces a new GO-word mask decoder,
reserved-bit checks, modulo-phase state and precise phase-reset/clock agreement.
A useful third option is therefore F16 masked LEAF with legacy expanded OVL:
retain the faster lifecycle model and avoid an unnecessary OVL format change.
F8 all-expanded remains the smallest implementation change if closure speed
and the existing leaf ABI take priority. ROOT chooses; neither is frozen here.

For future larger schedules, historical capacity results show when expansion
adds banks and when two32-bit entries packed in one72-bit physical word can
save banks. Packing needs a registered halfword select and a qualified prefetch
latency; it is not implemented. P<=8 masks are a development proposal, not an
irreversible admission limit. A72-bit physical word can carry wider candidate
masks, with corresponding qualified logic. No reserved production bits changed.

## Canonical context and quiescence

The logical MU selector is kind12/beat1 at K cycle2, followed by the user0
kind12/beat0 at cycle3. BOTH opaque548 wire headers carry beat0. TAG is
{seq14,user2,stage0,token18,pos13,seg0}; header epoch matches TAG. ctx_x is the
existing129-bit {load,record128} layout (4D43, user mask, token and position).
The production source must reuse full face digest/image-epoch/cap validation;
the raw observer's header/TAG checks are insufficient. The conservative folded
observer candidate reaches the controller bank at RXslot+3. That age is
explicitly provisional pending RTL measurement.

Both exact manifests bind user1/2/3 loads to actual user0 head slots0/1/3:
MU wire arrivals251422/503098/1006450 and bank loads251425/503101/1006453.
First INIT heads261098/513849/1084658 follow those loads. F8 per-user quiet
intervals from retired head completion to next cyclic load are452653/573495/
1390202 edges; F16 intervals397565/518407/1221158. These are conditional static
model bounds. Actual KV/native/controller lifetimes and the validated context
source still require production binding and negative controls.

## Initial epoch remains a separate contract requirement

The exact expanded lists use steady cyclic origin247497,D0=16. Binding the
existing OVL FIRST1176 to a positive leaf L0 anchor without compensation would
place raw L0 before the epoch and/or omit user0's first attention exchanges.
A valid initial-epoch manifest must provide either an origin0 playback plan
with user0 context/embedding prelude, or an explicit cold prefix and steady
wrap-base/anchor mapping. Current sequence/player pin launch ages must be
measured into that equation. A rotated steady superframe alone is not first-
token proof. This remains a blocker for every option above, alongside production
Q-ready evidence and full-identity context loading. No physical phase wrapper
or new word/schema is implemented by this comparison.

## Selected model follow-up: F16 fully expanded, no OVL masks

ROOT selected F16 fully expanded (Calpipe notification). The leaf owner handles
three4096 ROMs,14-bit pointer and23-bit timestamps/header. The OVL entry layout
stays32 bits. selected_F16_origin0_model contains independently re-encoded and
decoded origin0/D016 lists from that exact lifecycle input:3260 words/direction,
AW12, period8053632,3259 GO starts each. Adjacent and wrap playhead occupancy
checks pass, with wrap slack1014/2580/2561/1019 edges (C_TX/C_RX/K_TX/K_RX).
Reproduce using expand_lifecycle_ovl_model.py. These remain model files, not a
production wrapper bind. The cold user0 prelude remains explicitly unbound.

A Verilator5.050 boundary bench (tb_ovl_launch_age.sv) measures the existing
face input/output pin-flop and D2D pin/calendar stages using the selected lists.
With raw face fwd_epoch sampled at E, FIRST1176, first C_TX word789:
controller start E1966; face cal_start output E1967; D2D cal input-flop E1968;
D2D request tx_slot output E1971. First RX cal_start output is E3773. The ROM
read+capture prefetch adds no start-edge delay. Against raw CMD reference774,
the extrapolated L0 reference is E1197=E+FIRST+D0+5 (or internal list-go anchor
+D0+4). This is a boundary-model measurement, not a die-netlist/native-producer
composition proof. The native codec/seam programme reference and initial epoch
prelude must still be composed into the final absolute anchor. launch_age.log
is committed; run_ovl_launch_age.sh reproduces it on the fleet.
