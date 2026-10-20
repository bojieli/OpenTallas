# HWIN namespace NS47 four-state -- full rerun, terminal (S81-MUBUF4, 2026-10-20)

The original NS47 job (four_state_ns47_01, ot-epyc8 unit oth-ubuntu-2266279) had phases 0-5 PASS when ot-epyc8 was deleted
(10-20 02:26); its directory was not archived. Rerun with the identical immutable input src_06f8ca8dc (de061577f package,
run_campaign.sh four_state, FOUR_STATE_NS=47) on ot-epyc5 unit oth-ubuntu-3308118-1792488588, output
/srv/opentallas-scratch/claude/s81-hwin-private-package-1019/four_state_ns47_02. Actual client line: `RAN on ot-epyc5: exit 0`
(CAMPAIGN_EXIT=0 printed by the wrapper; the runner is set -euo pipefail with bare grep checks).

- all 11 occupied-reset phases 0-8, 90, 93: MUWIN PASS, starts 188 / fires 188 / expected 188 each;
- primitive probe PASS cases13; X causals: PAYLOAD and CONTROL each EARLY_X_CAUSAL c1132 valid1 fresh1 (fatal, rc != 0);
- original vs projected trace pairs seeds 1/19/313 byte-equal (Verilator 5.050).

MU.TOK.DS4 NS47 phases 6-10 (the remaining open part) are therefore PASS, with phases 0-5 re-confirmed on the same run.
