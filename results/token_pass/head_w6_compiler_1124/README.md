# HEAD compiler witness on W6 (HEAD-R18, COORD ruling 2026-11-24)

`tools/s81_dv/layer_prog/head_root_boot.py` now pins the live W6 plan b3507e628de6 (it was pinned to l48uo f140216c).
The status is still SOURCE_WITNESS_ONLY: there is no physical START, HOST, PMA or mission date, and no token was run.
The l48un and l48uo `qualify*.py` scripts now fail against these pins on purpose; their records stay as evidence.

## Inputs (none of them is on main; `current_source_manifest.json` records each sha256)

| File | sha256 (12) | Source |
|---|---|---|
| source_plan.json | b3507e628de6 | HEAD-WEST prep_r18w6 (live W6) |
| source_sidecar.json | ba968452ea5a | W6 sidecar with the lep0N_w status-network fix (HEAD-WEST w6_live/sidecar_w6_coll.json) |
| start_stages.json / .sv | b0970ff4a93e / 8ac30434ad22 | START tree re-sited on the W6 type raw exports (`start/`) |

How the START tree was made (`start/start_w6.sh`, tools rt c0b6e2d03408):
1. `unpatch.py` reverts the 11-22 provider_e1br to the canonical emit form (one `rst_raw_n`, 9 relays undone).
   It proves the reversal by re-applying the provider's own reset rows, which reproduces the provider byte for byte.
2. HEAD-START-R16 `start_reset.py` sites every stage reset on the nearest declared W6 type raw export.
   That gives 969 ports and 9 hops over 405 um, and the settle is max(88, span 72 + 4) = 88.
3. `relay_over.py` adds one die-level relay per over-reach stage (max half hop 286.2 um).

The stage geometry is unchanged, because the NF15f die_clock has not changed since 11-21. The 1389 stages are exactly
the sidecar's 1389 `st:` regions. Compared with provider_e1br, 10 stage resets moved, 3 of them onto the lep0N_w
split exports. The root stays b0 on sp3 u_rrl_208 (raw release 24), with `ot_dp_landing_root #(.SETTLE(88))`.

## Measured (make_bundle.py, the 10-30 accountant arithmetic)

| Bound | W6 recomputed | sidecar boot_budget (still l48uo) |
|---|---:|---:|
| root START upper | 113 | 110 |
| part START max | 365 | 382 |
| ready-or-fault upper | 5851 | 5861 |

The root START bound is +3 because the root raw release moved from 21 to 24. The witness uses the recomputed bounds.
The settle is 88 in both the RTL and the sidecar (rst_n >= 64 holds). The plan field
`clock.landing_network.count_aligned_bind.root_settle_cycles` is a stale copy that says 64; row
HEAD-ROOT-SETTLE-COPY-1 corrects it.

## Rebuild

    start/start_w6.sh                                   # START tree (E11 lane paths inside)
    make_bundle.py PLAN SIDECAR STAGES_DIR BUNDLE
    qualify.py REPO BUNDLE OLD_L48UO_BUNDLE OUT          # OT_HEAD_E1BR_PROVIDER=<provider_e1br> adds that control
    qualify_pipeline.py REPO BUNDLE RUN OUT.json

## Open

- The SPN eight-tap plan 5fb8ca47357d renumbers the hd_spn relays, and the root reset source is an hd_spn relay.
  When that plan is adopted, `start/start_w6.sh` must be rerun on it and the witness re-pinned.
