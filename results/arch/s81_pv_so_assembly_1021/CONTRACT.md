# S81 all-quarter P.V to SO source assembly

Default-off candidate, based on current-ABI G4 source136a3dcae. No physical qualification, die binding, or functional-token completion is claimed. Consumer-only full-shape no-ABC synthesis measured14465 technology-independent cells (1976FFs,9297mux cells,136SRAM macros); this is not mapped area or timing. The HC BF16 copy transpose and HBM18-bit tile transpose have different layouts and cannot implement this transport. Historical bb3262 describes only a model. This candidate uses existing native32x64 SRAMs and existing service/SM arithmetic; it introduces no arithmetic.

The real hierarchy is dsdv_svc_rs_pvso_entry -> dsdv_pv_so_ingress -> current dsdv_svc_rs_entry q port -> existing job gate/frame parser/SMJ consumer -> existing SMS/SO target/gather. PVSO_ENABLE defaults0; it also forwards PV_IDENTITY to the real ATT producer. The wrapper retains all current service ports and detects any external-q/generated-q collision as a sticky fault. It never stalls or arbitrates. The old service/source branch and its progressing jobs are untouched.

## Producer authority and wire format

PV_IDENTITY defaults0, preserving the old P.V header zeros. CFG reserves owner[52:33] and owner_valid53; owner is {epoch2,user10,service_tag8}. At actual GO, the producer validates CFG user/tag against accepted WIN_LOAD, and latches the owner, position, quarter and global tile. Subsequent CFG writes cannot relabel an old drain. Position comes from the actual WIN_LOAD header[479:459], not from the quarter collector.

P.V header (pv_d[512]=1):

| Bits | Meaning |
|---|---|
|511:120|reserved0|
|119:99|actual launch position21|
|98|valid source identity|
|97:94|global tile4|
|93:92|quarter2|
|91:72|launch owner20|
|71:64|P.V column8 (must fit0..7)|
|63:0|original producer flags|

Nonzero producer flags become a sticky ingress fault rather than being discarded. Four subsequent records contain16 head FP32 values each. Dimension =32*global_tile+8*(data_word-1)+column. The collector accepts only the declared quarter's tiles, matching owner and position, and128 distinct(tile,column) headers with exactly512 data records. All four quarters can interleave but the single input face accepts at most one record per edge. A caller must serialize the four physical routes into booked slots; there is no hidden multiport write assumption.

## Control and parameter ownership

All control/data pins land in registers. cfg_v installs cfg_owner20, cfg_position21, cfg_se_jid8 and cfg_so_jid8 only when the preceding serializer transaction is inactive. Five param_v rows carry param_row0..4, param_owner20 and param_position21. Row0 is obase; rows1..4 are coslo,coshi,sinlo,sinhi,16FP32 values each. Owner and position must match the current transaction before storage; duplicate or missing rows fault. The caller must supply coefficients from the declared position's actual source; tagging arbitrary coefficients is not numerical qualification.

den_v carries den_mask16, den_owner20 and den_jid8. Every head must have the same transaction's SE denominator before ready. These event faces must be connected to actual source-owned producer/SM state in the final assembly; the standalone protocol bench is not that die-level binding. Existing SOT14 must be installed before SE, independently preserving the output target's own SE/denominator proof and booked write/read/retire windows. Late SOT is invalid.

launch is a fixed compiler event. The block does not start itself when ready rises: a missing all-quarter/parameter/denominator fence at launch is a sticky fault. Config must capture at least one edge before the first quarter/parameter/denominator record. The earliest legal launch capture is one edge after the latest required quarter/parameter/denominator input capture (their landed checks/storage commit on the intervening edge). Launch captures at E; first q output is E+2, followed by534 consecutive pin words through E+535. The first six words are a parameter SMJ9 header plus five rows. Sixteen operand frames follow, each one header plus32 rows of16FP32 values, with headmask=1<<head. The outer frame tag is the service tag owner[7:0], while inner SMJ jid is cfg_so_jid. Both user and position remain in the outer header.

The enclosing engine4 descriptor must book original frames +1 SOT frame +17 generated SMJ frames in the same pending job. The existing so_pend/target retirement path defers completion. Serializer done means the last q word was emitted; it is not SO retirement or token completion. Per-entry SOT route/gather windows differ between E and W and must be lowered independently.

## Storage, bandwidth and latency bill

- P.V storage:16 coherent32x512 head stores =262144bits, implemented by128 single-clock32x64 SRAM macros. Each data record writes one32-bit half-bank per head; no SRAM sees two writes in an edge.
- Parameter storage: five512-bit rows exceed2kb, so eight additional32x64 macros hold them. Total136 macros,278528 physical bits (34KiB).
- Native macro outline31.968x17.280um: total macro area75127.35744um2 (0.075127mm2). This excludes standard cells, reset/clock, relay channels, power and placement.136 macro clock pins require a physical clock plan.
- Complete ingress:640 records (128headers+512data) at II1. Unique P.V payload262144bits; remote three-quarter payload196608bits, excluding packet overhead. At1.2GHz,640 occupied edges cost533.33ns before actual link/landing costs.
- Serializer:534 occupied edges, first-to-last533, at II1. On an NP4 input path this is at least2133 first-to-last edges. Existing entry/tree/SM landing ages and54-edge SMS result latency are additional schedule obligations.
- No output rate, die fit or timing gain follows from these counts. The8192-bit head read select is a source-level registered mux; localization, mapped fanout/depth, SRAM timing, pin reach and complete clock spread remain unqualified.

## Evidence scope and remaining integration

The transport bench checks all8192 FP32 bit patterns over two full transactions through real SRAM models and the actual ot_s81_svc_job gate. Patterns test permutation and metadata; they replace no P.V data in a token replay and do not qualify attention arithmetic. The producer-identity bench exercises the exact helper instantiated by the real ATT, including default0 behavior, CFG-after-GO preservation, wrong tag and reset-stale controls. Whole-hierarchy lint elaborates the real current service entry, not a substitute consumer.

Still required before release adoption: actual four-quarter routed sources and immutable calendar; actual SE proof wiring; position-owned coefficient source; compiler entry-specific SOT/job-frame schedule; full source-assembled attention/SO token replay; die pins/landings and packet lifetimes; mapped sizing/census/clock/floorplan proof; SS/FF physical closure. No synthetic fixture or cut-only pass may stand in for these obligations.

## Recorded validation

Finaltransport unit1135723 exit0:2 fullshape jobs,8192FP32 values each,534words/533span,launch+2first output,allwords passed actualsvc jobgate;7 causal controls caught the required primary fault bit. Producerguard unit1169437 exit0 checks actualboundhelper default0/GO/CFG-afterGO/wrongtag/resetstale/invalidGO. Final exactsource hierarchy unit1223747 exit0 elaborates PVSO_ENABLE1/NTP1 and the real entry/SM/target graph. Coarse sizing unit1147942 exit0. All on ot-epyc7 via unpinned ot-run. Immutable logs, source hashes, units and scope are in record.json. No physical gate, view promotion, source-assembled token claim or main merge.
