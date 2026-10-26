All thirteen preserved f1 station routes completed normal collect and auto-merged to main without rerouting. Each retained ODB/SDC/SPEF, original frozen helper payload and manifest, routed measurement files and failed export snapshot passed the remote immutable hash check after closure. The separate recovery helper is source-pinned to main and its exact child_lint SHA256.

The first pilot, s81fill_hstnh_112-f1-e5bab3fc7, published record 00680c3c9 before the recovery metadata followup. Its published evidence remains untouched. Its additive JSON here supplies the full original/recovery provenance, as do the other twelve job records.

Generic component closure: TT setup 330.74..350.04 ps, FF hold 27.74..32.91 ps, DRC 0. SS is sensitivity only.

Current raw-precision native ETM/insertion audit: 13 PASS, no launch/capture over-budget pins or combinational pins. Launch 168.7159..185.8345 ps; capture 101.08685..121.45589 ps. Every actual clock reference meets insertion <=300 ps and spread <=80 ps. The JSON preserves raw reference values as well as the rounded audit display. This does not establish current die binding, static schedule integration, die timing, or whole-token qualification.

Each per-job JSON includes the original helper plan, new helper commit/SHA and guard manifest, remote immutable verification, exact metrics, publication commit, exported file hashes and raw-precision native audit. summary.json pins the exact current native audit source.
