# ROOT erratum: all-corner MIN admission refused

The native API calibration below remains valid and unchanged. The earlier
claim that FF-MIN had a reviewed conservative intrinsic CQ minimum is
superseded: FF 346.043664 ps, TT 415.195299 ps and SS 524.072474 ps all come
from nominal analytical CQ, and none is qualified as earliest CQ. No positive
nominal CQ may be admitted as MIN. A conditional zero CQ proposal and its
unresolved threshold/transition dependencies are in
`../sc2_same_corner_min_model_1019/REVIEW.md`. It does not authorize Liberty.

The unconnected manifest prototype now requires six explicit same-corner
roles and deliberately refuses admission because no complete independently
reviewed MIN policy exists. This also prevents max-only caller declarations
from hiding internal minimum clock/constraint queries. An externally approved
manifest hash alone cannot establish an unstated numerical bound. ROOT must
approve the complete policy and all 33 reader/writer implementations before
future admission logic is implemented. Legacy production helpers are untouched.

Original REVIEW, manifest source/probe/log and hash list are retained in
`.historical` files; old claims below are historical where this erratum
supersedes them. Native logs, source libraries and receipt are unchanged.

# Timing-role binding prototype: native API PASS, production adoption BLOCKED

Inspected source is `22f53efd97b219b16039486b0638e3c592d37a63`.
This packet changes no shared helpers, compiler defaults, old views or production
activation. It creates no SC2 Liberty. The source/geometry prototype remains
`19ccd29b9`; its access model requires separate delay bounds.

## Actual native discriminator

An unpinned `ot-run --mem 3 --threads 1` selected ep4. Exact image ID is
`sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
OpenROAD `26Q3-1510-g6cb3f2b704`. The public API accepts
`define_scene CAL -mode calibration -liberty_min MIN -liberty_max MAX`.
Two actual `ot_sram_1r1w_32x546_m1` instances connect launch data to capture
write data. Untouched native TT/FF files, their exact source hashes, the
read-only C++ scene/arc accessor, complete expanded min/max paths and receipts
are retained here. Native queried launch rise arrivals, in library ps:

| Actual scene | Minimum | Maximum |
|---|---:|---:|
| FF reference | 277.284485 | 277.284485 |
| TT reference | 328.019043 | 328.019043 |
| Explicit FF-min / TT-max | 277.284485 | 328.019043 |
| Swapped roles, refused | 328.019043 | 277.284485 |

This deliberate cross-PVT fixture distinguishes actual library/arc selection;
it is **not** a same-corner bound, SC2 characterization, or a signoff scene.
The native accessor also identifies each min/max cell/library filename and
checks scene-specific arc mappings. Missing max role is refused before load.
The first missing-technology diagnostic is retained separately, then the
probe was corrected to read the actual technology and macro LEFs. All runs
are terminal. Remote retained packet:
`ot-epyc4:/srv/opentallas-scratch2/claude/codex-timing-role-binding-1019`.

## Bounded standalone manifest admission

`role_manifest.py` is deliberately unconnected to production. Caller supplies
an independently approved manifest digest and exact master/source/model/
geometry/behavior identity. Only distinct SC2 is accepted. No filename or
corner fallback exists. JSON duplicate keys, missing/aliased role files,
wrong file/library/cell identity, wrong source, swapped corner/analysis,
foreign domain, manufactured positive minimum access delay, and missing
TT/SS minimum roles refuse. Per-file hashes are meaningful only because the
whole manifest digest is approved externally: a self-generated sidecar
cannot certify a numerical lower bound. The structural fixture used by
`manifest_probe.py` contains no valid timing arcs and must never be loaded
in STA; its eight witnesses test admission semantics only.

Initial exact roles are TT-MAX, SS-MAX, FF-MIN and FF-MAX. FF-MIN added access
delay was proposed as zero; its original positive intrinsic CQ is now
unqualified and superseded by the ROOT erratum above. All role
files carry upper constraint requirements, including hold. FF-MAX carries
its actual load-dependent maximum. Inputs receive actual input capacitance;
outputs require correctly modeled intrinsic/output lead loading, not input
capacitance applied to an output. Slew/load domain remains 5..320 ps /
0.72..46.08 fF. No extrapolation qualification.

## Coherent writer and reader plan requiring ROOT approval

Use explicit native scene min/max binding, not two ordinary read_liberty
calls. One approved role receipt must travel from generator through route,
native/export, final verdict and every parent consumer. It records source,
model, geometry, behavior, file/library identities, domain, image/tool and
actual scene-mapped instance/arc identities, with query-role inventory.
Generated Tcl must check actual mapping after link and whenever modes/scenes
change. Missing SC2 role always refuses, even in otherwise legacy flows.
Legacy masters without this opt-in manifest remain byte-identical.

**The four current roles do not yet authorize a mixed TT or SS session.**
A maximum setup query can depend on early capture clock paths and minimum
checks can be invoked internally by resizer/export. Such dependencies must
be inventoried, not hidden behind a max-only headline. TT/SS/FF minimum admission now refuses under the ROOT erratum. A separately reviewed explicit TT-MIN / SS-MIN lower
bound, including clock dependencies, is required before those mixed sessions
can run. Do not substitute the TT/SS MAX table or silently borrow FF across
corners. Extending the schema to those roles is a subsequent reviewed step.

| Consumer/writer | Current concrete behavior | Required role change before SC2 use |
|---|---|---|
| `tools/mem_compiler/views.py:write_liberty` | One Timing CQ table per corner; uniform pin caps | Distinct reviewed per-pin/per-role writer; four files initially, no ordinary FF alias; preserve constraints and electrical domains |
| `tools/mem_compiler/sram_gen.py` and SC2 generator | Legacy per-corner views; SC2 stopped before Liberty | Explicit opt-in fingerprint and complete immutable manifest, default unchanged |
| ORFS `read_liberty.tcl`, `tools/orfs_hold_mm.py`, `tools/orfs_hold_mm.tcl` | Route synth and TC/BC scene libraries; BC single FF list | Split min/max lists for every SC2-containing mode including synthesis/pre-CTS, CTS, setup and hold repair; fail if requested bound absent |
| `tools/ref_tile/ref_tile.py`, `pre_route_gate.py` | Supplies macro ADDITIONAL_LIBS, gate Tcl and exports | Carry manifest into frozen source closure and every generated stage; reject unsupported roles before starting route |
| `tools/ref_tile/path_classes.tcl` | Loads ordinary TT libs with caught errors; prints max setup and min hold | Explicit role scene; no catch-and-continue for opted master; TT minimum presently refuses |
| `tools/w18/corner_sta.py` | Per-corner ordinary macro library; TT/SS max, FF min; SDC may query both | Explicit scene roles including clock/data/constraint dependencies; FF min/max distinct; TT/SS lower bound required where queried |
| `tools/closure_loop/meas_resta.py`, `tt_overlay.py` | Rewrites `_ss.lib` to `_tt.lib` and regenerates re-STA context | Regenerate approved manifest role mapping; never suffix-rewrite role or stale receipt |
| `tools/closure_loop/hold_eco.tcl`, `hold_eco_corner.tcl`, `vtswap_eco.tcl` | Reloads corner libraries and repairs/checks timing | Same manifest scene binding; preserve upper hold constraints and setup side checks |
| `tools/closure_loop/path_summary.py` | Ordinary corner macro read and path queries | Same selected scene and receipt, no single-lib fallback |
| `tools/closure_loop/ck_insertion.py`, `tools/w18/clock_insertion.py`, `macro_clk.py`, `child_ins_env.py` | Clock arrival extrema, macro clock/load ownership and library-derived references | Keep real clock cap and role-specific clock paths; identify actual scene mapping; never reuse max bound as earliest path |
| `tools/ref_tile/clock_entry_constraints.py`, `direct_macro_clock_entries.py`, `sta_scene_binding.cc` | Existing source/clock/arc checker expects ordinary same-corner libraries | Extend exact identity expectation to approved role per min/max; retain native per-instance sceneArc check (prototype reuses accessor unchanged) |
| `tools/ref_tile/wires_only_ioref.py`, `registered_cluster_budget.py`; parent PINFLOP SDC | Derives input/output timing from measured/library clock references | Use actual role-qualified bounds and carry evidence into every parent scene; missing earliest reference refuses |
| `tools/w18/export_view.py`, `recover_abstract.py`; `tools/tt_views/view_export.py` | Exports mixed min/max ETM; forwarded clock reads both arrivals | Separate role-qualified native export or certified merged model preserving both bounds; refuse unsupported TT/SS minimum, no ordinary single-file ETM masquerade |
| `tools/ref_tile/cts_native_probe.py`, `scalar_pin_view.py`, `probe_clock_entries.py`, `probe_dual_clock_etm.py` | Native/clock diagnostics and exported model parse | Import same approved scene prelude; receipt must identify all role files and query set |
| `tools/hier_contract/native_pin_audit.py` | Reads exported TT launch/capture and FF earliest launch/hold | Reject legacy single-table SC2 evidence; require propagated role receipt on exports |
| `tools/closure_loop/route_corner_check.py`, `closure_loop.py` | Parses read_liberty stage logs and decides signoff/export | Parse min/max options and scene role receipts, verify frozen helper membership/source; preserve old failures, no blanket waiver |

The inventory covers the production readers/writers reached by the current
SC2 closure path and their exposed native/export consumers. Unrelated legacy
diagnostic scripts (`elem_grid.py`, `die_pdn.py`, `die_constant_cells.tcl`)
load standard-cell-only libraries; they need no memory-role change unless
SC2 is later introduced there. Any new external/manual reader must consume
the manifest or explicitly refuse SC2. This is a scope boundary, not proof
that an arbitrary unpublished script is compatible.

No SC2 generation/route/client qualification is authorized by this packet.
Next: ROOT reviews this exact consumer/writer plan and missing TT/SS minimum
bound policy. A fresh task may then implement all required readers together,
followed by same-corner actual SC2 arc/constraint/load probes and causal
missing/swapped-bound negatives before any gate.
