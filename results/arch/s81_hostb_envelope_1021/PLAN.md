# Connected HOST(b) source plan — candidate, no rack qualification

The preserved HSF0 HFWD type7 carries exactly512 data bits through HD-CTL as kind6 ring payload[532:21]. Legacy stage HOST is514 bits `{class2,data512}` plus valid. A single HFWD cannot carry it. This successor uses two HFWD records per word; no implicit class, stage, rank, token, position or launch epoch is synthesized.

## Protocol HBE1

HOST_WORD uses a header followed by its512-bit body. KS_DESCRIPTOR, ARM and STAGE_RETURN are single-record messages using the reserved header region for their bounded inline fields. Other ring kinds may occur between them, but no second HOST header/body pair may interleave. All receivers track the header/body phase even for a nonlocal destination, preventing raw body data from being misdecoded as a header. Missing body by its explicitly programmed static deadline faults; no completion wait/reschedule. Every consumed header validates magic/version, opcode, source/destination range, exact length, transaction identity and context. Header-only opcodes cannot occur while a HOST_WORD body is pending. Any incoming kind6 that fails framing is a sticky fault and cannot issue a stage write/start.

Header bit allocation (LSB first):

|Bits|Meaning|
|---|---|
|31:0|magic0x31454248 (ASCII HBE1 in little endian)|
|35:32|version1|
|39:36|opcode:0 HOST_WORD,1 KS_DESCRIPTOR,2 ARM,3 STAGE_RETURN|
|47:40|stage ID0..240, explicit configured strap matching actual rack S000..S240|
|49:48|TP rank0..3, explicit configured rank|
|65:50|transaction ID, supplied by actual producer|
|75:66|body valid bits:514 for HOST_WORD (class in header),53 KS, defined ARM/RETURN lengths|
|77:76|legacy HOST class2, preserved exactly; no inferred class|
|87:78|user10|
|108:88|position21|
|129:109|token21|
|161:130|epoch identity32; supplied by an actual armed epoch source|
|209:162|static body-arrival deadline48, in explicitly bound local counter units|
|273:210|programme/source identity64, checked against actual boot contract|
|511:274|opcode-specific inline fields, otherwise zero: KS raw53[326:274] and slot3[329:327]; RETURN t_host77[350:274] and t_kd54[404:351]; ARM active-slot mask6[279:274]|

HOST_WORD's body is the original data512 without truncation. KS_DESCRIPTOR's inline[52:0] is the exact53-bit `{start,user10,tok21,pos21}` word; all other inline bits zero, length53 and duplicated header context must agree. HOST_WORD length514, ARM length0, RETURN length131 are fixed and rejected otherwise. The current fixture's corrected word is0x1000082e4fffff for user0/token16754/position1048575; old0x1001ffffe04172 swaps token/position and is retained as an unexecuted failed witness by TOKEN. This is fixture context, not a shipping descriptor or programme anchor.

Only genuine accepted KS descriptors enter the existing default-off six-position starter slots. ARM never invents descriptors or epoch0. The existing5cf63dca5 static starter is configured by full legacy class0 CSR0x19(SYNC)/0x17(ARM) carried unchanged as HOST_WORD records. Those real512-bit CSR payloads retain explicit epoch, firstKS, firstcommand, owner, graph and phase. The HBE1 ARM inline6-bit mask is a commit/selection record that requires the actual starter armed/sealed contract; it is not a compressed substitute for those CSR words. Descriptors arrive after that actual ARM as the existing source requires, in exact slot order and before each immutable deadline; missing/late descriptors fault. Production first-command anchor remains open: current21fbf0c14 has96 unsealed NORMR80+XFIN16 rows, no END/HOSTboot/global phase. A KS transport component proof cannot qualify the whole stage programme.

HOST_WORD preserves original class0 CSR/calendar/template/GUNIT semantics (0x10/11/13/14) and all ingest descriptor/address/data/marker words in order. No boot or programme write is permitted while an affected job is active. KV ingress is the original class/data sequence through the actual ingest, not a new synthetic KV interface. Exact legal class and active-write checks are sourced from that selected consumer.

Stage return uses a distinct source-qualified single-record return opcode and egress type, never HSF0 RESULTtype9. Its inline131bits preserve both real t_host77 and t_kd54; valid/event bits remain those actual producer bits, with no fabricated event. Full t_host77 and t_kd54 plus source stage/rank/transaction/context must reach an actual head collector on a reserved static slot. Return injection collision, late/missing return and wrong identity fault. RESULTtype2 vs DRAFTtype4 in kind5 remain distinct; neither is generically spliced into KS. Later-stage input-token context must be forwarded from the admitted descriptor, not overwritten with its KIT output.

## Static cost and real connections

Each514-bit HOST word requires2 HFWD512 records, each a1104-bit ring beat crossing the real two-lane endpoint. Against the existing reliable-link cap456/596×1023/1024≈0.764 beats/cycle, the wire-only lower bound is2/0.764≈2.618 cycles/HOSTword, versus1/0.764≈1.309 for the old legacy frame. This is a throughput ceiling/lower latency bound, not a scheduled or measured production rate. The current417-word fixture job requires834 ring beats, at least1092 wire cycles before source-head holding/calendar gaps and hop/landing costs; exact integer calculation and selected head spacing will be recorded in the codec model. KS_DESCRIPTOR, ARM and STAGE_RETURN each cost one additional ring beat at their booked static slot. No zero-prefill or decode-rate claim.

The existing head has one pending HFWD register and faults if another becomes pending before its static pop; actual safe acceptance spacing must be established from the selected controller, not guessed from line bandwidth. Calendar composition must reserve both records and every return slot without overlapping XB tag windows. A per-stage continuous producer cannot exceed the lowest head/route/ingest rate.

Required named source/binding changes: actual head HFWD producer/collector; actual stage entry tap *before* the ordinary ring stop; stage HOST/KS adapter feeding the existing seq_host and Engram fork; static return injector on an actual available outbound circuit; actual die landings and clock/reset source roots. Current HD-CTL emits hops1, so an unchanged ordinary ring stop locally delivers the beat and does not transport it across241 stages. There is no automatic rack broadcast. Exact selected NEXT head→S000 and stage→stage endpoint/circuit mapping is being supplied by die owner before any adapter RTL or pin route is claimed. Any required internal crossing/extra registered relay is priced, not aliased to existing s_7N HOST wiring.

Preserve HOST_EN1 and original endpoint views throughout this candidate. New connected source is separately named/opt-in until native<=32, exact source mechanism, layout/reach, CTS/GRT and route qualification. No canonical master or rack claim follows this plan alone.

## Bounded source/proof sequence

1. Pin actual circuit entry/exit and source files with die owner; pin genuine descriptor/boot producer with TOKEN. Keep absent production anchors explicitly open.
2. Add executable envelope codec and exact range/length/context/static-word accounting. Implement head producer/collector and actual entry adapter together, preserving old default behavior.
3. Minimum connected head→two distinct addressed stage adapters→head proof uses actual514 HOST consumer ports and real return producers. Exercise full-width classes/tokens/users, ordered KV descriptor/data/marker, wrong destination/identity/length, body timeout, missing/late return, RESULT vs DRAFT and boot-active refusals. Qualify source mechanism only; production stage anchors remain separate obligations.
4. Book every added head/tap/forward/injection edge, storage and circuit slot. Bind real die landings and gate each changed master using the normal source/native/physical rules. No global all-closed barrier for independent element work.

## Actual circuit evidence and remaining binding

The selected G8 plan is gold2:/srv/opentallas-scratch/claude/codex-s81-g8-resume-1021/die72-g8iq/plan_routed_g8.json. s_0N has NEXT pairA tx/rx0/1 on lk_WN0/1 and PREV pairB tx/rx2/3 on lk_WN2/3 (older overlay calls those link_0_4/5). Legacy s_7N HOST input is uniquely routed by hf_7N_l0/l1/l2 with6/7/7 stations; status ht_7N has8. A connected source successor must intercept before s_0N ordinary ring delivery and provide explicit registered crossing/landing to the real host consumer; these existing routes are evidence, not permission to pretend s_0N equals s_7N. The actual head-to-S000 rack mapping remains required.
