# Wide x8 clock phase audit

Fresh actual wide gate at `/srv/opentallas-scratch/claude/ref_gate/dsfd_capt_x8_dual-20261013-213408` on ot-agidock128. The leaf is 123.12 x 136.08 um; these are independent measurements from its actual 4CTS ODB, with placement-estimated parasitics. They do not qualify a routed leaf. Source snapshot is frozen at bc2c93f92; job dsfd_capt_x8_dual-v2-bc2c93f92 uses that commit.

Core and serial clock insertion were measured independently in TT, FF and SS. The scripts first report actual cross-domain paths with a common pin phase, then apply negative boundary mean insertion separately to each clock, matching the parent's required delivery phase phi - R. No false paths, uncertainty relaxation, latency change or IO budget change was used. Both directions and max/min paths exist in each corner.

At route periods 770 / 1026.666667 ps, compensated TT core-to-serial setup is +38.64 ps and serial-to-core setup +61.79 ps. Compensated FF serial-to-core hold is -1.738 ps at `u_half.g_r[4].u_x.rp_w[1]$_DFF_P_/D`. The approved wide route includes ordinary FF hold repair with 30 ps margin. A routed compensated-phase TT setup / FF hold audit is mandatory before parent adoption; a common-phase CLOSED record alone is insufficient. SS setup sensitivity is retained in phase_pairs.json and must be classified at nominal 833.333 / 1111.110667 ps after route, rather than silently borrowing route-period results.

Actual assigned native M3 pin width is 0.018 um, confirmed in wide_pin_probe.out; M5 width is 0.024 um. The historical narrow IOP retained 0.024 um M3 width after centre snapping; the wide assignment repairs that geometry.
