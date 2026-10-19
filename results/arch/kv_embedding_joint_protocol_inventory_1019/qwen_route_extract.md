# Qwen E route and owner inventory: source facts and private MODEL only

Inputs are the frozen 0d4c9808f source copies and actual_gen0_connections.txt / actual_gen0_bindings.json under /home/ubuntu/artifacts/qw-calendar-producer-contracts-1019. No RTL changes, builds, production dates, native qualification, or calendar installation are asserted.

## Existing actual and expected E routes

SYSFACE runs n_clk_d2d, port reset n_rst_d2d__fo2__r4__t24. Actual decode resets from internal rr_q[7] (rst_emb); expected/FILL output register block resets rst_out=rr_q[5]. Provider runs n_clk_r54, port reset n_rst_seq__t25. Its synchronizer rr_s[1:0] and two kept rr_q regions release face/store on the third local rising edge; this is initialization, not a production date. Source-clock to destination-clock phase, equal capture ages, and timing of the distinct reset leaves are unproved here.

| Bundle | Source fields and total width | Actual generated stations | Source enable reset / destination reset |
|---|---|---|---|
| Actual word | v1,data512,token18,index6,scale1,epoch16 = 554 | six separate landh0 stations, each one station | v/data/token/index en d2d fo2 r4 t16; scale/epoch en t14. v/data/token rs seq t25; index/scale/epoch rs seq t29 |
| Expected word | slot1,token18,word6,scale1,epoch16 = 42 | five separate landh0 stations, each one station | all en d2d fo2 r4 t14, rs seq t29 |
| FILL | begin1,token18,epoch16 = 35 | three separate landh0 stations, each one station | begin en d2d fo2 r4 t29,rs seq t31; token/epoch en t12,rs seq t20 |
| Core epoch | epoch16 | rlyh0 + landh, two stations | start en d2d fo2 r4 t27, end rs seq t57 |

All first three groups use ck_s=n_clk_d2d and ck=n_clk_r54. These are actual instance counts, not a claim of one receiver cycle per station or exact FF storage cost. The provided finite source inventory does not include their landh0/rlyh implementation definitions. Internal ring slots, E/K capture state, forwarded phases and native arcs must be priced from those definitions before assigning storage or cycle totals.

The upstream actual emb_rx_v route has four stations (three forwarded hops plus landing), while emb_rx_slot has three. Both originate n_clk_d2d; final resets differ (v t24, slot t44). RX payload arrives SYSFACE on n_lnk_rx_payload__fo1__r3. The v/slot/payload names do not establish common logical sampling age.

## Existing actual owner versus expected owner

SYSFACE lines 491-520 retain only row_tok18 + row_ep16 + row_v. Header actual token is payload[547:530]; actual epoch is payload[47:32]. Code words carry token and word index but inherit row_ep. Source checks valid equals compiled emb_rx_slot, strict reserved bits, header syntax, row presence, and code token equals retained row token. emb_fill_begin clears row_v. Actual outputs are registered one SYSFACE edge; payload data is an unreset always-capture register, while valid/identity are reset.

Expected slot/index/scale are compiled E-calendar events. Expected token is tok and epoch is host_epoch. tok is assigned from host_tag[36:19] at a context slot, or from seq_dc[49:32] on ev_res; position advances separately. There is NO independent full TAG59+gen2 accepted-allocation owner route into this expected interface. Merely adding 27 wires to the current expected token+epoch would not create that provenance. Source-root and producer acceptance/capture binding remain explicit missing work.

preload_face compares actual token/index/scale/epoch against expected values on expected_slot. It registers ACTUAL identity/data and FILL one edge. It does NOT retain expected_token/expected_epoch; those are combinational comparator operands. The previous prose phrase “captures complete actual and expected identity bundles” must not be used as a state census.

core_store resident_token18/resident_epoch16 are assigned on FILL, filled64 and scale_filled clear there. All64 code words and scale must be present before core_start/read, and identity must match. Its true 64x512 SRAM writes preload_word, all512 mask bits. Scale is a distinct16-bit register. Fill/preload/read overlap faults; none of these checks introduces a wait.

## Precise paired private header proposal (not implemented)

Define full owner O={TAG59,gen2}, with TAG={epoch16,stage6,input_token18,position13,segment6}. Preserve existing input token payload[547:530] and epoch payload[47:32]. Use ONLY formerly zero header bits:

| Header bits | Proposed field |
|---|---|
| [74:69] | stage6 |
| [68:56] | position13 |
| [55:50] | segment6 |
| [49:48] | gen2 |

These are exactly27 added identity bits. Preserve word[529:524]=0 for header, [523:512]=0, [511:75]=0, and [31:16]=0; [15:0] remains scale. Code payload format is unchanged; subsequent words inherit the retained full owner, so stale code-word/overlap protection still requires a proven single-row lifetime and token ambiguity analysis, not just this header.

Legacy decoder r_hdr requires payload[511:48]==0. A nonzero proposed owner therefore FAILS legacy syntax. Producer and decoder must be an explicitly paired opt-in private protocol; never call it legacy-compatible or weaken all reserved-bit checks. Existing 548-bit flit width and 65-record count do not grow, but metadata logic, retained state, fanout and route costs do.

## Capture-bit lower bounds, not final physical totals

Full owner replaces existing token18+epoch16 (34 bits) with61, so delta27 per identity register/copy. For just the old actual-word and expected-word source-output/landing boundaries:

- Actual SYSFACE output needs +27 registered bits; its single landing output needs >=27 added stored payload bits. Minimum +54, excluding landing internal slots/captures.
- Expected SYSFACE output needs +27 registered bits; its single landing output needs >=27. Minimum +54, excluding the NEW unbound accepted-allocation producer/route and landing internals.
- Together these two route boundary floors are +108 bits. They are not a complete-source cost.
- Actual row-owner latch +27, preload_face actual owner register +27, resident-store owner +27 are three further named captures (+81). Actual route plus those named captures is >=135 bits; actual+expected subtotal is >=189 before other paths.
- FILL source output +27, its landing >=27, and face FILL register +27 add >=81. Do not count resident_store twice. Core-start owner, EMB-command owner, last-read retention, sender, allocation source, reset/copy forests, relay internals and strict-protocol machinery are NOT in these floors.

No expected owner register is added inside preload_face by necessity: comparison may use the independently retained expected owner directly. If one is added for timing or lifetime it costs another27 relative to old token+epoch, plus its valid/reset/control. A fresh full61 owner capture with no preexisting34-bit capture costs61, not27; a fresh valid owner capture generally needs62. All copies and instances must be counted individually. No zero-cost old token path is assumed reusable until source lifetime matches.

## Actual 65-read and last-scale lifetime

native59 port ck=n_clk_r54/reset=n_rst_seq__t80 captures native_cmd into p_cmd. EMB is !p_cmd[0] && p_cmd[379:376]==E; token occupies[375:358], all[357:1] must remain zero. The command carries NO epoch/stage/position/segment/generation owner. emb_go captures emb_tok only when idle. emb_act then issues64 code reads (emb_k0..63) and one scale read (64); emb_act clears on scale ISSUE, while e1/e2/e3 and k1/k2/k3 still track returns. No source-owned release event or in-use owner scoreboard is exposed by this sequence. A later new emb_go can occur before old return drain; the existing emb_go&&emb_act fault covers active issue overlap only.

Actual provider read routing is asymmetric: code_re1 station, code_addr24 one station; scale_re1 two stations, scale_addr18 one station. All endpoints use n_clk_r54, but reset leaves differ: code_re seq t57, code_addr/scale_addr t43, scale_re source t61/end t43. Provider code_q512 returns to native on __r3 (three named suffix stages); scale_q16 on __r2 (two). The finite connections file does not list those return instances, so suffixes alone are not a certified station/cycle census. Native captures answers in p_ecq/p_esq before group1 dr_o. Its local e1/e2/e3 comments describe an ideal local sequence, not proof of this generated skewed physical graph.

core_store does not retain a read-transaction owner, count final consumption, or wait for native return/release. It permits a later FILL absent simultaneous read/preload/core_start; that alone cannot prove no late old return or overwrite hazard. A private proposal must bind expected full owner from allocation, full owner to core_start and EMB command, actual final scale capture and all outstanding returns, and next FILL permission using real accepted events. No synthetic release1850 fixture or inferred “issue done means consumed” is justified.

Production E dates, installed E programme, first-use bootstrap, full-owner producer routing, relay definitions, exact reset epochs/phase, physical arcs and total cost remain NULL/HOLD.
