# Actual selected Q producer mapping: complete finite seat contract, execution unresolved

The missing upstream mapping is now concrete: **four Q-producing receiver slices issue eight RoPE commands, forming 64 eight-lane DD words and all 512 distinct native59 Q-seat addresses**. This is a source-derived contract, not observed selected-programme execution. Actual publication edges, token/reset epochs, QSLOT dates, native phases and a connected compile budget remain NULL. No source, programme, calendar, profile, metadata, runtime or existing job was changed.

`extract.py --extraction-only` checks all 400 ISA PW beats against the exact selected 25 instructions, the unchanged 406 decode commands, selected lowerer receipt hash, native GEN0 hash and complete distinct-seat coverage. Without that scope it exits 2 / UNRESOLVED. It never invokes a lowerer, compiler or simulator. `sources.json` pins every extracted source; `commands.json`, `isa_decoded.json`, `q_words_contract.json`, `q_seats_contract.json` and `actual_constructor_ports.json` contain the machine-readable mapping.

## Exact source and instruction ownership

Selected ISA is SHA cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796. PW0..399 carry its 25×16 beats; PW400..975 are zero. Global ISA PC7 writes the lower64 elements of each of four Q heads, PC9 the upper64: their union is global VM13696..14207. These global ISA words are not the slice's 457-bit PROG words. In particular the ISA has no direct window10 Q write. CALR drives separate local PROG indices after DV lowering.

Frozen `dv_lower.py` alone only lowers global RMSNorm and lists QK/RoPE as unfinished. That TODO must not be used to claim that Q arithmetic has no implementation. **Selected7e515 `dv_lower_vec.py` exists and SHA3f01c9a9… exactly matches the retained body lowerer receipt.** Its `qkv_roles`, `words` and `PIDX` provide the real Q/K/V split and Q write addresses. The 406-command body's qk family contains26 commands: six q/k/v first steps, five head RS, five QN, and ten RoPE halves (eight Q, two K). The Q words use destination VM with full address `W_D2D | seat`, W_D2D=2<<22. `qfd_dv_slice2` recognizes address[23:22]=10 and emits kind0 rather than writing local VM.

| Head | Slice ID / actual GEN0 instance | PC7 / rlo local PROG | PC9 / rhi local PROG | Native seats | Clock / reset |
|---|---|---|---|---|---|
|0|0 / dvs_W5|7, original body command edge513|8, edge554|0..127|n_clk_r135 / n_rst_field__t1774|
|1|2 / dvs_W3|7, edge514|8, edge555|128..255|n_clk_r125 / n_rst_field__t4171|
|2|4 / dvs_W1|7, edge515|8, edge556|256..383|n_clk_r119 / n_rst_field__t4902|
|3|6 / dvs_E0|7, edge516|8, edge557|384..511|n_clk_r95 / n_rst_field__t7291|

These edges are unchanged historical command-record values, **not newly qualified launch/write/arrival dates**. For each head h and half j, source address is `(2<<22) | (128*h+64*j+8*beat+lane)`, beat0..7/lane0..7. The expected mask is FF for each complete64-element half. `q_seats_contract.json` enumerates all512 addresses and their PC, local PROG, head, beat and lane. It deliberately leaves actual write edge/token/epoch NULL. Actual masks/data still require observing accepted SU writes; arithmetic enumeration does not prove receipt.

The remaining receiver IDs8/10 produce K/V at dvs_E2/E4, not Q. `q_origin_routes.json` checks every actual source net and receiving port in the four routes:

- W5 own Q → n_dvw_dd_wo.
- W3 own Q → W4 → W5 → n_dvw_dd_wo.
- W1 own Q → W2 → W3 → W4 → W5 → n_dvw_dd_wo.
- E0 own Q → n_dv_x0_dd_dd → actual rly_dv_x0_dd_dd_0 → W0 → W1 → W2 → W3 → W4 → W5 → n_dvw_dd_wo. That FIRST landing uses ck_s=n_clk_r95, ck=n_clk_r96, en/rs=n_rst_field__t7358.

Each joins the same26-station native lane, whose adjacent nets and final native59.dd_i are also asserted. `actual_dd_relay_lines.txt` retains all27 original relay constructors. The Q path through W5 includes pass-through arbitration in the intermediate slices. `p_dd` has priority over own DD; simultaneous pass/own and Q/KV overlap latch faults. Do not observe only W5's own SU as if it owned all512 words. QK arithmetic in the vector bench is useful mechanism evidence; its fixture preloads and tied clocks do not establish this installed source path. The NH8 XT1 fixture is a different mechanism and supplies neither these four Q publications nor this source calendar.

## Actual transport, context and source selectors

GEN0 SHA7b1bdfc5… is retained by77dc. Its actual W5 `dd_wo=n_dvw_dd_wo` traverses26 original stations and reaches legacy `qfd_native59_dv_service.dd_i=n_dvw_dd_wo__r26`. Native59 is clock n_clk_r54 / reset n_rst_seq__t80. The legacy constructor is not safe3c `_r1` and its Q bank must not be replaced with safe3c's SRAM/prefetch pipeline during this audit. The 26 instances are not a certified26-edge delay.

Native kind0 DD contains valid[547], kind[546:545], mask[544:537], eight24-bit addresses, eight32-bit data, and89 zero low bits. Q full addresses are stripped to22 bits in the slice before transmission; legacy native59 then requires addresses below512 and zero high bits. The DD word has **no explicit token/user/epoch field**. Identity is the existing begin_slot/qctx/qseen context, request/lock and reserved slot sequence; a source trace must prove that relation. No implicit token identity is added here. All512 writes must arrive exactly once before lock, and the request/QSLOT relation must reserve32 ordered16-seat export beats with the original identity. Readiness cannot move a slot.

Frozen GEN0 `tt_ctlm` is actual qfd_tt_ctlm_dv; both its exact frozen source and selected7e515 source omit CALENDAR_ROM/TABLE_ROM/table_load bindings. Its hard-head programme/fixed issue→relocation/IB→HR path supplies ME commands, while CALD supplies separate SU local PROG commands. Default legacy source does not select CALR. Even selected7e515 LPF `u_cal` leaves CALENDAR_ROM/TABLE_ROM at their default0. The77dc private constructor patch is a proposal, not applied source. Therefore putting the exact 25 ISA words in PW does not install the 406/1009 CALR path or the local Q PROG words.

The body decode contains no LOCAL3 TLOAD or LOCAL4 table-load command. The selected1009-entry descriptor adds36 separate preload ranges with LOCAL4. Selected cal_mu's LOCAL4 only emits `table_load/table_stage/table_user`; an actual table store/loader, its payload identity and its constructor connection are still required. Original LPF has no connection to these outputs. In CALENDAR_ROM mode LOCAL3 is explicitly rejected, so the old SRAM-TLOAD mechanism cannot silently fill the hole. The old composition's 72 PROG,188 BTAB,528 CROM blocks and13,942-PW capacity failure are historical diagnostics; the later table-ROM mechanism must be bound and observed, not dismissed using the earlier capacity result. Per-token RoPE CROM row ownership and its fixed publication remain separate.

## Provenance and exact unresolved input

The preserved old `body.json` source programme hash is fd2668d9… and phase hash all zero; the selected cap1 descriptor source corrects programme to cc5bc8fc… and metadata to a3ee4a0e…. The body406 command sequence exactly equals its preserved composition sequence, and the selected CALR payload reconstruction in cfe2d7e85 already checks that same decode range against both published ROM hashes. This packet preserves both provenance records. It does not claim fd2668 is merely serialization or invent the missing source bytes. The body receipt names dv_layer.py SHAde3cef…; that file is absent at selected7e515. Its emitted command/composition records remain available, but a complete reproducible producer manifest is not established merely by the matching vector lowerer.

Frozen events787345b9… and selected eventsb8e8121a… differ at exactly four class3 KV slots. Neither contains actual L/E. The Q address/command extraction reads the unchanged selected ISA, vector lowerer and recorded406 command body and is independent of those four dates. That limited independence does not qualify the Q→request→QSLOT timing or allow L_compiled to be renamed L.

The exact missing source input is one coherent installed manifest binding actual CTLM/hard-head PW and CALR descriptor/ROMs; all local PROG/BTAB/CROM payloads and original table-load source; genuine INIT/prior-stage VM and global RMSNorm scalar residency; QKV ME/XPF/head/tile-result writes; the original per-token RoPE row; and source clock/reset/first-accepted context. The composition explicitly leaves tile_first40 and head x-consumer delivery unresolved. Four original ME mismatches remain PC11 543vs672, PC12 2232vs2459, PC16 3883vs3625, PC20 4567vs4447. No dates, GO16, warm18, done-based runtime waiter or new programme is introduced.

## Minimum passive trace inventory, no build grant

The Q publication segment needs the four actual Q receiver SU/VM/CROM mechanisms, all original intervening DD pass-through stages from E0 to W5, the26-station W5 DD lane and full512-seat legacy native59 capture/export/context. The upstream segment additionally needs the actual global RMSNorm contributors/scalar chain and genuine QKV source/result landing. Four independent Q arithmetic coupons or one NH8 head cannot substitute for those dependencies. A complete minimum connected source inventory and memory budget remain NULL until the installed payload and upstream producer source are supplied; this is not permission to elaborate seven slices, twelve whole slices or a whole array.

Passive hooks are actual accepted CALR command and local pidx; table-load request/output and each PROG/CROM SRAM write; PC/operator/actual fixed issue, IB and original HR; source SI acceptance and actual vm_we/address/data; QKV/STN residency; per-token RoPE write; every actual Q DD mask/address/data and pass/own collision; all relevant local clock edges/reset epochs; native begin/request/qseen/lock; QSLOT beat/transaction and returned result/commit/visibility/complete. Observers may not supply missing payload, shift an event, wait for ready or replace actual clock/reset origins. The full graph remains UNRESOLVED and exits2.
