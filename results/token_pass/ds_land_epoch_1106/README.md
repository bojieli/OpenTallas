# Static landing epoch origins

The recovered pinned 11-01 S81 native diagnostic measured 833000 fs, then aborted before KS ingress at `s_7S_LP.u_u_lnl1.u_kn.u_r.g_chunk[68]`: slot0 epoch4 expected0. The unchanged protected hierarchy was observed through a read-only C++ main; no RTL force or assertion suppression was used.

The station writer takes `rs_k=lpc_i0_q[0]`, while its reader takes `rs_n=rst_n`. Writer `rq` rises at cycle37, reader `rq` at43. Thus the writer counter is six edges ahead when the reader starts. D4/K2 with independently zeroed counters selects the wrong slot as well as checking the wrong epoch. Changing K or suppressing the check does not repair the transport.

`ot_pl_land_local_r.EPOCH_BIAS` describes this static counter-origin difference modulo2D. It defaults to0; the old reader is kept as a frozen lockstep reference in the bench. The bias rotates the initial onehot pointer and translates the expected epoch. Local `rc` and `warm` still measure reader age. There are zero added data/pin cycles; K2 still captures a word two edges after its writer capture, visible to the downstream consumer on its third edge.

Allowed contracts: D is a power of two >=2, AW matches D, 1<=K<D, 0<=EPOCH_BIAS<2D. D4 therefore permits0..7, D8 permits0..15. Bias is a bind-time constant, not dynamically inferred from data.

The smallest proof compares arbitrary32-bit LFSR payloads to an independent two-edge history. D4 andD8 pass at equal origins and at both +6/-6 origins with the corresponding bias. A wrong bias of5 fails payload comparison. The actual +6 origin with bias0 reproduces the original epoch4/expected0 failure. Invalid D6 and D4 biases8/-1 are rejected. All12 expected outcomes passed in ot-run epyc2 unit3329383-1793954812,8GB1T. Logs remain at `/srv/opentallas-scratch2/claude/codex-ds-land-origin-1106`.

Replay via `python3 tools/s81_dv/check_pl_land_epoch.py --work NEW_SCRATCH_DIR --verilator VERILATOR` under ot-run. No die bound adopts a nonzero bias in this change. Each direction needs a receipt deriving both reset release ages from its actual bound source before adoption; observed six at this station is not a blanket die setting. The bias must propagate through the vector-reader/parent ABI when that receipt is integrated.

A common reset origin also passes the core vehicle, but feeding the K-side control reset into the N-side reader forest changes reset routing and source assumptions. Static bias preserves the existing physical reset forests. Physical review and timing closure remain required for any adopted nonzero configuration.
