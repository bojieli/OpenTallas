# KV-SENDER-SKEW handoff (split from KV-DIE-SEAMHOLD 11-23 23:0x PST)
Job: sender-side LATE fclk EXPORT defect (fam-late-export.tsv: 67 ring outs m<-100: pv_v12 53, pv_v6n 3, hgi_v7 8, io_ft_v1 2, phy_v1 1).
## Census (lanes/handoff/KV-SENDER-SKEW-census.tsv; probes epyc11 /srv/opentallas-scratch2/claude/kv-sender-skew/g/<type>/geom.tsv on seamhold kits)
- 66/67 LATE_FWD_TAP: landing_exports.tcl puts the export BUFx24 at the SOURCE tap pin (clock.landing_contract pins source_clock_port).
  The source tap is 320-1942 um from the port (stale since landing compose; tap grid regrown/renumbered; io_ft_v1/phy_v1 on root clk),
  so repair_design adds 2-12 wire repeaters: fclk_out 294-964 ps vs data 132-411. Launch flops sit on the nearest tap (65/67; 2 one tap over).
- 1/67 io_ft_v1 ft3_o: same tap 9 um; -107.8 = kit SDC tap window (early -100/late 0) with no CRPR between clk and the generated fclk; structural -7.8. No defect.
- Kit SDC window note: hgi_v7 120, io_ft_v1 100, phy_v1 80 ps windows are counted in m for same-tap exports (seamhold m values are pessimistic there).
- Die-wide in A5 (KV-SENDER-SKEW-plan-A5.tsv): 2769 fclk_out pins, 1901 on a tap >50 um farther than the nearest, 1457 source hop >300 um.
## Row
- epyc10 /srv/opentallas-scratch2/claude/kv-sender-skew/ROWS_KV-SENDER-SKEW.py (cwd = launch tree). Uses reach_rules.fix_fwd (FWDCLK-1 rule 4)
  with limit 150 um + ladder: 1895 exports / 89 types repointed to the nearest tap; 245 left already on their nearest tap (242 <=300 um; pv_v7e x2, sys_SD/sys_SD_v1 cland_up >300 need a tap).
- Base KV-ALLFIX A5 95c853437992. Gate ss_gate.sh: s5 (5 defect types) and all (full strict bind) on epyc10, gate_<tag>/.
