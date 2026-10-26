# STG4 receipt collection

The positive build uses `SU_LT=1` (older ML1 hard lane). This is distinct from the current die's `SU_LT=0` flat mode; matching source bytes do not qualify that parameter change. See [the scope correction](SCOPE_CORRECTION.md). Original receipt verdicts and raw hashes are preserved.

The local evidence fold passes all 527 expected outcomes with zero unknown VM delivery ages. The rel/pos/mut prospective build identities match the binaries used by their runs, source manifests, and flags. Each manifest contains 36 inputs. RTL matches assembly c0f8097f3 except qfd_dv_redstn2.sv, explicitly pinned to a4cf9a360. The VM-write probe is a bench-only overlay recorded in the receipts.

Checks on these actual collected receipts reject a changed binary digest, REFUSED identity log, empty source input list, and changed build flags. Restoring the exact receipts passes. Source evidence remains at /home/ubuntu/scratch/steward-tok-qw/run_stg4b/results/stg; original remote results are preserved. This qualifies this component source assembly only. KV/chain current rebuild and current physical-die source mapping remain open, so no complete current-die token claim is made.
