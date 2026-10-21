# DIAG pricing of the current paired STATUS completion barrier

This is a separate conditional model overlay, not a production composer edit or release claim. Baseline is exact TOK.QW.SCHED commit23314a50c. The current paired proof is880c8c651, source-pinned against immutable original702d24a78; it uses the corrected matched calendar, not the currently failing bound images. Run `python3 results/rtl/xdie_qwen_1018/seam_status_pricing/audit.py` from any directory to reproduce record.json. Seven baseline source snapshots are included and hashed.

All endpoints below use the same native59 CMD issue anchor, in streaming cycles:

| Endpoint | Baseline K_REAL3 pair | Current K_REAL4 pair |
|---|---:|---:|
| First RESULT at native59 dr_o |1809|1811|
| Last RESULT at native59 dr_o |1840|1842|
| native59 completion |1854|2061|
| Existing composer attention endpoint (first RESULT +16) |1825|1827|
| Existing 98-cycle return/operand path ends |1923|1925|
| Required max(data return, native completion) |1923|2061|

The raw STATUS_DELAY213 is a producer-programme calendar tail. It is not a new serial delay to append after all data work. Relative to last RESULT, actual native completion moves14->219 (+205), while the existing composer return path hides the old completion and83cycles of the new219cycle completion age. Current extra wait is219-83=136cycles; data arrivals themselves move+2, giving138/layer and4,968/token for36 layers. The existing native_ret input landing charge (+6 successor /0 asbuilt) remains exactly once after the max gate, as do dependency gaps and other pre_o die edges. Do not add213 or native_ret6 again.

The exact23314a50c inputs, composer and ledger contain no explicit serial STATUS20 term. The baseline attention term is1825 and return span98. No unexplained20 is subtracted. If a newer scheduler already charges such a term, it must be source-pinned and this overlay must be recalculated against that scheduler.

Conditional one-user estimates, holding the existing mixed measured/DIAG/priced composition fixed:

| Baseline variant | Baseline cycles/token | Conditional cycles/token | Conditional tok/s at833ps | Change |
|---|---:|---:|---:|---:|
| Ledger with successors |261667|266635|4502.3|-1.863%|
| Asbuilt ledger |253549|258517|4643.7|-1.922%|

These are DIAG scalar overlays, not a rerun of the full composer or measured full-token rates. The98cycle return span remains the baseline's DIAG term; the shared CMD anchor, unchanged downstream stages, and a serial dependent o_proj barrier are assumptions. Four-user OVL extrapolation is withheld: die_qwen confirmed current g5r2b sourcecfc5a82ac still uses oldqfd_d2d_static/sysface and offers no proven next-layer-before-STATUS overlap. The closed sf7 adapter is not yet implemented in that die.

Binding holds remain: both die calendars must use the matched r17 codec2/TX_SHIFT1/STATUS_DELAY213 law; currently bound-image and compute-codec1 scenarios genuinely fail. KV K22 geometry natural13>image9 remains unresolved. The new schedule and final bound hardware need qualification before adoption. No release ledger or production RTL is changed here.
