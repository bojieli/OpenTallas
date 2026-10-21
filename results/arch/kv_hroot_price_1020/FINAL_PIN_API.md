# Candidate GEN handoff API (unqualified until actual evidence exists)

`tools/qwen_kv_die/kv_hroot_calendar.py:profile_requests(model, port_widths)`
emits every primary and fork destination for root, PC neighbour and group
neighbour words. `port_widths` maps actual rendered `instance.port` to full
functional width. Missing or unequal widths refuse. Without a width table the
request inventory is useful for planning only; validate_profiles refuses it.

`validate_profiles(requests, profiles, identity)` requires exactly one row per
request, with identical src/dst identities, width equal to actual rendered port
width, and a `bits` dictionary with every bit index (string) mapped to its actual
fixed age. Missing bits, unequal ages, unresolved values, missing destinations,
or mismatched endpoints refuse. The exporter must resolve mesochronous phase
profiles to the actual fixed sampled age first; max(stagecount) is insufficient.
Identity carries candidate_sha256, die_v_sha256, strict_bind_sha256,
root_rtl_sha256, relay_table_sha256. These hashes bind artifacts; passing the
schema does not certify RTL equivalence, physical legality or timing.

The returned external ages exclude internal stages. For selected LAND root,
fan_root2_b contributes2 to chain launch, stack_bl contributes2, relays_l
contributes2 on fan/gather/return. PC neighbour internal chain/return latencies
must match the actual bound PC RTL (C3 historical hop1/trainhop2 are unqualified
until source/view matching). Follow the actual endpoint graph, including every
PC hop, group fan/gather hop, fork, landing and final pin. C3 target12/13 must
consume composed per-PC down and return ages, not scalar stack maxima unless
all actual per-PC hop differences have been proven/equalised.

`observation_intervals(rows)` requires all32 groups at both enter and leave.
Each row has stack, group, phase, last_change, first_use, hold_through,
transport_edges. last_change is AFTER the actual group drain/fault producer
changes, transport_edges includes all external group-chain/root-to-ctl edges,
root2 and capture+decision2 are added separately. first_use must be at least
last_change+transport+4; sources must remain settled through first_use. Real
compiled enter/leave roots plus go/cycle/capture alignment determine first_use;
never substitute QUIET_WIN or writer->farthestPC age for this path.

Also emit the separate160 boot CDC applied/fault last-change / setup-ready
first-use interval inventory, retaining source clock, sink clock, absolute edge
basis, boot observer synchroniser stages and strict-bind identity. Reset releases
must precede each path's first valid use under the actual selected source.
No new full GEN solely for this audit until structural relay/reset repair is ready.

`baseline_profile_requests.json` enumerates396 historical d22bu plan requests,
source model SHA1082052bed954b47d891d10e2708c05c4e4a0e54bf0a603ea658f6dc2b25adb8.
The frozen model is compressed alongside. Widths intentionally null: this is
unlanded plan-only evidence, not a selectedLAND or final-pin source contract.
