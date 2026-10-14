# Composition checkpoint

Passing component evidence is immutable in `component/` (593),
`f460_component/` and `f460_transition/`. The last f460 transition gate actually
ran on EPYC1 as `oth-ubuntu-1569430-1791964988`, terminal exit 0. All 1,024
layer0/layer1 outputs matched on one kernel/frontend/sector/128-PC/VM instance
with no reset after boot. Layer1 K mutation caused 512 numerical mismatches;
a genuine layer1 ACK retagged with old epoch17 faulted after exact layer0.
Q/current SU transactions remain fixtures; executed core X carry is unproved.

The generic executed-layer driver `tools/qwen_composed_harness/full_layer.cpp`
is an **unexecuted draft**. It is staged on EPYC1 at:

`/srv/opentallas-scratch/codex/qwen-composed-harness-1014/full-layer-v1`

Its kernel archive is actual f460 (SHA256
`54a3930e1a7d279cd5fdc987e76d25a8d8eaabc6e8cd22b75e6e7118ff091f8e`),
and the original 593 stage/archive was preserved. Required real provider
libraries already exist at:

- Frontend: `/srv/opentallas-scratch/codex/native-services-frontend-1014/library-v1/obj`
- Sector mapper: `/srv/opentallas-scratch/codex/native-services-frontend-1014/sector-library-v1/obj`
- Physical PC: `/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj`

Layer0 inputs/reference and observer catalogs are staged under
`/srv/opentallas-scratch/codex/qwen-composed-harness-1014/full_inputs`:
`images/layer0`, `fused_images/layer0`,
`oracle/position255_production_tp8_two_level`,
`operation_destinations_layer0.json`, `resolved_SU_fields_layer0.json`.
The real collector is under sibling `collective/` (`runtime.py`,
`build/obj/Vtb_coll_tp8_provider`). No expected values enter any provider.

Wait for the **existing** fullshape provider v6_600 build owned by
`/root/qwen_native_dispatch/fullshape_rom_su_provider`, EPYC1 unit
`oth-ubuntu-1392525-1791962656` (parent session23163). Its intended library/header
directory is
`/srv/opentallas-scratch/codex/qwen-fullshape-provider-1014/v6_600/full_g3072_su64/obj`.
The preceding v5 build had actual scoped OOM at ~381.2GiB. Preserve this
progressing successor; no usable fullcore header/archive existed at checkpoint.

After the actual library exists, admit the C++ link/run with `ot-run` and call
`src/run_full_layer.sh` from `full-layer-v1`, supplying these nine arguments:
core object directory; actual image root; fused program root; production oracle
root; collector runtime; collector executable; fresh output directory;
destination sidecar; resolved SU fields sidecar. Check the actual exit and run
all independent per-operation/destination/field/effect observers.

The driver captures old accepted provider ownership before each new issue,
retains VM across warm segment starts 0/14/22, uses actual core QR/KV writes,
and requires all 22 non-END issues plus END PCs13/21/24. It captures every
actual operation commit and all three quiescent END snapshots. The observer
rejects missing/extra/duplicate destinations and checks all actual written
values, exact current KV addresses/values, accepted resolved SU fields,
collective returns and retained VM state. Expected data is observer-only.

After a passing layer0 run, bind actual layer1 payloads and the parent's warm
reference seeded from independent expected layer0 final VM. Actual VM/X must
carry directly; never preload oracle intermediate or previous-layer values.
Current draft handles layer0 only. Add meaningful actual stalls and layer/epoch
faults after the real core is bound.

Remaining production contract gap: the generic core exposes actual accepted
PC/unit and resolved SU descriptors, but no observed accepted raw
IB379/context16/version32 face. `accepted_source_words.hex` is pinned input
provenance. A nonfunctional production accepted-IB observer/source successor is
required for that lifetime proof. Functional PHY/common-core-clock composition
does not qualify physical VM, routed timing, production cached ROM/bands,
interconnect bandwidth or token throughput. The separate collector invocation
also does not provide a unified production clock/rate measurement.
