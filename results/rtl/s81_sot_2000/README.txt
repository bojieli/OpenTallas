SOT source and minimum component replay

The original ALLQ producer returned exact P.V values but failed with the real SMT=1 target because it omitted SOT. Those failure receipts remain with the RTL gap owner. This change supplies the actual SOT frame encoding and inserts it in lower_svc.Job through build(..., sot_booking=...) or ctx.svc_sot_booking, after WIN_LOAD and before SE. The real Job scheduler counts its frame and three words.

booking() requires explicit target installation, write, read and retire pin edges. It validates the complete source-width fields before using the established SOT encoder; dates cannot silently wrap. attach_to_job checks the actual accepted WIN_LOAD owner. Configuration alone does not complete the legacy SE/PV-only programme; full SO input, fence, route and current-die bindings remain required.

The component caller takes the real ALLQ-derived SMJ image from so_bench, inserts WIN_LOAD and SOT, and drives the unchanged real SMS decoder and SOT target. Only heads 0 and 15 are elaborated, covering even/odd masks and both output groups. It checks real SM output arithmetic, target faults, eight gather beats and retirement per selected head. The original head-mask negative remains causal.

The first 16-SMS replay scope exceeded its own 32 GiB cgroup limit, unit1399888-1792642509. Fleet confirmed abundant host memory and no host earlyoom kill. Its log and initial source tar remain remotely preserved; no completed objects existed. The replacement is the minimum two-head mechanism, not a full-shape claim.

The original stale-helper19-RoPE-row arithmetic failure remains with the RTL gap owner; the corrected source-pinned image is its independently qualified images_pinned input. Production transport ages and private configuration/final-parameter bindings are not yet selected in the bound die. No global dates or full-layer pass are claimed.

Completed minimum replay: unit1612637 built the real two-head component; final runner unit1772927 reused the exact same binary and identical q words. Both selected targets accepted the SOT source, emitted eight beats and retired once, with no parser/target faults. All16 SE rows and64 SO rows were exact, including RoPE, at54-edge SMS latency. Existing head-mask mutant caught64 mismatched SO rows. The final runner requires both target and arithmetic PASS and checks the causal negative; its exit was0. No owned live jobs remain. Exact source/hash and scope fields are in component_result.json.
