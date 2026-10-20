# KV selected native parameter qualification: takeover-3 pickup

Snapshot: 2026-10-19 17:43 PT. Evidence only; no RTL, helper, parameter profile, native receipt, clock, reset duration or property was changed. All original remote proof work remains intact. The source-map diagnostic alone was run on the fleet (ep6 units 1571817 and corrected 2039722, both exit 0); no replacement equivalence proof was launched.

## Actual terminal results

The six-reset-edge, paired-initial healthy ktree base **fails**. Its D-rewired native mutant also fails, with a different trace. The prior lane's expected positive result did not happen.

| Frozen run | Native proof rc | Checked failing steps | Wall | Peak RSS |
|---|---:|---|---:|---:|
| `base_ktree` | 1 | 7; steps 8–10 pass | 47:38.40 | 25,305,160 KiB |
| `base_ktree_mut` | 1 | 7, 9, 10; step 8 passes | 49:26.75 | 25,319,284 KiB |

Raw trigger waves are `41......0..` and `41......01.`; index zero is the WaveJSON preamble. The original six low-reset target steps and checks at 7–10 are unchanged. Each script contains exactly 10,864 initial gold/native equalities. Full logs, proof scripts, CEX, stderr/time and proof rc are preserved losslessly under their run directories. `gzip -cd FILE.gz` reproduces each original byte stream. Yosys emits some invalid JSON escapes in raw CEX names; the original decoder preserves the raw file and escapes those names only in memory.

The CEX was generated without `miter -make_outputs`; the failure trigger is observed, but this packet does not identify a particular failing comparator from that CEX. Claude already launched an additional output-observation diagnostic at 17:23; it is progressing. Do not infer that the original 213 independent-initial-state replay mismatch is the new paired-initial mismatch. The mutant is not an independently qualified causal control while the healthy proof fails.

The only fresh terminal positive profile at this snapshot is `ot_qwen_tp8_pv_wide_ctl_tb`, 916/916 induction comparisons and a six-reset-edge paired-initial base PASS. Its MUT=1 negative has 39 unproved comparisons. Their full audit JSON files are included. Proof command exit 0 for the expected negative means its expectation was met, not that the mutated design was proven. No broad native-qualified receipt was generated from this pair.

## What the source map establishes

`source_map/state_cone.py` reads the actual ktree `gold1.json` and frozen `joint_prelude.ys`. It excludes `S__proof_*` observations when counting native-corresponding state. The source contains **11,254 register bits**, with **10,864 paired initial source bits** and **390 source-only bits**. Of the source-only bits, 95 are the explicitly observed metadata and 295 are other omitted state. Observing source-only metadata is not an initial pairing to a native register.

Thirty of the 390 source-only bits have syntactically identical D, clock and flop type to retained source state: the two `u_cb.g_r.r` difference bits 0 and 27 in each of the 15 adders, compared with the kept HSPLIT `g_hs.hq` copies. This identifies an optimization/correspondence candidate. Equal D does **not** imply equal arbitrary power-up Q, so the report does not assume their initial equality or claim that these thirty explain the CEX. The other 360 source-only bits are not covered by this same-D observation.

For representative `g_n[0].u_a.u_cc.g_r.r[64]`, the six exact direct data predecessors (`u_cc`, `s2_code[31]`, `u_cd`, `u_cb`, `s1_code[31]`, `u_ca`) are already paired. The chain then reaches a combinational bypass-code function. Merely adding a missing `cc` or `kp_r` name equality cannot explain or repair this paired-base failure. Bits 31/32 reach combinational exponent logic after two direct predecessor flops; that logic was not replaced with a guessed dependency graph.

The native DFFHQN model uses `IQN <= ~D`, `OT_S = ~IQN`, output `QN = IQN`. The exposed correspondence therefore has D polarity. No Q/QN inversion fix is justified by this source inspection. Source hashes and original proof input hashes are recorded in `fleet_snapshot.txt`.

## Genuine live work, preserved

All entries below are on **ot-epyc6** under `/srv/opentallas-scratch/claude/kv-params2-1019/`; exact start time, elapsed time, RSS, command, cwd and actual log tails are in `proof_processes.txt`.

| Native PID | Work directory | Actual stage at snapshot |
|---:|---|---|
| 224474 | `base_lane8` | SAT, 38,961,962 variables / 103,257,357 clauses; ~28 GiB RSS |
| 2306049 | `base_ktree_diag` | Existing `-make_outputs` diagnostic; adding exposed gold state |
| 1702958 | `work/ot_qkh_ktree` | `equiv_induct`; observed metadata remains jointly compared |
| 1706728 | `work/ot_qkh_lane8` | `equiv_induct`; observed metadata remains jointly compared |
| 1793096 | `work/ot_qwen_tp8_pv_join_t` | `equiv_simple` on actual adder state |
| 402574 / 391828 | `work/qkd_seq_xs_s_pos` / `_mut8` | `equiv_simple`; FIFO range observations are comparisons, not assumptions |
| 3334304 / 3328722 | `work/pvslice_pos` / `_rp0` | Gold state construction with shared stateful SRAM model |
| 3168847 | `seqxs` | Existing stronger-induction diagnostic, distinct from the current range-observation pair |

No process was restarted or cancelled. Original ktree/lane8 unforced independent-initial bases, replay failures, and parameter NOT PROVEN records remain historical failures; this packet does not supersede their scope.

## Exact next pickup and admission

Read existing terminal files without launching a duplicate:

```sh
ssh ot-epyc6 'cd /srv/opentallas-scratch/claude/kv-params2-1019; for d in base_lane8 base_ktree_diag; do ls -l "$d"; tail -c 600 "$d"/*.log; done; find audits -maxdepth 1 -name "*.audit.json" -o -name "*.rc"'
```

When the existing ktree diagnostic terminates, preserve its original rc/log/CEX, decode **all** failing outputs at step 7 and the mutant's later steps, then trace each through the exact retained/source-only initial relation. Prove any new relation from actual source equations and native correspondence. Do not add a reset edge, drop an error/metadata comparison, mask under valid-low, equate independently unreset replicas, or strengthen an assumption to obtain a positive result. If the actual source/native relationship requires a different refinement domain, name that domain and keep unforced cold-reset/first-use qualification separate. An implementation change needs its own complete source/latency/reset cost and causal tests.

GEN9 remains blocked on a true selected-source/view/parameter profile. The `qkd_astk_rly_296_fl` MUT=0 wrapper needs a receipt tied to its actual new native view after route closure; the intentional DIAG alias fixture supplies no receipt. The sibling GEN9 owner handles explicit lane8 ADD_LAT=7/LTW=12 unused-role compatibility; no duplicate role-helper change was made here.

The private KV-PARAMS2 receipt generator currently sets `native_qualified=true` for a matching `proven` audit even when the optional reset base was absent. It was not invoked here and is not present in this worktree's origin/main baseline. A future source owner must require the proof/domain obligations before publishing a production receipt. There is no production-helper tightening in this evidence packet because adopting an incomplete private generator would broaden this task and could admit an incorrect qualification domain.

At 17:45 PT the coordinator relayed CLAUDE IS BACK. The proposed private receipt-admission guard had not been written or launched, so no patch or new test/job was started. Its next implementation should reject induction-only audits, require explicit actual reset/initial-state proof-domain evidence, reject conditional paired initial state as universal cold qualification, and test the receipt path against positive/current identity plus missing-base, failed-base, conditional-pairing and source-drift refusals. This is an unimplemented proposal, not a tested tightening.
