# HBM source compiler narrow closure

Main-based branch codex/hbm-token-closure-1030 starts at main12cd49f66075f259ae06f185aa462d0c6d647823. This single closure commit imports only the12 HBM VM compiler tools below and selected current source receipts/LOAD proposal. No RTL, physical plan, target, gate, model rate or other lane is changed. It does not import the older branch ancestry. Historical intermediate binary chains and failure receipts remain preserved at codex/hbm-token-1030@bc8e04ee5; README historical paths refer to that source branch when absent here.

Current compiler files (all newly added against main):
- tools/hbm_next/vm_attention_phase.py
- tools/hbm_next/vm_canonical_stream.py
- tools/hbm_next/vm_capacity_witness.py
- tools/hbm_next/vm_expert_entry.py
- tools/hbm_next/vm_phase_link.py
- tools/hbm_next/vm_phase_publication.py
- tools/hbm_next/vm_phase_region.py
- tools/hbm_next/vm_phase_shadow.py
- tools/hbm_next/vm_phase_split.py
- tools/hbm_next/vm_pipeline.py
- tools/hbm_next/vm_static_cache.py
- tools/hbm_next/vm_value_phase.py

Runtime compiler dependency remains explicit: --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools provides the actual HGI-1R isa_rows.py/image_check.py snapshot; this code does not silently substitute main's absent ISA tools. Actual image a122.hgi1r SHA a1228bb5771a604f53aad9de3366f460fd9d7c0c59b9a04fa2856405b5726933,3916records,540064bytes. Also requires Python/numpy and main tools/hgi_sim records via PYTHONPATH. Canonical source remains an unpublished candidate.

The retained final canonical_resident_cached candidate is37226commands,319227648boundarybytes,max255168VMwords. resident_address_check.json proves source relocation before copy elision; its proof covers20842checks/40expertregions/6headstreamrows and4controls. stream.json elision receipt proves29345copyinductionchecks/finalstate equality+2controls. Whole-token numeric RTL/calendar/stackcoverage/scratchreservation are open. Do not use check_canonical.py directly on a copy-elided stream: its one-to-one canonical boundary expectation applies to the reproducible pre-elision resident baseline described in README. Source-only counter/overfetch budgets are conditional on the proposed implementation and are excluded from existing1.8ktoken/s model.

Capacity units: current ordinaryVM262144words=1MiB. Smaller256/512KiB currentexpert placements fail; 2MiB is outside current ordinary18bitword namespace. capacity_sensitivity.json gives bounded component failure counts without inventing a new architecture.

Original source commit sequence (history reference; do not cherry-pick this entire ancestor chain):
```
56850b3cb HBM token: prove old regular VM capacity fails unchanged a122 dataflow
eedbe28aa HBM token: prepare exact finite row phases with explicit producer publication holds
b1bed3294 HBM token: construct native producer publication and reload fragments
db70a30d7 HBM token: remap actual producer dependency regions into finite VM
84a251a37 HBM token: encode publication fences and consumer DMA dependency
34875f5b0 HBM token: reject native consumers lacking reload completion dependency
934ecb6a8 HBM token: preserve native three-lane attention plans in finite VM phases
a1a37b1fe HBM token: fit native three-row producer lifetimes with sector ownership
c793a755e HBM token: emit native sector DMA with canonical cross-phase producer epochs
8f450e4df HBM token: extend finite three-row source phases through attention preparation
fdfaa707f HBM token: link native finite-VM producer and attention-preparation epochs
2cc225fce HBM token: link canonical finite-VM source through native NL3 attention
8f10f0dba HBM VM compiler: preserve real post-attention phase dependencies through source1558
0feaf0502 HBM VM: bound actual expert union and rsel block, publish its native input epochs
a31c7faf4 HBM VM scratch: reject actual stack overflow and prepare source-disjoint MTP tail candidate
d9e40eabc HBM VM: derive and qualify all40 native dynamic expert regions within old VM
a3f33f16b HBM VM: lower all3916 source records to bounded canonical-backing stream
f8c0aa07f HBM VM: group only commuting source rows and honor prefetch lifetimes
4b3ad9011 HBM VM: elide statically redundant DMA with exact resident value identities
603ebf283 HBM VM: prefer resident input placements and remove16.84percent boundary traffic
```

Source descendants carrying current results/proposals:0594379e8,b9fb6a3d3,e1c36f4a7,a0cdb68a0,6b2d8b60c,bc8e04ee5. The narrow closure replaces the need to cherry-pick these old-ancestry commits. Validation here is Python syntax only; existing address/value/component receipts are retained unchanged and no physical qualification is asserted.
