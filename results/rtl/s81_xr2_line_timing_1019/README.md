# XR2 tier-line timing contract

The unchanged mu1 cut3S simulator was built with XR SHA
`cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3`.
That RTL adds XR2's registered classify stage between its input register and ci_r.
The V-pin-to-line-out path is seven edges: rstop iv, dl_vb, XR vb, classify,
ci_r, rstop ci_q, ro_e/ro_w. Historical compiler/replay used six.

Before editing, four layer replay FAIL checks and source inventories were committed
under before/. Trace paths and SHA digests preserve the existing external failure evidence.

The compiler records a source-qualified timing_contract in schedule and manifest.
ctl_path, slot reservation, and both replay injection derivations use that contract.
Replay checking additionally refuses a simulator whose recorded XR source differs.
Archived programmes without the field retain their six-edge interpretation; unknown
new RTL hashes require new qualification. There is no change to RTL, golden words,
check masks, comparison strictness, or the simulator executable.

Four compatibility tests exercise legacy interpretation, the qualified seven-edge
contract, wrong latency rejection, and simulator source mismatch rejection.
The replay vehicle remains partial: encoded boundary CTL behavior is the scope;
these runs do not establish all missing operator lowering or whole-token execution.

Fleet run: /srv/opentallas-scratch/claude/codex-s81-xr2-line-timing-1019/run.sh.
Reused object: /srv/opentallas-scratch/claude/mu-die-s81-tok/out_cut_3S_idle/obj/sim.
Full matrix, reservation collision counts, and measured schedule cost follow in the receipt.
