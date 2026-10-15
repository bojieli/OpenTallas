# Live element evidence registry

The canonical live table is `/api/elements`, assembled by `elements.py` and displayed by `index.html`. Its generated Markdown view is `ELEMENTS.md`. Closure-loop jobs continue to determine physical closure categories and measured timing. To register an implemented block before routing, add a uniquely named, committed JSON document under `results/fleet_viz/element_registry/`; do not replace prior documents or verdicts.

Documents contain `schema_version: 1` and a `records` array. Each record requires `element`, a canonical `target` (`Qwen ROM`, `DeepSeek ROM`, `HBM accelerator`, or `Other`), and `source: {commit, paths}`. Commit is a Git hexadecimal source identifier of 9–40 characters; paths is a nonempty array. Record `recorded_at` in ISO format so successors sort chronologically. The filename breaks ties.

Additional fields are `owner`, `description`, `implementation`, `model`, `exactness: {positive, negative}`, `physical`, `dependencies`, and `integration`. Each qualification field contains `status` and `evidence`; physical evidence should state actual measured corners and the boundary/clock qualification scope. Evidence entries should identify committed paths and the source commit or remote immutable artifact identity. Use explicit `pending`, `missing`, or failure statuses when a gate is incomplete. Do not equate a simulation pass, synthesis estimate, or pathfinding route with qualified integration or closure.

The API exposes the latest record as `qualification` and all additive records as `evidence_history`; the UI and Markdown show a compact qualification summary. Registry-only rows use `implementation recorded (no physical job)` and have no timing values. Existing job verdicts retain their categories even when registry evidence is newer. A physical job and registry entry may refer to different source versions; consult the evidence before claiming adoption. Malformed documents appear in `sources.registry_errors`. Recording reacts to evidence changes as well as physical status changes.

After adding a block, fetch `/api/elements` and verify that its canonical element name and source commit occur in the row, and that unfinished correctness, physical, dependency, and integration obligations remain explicit. The collector refreshes every minute. Share-safe API responses retain summary counts only.

## Top-down element list from the current die contracts (registry-sync 2026-10-15)

The element list is no longer only "blocks that once had a closure job". `die_contracts.py` reads
`results/fleet_viz/die_contracts.json`: one entry per die (Qwen compute, Qwen KV/system, S81, HBM) naming the
machine-readable sources of its CURRENT contract revision (die port-bind JSON, hier-contract slots, pin-contract
indexes, native-join nodes, the canonical `.f` file list, another stream's registry file), plus the replacements
(`retire`) and additions (`add`) the die lead recorded in the die log, with evidence. Every die master and its
physical leaf hierarchy (contract leaves, and modules instantiated under a master's RTL that are registry elements)
becomes an element annotated with `dies` (design, revision, role, parents), `owner_stream` (STREAM_CHARTERS
patterns per die) and `native` (the die port-bind verdict or contract qualification, where recorded):

- contract element with no closure job: `not started (open)` (registry-only evidence rows of contract elements too);
- retired by a contract: `superseded`, `superseded.source_evidence` = the contract;
- for a die whose contract is `complete`: a non-closed row with no live job that no current contract contains is
  `superseded` with the contract as evidence; closed or live rows outside every contract are kept and flagged
  `contract: not linked to a current contract master` (their leaf link may only exist in a generator composition);
- `designs` in `/api/elements` (also share-safe) and the fleet header give per-die closed / open / not started.

Die leads: when a contract revision lands, update that die's sources/retire/add in `die_contracts.json` (commit by
path); the collector picks up origin/main within a minute. Other streams register masters through a registry file and
list it as a `registry` source rather than duplicating rows.
