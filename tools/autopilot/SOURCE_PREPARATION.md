# Source inputs and current-wave recovery

Recipes can read a historical commit even when the current source tree contains a
file with the same name. `source_history.py` packages the exact declared inputs,
including per-file `files_at` overrides. It includes the path trees and blobs needed
by `git show`, with their immutable Git identities.

On the authoritative hub repository:

```sh
python3 tools/autopilot/source_history.py pack \
  --source REPO --revision SOURCE_SHA --authority REPO --out SCRATCH/history
```

Copy the reported pack to the new source host, then install its objects:

```sh
python3 tools/autopilot/source_history.py install --repo NEW_SOURCE --pack PACK
```

The existing `source_follow.py` worker performs this packaging and transfer while
preparing its new snapshot. It keeps launching from the previous source. Missing
historical inputs remain explicit in the report; availability reporting adds no
sign-off gate. Pack installation changes no refs, RTL, index or constraints.

For a read-only operational report:

```sh
python3 tools/autopilot/autopilot.py reconcile-wave --root COORD/autopilot \
  --required-items required_items.json --repo REPO --out current_wave.json
```

`required_items.json` maps dies to current plan type/core names. Without that list,
absence from the stage cache leaves ownership unresolved. The report distinguishes
exact terminal AP jobs from stale cached `RUNNING` labels and preserves live or
unknown alternatives, including generation and jobs spilled to another host.

Recovery suggestions require `--approved-fixes` entries such as:

```json
[{"die":"s81","item":"slice_station__t30","attempt":9,
  "sha":"abcdef777","scope":"src","reason":"measured source-insertion class fix",
  "live_checked":true,"clear_hold":true,"lane":"CODEX-WAVE"}]
```

The operator supplies `live_checked` after checking private jobs too. The helper
checks fix ancestry against the configured source (`src`) or `origin/main` (`hub`).
It emits proposed cache corrections, hold changes and recovery rows; it writes no
job, state or configuration file. Reviewed recovery rows use the existing
`kit_wave_pending.tsv` path. Superseded rows do not produce retries.
