# DIE-QC-58A variant B3 (A0 ICG=1 root gate, no RTL change) + zero-logic HB4 hook

Base: the DIE-QC-58B ICG=1 kits (claude/die-qc-58-a0root-1031@47087308c8b), copied to intel2
/srv/opentallas-scratch2/claude/die-qc-58a/kits/.

## B3 (b3_early.tcl)
b3_early.tcl is sourced from b3_pre_cts.tcl, which is the kit PRE_CTS_TCL. It acts right after clock_tree_synthesis.

- **EARLY:** the CLK pins of g_icg.dr*, go_h* and g_rr.* move onto the ICG CLK net through one BUFx8 branch buffer.
- **MID (auto):** the ENA start flops are re-tapped onto the ungated pre-gate delay chain.
  - The shift is the ENA deficit + 30 ps. If that shift would break the flop's own D setup, the ENA and D-setup slacks are balanced instead.
  - Each re-tapped flop gets a local BUFx4, plus BUFx8 repeaters every 90 um on long branches.
- **ENA repeaters:** BUFx8 every 120 um, dont_touch.
- **Hold pads:** planned HB4 pads on the late captures of the re-tapped flops.
- **Legalization fallback (kit-local, in b3_pre_cts.tcl):** if detailed_placement leaves an illegal placement, it reruns with -use_diamond_legalizer.
  - Reason: the NegotiationLegalizer left 4 overlaps after ~19k hold buffers (nl_FAIL1_4_1_cts.log.gz).
- **Endpoint cap (orfs_hold_mm_epcap.diff):** OT_HOLD_EP_CAP_INFO=1 turns the 2000-endpoint cap into INFO when FF hold ws >= -100.
  - Authority: DIE-QC-58 ruling 11-01, per COORD 21:2x (3)(a).
  - ws >= -100 still gates.

## NL results, CHECKED
Kit: qfd_tile_nl_a0c_a0nl14icg1b3. nl_config.diff holds the changes: CTS distance_between_buffers 70 plus the B3 env.

- **LEC:** EQUIVALENT 43013/43013 with 58B's 2 eq hints (nl_lec_hints.diff). This closes the otsg_a/tsg_a[23] UNPROVEN points.
- **CTS probes** (probe_nl_b3*.txt), FF hold ws (ps) / failing endpoints:

| CTS distance_between_buffers | FF hold ws | Endpoints | Note |
|---|---|---|---|
| 100 | -103.74 | 3020 | B3 ENA TT setup after repair +0.54 |
| 60 | -97.41 | — | |
| 70 | -84.66 | 2822 | chosen for the full run |
| 80 | -108.33 | — | |
| 100 + cluster | -134.35 | — | |

- **Full run (dist 70):**
  - B3 ENA before repair: -22.3.
  - FF hold -84.66 / 2822 → in-flow repair with 18975 buffers → FF hold +15.00.
  - TT setup -12.44 (me_idle/D).
  - Diamond legalization clean, max displacement 5.4 um.
- **GRT on 4_cts, including 1184 clock nets:** 0 overflow on every layer after 30 congestion iterations; usage 8.39%.

## NK results, CHECKED: B3 does not close NK
Probe outputs are in probe_nk_b3*.txt.

- The ENA starts include the both-reset relay n_a_q/n_b_q[513:512], which sit 400-520 um from the root ICG.
- The best re-tap clock for them is ~235-297 ps, even with a repeated branch. ENA improves from -881 to -192 ps and no further.
- Their early launch puts mis_q/fy_q TT hold at -441: a hold window that conflicts with setup on the same captures.
- CTS dist 70 is worse on NK (hold -250).

## ot_zl_pad.tcl (zero-logic HB4)
Owner rule 10-27: "zero-logic seam hold -> HB4".

- **What it does:** a post-CTS hook. OT_ZL_PAT gives the capture patterns. It pads each D pin whose min path is flop → buffers → D until TT hold >= OT_ZL_TT_PS.
- **Offline result on 58B's NK CTS DB** (zl_nk_offline.txt):
  - 191 of 6240 g_tx u_tx/q D pins were below 0 ps TT hold.
  - 199 HB4 inserted; the worst of those pins is +13.8 ps after padding.
  - Runtime 1821 s.
