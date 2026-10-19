# GEN2e source closure recovery

The global RTL index previously chose incompatible definitions of four private children by filename order:
`ot_hdc_fp32_mul_lat`, `ot_hdc_fsqrt`, `ot_hdc_v41x_ins`, and `ot_hdc_v41x_vec_lane`. A strict bind cannot qualify
that choice. `l14_scoped_rtl.py` gives the seven affected master families private child namespaces using explicit
source inventories from their synthesis records. The die-visible master, ports, parameters, instance names and
latency classes stay unchanged. Canonical and pinned RTL files remain byte-identical.

The generated copies record every input/output source hash and require an inverse identifier substitution to recover
every original source byte. This proves an identifier-only transformation; it does not qualify old timing. Apply the
layer to both the pre-relay contract and the final contract, after other source-changing layers. Regenerate SYNTH
views from the resulting sources. The bind and synthesis tools explicitly prefer the contract's scoped source rather
than silently selecting the original global top. Memory macro names remain external.

The source inventory is `scoped_source_manifest.json`; generated RTL is under
`rtl/hbm_accel/die_glue/scoped_d4g/`. The synthesis inventory's source paths determine each family, including physical
quantizer RTL; current source hashes, rather than old synthesis hashes, are recorded when copies are generated.
An old synthesis cannot be reused merely because its wrapper matches a previous wrapper: every implementation and
macro hash must match as well. The regression test covers a changed implementation behind an unchanged wrapper and
missing source inventory. Nine focused binder/reuse tests pass.

The fleet pre-relay probe fixes all four ambiguous children (zero remaining), but the newest main binder independently
finds 70,866 unread bits. That result is a FAIL. The unread-output audit must distinguish repeated checker/observation
ports and declared relay padding from missing functional connections before any per-instance spare-output record is
adopted. No blanket unused-output waiver or gate relaxation is part of this change. Complete bit ranges are now
included in diagnostics so a reviewed declaration can be exact and a new disconnected functional bit still fails.

GEN2e also reached placement with zero geometric placement errors and then crashed while formatting a diagnostic
label: a legacy layer had converted `exposed_inputs` to a list of keys. The label now retains unknown counts for that
malformed summary. It still says `NOT_A_DIE_RESULT`; this fix grants no correctness, timing, reset or placement waiver.
