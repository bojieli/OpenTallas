# NF15b independent Fable review — 2026-11-16

Verdict: ADOPT-OK for the NF15a → NF15b plan and sidecar successor. Adoption remains the coordinator's ruling. This review does not qualify an assembled die or substitute for the outstanding physical type results.

Reviewer: Codex HEAD owner, independent of the Claude Fable authors of e7ba8526df357af4ce6157fc4eb17bdf7128cadc, 88bba1a269d3fa2df298bb0807e849a0556a932f and the NF15b composition. I read their actual changes, the existing generated parent and reports, and personally LOOKED the three actual-plan/frozen-clock renders below. No new bind, gate, component simulation, clock build or P&R was run for this review.

## Exact candidate

All paths below are on epyc7 under /srv/opentallas-scratch2/claude/fable-die-head.

- Plan: prep21z20NF15b/prep/source_plan.json, SHA256 8fc6cba9fd52af245a1b76afad7cae6cf5eaa6a608157460eeace3dc13f6e815.
- Sidecar: prep21z20NF15b/prep/source_sidecar.json, SHA256 6fcd1d3dfc43434bcbf774528cbaefa2ccb2fce156d0ada588297637fb793f0e.
- Baseline adopted NF15a plan: 88f7ab5a6f2e9eb73a2b5c9d369563cec0fb2970f88002d930af307de72885ef; sidecar aef151594c563e98af58fd43e5d60968613ce15673c67a27bc30d93fee710127.
- Frozen actual KIT graph: base/head/fdh_st/tree/kit/clock/tree.json, 45,100 sites, c1cefe644d8327263fb8bdfb9f0b8d829810ae2c22ff7232868b2a3860858b19. Its NF15a captured copy is byte-identical. The 44,543-site stamped input is not the physical site reference.

## What changes and why it is coherent

The partition instances, outlines, top ports, physical lanes, reset network and budgets are identical to NF15a. All 26 published wrappers remain byte-identical (nf15b_gate/cohort.json: PASS, 26/26). Type changes are limited to notes and five raw-pin coordinates: three host_e x corrections, hd_lep0N raw1 y1107→1104.84, and hd_mesh raw0 y405→402.84.

The approved FREG correction removes the declared face-register cycle from logical K and adds it once to the identity/loop accounting. Existing parent straps still account for the actual reader and writer START offsets; they are not uniformly raw K+2. All 30 FREG ports are non-tree. The actual generated parent count-strap audit passes 3,278 bits with no errors. Source e7 and 88 each had their existing normal 32/32 gate; 88 is now merged.

Rebinding uses the actual frozen KIT graph. The 22 under-margin crossings and corresponding 22 latency rows each gain one declared cycle. The existing count-align proof in nf15b_bind/bind.json report.verify has 2,000 samples, zero window violations, zero identity/loop errors, 427 fundamental cycles, minimum low margin100.7ps and high594.2ps. nf15b_gate/bind.log reports top and nested port bind PASS (26 masters,358 partitions; nested7157 instances) and tie audit1671 accepted/0 rejected. nf15b_gate/latcheck.json reports329/329 PASS, no unobserved lane or unexplained delta.

The committed TOKEN composition41038512cfa prices all22 lane increments: selected transport critical path remains402 cycles, delta0, HOST legs58/58 unchanged. It explicitly is plan-derived composition, not an installed native programme or a token-rate measurement. Production activation/residence/START programme inputs and candidate-specific PHY RX latency remain separate recorded work.

## Actual images LOOKED

- nf15b_review_images/nf15b_plan_frozen_clock.png: actual plan with the45,100-site frozen KIT reference. The regular tile arrays, spine/shims and peripheral service/PHY regions retain their adopted NF15a geometry.
- nf15b_review_images/hd_lep0N_fine_clock_raw_pins.png:628 actual fine reservations and raw BPin contracts; moved raw1 remains in the existing macro corridor.
- nf15b_review_images/hd_mesh_fine_clock_raw_pins.png:633 actual fine reservations and raw BPin contracts; moved raw0 remains at the existing edge corridor.

The pictures support this metadata/bind change; they do not assert routed DRC or timing closure. The 833ps clock contract is retained. Latest owner leftover M8/M9 policy remains conditional on actual imported infrastructure obstructions/masks; the historical M7 note does not cancel that later policy.

## Existing obligations retained

G0 has one ERROR record covering the same12 native-PMA reset release sites, zero pending-view findings and230 warnings. This is the inherited native release-qualification obligation, not twelve new errors caused by NF15b. It remains explicit. The plan itself records physical_qualified=false. Latest host_e/SerDes physical candidates, the parent seam fixes and native programme qualification are not relabelled as complete by this review. Historical failed verdicts remain unchanged.
