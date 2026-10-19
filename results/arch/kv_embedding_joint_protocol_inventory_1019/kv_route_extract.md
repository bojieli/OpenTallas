# Exact selected KV embedding route extraction

Read-only source extraction. No RTL edit, compile, physical qualification, or source adoption.

Source roots: `C=/home/ubuntu/artifacts/kv-embedding-controller-contract-1019/source/5f2`; `S=/home/ubuntu/artifacts/kv-embedding-seed-ownership-model-1019/source`. Below `E` means `C/rtl/qwen_sys/static_embedding_20261014`, `T` means `C/rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv`. References are exact line numbers in these frozen copies.

## Actual start and distribution cuts

* `S/selected_qkd_kvs_emb.sv:34-35`: the same incoming service bit 24 drives join calendar start and row-transmitter fill_begin directly. Fill token is bits 109:92, epoch 89:74. This has no HC or native allocation input. Token/epoch px outputs are direct service fields at lines 38-39. Internal join fault, rowtx fault and row_ready wires (29,32-33) have no exported assignment/port.
* `T:788`: control tile fan root (`qkd_kv_es_fan_root2_b`) receives service bit24/token18/epoch16. This is a DIFFERENT instance pin from the direct join/fill pins. `T:1709-1710`: each hroot has a `qkd_kv_es_fan_stack_b` distribution and `qkd_kv_stack_relays` with HW784/FW334/GW144/RW299; PC output is 780 bits (1711), embedding return is 299 (1723). Exact root/stack implementation bodies are absent from this C packet.
* The complete selected die's `hsvc__f1__r3__pinfix1` relay instances are absent from these provided files. Therefore these sources alone cannot prove the added hsvc fork/pin-fix edge count, shared release authority, or exact root-versus-join start phase. Do not infer equal start arrival from identical field names. The earlier separate connected-trace evidence must supply those full-top nets/instances.
* `E/qkd_embedding_static_join4_cal.sv:32-35`: start captured into ss; configuration captured ca/cd/cw. Lines54-56 consume ss, start cnt/act, and register slot. The documented beat_slot is start-pin-capture+2+[off,off+len) (6-9), with eight offset/length entries (36-37); malformed/running boot and overlapping start fault (48-55). No retry/wait.
* `E/qkd_kv_pc_chain_station_b.sv:43-59`: actual 780-bit chain layout carries start bit719, token720:737, epoch738:753; start has resettable ss, while data has unreset c capture. rs_q is ONE plain sampled reset at47-48. Player tok/ep capture uses ss at133; act starts146-151, issue/return slot154-155. The writer/context/expected descriptor also has61-bit identity (26,76-99), but that identity is NOT carried in the embedding start/token/epoch lane or 298-bit return record.

## Topology and clocks/reset

* `C/tools/qwen_kv_die/kvjc3_pc_chain.py:4-8,19-25`: source compiler topology is four stacks WS/WN/ES/EN,32 PCs each, slot31 nearest root; four return trains, each one head+31 hops. This establishes the selected compiler contract, not an independently counted elaborated full-die inventory.
* `C/tools/qwen_kv_die/kv_die.py:2347-2375`: 32 per-PC DFI pairs per stack, PHY abstract separate from controllers, per-leaf core/HBM clock entries, per-stack PLL/reset distribution; CDC core reset redirected to the core reset tree. Physical forward-clock regional phases and matched reset release are not proven by this generator excerpt.
* `T:1279-1280,1624-1625`: normal PC uses return_hop; head PC uses return_head. Both return stations use core ck/rst_n. The wrapper maps all five PC HBM clocks to local hck, all HBM reset to hrst_n; return HBM hck/core ck are explicit; embedding merge and chain use core ck/rsi. A shared RTL wire name is not a physical clock/phase receipt.
* `E/qkd_static_kv_pc_path_fan_nc_b.sv:107-124`: embedding merge runs ck/rsi; underlying path receives distinct pll_hbm/port/ecc/cdc/obs and hrst. Merge default RETIME=1 (`E/qkd_static_kv_pc_es_merge_b.sv:29,78`), reset pin rs_q one sampled stage65-69. Selected controller deadline contract belongs to M2; no fixed physical HBM bound follows from compiler nominal ctrl_lat.

## Actual capture widths, state and ownership limits

* `E/qkd_embedding_static_return_head.sv:6-7,17-32`: record298={epoch16,scale1,half1,word6,token18,data256}; output299 adds valid. record_q298 and retained298 plus output payload298 are unreset; cs_q/cv_q/ts_q,output valid,occupied,fault reset on rst_n. Capture and transfer are two sampled cuts; retained is written only from the previously captured record when cs_q&&cv_q. Missing/occupied/simultaneous capture-transfer fault; no queue.
* `E/qkd_embedding_static_return_hop.sv:13-30`: adds up_q299 capture; payloads unreset, valid reset. Output selects retained on ts_q, else captured upstream; collision/missing/occupied/simultaneous captures fault. Declared head=900 state bits; hop=1199 (source declaration count, not mapped FF or SRAM result). Under the compiler's 4 heads+124 hops contract, return-station subtotal=152276 declared state bits, excluding controller/merge/join/relays and any root pin copies. Do not treat this subtotal as a new implementation or complete cost.
* `E/qkd_embedding_static_join4.sv:20-40`: four299-bit pin captures, slot_q, combinational one-hot298-bit select, then inner join. Valid and slot reset, payload does not. Multiple valid trains faults. `E/qkd_embedding_static_join.sv:16-39`: retained low_data256/token18/word6/epoch16 and low_valid, then registered512-bit word+token18/index6/scale1/epoch16. Half-pair comparison checks token/word/epoch only, not native TAG/gen. Scale packs token-selected16 bits from returned beat. There is no row-owner accept input.
* `E/qkd_embedding_row_tx.sv:48-64,70-99`: ONE64x512 row SRAM plus filled64/armed/scale_filled/tok18/ep16/scale16/n7, output548/v/fault and rst_q. Actual row identity only token/epoch. fill_begin always captures tok/ep and arms/clears occupancy, even when overlap raises sticky fault. Writes are gated by word_v/code/armed/n0, but foreign token/epoch only raises fault; it does not independently suppress that write. Fault is diagnostic here; no local admission freeze. Header requires resident64words+scale; final slot de-arms. Header through 65th slot lifetime must be associated externally with one accepted owner; none is present in this ABI. Reset is ONE sampled rst_q at77-81; no assumed +2 input/output boundary from e1.
* Full native TAG59+generation2 carried through accepted PREP_ROW and return/row/header lifetime is a NEW protocol proposal. Existing61-bit writer expected/context identity does not establish embedding ownership. No new owner bit counts or calendar dates are implied by this extraction.

## All-driver fanout lower bounds (source bit-load analysis)

These are logical bit-select/enable consumers before mapping, not mapped endpoint count or proof of native closure. They show structural work is required and cannot be waived by clock-only audits. A synthesis may refactor logic; closure must count BUF/INV-transparent comb/input/tie/reset/macro drivers too.

| Actual driver/control | Lower-bound source consumers | Exact reference |
|---|---:|---|
| join4 u0/u1/u2/u3 valid, each |298 data gate bits per train, plus hot/multi logic | join4:27-30 |
| return head/hop ts_q |298 output payload mux bits, plus valid/occupancy/fault | head:23,29-32; hop:20,26-30 |
| return capture enable cs_q&&cv_q |298 retained bit enables | head:22; hop:19 |
| row_tx fill_begin |34 tok/epoch capture enables, plus armed/filled/scale/n/fault control | row_tx:70,85,96-98 |
| row_tx emb_tx_slot |548 output capture enables plus read/control/valid | row_tx:58,67-69,83,90-94 |
| row_tx reset rst_q |75 resettable state bits (v,fault,armed,filled64,scale_filled,n7) | row_tx:77-81 |
| chain rs_q |at least128 calendar bits plus cnt16,last16,act,fault | chain_station_b:128-139 |

No whole-tree all-driver census, kept-copy fixed point, individual <=405um route reach, reset authority/first-use proof, or PG/contact/timing qualification is available here. Missing root/stack implementations, full selected relay netlist and programme/calibration/PHY receipt remain explicit dependencies. The static compiler assumes r is present at BOTH root and join inputs (`kvjc3_pc_chain.py:7-8`); its ROOT2/HOP1/PLAYER3/MERGE2/TRAIN_HOP2 constants (21-25) and exact ctrl_lat argument are compiler model assumptions, not installed E/calendar or measured phase closure.
