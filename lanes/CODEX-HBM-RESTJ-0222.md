# Joined RESTJ redesign — Codex 2026-11-08 02:22 takeover

## CODEX notes

Collected actual completed JOINED3D89 (found by Q2NF lead): intel1 `/srv/opentallas-scratch2/claude/die-hbm-89/restj/build_JOINED3/kits/ot_hgi_sfu_split3_ctl_rest_1c_f057777f78e4-JOINED3D89`. It is NOT SIGNED: TT -58.99 ps / 83 setup endpoints, FF -179.07 / 5947 (5790 ports, 157 internal; internal worst -14.44), DRV0, DRC0, antenna0, synth LEC EQUIVALENT. No ECO: setup exceeds near-miss limit.

GEOMETRY viewed actual PLACE density (`run/layout_review/place/density.png`, local `/tmp/restj_density_0222.png`), plus Q2NF lead's route heatmap: no macros, sparse interior, long E pin-edge clump at roughly60–70% local density, W-to-centre logic tree. CLASS: long single-driver control fanout into VM wide write data mux. TT worst `_0886_[16]` (lane0 registered drain sector bit16) -> `_0896_[252]` (lane1 VM write data), large repeated buffer fanout chain. Reset-recovery `_0919_ -> _0922_` is +29.99 and is NOT the failing setup path; no reset-only rebuild.

REDESIGN in progress, cycle neutral: lower extracted rest leaf into one-bit generic FF/mux cells, duplicate the four measured drain-sector selector FFs so each copy serves at most8 bit-cell consumers. Clone same entire FF function/clock/reset, keep each clone to prevent remerge; no logic, interface or cycle changes. Targeted estimate about280 extraFF, far below150k cells. Broader conservative companion can cover all high-fanout FFs if measured generic census supports it. Preserve existing joined scalar_data128/load4/address96 +1 cycle; no old data-only receipt inherited.

Own source branch `/home/ubuntu/codex-restj-0222-src`, `codex/hbm-restj-local-0222`, base main289149dea5. Transform `results/codex_hbm_restj_0222/clone_selectors.py`. Own lower-only run intel1 `/srv/opentallas-scratch2/claude/codex-restj-0222/{input/core.sv,lower.sh,clone_selectors.py}`; local ot-run client3630967, log `coord/tmp/codex-restj-lower-0222.log`,16GB2T. Last observed memory wait. This is generic elaboration/structural census, no P&R or STA. Next: collect exact clone count; full source equivalence + clone mutant; commit source/factory; one PLACE pilot and view before CTS.

OWNER? none newly raised.

## CODEX notes — proper joined-mode follow-up

Own branch pushed `codex/hbm-restj-local-0222@18ea1cb765` (predecessor193d1efccd). It carries the exact existing JOINED3D89 source deltas with the canonical wrapper name restored before hardening, selector-copy factory, full leaf equiv recipe, and a fail-fast requirement for the joined `__p56_ctl` export. No adoption or POR change.

First export failed before P&R on my clone cell/net names sharing one Yosys namespace; v2 uses distinct `_ff` cell names and exports cleanly. Exact census: four selectors /16 added FF /maximum8 immediate consumers per copy. The earlier280-FF estimate was too high because combinational decode nodes are shared. Broader wire/control reach still requires actual PLACE review.

Mechanism gate PASS: four-step SAT after the first edge, arbitrary selector and bank data. Wrong-D clone mutant is caught (`proof did fail`). Existing proof logs E6 `codex-restj-0222/mechanism_{clean,mutant}.log`.

Correction before any P&R: the first baseline generic lowering omitted `OT_REST1C_SCALAR_OPIPE_JOINED`, so its generated leaf lacks `__p56_ctl`. Its full proof is a baseline-mode diagnostic only, never current joined qualification. Stopped only my now-obsolete exact container `codex-restj-full-equiv-0222` (healthy jobs from other lanes untouched); failed/baseline files retained. New helper refuses a graph without that port.

Proper joined-mode lower/export/full-equiv now running on E6 `/srv/opentallas-scratch2/claude/codex-restj-0222/joined/`, own local client3685666, log `coord/tmp/codex-restj-joined-0222.log`,16GB2T. It reads the exact old source with the joined define, folds constant logic before one-bit lowering, then adds same-cycle selector copies. No P&R/STA yet. Existing tiny mechanism proof is reused (same clone operation and mutant); the full joined leaf proof is new and required.

Resource move: cancelled ONLY my unadmitted intel1 export client3645374, explicit NOT RUN receipt in `codex-restj-export-v2-0222.log`; staged current source to E6, where memory was available. E6 scratch2 was63GB, so any physical pilot should go to roomier intel1/E4 after the proof is read. Source-only base kit has been collected separately, with no old run/LEC/signoff artifacts copied into a new physical context.
