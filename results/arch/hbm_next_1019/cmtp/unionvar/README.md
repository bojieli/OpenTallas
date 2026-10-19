# HNEXT-UNIONVAR: static union-size selection component

COORD 07:26 is implemented at compiler/component level. This does **not** qualify the next die end to end. The old average-union rate is not a safe static-schedule headline.

`union_variants.py` compiles each P3 whole-token layer into a common prefix through IDX.UNION plus 31 precompiled suffix variants (U=6..36). Both expert loops in each suffix have immediate U counts; VM addresses, rsel tables, expert IDs and each position's kappa order are unchanged. A hardware selector chooses `base + ((U-topk) << shift)` once when the successful real IDX.UNION retires. Selection cannot consult a ready signal or software.

U is insufficient to determine the number of SM passes. `counterexample.json` gives two legal N6, top6 route inputs with U=24: the balanced input has maximum cardinality two (one P3 pass), the skewed input has an expert in all six positions (two P3 passes). The real IDX/SW-slice boundary bench executes both inputs. The opt-in `plane_compiler.py meas --union-safe` reserves N rows for **every** union expert, including its SM work, publish/skew and intermediate gather; the existing mean/histogram model remains historical/conditional. This bound is conservative even for U=36.

`ot_hnx_union_calendar` is real RTL: one registered U selection, a preinstalled 81-bit event SRAM, a fixed read pipeline and autonomous time counter. It emits the chosen bank's `(unit mask, record reference)` events on fixed cycles, faults on late/overrun calendars or a new transaction/configuration write while active, and has no ready or credit input. The first event is at least three edges after selection; events are at least three edges apart. The minimum production mechanism bench includes the actual IDX.UNION and actual SW VM slice, not a software-generated U driving the selector.

`union_calendar_compile.py` emits all U6..36 static model-record calendars for production L2/N6/P3 with measured v2+frames/FUSED tree/SM3 costs and conservative expert spans. It checks C1/C2/C3 after integer launch serialization. Model references are not native unit descriptors. `tb_hnx_union_compiled` replays those calendars against independent tuple expectations from the compiler JSON. The small unit bench covers every selector value and a wrong-variant mutant; the real IDX boundary bench also requires that mutant to fail.

## Capacity and integration limits

The 40-layer immutable record suffix banks occupy 10,158,080 bytes. This fits a **proposed** 64 MiB HBM allocation; that allocation is not installed. Each expert loop body fits the legacy 64 KiB CP ring, but that is only a storage check. The legacy die CP remains a HGI-1 record-fetch/credit sequencer and cannot run HGI-1R/static calendars. These bytes must not be presented as executable resident CP state.

The new component's proposed store is 16,384 x 81 bits (1,327,104 bits, 165,888 bytes). The L2 fixture holds every U variant before routing, so selection performs no transfer or code loading. This does not establish that all 40 layers' calendars/descriptors are resident, nor price a layer-to-layer installation. No new SRAM macro binding, area claim, TT/FF (SS sensitivity) closure, native descriptor dispatcher or die connection is supplied. `model.json` and both compiler manifests state these gaps explicitly. Native adoption therefore remains blocked on resident storage/loader timing, HGI-1R descriptor dispatch, physical qualification and full price composition. No fallback to the old credit/ready CP is authorized.

## Reproduction

All Python compiler/model jobs and Verilator 5.050 builds run through `ot-run`; none run locally. The pinned fleet root is `/srv/opentallas-scratch/claude/codex-hnext-unionvar-1019` on ot-epyc7 (host chosen automatically from roots with the input data).

```
python3 tools/hbm_next/union_variants.py --image INPUT/mtp_N6_token.hgi1r --meta INPUT/emitter.json --out OUT/banks
python3 tools/hbm_next/union_calendar_compile.py --out OUT/calendar
bash tools/hbm_next/union_bench.sh OUT/bench
python3 tools/hbm_next/plane_compiler.py meas --step5 --union-safe --only P3a_u4 --cases 'ALL measured v2 + frames + die FUSED tree + SM P3 tile' --jobs 1 --out OUT/reprice.json
```

The reprice is a conservative U-only body budget evaluated at the existing workload union statistics. It excludes new store area, native installation/dispatch and physical boundary costs, and is not an adopted token-rate claim.

## Results

All three RTL benches pass on Verilator 5.050. Each wrong-variant mutant fails with its committed witness: `cal_run1.log`, `bound_run1.log`, `cmp_run1.log`. The real boundary bench executes 15 records including both U24 counterexamples; the compiled L2 replay executes 3,193 model-record launches across 31 variants. All L2 banks use 7,936 of the proposed 16,384 event words (80,352 packed bytes). The event store is preinstalled for these tests.

The conservative reprice is **AR 1,967.8 / MTP 3,014.1 / four users 3,706.3 aggregate, 926.6 per user**. Both the MTP target and the 1,000/user floor fail before any new store/dispatch/loader costs. This result supersedes no released evidence and authorizes no adoption. `reprice_source.py` is the exact fleet model source used by that run (the working tool additionally labels its union-safe metadata/tag). The 3,377.5 mean/histogram estimate cannot be promoted to a U-only static-schedule claim.

The source-derived richer-key study is now recorded in `KEY_OPTIONS.md`: U plus actual maximum expert-row cardinality, or a cardinality histogram with a proven hardware ordering mechanism. No richer-key RTL is included; root chooses the next mechanism from the concrete model options.


The source-derived study (`key_study.json`) identifies 118 legal N6 `(U,Cmax)` keys versus 2,432 cardinality histograms and 26.65 billion ordered vectors. `KEY_OPTIONS.md` inventories macro ports/area, fixed installation counts, pre-loop metadata, and unresolved native descriptor storage.

The final candidate prices use the structural bound `Cmax <= min(N, topk*N-U+1)` for uncaptured draft/seed routing. In particular, the current draft model uses no-sharing U15 for N5/top3, implying c1 exactly. `(U,Cmax)` remains too slow: 3,144.0 MTP, 1,020.8/user. Factored exact-cardinality work prices 3,380.3 MTP; adding the proposed 108 pre-loop cycles on each main-model layer gives **3,370.44 MTP / 1,035.72 per user**. This is only 0.19% above 3,364 before unqualified physical/loader/descriptor costs, and is **not an adopted or measured rate**. The initial more conservative candidate prices are preserved separately as `key_*_price.json`; final structurally tight candidates are `key_*_tight.json`. Both exclude new SRAM area from the original 767.41 mm2 denominator.

## Factored successor (LH-P3UNITS/UNIONVAR 10-19)

See `factored/README.md`. The real-IDX factored dispatcher bench passes, and its 3 wrong-variant/start mutants fail with committed witnesses. The capacity check fits with dedicated SRAM stores (7 kernel macros × 4 quadrants plus 1 metadata macro, no per-layer load). The composed reprice gives MTP 3,377.19 (+0.39 %) and 1,038.38 per user, with the measured 0-cycle prep replacing the 108-cycle assumption. The TT/FF gate and the native lowering are still owed.
