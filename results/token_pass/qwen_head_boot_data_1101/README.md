# Genuine HEAD boot-data assets, 2026-11-01

`tools/qwen_layerbench/head_boot_data.py` recovers the actual released row scales from the previously generated TP8/G3072 HEAD scale bank, preserving every BF16 bit. It uses `dv_lower_mat.btab_layout` with the selected native s8 ownership to emit 298 kind-2 native table records per rank. These occupy the shared HEAD window [72,272) on slices 1/3/5/6/8/10. Rows beyond vocabulary are padded with zero exactly as the authoritative `btab_stream` does; matrix-engine bank padding (1.0) is excluded.

All eight actual recovered ranks were emitted and checked against `dv_lower_mat.btab_stream`. Independent native field decoding agrees for every record; changed scale payloads are rejected. `gate.json` records this DATA ONLY pass. Runtime data are on intel2 at `/srv/opentallas-scratch2/claude/codex-qwen-images-1101/head_boot_data1131/rankN/{head_btab.json,head_final_norm_crom.hex,head_boot_data.json}`. The checkpoint was already recovered and checked against the released lock by the preceding recovery lane; this tool does not repeat a 16 GB checkpoint hash pass.

The small logical norm image contains all 4,096 genuine `model.norm.weight` values extracted from the pinned BF16 safetensor, widened exactly to FP32 in the low half of 64-bit pairs. This matches the existing `qwen_o4_fulltoken_binding_w12.write_final_norm` producer. It has NOT been assigned native per-user CROM row addresses and is NOT a native CROM delivery receipt.

## Missing production source/transport

- `tools/qwen_layerbench/programme_store.py` requires exactly 36 transformer stages and reserves only 18 BTAB / 64 CROM / six PROG records per user per stage. Its compact relocation deliberately protects the shared HEAD window; that is not a producer for HEAD contents.
- `rtl/qwen_dv/qfd_dv_table_rom_loader.sv` rejects stage >36 and therefore cannot install HEAD from a putative 37th stage. No RTL change was made here.
- `tools/qwen_layerbench/dv_lower_vec.py` lowers transformer operations and Q/K normalization. It has no native HEAD final-RMSNorm SU image/address allocation. `ctlm_image.lm_head_programme` and `qwen_o4_fulltoken_binding_w12` instead emit the older ME ISA's three normalization operations plus head matvec. Those instruction words cannot be copied into native SU PROG.
- Required next work: author the native HEAD SSQ/apply instruction image using actual per-slice residual ownership and final-norm constants, assign its CROM and PROG addresses without overwriting other users, and provide a genuine BOOT transport that installs these plus the shared BTAB records. The activation calendar remains separate and is not emitted by this tool.

Every asset manifest remains `PARTIAL`, `native_head_programme=NOT_LOWERED`, `native_norm_crom_addresses=NOT_ASSIGNED`, `boot_transport=NOT_INSTALLED`. No default activation, filler instructions, stage37-loader alias, die-token pass or current825 BOOT installation is claimed. Source-only tooling adds zero hardware cycles.
