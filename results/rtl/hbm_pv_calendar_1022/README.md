HBM PV command calendar correction, 2026-10-22
============================================

Draft: full 181-check replay is running, so this packet is not ready for ROOT promotion. The corrected programme passes all 32 exp/P numerical checks reached in the 6,000-edge replay. Its two remaining failures are the deliberately incomplete full replay and the SM node that has not executed yet. This is a component probe, with no native layer, token, physical closure or rate qualification.

The original r18 programme issued tree_cmd one edge after the lanes' ro_v. Moving tree commands one edge earlier removes the sticky pre-tree fault. The reducer must also follow the pre-tree's valid pulses. The original paused HBMc compiler used PT_RED=80, appropriate to the generic OPR1 slice plus OPR1 join. The actual selected source has an OPR1 slice and an r13 OPR0 join. Their measured tree-to-reducer command age is 77. The fresh main compiler's legacy default is 69; that default stays unchanged for historical profiles.

The minimal Verilator 5.050 vehicle uses the actual flattened selected modules and measures input edge 8, slice output edge 66 and join output edge 86. The selected qcore captures red_cmd before sampling the external operand on the next edge, giving 86 - 8 - 1 = 77. The receipt pins both module names and both complete source-file SHA256 identities. Changing either source identity, the selected module or the declared measured age fails closed. A different source pair or different instance parameters requires its own measurement; this receipt does not qualify r18h3/r18h4/r19b by alias.

The emitter accepts `--su-pretree-profile <receipt.json>` alongside `--su-lower2`. It validates the receipt and passes the measured age through both KIND1 reductions and the scalar B transfer. The current-chain wrapper must select a receipt that matches its actual source manifest and instance parameters. An unknown current pair must not silently inherit the legacy default. Expected arithmetic, golden reduction order, inputs and check masks are unchanged. Actual RF export timing metadata follows the earlier commands; RF reads, drains and programme occupancy derive from the selected profile.

| Preserved replay | Reached numerical checks | Result |
| --- | --- | --- |
| Original programme, old profile 80 | 32 failed | Original sticky pre-tree fault |
| Tree commands alone advanced | 32 failed | Sticky fault removed; scalar/exp values remain wrong |
| Tree and reducer graph advanced, old profile 80 | 32 failed | Selected source age still wrong |
| Genuine re-emission with measured profile 77 | 32 passed | Full replay and SM node still pending |

Original programme occupancy was 803 serial edges. The measured-profile programme uses 794: attend.max 243 to 240, attend.exp_sum 472 to 466, attend.bf16_p 86 unchanged. This is a programme occupancy comparison, not a token rate claim. Final validated-loader emission has byte-identical quarter commands and SRAM configuration to the fixed full replay already running. `source_comparison.json` verifies unchanged real input words, expected arithmetic and masks for records 20, 21 and 23.

All work runs through ot-run. The immutable replay binary is identified in `binary.before.sha256`. Source and input history remain untouched at gold1 `/srv/opentallas-scratch/claude/hbmc-token2/pv_r18_probe`; new recipes, re-emissions and logs live at `/srv/opentallas-scratch/codex/hbm-pv-calendar-1022`. The same binary runs all variants. Full fixed replay unit `oth-ubuntu-8293-1792731784` runs 86,000 stream edges with 181 checks, authentic score/KV inputs, no preloaded exp/P, and the existing real 512-value SM node scoreboard. Its result will be appended without overwriting the failed variants.

Minimal exact-source latency measurement: unit `oth-ubuntu-4139789-1792731316`. Fixed 32-check replay: `oth-ubuntu-4191760-1792731737`. Final profile validation, three causal negatives and byte-identical re-emission: `oth-ubuntu-48092-1792732023`. Syntax and diff checks pass. No RTL, masks or timing constraints were changed.
