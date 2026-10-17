# d4e A2P half die (OWNER 10-16: 16 SMs + 2 HBM stacks per die; coordinator provisional approval 19:30)
19,502.24 x 24,094.24 um = 469.9 mm2; reticle margins 8.91 (long) / 6.50 (short) mm; density 0.67 blocks, ~0.71 incl relays.
SM = H-SM measured portrait column F108 1,939.68 x 6,678.72 (claude/hsm-smframe-2row-1016 ab729be8a: 4 rows x 4 rp4,
xw 360.72 um on the band (N) short face, SM_HBM 244.08 um + result on the PC (S) short face, clk/rst on the front E face).
W half only (SW, NW quadrants; one PHY on the S, one on the N edge), 8 SM columns per stack over the PC row, E column
3.1 mm: hc_eng 3.10 x 3.06 (normal aspect), ep rows against hc_eng S/N faces, lk SerDes against the E die edge.
PHY/PC row shifted +4,000 um toward the VM hub (tools/hbm_die_v15/a2p_fix.py; HBM_VM 30.2 vs 39 unshifted).
Stages (v6_eval): SM_X 11.3, SM_HBM 2.81, COLL_EP 10.6, HBM_VM 30.2, VM_HUB 27.0, HC_ENG 2.0; cuts 0.506/0.542, 0 over 0.60.
Grants: results/arch/hbm_die_v16_a2p/grants_a2p.json (rehome_v6 --quadrants SW,NW --drop-ghosts --sm-column --homes
homes.json): 0 outside / 0 overlaps / 0 hard-block points; SM pins FACES_ONLY until the H-SM column kit.
Reproduce: compact_plan.py <d4c base args> --smw 6678.72 --smh 1939.68 --qw-extra 2760 --sm-columns 200 --sm-col-real
--half-die --column 3100 --channel 100 --area 900; a2p_fix.py DIR; shift phy_/pc_ x +4000; v6_eval.py DIR --slack 1200
--spread vmh_SW:W:159.84 vmh_NW:W:159.84 --lanes-mode legs.
