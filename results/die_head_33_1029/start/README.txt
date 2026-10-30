DIE-HEAD-33 step 4 (START + clock/CA regen on src25m), Thu Oct 29 05:49:10 PM PDT 2026. Plan = intel2 die-head-32/src25m/source_plan.json sha256 a7435da4
(25-type source + hk5m). Data intel2 /srv/opentallas-scratch2/claude/die-head-33/start. Tools = origin/main 01ddd2e80d5.

ESTIMATE (CHECKED): src25m vs hk5 (DIE-HEAD-26 plan_hk5.json): 357/357 partitions identical (name/type/origin/orient), lanes identical,
every type clock.tap_um identical; differences = source-form fields (edge_clocks, landing_contract, start_capture_um, ports, reset in_sites).
ot_clk reads partitions + tap_um + region map + feed only -> die clock tree expected unchanged.  START: only hd_tile start_capture moved
(362.4,354.208) -> (518.4,862.944); on the old Codex leaf plan (codex-head-start-0828/hk5_leaf2) all 264 hd_tile leaf stages sat 8.6 um
(manhattan) from the old capture and would be 673.4 um from the new one (264/264 > 405) -> the START leaf plan must be re-planned on src25m.

(a) CLOCK (clk/, ot_clk kit head_src25m.yaml = DIE-HEAD-26 head_hk5.yaml with plan -> src25m; run2.sh, unit oth-ubuntu-944439) CHECKED:
    ctree.v / tree.json / ctree.tcl byte-identical to DIE-HEAD-26 kit_h5 (sha 9250931c / 9f752e26 / ad83a0a6).
    die GRT0 incl clock (50 it): overflow 0 TT + FF (usage 0.43 %, M8 0.01 %) - grt_s25_{TT,FF}.txt.
    duty 0/739 outside 45-55 TT/FF (48.7-51.5 % / 48.2-50.9 %), MPW est fail 0;  spread x1.05 75.8 TT / 62.3 FF;
    spread incl OCV + shared droop 90.7 TT / 79.2 FF, stated 105.7 / 92.3, 0 regions > 150  -> clock check PASS, same as hk5.
    Routed tap arrivals (arr_TT/FF) = codex-head-ca-0840/ca2/proof tap_arrivals late_ps, 739/739, max |d| 0.0 ps TT and FF.
(b) START re-plan on src25m (leaf/; leaf.sh = Codex hk5_leaf2.sh steps 1-5, only the die plan/capture sites changed; unit oth-ubuntu-1085964):
    clock-only model, hop 360: 1582/1582 START edges clean (hk5_leaf2: 1607/1607), min sync dist 164.2 ps (131.2; main now has the
    aa6c84c8e virtual-tap class-B fix), skew limit min 137.7 (104.7); CA 427 crossings, 0 fail, worst margin 105.2 ps (>=100, model);
    bind verify 0 window violations; emit 1226 stages / 4786 FF / 357 die outputs; last hop stage->capture: hd_tile 264 x 8.6 um,
    worst any type 316.1 (hd_spn_eshim_tx) < 405.  CHECKED (numbers read from plan.json/start_stages.json).
    DATA-aware (data200.sh = Codex 1355 plan.sh, model-only dd, hop 200, unit oth-ubuntu-1125375 exit 1 = plan fails):
    3001 edges, 2501 clean, 500 FAIL = 357 native leaves (model-only dd fail closed) + 143 virtual; CA 427 0 fail, 105.2 ps.
    Summary identical to the Codex hk5 run (hk5_data_200) -> the src25m capture move does not change the data-aware outcome.
    plan_summaries.json lists every failing port.
(c) NOT DONE: physical START vehicle rebuild (map/pack/place/local clock-entry BUF8/GRT) - the vehicle tools used by HEAD-START-2
    (head_start_local_clock.py, head_start_route_overlay.py; codex/head-kits-0251@735403ad0) are NOT on main; die_sta_related on
    measured dd needs that vehicle (102 virtual ports) and native-leaf receiver measurements in routed kit views (351 ports; Codex 1355
    missing453.json). The clock-only plan is known not to be enough (HEAD-START-3: data delay 0.14-0.60 ns not modelled).
