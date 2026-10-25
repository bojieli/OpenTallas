# B2o token-model update: one clock and native W128 HC

B2o plan: claude/hbm-b2o-1024@b6cbd6362. Stages regenerated from the committed
B2o die plan and its own hbm_rows.json; no stale B2n/B2m sidecar reused.
The unmodified model reproduces B2o's published point exactly.

| model | DS AR tok/s | DS MTP tok/s | Qwen AR tok/s |
|---|---:|---:|---:|
| B2o baseline |1176.1|2013.8|846.0|
| one1.2GHz clock, ALAT4/MLAT4, leaf split |1190.7|2024.9|849.0|
| plus native W128 HC whole-chain delta |1190.3|2024.6|849.0|

Native HC uses TLA7, not TLA4. Its seventh half-tree level costs+7; replacing
four quarter sums by two half sums removes one three-edge root add, so RAW0
net delta is+4 at fixed XRD/XRU. Charge+4 to HC.HC_MIX/FUSED.HC_PRE_NORM;
HC_MIX_POST starts from gathered raw mixes and does not use this tree.
The correctly mapped native case adds324 AR cycles and384 MTP-step cycles
to the one-clock point. It changes no Qwen work.

The first exploratory hc128 case incorrectly charged MIX_POST instead of
PRE_NORM. It is not a result of record. The corrected native case ran from
a separate frozen source module and output native_hc128.json; the original
job's raw hc128.json remains in the remote run directory as diagnostic history.

Rules: same c_L4 array, X377.6ns, same native programmes/dependencies and
MTP pipeline law as plan_study_price_1017. One-clock case follows the FP32
lane's accepted model treatment (ALAT4/MLAT4 and leaf-split SERIAL1).
The old multirate bridge removal receives no extra benefit in this model.

OPEN: L74's second static beat and face-shell crossing latency need the
native compiler's per-record map. L74 mixes VM responses, HC subtree sums,
TKM del_flit traffic and SU tree data; blanket+1 per op is unproved. These
numbers exclude those pending deltas, so they are not final release rates.
Neither this model nor the minimum arithmetic gate is a native B2 token pass.

Runner: tools/hgi_sim/b2_native_price_1025.py, B2_NATIVE_MODE=baseline,
oneclock or hc128, --stages stages_B2o.json --x-c377.6 --jobs4 --out FILE.
Run: epyc3:/srv/opentallas-scratch/claude/codex-hbm-token-price-1025;
correct native case unit oth-ubuntu-2127458-1792922096 exited0.
