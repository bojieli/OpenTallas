Current bound S8 x-delivery consumer gate

This vehicle carves the actual current S8 tap, four xhead columns, south face register and 32 XS leaves for SID0. It replays captured actual E5 BF16 payloads; no arithmetic VM/SFU is included. The full current 12-slice producer baseline was run once and had numeric rc0, all 12 heads clean, x_tap=1/d_head=21. The carved replay must exactly match its SID0 CW and XL traces.

main_pins.cpp observes actual registered HR GO/XPF and xhead GO. Every case asserts that the requested control edges reached HR and records xhead GO. Each case runs fresh with a unique event/log/pin triplet; no verdict cache. Original failed explorations are preserved on the run host.

run.py selects the contiguous passing XPF tail within the finite legal lead envelope 0..16 at generous GO=24, then searches the contiguous passing GO tail through +24 at that exact selected lead. It expands the lower GO envelope only until an observed failure. This finite envelope does not establish global monotonicity. Adjacent GO-1 and XPF-1 and ISA-base-as-ME-base controls must all fail while nominal passes. Earlier binary calibration incorrectly selected an isolated negative-XPF alias and mixed GO thresholds from different arm leads; it is not qualification.

Run host intel2: /srv/opentallas-scratch2/claude/codex-xh-consumer-1027
Final run: otrun_gate6_pins.log and result_final_pins6.json; GU/QKV qualified gate4 evidence is retained separately.
No RTL or data-path cycle change. These are component delivery/timing checks; no new full-row, whole-token or G5 pass is claimed. Numerical qualification remains the actual full producer baseline, separately recorded in ../baseline.

Exploratory attempt3_failed_calibration.json is retained as FAIL: actual control pins were correct, but independent-lead binary search selected isolated arm aliases and yielded ineffective GO-early controls. The corrected finite-envelope algorithm is the only candidate for qualification.

GU GO=-5/XPF=4 and QKV GO=-35/XPF=4 have qualified nominal and all three controls in gu_qkv_actual_pin_qualified.json. O and down must instead stop the lower sweep at GO strictly after XPF. If every legal point passes, the result is NO_LEGAL_GO_BOUNDARY and the overall driver exits2 PARTIAL_COMPONENT_ONLY. It uses generous GO24 for remaining arm/base controls, so the arm-late control remains a distinct write. Neither a colliding write nor an unarmed GO is accepted as a useful read-window mutant. Attempts4/5 retain the assertion failures that exposed this finite-window constraint. No numerical O/down result is inferred from the timing-only vehicle.

Current QC peer supersession (reported by qwen owner): fresh_v6 strict bind PASS source5d2ce53210, 377parts/100types, actual omitted coll_regen hook restored LS407; C transport0a010308 and PHY362/343/362/R11 unchanged, zero data-cycle delta. This resolves the earlier QC collective checker hook discrepancy; it does not supply the still-missing current programme/GI/HEAD_PREP profile or make the xhead delivery coupon a full-pair image qualification.
