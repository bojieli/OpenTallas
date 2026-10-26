# QC calendar image ROM

One generated `ot_rom_64x64_m2` shape stores both live calendar images. Each
word has TX entry i in bits[31:0] and RX entry i in bits[63:32]. The current
D2D_CAL_C and actual OVL_C images each have32entries, so rows32..63 are zero;
the helper also accepts64-entry images without changing the macro.

Interface: synchronous read on `clk` when `ce_in=1`, address`addr_in[5:0]`,
output`rd_out[63:0]`, metadata parameters`VIAMAP`and`INSTANCE`. The physical
blackbox uses the shared classic-Yosys-compatible untyped metadata fix739ddb8364.
Views and RTL design do not depend on content; only the per-instance via map does.

Regenerate the content-independent aligned shape:

```
python3 tools/mem_compiler/qc_dcal_profile.py --compile-shape --out physical/asap7_memory_macros_v2
```

Personalise the actual OVL image:

```
python3 tools/mem_compiler/qc_dcal_profile.py --sv --prefix OVL_C rtl/qwen_sys/d2d_static_20261015/ovl_release_rope/ovl_release_img.svh --out physical/die_plan/qwen_compute/dcal_rom/profiles/ovl_release_rope
```

The default prefix is D2D_CAL_C. JSON inputs use TX and RX arrays of32or64unsigned32-bitwords.
Each profile includes its64-word logical image, a via map, and a rom_gen-compatible
personalisation manifest. All three production profiles passed64-word read-back
and rejected a one-via mutant. The actual QC rope chain uses OVL_C rather than
the D2D_CAL_C tables; both are kept explicitly named to prevent accidental substitution.

The existing analytical macro compiler gives12.312x9.192um=113.171904um2,
TTclk-to-Q250.330ps and FFclk-to-Q201.209ps. The modeled macro read fits one
833pscycle; downstream capture wire/setup and physical closure remain separate.
The v2 abstract passed track alignment in R0/MX/MY/R180 with M4pins.
The candidate controller must prefetch the first row before its first init write;
boot-edge equivalence and opt-in adoption are owned by the integration lane.
