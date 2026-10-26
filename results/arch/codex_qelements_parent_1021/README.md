# Slice parent selection of the p7 regional station

The slice source at 980d6e5c4 used a SCALE_LAT=6 generic station. The independently qualified p7 station at 103b505c6 uses SCALE_LAT=7 and the BZ16 arithmetic specialization. Import its exact three source files; the parent no longer invokes the legacy child generator while rebuilding its own graph. Independently selected child source must remain authoritative.

Validation: all three selected leaf files compared byte-for-byte with 103b505c6; parent generator passes Python compilation. Existing p7 leaf witnesses (regional equivalence, 20,000 edges/two resets; rmut1 causal failure), census max32 and MAIN/FALLBACK layout gates apply to the unchanged leaf source only. This packet claims no parent behavioral or physical closure. Current lp benches based on 16280a556 test the prior SCALE_LAT=6 source; they are not evidence for this composition. The token owner was informed to price the additional result edge and rerun current-source functional work.

Actual qualification routes remain live: qfd_dv_s8_station_tail1_p7a-p7a-a99364876 and p7b-p7b-1f80a0746. Parent assembly uses their real exported view when available; the existing census proxy is not a routeable view. MAIN/FALLBACK w13/e13 parent geometry is already planned, with both native census shapes PASS max32 under the prior hardened-child abstract.
