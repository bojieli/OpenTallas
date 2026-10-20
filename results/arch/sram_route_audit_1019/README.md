# Routed native 32x64 SRAM diagnostic coupon audit

The exact `sram_escape64_1019-coupon-3ff02bde1` coupon passes external routed access, reported detailed-route DRC, TT setup, FF hold and native boundary checks. This evidence qualifies only the approved 108 x 108 um synchronous diagnostic harness. It does not qualify a production banked client, independent-clock CDC, repair-enabled substitution, internal SRAM transistor layout, or production area.

Source: `3ff02bde11fe57867215021e1e0b6f4e5690a0c8`; closure record `56506d2563c27e975c80ae13e0d9a4cb3698f62a`, auto-main `944bbb859`. Immutable fleet route remains on ot-epyc7 at `/srv/opentallas-scratch/claude/closure-loop/sram_escape64_1019-coupon-3ff02bde1`. The source snapshot was receipt-trimmed after closure; its Git commit reconstructs it. No closed source or route artifact was changed during this audit.

## Actual final-route evidence

- Final ODB SHA256 `81c02e2165d2836fc5f816cd9727418e40e8fd5827af11290705a8e2098183e0`.
- Final SDC SHA256 `9ef26787244b16b0974cf531589185a7868ba06fec24570c49303ea828b068ab`.
- Final SPEF SHA256 `d93026c43b392058ff73bf7320a71278cabb1d71ad2192affadc287958c4eb8a`.
- Routed TT setup +422.52 ps; FF hold +17.87 ps. Detailed router converged 117 -> 3 -> 0 violations; 4637 signal vias. `5_2_route.log`, job snapshot and artifact hashes retain exact evidence. SS +380.24 ps is sensitivity only.
- Routed native launch 91.89238 ps (`rd_out[6]`); capture 74.69734 ps (`w_mask_in[59]`); no outputs over 220 ps or inputs over 190 ps. The reference is the measured routed TT boundary mean 127.0 ps. TT/FF boundary spread is 17.2/16.1 ps. Prior CTS-only 93.789/70.548 results are not reused as routed results.
- Actual macro clock TT wclk/rclk 117.7/117.9 ps, slew 13.4/13.5 ps; FF 92.2/92.4 ps, slew 11.4/11.4 ps. The analytical SRAM has no separately characterized internal clock insertion; its explicit Liberty clock arcs and raw external clock pins remain the model boundary.
- Fresh read-only `check_power_grid -floorplanning` on the exact final ODB reports all VDD shapes and all VSS shapes connected. `pg_probe.log` is a transcription of successful tool stdout, with exact ot-run unit.

## Dense contact proof

The bank's full-face density 5.95/um hides its approximately 10.5/um active contact cluster. This audit checks actual geometry rather than averaging that density away.

`contact_probe.py` decodes the final ODB signal wires, special wires and via enclosure/cut boxes. Every one of 206 signal/clock contacts and all 44 VDD/VSS stripe contacts overlaps actual same-net route metal. No contact overlaps route metal belonging to another audited macro net. Every original signal pad is only 24 x 24 nm (576 nm²); the connected same-layer M4 union is at least 3144 nm², exceeding the actual technology minimum 2000 nm². PG unions are at least 3,013,632 nm². The full union audit found zero failures. An independent conservative PG direct-contact union variant also found zero failures; both receipts are retained.

`obstruction_probe.py` checks all 972 signal wire rectangles and 3192 via enclosure/cut rectangles on the 206 macro signal nets against actual transformed macro obstructions. There are zero intersections. Macro origin is exactly (43.2,43.2) um, R0. The router's zero final violations remains the spacing/via rule-deck evidence; the geometry probe is not a substitute full signoff deck. The externally connected metal satisfies minimum area without inventing larger LEF pads or waiving tiny contacts.

The source-bound production bench passes 1392 checks on Verilator 5.050; inverted write-mask mutant produces the expected ESCAPE_MISMATCH witness. Logs and job snapshot are retained. Both modeled native clock ports are driven synchronously here.

## Scope and follow-through

The low-utilization distributed pin-register harness deliberately pays for external escape. Its 108 um outline and approximately 705 um² routed design mass are not the area of a production banked client. Such clients still need their own complete replicated banks, data/control/reset fanout, registered boundaries, clock/PG/access, legal rows and density, reach, native TT/FF timing, compiler latency and production throughput qualification. The analytical memory compiler remains research scope; no internal GDS/transistor qualification is asserted. No new physical route was launched by this audit.

Read-only fleet probes used ot-run without host pinning, with data locality on ot-epyc7: full contact unit `oth-ubuntu-3164500-1792429808`, conservative PG unit `oth-ubuntu-3168303-1792429890`, obstruction unit `oth-ubuntu-3170716-1792430014`, PG connectivity unit `oth-ubuntu-3166605-1792429857`; all exit 0. Artifact hashes bind every final route/export file. No interface edge or compiler schedule changed.
