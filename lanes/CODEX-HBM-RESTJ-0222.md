# Joined RESTJ redesign — Codex 2026-11-08 02:22 takeover

## CODEX notes

Collected actual completed JOINED3D89 (found by Q2NF lead): intel1 `/srv/opentallas-scratch2/claude/die-hbm-89/restj/build_JOINED3/kits/ot_hgi_sfu_split3_ctl_rest_1c_f057777f78e4-JOINED3D89`. It is NOT SIGNED: TT -58.99 ps / 83 setup endpoints, FF -179.07 / 5947 (5790 ports, 157 internal; internal worst -14.44), DRV0, DRC0, antenna0, synth LEC EQUIVALENT. No ECO: setup exceeds near-miss limit.

GEOMETRY viewed actual PLACE density (`run/layout_review/place/density.png`, local `/tmp/restj_density_0222.png`), plus Q2NF lead's route heatmap: no macros, sparse interior, long E pin-edge clump at roughly60–70% local density, W-to-centre logic tree. CLASS: long single-driver control fanout into VM wide write data mux. TT worst `_0886_[16]` (lane0 registered drain sector bit16) -> `_0896_[252]` (lane1 VM write data), large repeated buffer fanout chain. Reset-recovery `_0919_ -> _0922_` is +29.99 and is NOT the failing setup path; no reset-only rebuild.

REDESIGN in progress, cycle neutral: lower extracted rest leaf into one-bit generic FF/mux cells, duplicate the four measured drain-sector selector FFs so each copy serves at most8 bit-cell consumers. Clone same entire FF function/clock/reset, keep each clone to prevent remerge; no logic, interface or cycle changes. Targeted estimate about280 extraFF, far below150k cells. Broader conservative companion can cover all high-fanout FFs if measured generic census supports it. Preserve existing joined scalar_data128/load4/address96 +1 cycle; no old data-only receipt inherited.

Own source branch `/home/ubuntu/codex-restj-0222-src`, `codex/hbm-restj-local-0222`, base main289149dea5. Transform `results/codex_hbm_restj_0222/clone_selectors.py`. Own lower-only run intel1 `/srv/opentallas-scratch2/claude/codex-restj-0222/{input/core.sv,lower.sh,clone_selectors.py}`; local ot-run client3630967, log `coord/tmp/codex-restj-lower-0222.log`,16GB2T. Last observed memory wait. This is generic elaboration/structural census, no P&R or STA. Next: collect exact clone count; full source equivalence + clone mutant; commit source/factory; one PLACE pilot and view before CTS.

OWNER? none newly raised.
