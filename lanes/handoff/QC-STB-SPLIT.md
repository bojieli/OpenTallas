# QC-STB-SPLIT handoff (Opus 5.5, started 11-24 12:5x PST; one job: QC st_b under the 400k OpenROAD cap)
## Measured (E2 kit sle_st_b_v2__cl14c98df5__pvcd986c42, 1_synth_odb.v, net-hierarchy attribution)
- synth 391.9k: 4 regions u_u_r4..r7 250.9k (62.7k each), 5 cland rings 92.7k (hc3 38.6k, st_a 16.2k, fw_ctl_p2 13.4k, hc1 12.9k, su_l0 11.5k), ft stations 25.8k, lpad 13.5k, rest 9k. fp 394k -> place 417k -> CTS 430k.
- Hold: pass 1 fixed 9854 (WNS -84 -> +5.0); pass 2 "63,415 endpoints" at WNS +5.000 TNS 0 = margin artefact (flow), not seam class.
## Form: ring harden (st_a RCAP-STA-B / KV CLAND-MACRO-1 precedent), all 12 st_b types, 6 shared masters x 66 inst, 0 cycles
- Delta: intel1/epyc10/epyc2 /srv/opentallas-scratch2/claude/QC-STB-SPLIT/dev/delta_stb_ring_harden_1124.py (--tree --plan --rtl-dir --out --report)
- C1j draft out: dev/out/plan_stbring.json (dst f3260c6aecb2), report.json, cores/st_b/*_pins.json (6 masters qc_cland_w{1575,653,517}_ew / w{537,457,259}_ns)
- Child kits: dev/rk/<master>/kits/<master>_synth0, prep_stb_rings.py; launched 13:2x via dev/launch_rings.sh (ot-run finish 24G/8t), all on epyc2; logs dev/rk/launch_*.ot
## Next
- Tree fork cJ -> epyc10 QC-STB-SPLIT/tree (unit oth-ubuntu-2681975-1795554482, fork.ot) -> install plan + pins -> PRE + scoped strict bind (--types st_b) 
- Rebase on C1k when QC-ALLFIX gives sha. Then child views (lef/lib) into rows -> parent kits.
