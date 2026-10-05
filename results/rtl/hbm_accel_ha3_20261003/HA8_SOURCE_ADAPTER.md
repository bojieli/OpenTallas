# HA3 native-engine source adapter for HA8

Use `tools.hbm_accel_epilogue_ha8.select_native_engine(installer_root=ACTUAL_ROOT, enable_ha3_clock_lookahead=True)` in Euclid/Claude's **native tensor-core instance emitter**. It returns:

```python
{
    'module': 'ot_hbm_accel_sm_q',
    'parameters': {'ENABLE_HA3': 1},
    'sources': [...],
    'source_sha256': {...},
    'adopted': False,
    'numerical_fusion': False,
}
```

Keep the original `ot_gpu_sm_q` instance port connections, sizing parameters, enclosing clock, physical provider, x/scale stores, result capture, issuer and lifecycle bindings. Selecting this module does not replace the guarded RF/SIMD service. Without the explicit opt-in, the helper returns the original engine module and no new parameter.

`rtl/hbm_accel/epilogue/ot_hbm_accel_sm_q.sv` is an additive sibling of actual engine source SHA256 `8e0aa477664f385a8536b1610c508fdd637bb020377adf744671c960d984b06f`. Exactly three substitutions derive it: module name/default-off `ENABLE_HA3` parameter, bulk-copy child+parameter, issue child+parameter. Reversing those substitutions reconstructs the entire original file byte for byte. No rounding, reduction, arithmetic pipeline, x-store, scale-store or output-retirement edit.

To obtain the actual enclosing installer source list, verified book pins, candidate dependency list and reused definitions:

```sh
python3 tools/hbm_accel_epilogue_ha8.py \
  --installer-root /actual/HA8/source/root \
  --enable-ha3-clock-lookahead \
  --out /new/path/forwarded.json
```

`forward_installer(...)` leaves the supplied sources/book unchanged. Its `candidate_sources` is a complete module-definition list for forwarding to the native emitter. It reuses six existing HA8 arithmetic/SRAM files only after byte equality with the genuine engine dependencies; differing shared definitions are refused. Historical duplicate file entries in the input list are preserved in `installer_sources`, and removed only from the candidate build list. The installer still must emit the genuine engine instance and its actual pins before that candidate can run in context.

Actual run of the adapter against `/home/ubuntu/OpenTallas`:

- **40 actual HA8 sourcebook pins matched**, including the current ranked top, guarded SM, issuer, STATE RPC and terminal cohorts.
- **55 candidate source files**, six shared definitions reused, no duplicate module definitions; original native dependencies retained.
- **6 focused source checks PASS** in `ha8_forwarded_sources_r3.test.log`. No whole-system lint, HDL build, model inference or P&R was launched.
- `ha8_forwarded_sources_r3.json` carries actual book/list hashes, the 40 installer pins and all 55 forwarded file hashes. Earlier r1/r2 inventory outputs and r2 missing-vline test failure are retained. r3 adds the real `ot_hdc_sfu.sv` definition of `ot_hdc_vline`; the two intentionally undefined invalid-CUTS traps are static-disabled under the unchanged LAT7/CUTS=-1 wrappers.

The **actual current installer does not contain a native `ot_gpu_sm_q` instance or its engine start/op_rows pin namespace**. Its guarded SM supplies RF/SIMD services. The adapter therefore records `native_engine_installed=false`, `measured_real_sm_cycles=null`, `physical_qualified=false`, `adopted=false`. The native emitter's source join is the next owner dependency; adding definitions to a file list cannot substitute for that connection.

The existing 72-case issue/bulk-copy protocol measurement remains the functional evidence, unchanged. No new real-SM, whole-token, clock, area, route, SS/FF or gain result is claimed. The fused non-finite/wide-overflow failures remain blockers for numerical fusion.
