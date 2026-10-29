HEAD kits takeover 2026-10-29 13:55.

Prior full cropped ctl/host/mesh synth jobs stopped before LEC at PORT_BIND: ctl extra32count straps/missing5raw aliases, host extra14/missing4, mesh extra14/missing6. Generic gen.py regenerated wrappers without the HEAD registered raw-export patch; the logical count strap declarations had no physical pin sites. No RTL mismatch was established by these stops.

head_source_cropped_kits.py applies the SAME existing count-strap planner and registered raw-Q patch used by head_tile_source7_kit.py to these three types. It generates only into a fresh output directory, resolves plan-relative hard-core pin tables before relocation, and refuses wrong raw source instances/Q nets. No source algorithm, cycle or gate relaxation. Generation is LIVE on intel2:/srv/opentallas-scratch2/claude/codex-head-kits-1355 (gen.otrun.log, cropped1), client341563/unit342468-1793307595, using exact source_plan/source_sidecar from codex-head-start-0828/hk5_source/source and pinned native/tool root wt/codex-head-kits-0822 (approved automatic-isnan retained). This builder is not yet a PASS or READY physical view; do not route it without source gates and visual review.

FT fixed-input census v3 terminal PASS: all9types relay-to-tap <=146.688um, all boot deltas0; old v2 also completed. Reports/plan under intel2 codex-head-kits-0822/hk6_ft/plan_clockcensus_v3.*. Parent owns batch adoption and die clock rerun.

Current-preseed copied mesh diagnostic LEC terminal KEEP FAIL:7 of16521 kept bits missing as independent named FFs plus419 compare differs. These are the existing EP ready / gearbox phase-FSM alias class under both native lanes; reuse qualified same-edge/FSM correspondences, do not drop KEEP obligations. Host diagnostic still has no terminal lec.json. Original jobs are untouched.

SerDes quarter+keep EQUIVALENT4217/4217; own reviewed trialPLACE0. No inherited CTS/GRT had been launched. Helper /root/head/kits/serdes started ONE diagnostic CTS in codex-head-serdes-1355 (unit332115-1793307569/client330588), no GRT/DRT. LEP actual V1/V2 PLACE jobs absent; coupled move5d47d7bcee8 has analytic0 at378 but needs a fresh physical kit.
