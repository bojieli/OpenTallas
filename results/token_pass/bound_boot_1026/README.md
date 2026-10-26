# Bound native command records to HOST boot

`layer_prog/bound_boot.py` composes actual native entry/norm records with the current BoundDie control result, measured seqhost/BK timing and current direct-native CSR cadence. It emits concrete 515-bit HOST words and an unsealed prototype manifest. It never calls legacy `finish()` or invents store readiness, HLOAD/GAIN completion, KIT or END.

Inputs are the actual canonical top `1c11db22…` / source graph `003a165c…`: genuine L14 entry writes and the route lane's `routes2` norm retime. All 16 current per-bit routes pass. The 96-command retime fixes the known original NORMR spacing failure while preserving GO dates and the source span; GO/readiness remains unqualified.

Results:

- `norm/`: 96 real calendar rows, 96 templates, 385 actual HOST words (LEN + 288 PW parts + 96 templates). Every emitted row/payload decodes exactly to the inputs; a payload bit mutant is caught. Local CSR reservation is 1,925 edges at the measured five-edge spacing. This is encoded partial boot cost, not elapsed token time.
- `entry/`: all 3,920 actual target-5 payloads encoded into 31 template batches, each fitting the actual 128-template table. Every payload decodes exactly; a payload bit mutant is caught. These template writes reserve 19,600 local CSR edges. Entry inputs provide no issue/ACK calendar, so no PW/LEN/BEGIN is fabricated. Template batches need actual calendar/launch adoption before execution.
- The original local seqhost receipt is passed separately because the route lane's timing aggregate retained master profiles and production hashes but omitted reset/KS phase metadata. The composer requires exact source, master, parameter and define agreement before adopting that metadata.

The mandatory initialization provider is composed through `--mux-config`: actual CSR 0x15 gap/RL words and all eight CSR 0x16 window rows with explicit slot attributes, plus source-qualified reset/KS pin dates. Current native programmes do not supply their actual gaps, RL, window dates, KIT or header stage/start phase. Those missing fields are named in `holds`; diagnostic bench values are not adopted. Consequently BEGIN, SEAL, KIT and END are absent and `host_boot_complete=false`. `--host-booking` optionally records explicit first sink-pin dates with five-edge spacing, without claiming external host/reset transport qualification. No fixed END/readiness or global launch dates are inferred.

API:

```python
manifest, files = compose(program, bound_control_record, local_timing, csr_cadence,
    mux_config=actual_mux_config_or_none,
    host_booking=actual_sink_pin_booking_or_none,
    seqhost_receipt=original_source_pinned_seqhost_receipt)
```

CLI uses `--program`, `--control`, `--timing`, `--cadence`, `--seqhost-receipt`, and a fresh `--out`. The optional `--mux-config` and `--host-booking` must contain actual programme data. For reproduction, use the committed inputs here, `../seqhost_local_1026/{control_local,host_csr_cadence}.json`, and a fresh output directory. The CLI performs complete byte decoding plus a negative control. A changed programme command issue is rejected against its actual BoundDie annotation.

This packet starts at main `51fe3d1f8` and cherry-picks only the three original seqhost/BK timing, native mux boot, and CSR cadence commits, then adds this isolated composer. It preserves the original branch. No production RTL or shared compiler/control file changes; zero added RTL cycles. No physical, global reset/transport, residency or whole-token claim.
