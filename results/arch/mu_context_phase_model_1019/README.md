# Cyclic admission: OVL representation comparison (model, not implementation)

This compares storage and player changes before choosing a phase word/schema. It
makes no reserved-bit changes to the production OVL player. Calpipe owns unified
INIT/RETIRE eligibility, context-load slots and the final programme manifest.

The private compiler inserts the existing canonical logical MU context selector
(kind12/beat1 at K cycle2) before the existing user0 selector (kind12/beat0 at
cycle3). Both opaque548 wire words retain beat0. Calendar reservations are then
recompiled, rather than treating a missing word as a free admission slot. The
new mu_opcal input snapshot reserves the real three-edge leaf prefetch spacing;
its SHA256 is recorded in both JSON outputs. It is kept here for reproduction.

Run on the fleet with Verilator-independent compiler/model inputs:

```
PYTHONPATH=tools python3 -m qwen_static_schedule.d2d_phase_storage_model \
  --frame 8 --calpipe-opcal results/arch/mu_context_phase_model_1019/calpipe_mu_opcal_input.py \
  --out F8.json
```

Repeat with --frame16 for F16. F16's real leaf guard rejects4521 entries in the
4096-word ROM; the model records that rejection and uses its reported count only
for capacity comparison. It does not bypass that guard in production.

## Concrete options

The table covers list ROMs across BOTH dies (four directions), excluding the
unchanged sys_face configuration ROM and the compute observer leaf ROM.
One4096x72 mask ROM is2391.58656um2 (38.016x62.91um).

| Candidate | H | Base list words/direction | Expanded all-active2H upper bound | Leaf base words | 2H fits current22-bit leaf period? | List ROM area |
|---|---:|---:|---:|---:|---|---:|
| F8 expanded32 |2013400|815|1629|2063|yes4026800|9566.35um2|
| F8 masks |2013400|815|815 (reused each phase)|2063|baseH fits; needs phase state|9566.35um2|
| F16 expanded32 |4026800|1703|3405|4521,FAIL4096|no8053600|9566.35um2|
| F16 masks |4026800|1703|1703 (reused each phase)|4521,FAIL4096|baseH fits; needs phase state|9566.35um2|

F8 expanded2H fits even the existing11-bit OVL logical address. Actual cyclic
cohort filtering reduces GO words but may add long-gap wait words; exact INIT /
RETIRE/context counts still come from Calpipe. The all-active bound is deliberately
separate from that unfinished admission manifest. A small number of explicit
context heads also fits the815-word headroom below2048, but must be scheduled.

A masked GO word needs a phase mask and the player needs a modulo-P counter;
wrap is meaningful only on wait words. A32-bit candidate has eight mask bits by
reusing the current low byte, which includes the old wrap bit. It therefore needs
new decode/validation, precise common phase reset, and agreement with both wrappers,
leaf masks and context authority. Eight phases is a development candidate, not an
irreversible limit: a72-bit physical word can support up to48 candidate mask bits
before other metadata, with new qualified logic. No such format is selected here.

Expanded words preserve the existing32-bit entry format and require only wider
addresses / banking when necessary. F8 four-phase all-active3257 words still fits
one4096-word ROM per direction, though its expanded period exceeds the current
22-bit leaf period. F8 eight-phase6513 words needs two banks/direction if unpacked;
packing two32-bit entries per existing72-bit physical word restores one bank at
the cost of a registered halfword select. Current minimum list interval is35
edges, leaving room for an extra prefetch stage, but that implementation is unbuilt.
F16 four/eight-phase unpacked areas are19132.69/38265.38um2. Both encodings must
still qualify the leaf capacity; masks cannot repair the F16 leaf4521 overflow.

## Throughput and admission conditions

Recompiled steady frames: F8 13112.15tok/s, F16 13708.16tok/s. Under Calpipe's
candidate policy (user0 always active, fillers activeH then inactiveH), the work
budgets become F8 8940.10tok/s vs F16 9238.10tok/s, before any extra admission
work. This assumes one activeH performs the same complete filler tokens as the
steady frame and must be confirmed by the final INIT/RETIRE manifest. User0
stays4768.05tok/s. The difference is3.23%; storage/table rate is not end-to-end
measured token throughput.

A conditional preference is F8 expanded legacy entries: at the bounded two-phase
candidate it saves the new OVL decoder/counter contract while fitting the same
physical ROMs. F16 masks remain an option if the extra leaf ROM and phase logic
are worth the3.23% cohort-work difference. This report does not select either.

Both frames retain a7780-edge common LINK PLAYHEAD gap around the chosen origin
(last busy -3856, next start3924). That is not a programme-retirement proof: the
KV attention programme, host context source, compute result/embedding tail and
controller bank lifetimes must be included in a per-user quiescent load window.
Request and response eligibility must follow their originating exchange, not
independent mask decisions at their different link-start times.

Canonical context identity: TAG={seq14,user2,stage0,token18,pos13,seg0}; epoch must
match header; ctx_x={load,record128}, tag4D43, mask1<<(user-1), token/position as
existing ABI. The raw observer omits image/digest/cap checks and is not an accepted
production load source. The preferred folded sys_face observer waits for full
context RX acceptance before issuing ctx_x. The conservative candidate bank-load
age is RXslot+3 (full validated observer edge plus controller landing); direct
same-edge full validation might retain+2 but has not been implemented or measured.
Final phase manifests must name the actual paired load slots and validated age,
then reject INIT before load or load before previous-generation retirement.
