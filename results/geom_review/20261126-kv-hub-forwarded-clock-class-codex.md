# KV Hub and Hroot forwarded-clock reach, November 26

The live G5 plan `87d01254579e` and its emitted wrappers agree on all 384 forwarded-clock source aliases across Hub C/Ei/Eo/Wi/Wo and Hroot. Seven planned source legs exceed 300 µm. Only two exceed 405 µm, both on the shared Hroot type. The whole phase ledger still reports 3,587 untraced landings.

| Hroot output | Existing source | Current plan leg | Same-source projected longest segment |
| --- | --- | ---: | ---: |
| `fclk_out_cland_up` | `clk_t4` | 515.088 µm | 257.562 µm |
| `fclk_out_o_kvs_hroot_Q_o_pc` | `clk_t4` | 477.072 µm | 238.554 µm |

The viewed geometry places one downstream repeater at [1762.236, 17.010] and [1732.428, 6.210] µm respectively. Retained D29 CTS/GRT confirms the stock BUFx24 source isolation and an ordinary downstream BUFx6f on the older CLAND export. Preserve the existing launch root and stock export. At the next separately approved exact Hroot checkpoint, inspect both existing stock output networks and measure TT/FF source insertion and slew. Apply the local fit only where excessive reach persists and check the receiving clocks on all four sectors. The CLAND outputs feed Hub Eo/Wo inputs 1/0 for EN/ES/WN/WS. The PC outputs feed pc_EN/ES/WN/WS_7 via L1545/L1565/L1585/L1605_0. Retain their existing reader depth 7 and boot additional 14. The geometry study leaves production source untouched and supplies no propagated timing measurement.

Retained R6 read-only DP confirms the same near siblings. Eo ft12/ft13 are 360.448/370.496 µm on t4, Eo hp_fault is 296.885 µm to its output buffer plus 2.931 µm on the final leg from root `clk`, and Wo ft21 is 403.648 µm on t3. Keep those clocks on their existing roots. Hub split mission timing, Wo aisle limits and PC ingress timing remain independent holds.

Replay and report are on epyc8 under `/srv/opentallas-scratch2/claude/kv-allfix/a5t9/hub-class-1126/`. Read `hub_forwarded_reset_census.json` first for the complete alias and flagged-leg census. `hub_forwarded_reset_census.py` performs the scan. `hroot_two_fclk_same_source_study.json` and its companion geometry PNG record the same-source fit. `hroot_4_cts_upstream.tsv`, `hroot_5_1_grt_upstream.tsv`, and `eo_dp_upstream.tsv` record retained native paths. `wo_dp_upstream.tsv` is in the same directory on intel1.
