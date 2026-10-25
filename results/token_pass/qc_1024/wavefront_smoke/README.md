# QC wavefront reset in the bound xt1 carve

The current generated top routes reset over `rstw_*` wires. The old smoke carver treated any external wire without a payload lane as idle0, which would keep partitions whose reset parent sits outside the carve permanently in reset.

The carver now reads the emitted `bind_reset.json`. Kept partition reset links use the real emitted RTL. A reset entering from an omitted carrier is modelled by its published prefix age (`release-entry_stages-depth_K`); an unrecorded or inconsistent reset boundary fails closed. No reset is converted into an idle payload lane.

The event-calendar start is explicit and occurs after the latest published partition/core reset pin release. On the current r3 bind, partition max128, latest core pin129, calendar start130 cycles after raw reset release. This is a boot/recovery cost; event-relative compute latency and steady token period do not change. Actual internal reset/readiness remains a functional simulation gate. The whole die already uses the forwarded epoch bump and first_ofs as its explicit token-start source; the carve supplies the three event lane ends after its boot barrier.

Software tests5/5 PASS. Dry generation on epyc3 `codex-qc-bind-1025/wavefront_r3` PASS:22partitions,32ROMtiles,5outside reset prefixes (72,74,75,83,90cycles), no reset assigned idle0. `carve.json` records the actual metadata digest. Full RTL smoke is pending and must not be inferred from generation.
