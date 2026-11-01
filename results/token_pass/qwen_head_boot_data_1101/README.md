# Genuine HEAD boot-data assets, 2026-11-01

**Selected-programme correction:** actual59P HEAD37 issues zero native SU commands. The optional native-SU contract below describes a possible future source bridge, not a requirement inferred from the selected programme. The selected ROOT/STN path and actual normalized-input producer must be reconciled before selecting any implementation change. See the final section for the physical image decode.

`tools/qwen_layerbench/head_boot_data.py` recovers the actual released row scales from the previously generated TP8/G3072 HEAD scale bank, preserving every BF16 bit. It uses `dv_lower_mat.btab_layout` with the selected native s8 ownership to emit 298 kind-2 native table records per rank. These occupy the shared HEAD window [72,272) on slices 1/3/5/6/8/10. Rows beyond vocabulary are padded with zero exactly as the authoritative `btab_stream` does; matrix-engine bank padding (1.0) is excluded.

All eight actual recovered ranks were emitted and checked against `dv_lower_mat.btab_stream`. Independent native field decoding agrees for every record; changed scale payloads are rejected. `gate.json` records this DATA ONLY pass. Runtime data are on intel2 at `/srv/opentallas-scratch2/claude/codex-qwen-images-1101/head_boot_data1131/rankN/{head_btab.json,head_final_norm_crom.hex,head_boot_data.json}`. The checkpoint was already recovered and checked against the released lock by the preceding recovery lane; this tool does not repeat a 16 GB checkpoint hash pass.

The small logical norm image contains all 4,096 genuine `model.norm.weight` values extracted from the pinned BF16 safetensor, widened exactly to FP32 in the low half of 64-bit pairs. This matches the existing `qwen_o4_fulltoken_binding_w12.write_final_norm` producer. It has NOT been assigned native per-user CROM row addresses and is NOT a native CROM delivery receipt.

## Missing production source/transport

- `tools/qwen_layerbench/programme_store.py` requires exactly 36 transformer stages and reserves only 18 BTAB / 64 CROM / six PROG records per user per stage. Its compact relocation deliberately protects the shared HEAD window; that is not a producer for HEAD contents.
- `rtl/qwen_dv/qfd_dv_table_rom_loader.sv` rejects stage >36 and therefore cannot install HEAD from a putative 37th stage. No RTL change was made here.
- `tools/qwen_layerbench/dv_lower_vec.py` lowers transformer operations and Q/K normalization. It has no native HEAD final-RMSNorm SU image/address allocation. `ctlm_image.lm_head_programme` and `qwen_o4_fulltoken_binding_w12` instead emit the older ME ISA's three normalization operations plus head matvec. Those instruction words cannot be copied into native SU PROG.
- Required next investigation: connect the selected ROOT/STN HEAD37 path to the actual normalized-input producer and the genuine shared BTAB installation. No separate HEAD SSQ/apply kernel is inferred: final transformer residual-add instructions already chase SSQ to the 32 PSUM tags. Whether those PSUMs reach HEAD ROOT under the selected global timing, and where final gain is applied, remain unresolved. Any new arithmetic path requires explicit source authority and its own gate.

Every asset manifest remains `PARTIAL`, `native_head_programme=NOT_LOWERED`, `native_norm_crom_addresses=NOT_ASSIGNED`, `boot_transport=NOT_INSTALLED`. No default activation, filler instructions, stage37-loader alias, die-token pass or current825 BOOT installation is claimed. Source-only tooling adds zero hardware cycles.

## Optional native HEAD source bridge input schema

`head_native_contract.py --template --out INPUT.json` exports the missing input contract. No HEAD address, reservation, issue date, or RSTD date has a default. `--contract INPUT.json --out REPORT.json` fails with `BLOCKED` until every required source authority, user-bank allocation, liveness inventory, and per-slice producer/consumer date is supplied. It emits no arithmetic instruction words and cannot turn a supplied source label into an execution gate. A complete input earns only `BRIDGE_INPUT_VALIDATED`; arithmetic and BOOT installation remain separate gates. The committed empty template fails on 228 missing/invalid fields, rather than installing a default programme.

Actual existing transformer reference allocation (`dv_lower_vec.vm_map_vec/crom_map`, not a HEAD reservation):

| Namespace | Local element or instruction allocation |
|---|---|
| VM X | 0..383 |
| VM SSX / RX | 384 / 400 |
| VM T / QKV / SS / RS / QN / GU / ATT | 416 / 800 / 928 / 944 / 960 / 1088 / 1344 |
| CROM PS1 / PS2 | 0..383 / 384..767 |
| CROM QG / KG / ROPE | 768 / 896 / 1024 |
| PROG | pidx0..11 already assigned transformer SSQ/residual/xstream/qk/RoPE/SiLU/attention ops |
| Four-user private strides | VM4096 elements, CROM2048 elements, PROG128 instructions |

Owned residual blocks are `[s,s+12,s+24]` for slices0..7 and `[s,s+12]` for slices8..11, totaling exactly32 blocks×128 elements. No existing HEAD gain range or HEAD SSQ/apply pidx reservation was found. A future lowerer may reuse the *arithmetic form* of `dv_lower_vec.words()['qn']` (`ma=MA_AB,csrc=1,mc=1`, separately rounded `(x*r)*gain`), but must use actual HEAD operands/output mode and pass a native-SU gate before READY. Transformer norm-folded `xs` words omit finalnorm gain and are not HEAD lowering.

Scalar producer trace is unchanged between source8250069cc and this investigation: `qfd_dv_s8_flat.u_sc` is `qfd_dv_s5_sc2_leaf`; the functional scalar implementation `qfd_dv_s5_sc2.sv` gathers32 tagged PSUMs, computes fused `rsqrt(total*2^-k+eps)`, broadcasts K_RB, and sets `w1_addr=rx` for both root `rr_v` and broadcast `tap_rb`. The registered `sc_w1_*` path passes the slice control to `w1_*`, then `qfd_dv_s8_suvm_rp1.u_vm8q` writes it into VM. Therefore raw scalar completion is not yet VM operand visibility. Required dates distinguish actual ROOT configuration effective edge, SSQ issue, each PSUM root arrival, RSTD single-word write, RSTD VM-visible edge, apply issue and first operand read. Every date must use one explicitly supplied global edge reference; this bridge does not derive physical latencies from the older slice2 calibration.

The bridge rejects wrong-user operands/pidx, overlapping X/RX, overwrites of supplied live ranges, missing gain/PROG publications, repeated ROOT scalar arrival slots, and RSTD reads preceding visibility. Four small source-validation tests pass using explicitly synthetic contracts; they are not numerical or production-calendar evidence. No native arithmetic gate was run. The selected HEAD37 calendar does not select a native-SU instruction image; this optional schema does not establish that such an image is required.

## Selected actual59P HEAD37 reconciliation

`head37_calendar_trace.json` decodes the actual selected physical calendar masks and DW descriptor. HEAD37 starts at entry476 with count320: **12 ROOT, 298 STN, 9 AMAX, 1 XC; zero native SU, STREAM or PORTS commands**. The BOOT descriptor selects only entry796 (SETID0). The physical mask hashes exactly match the parent calendar/prog join receipt. **The selected mode2 STN receiver destinations are legacy0/2/4/6/8/10, while current native s8 and the emitted genuine BTAB payload use1/3/5/6/8/10. This is an actual calendar-to-current-BTAB ownership mismatch; do not claim these assets are installed into a matching selected calendar. Current s8 calendar reconciliation is required, without regenerating weights.**

Root dst0 at entry488 has nb32, ss384, fuse1, rx400, k12, eps0x358637bd, amnb6; the other11 roots have fuse0. The root configuration carries norm parameters but does not itself create PSUM operands or apply gains. Importantly, transformer residual-add lowering already performs red=1/redsq=1 and can supply the 32 final residual PSUMs. Determining whether those actual PSUM arrivals land after the selected HEAD ROOT configuration requires the global producer/consumer timing; zero HEAD SU entries does not prove that a separate SSQ kernel is needed.

The selected finishing STN commands use mode2, sdst0, amax1 and sbase72..264; mode3 senders use sbase0/amax0. All STN commands select wsrc0; actual encoded kc is1, without assuming the alternate running-K profile's kc8. Native station RTL (`qfd_dv_redstn2_regional.sv` multiplier) computes each result times its BF16 BTAB row scale, or unity for wsrc1. It has no CROM final-gain or RX/RSTD input. ROOT fields do not add an implicit final-gain multiply to this station calculation.

Source/gold evidence: `qwen_o4_head_rom_w12.emit` calls `hdc_qwen_int8_image_w12.shipped_vocab_rows`, which reads and quantizes **lm_head.weight directly**, without folding model.norm.weight. `qwen_tp8_token_oracle.py` explicitly computes `H=(X*RSTD)*model.norm.weight` before matvec against that raw HEAD image and then applies its BF16 row scales. The recovered norm contains4096 values/220 distinct values/no exact1.0 values (first two FP32 bits0x40080000/0x3ff60000). Thus the genuine BTAB payload is a row-scale asset, not an implicit representation of4096 feature-wise final gains. Folding those gains into the matrix or moving input normalization after reduction is not justified by this selected source/gold and would change the arithmetic contract.

**Result:** genuine shared BTAB installation remains open; actual final-gain/normalized-H input delivery remains unidentified in the selected production path. Current evidence does not establish whether CROM gains need installing or an existing input producer provides H. Do not call the optional SU contract a required production kernel, fabricate a default gain path, or claim ROOT/STN alone qualifies final normalization. No arithmetic/RTL/calendar change was made by this reconciliation.
