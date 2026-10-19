Current-main KV alias/declaration validation, 2026-10-19

This packet runs the real current-main producer, fleet Yosys and binder on a single relay connectivity fixture using the actual frozen 5f2 RTL and selected views. It also runs the existing parameter-declaration fixture, whose two-pin bodies and fixture views are explicitly diagnostic. Neither fixture qualifies arithmetic, native timing, reset fanout, PG safety, or production adoption.

Baseline: efae17de2128f3813aff8cf76226e8be8d60ea97. Candidate source: 716f993f9, exact three-file d19 port, producer/parser SHA values retained in summary. No predecessor helpers, diagnostic-autoprofile enablement, or runtime changes were imported. The artifact_identity/preserve/verify_bound suffix remains byte-identical to baseline.

The original alias fixture from 40208beeb/4434fa90e calls face_land_rtl, an API absent in current main. Its 13 setup errors on both shapes are preserved under evidence and are not causal refusal evidence. The adapted fixture uses the existing FACE_LAND_TILES selected master and actual RTL-file existence assertion, while preserving the actual face_land_require_closed selection, Yosys, producer and binder calls. Both shapes receive identical adapted fixture bytes.

Actual inputs: frozen source root wt-kvs14r-cda9d9f9d-gen8v4mub, generated source 5f2ce19bc and driver cda9d9f9d. Current-main tools and RTL are separately archived and hashed, including current import dependencies; frozen views are read-only inputs. Per-case actual source/view and produced output inventories accompany the alias run. No full ledger continuation, routing, gate, native receipt positive, or production publication was performed. The original live v4 and offline 912-row proposal remain strict REFUSE.

Commands and per-suite exit codes are retained. The ot-run shell exit only means all requested suites finished; use each suite result.json and exit_code for actual outcomes. Original setup failures and actual baseline semantic failures are retained separately from candidate results.
