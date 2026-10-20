# QW-GEN3: successor GEN + die chain of the Qwen MU compute die (after dv2f19g2), LEAD2-QW 10-19

PILOT_NOT_A_GATE die run with declared stand-ins (owner rule: die integration early and often). Strict bind must PASS
(no stubs, no ties). Branch claude/qw-gen3-1019 = claude/qw-gen2-1019 6bca9694c + claude/qw-dieclk2-1019 04f228b61 +
MU-DQ-BOOTCTX 600df51cd + the commits below. Run dir ot-epyc6 /srv/opentallas-scratch/claude/mu-die-qw/dv2f19g3.

## New in this GEN
- LANDINGS (QW-DIECLK2 R5, LEAD2-QW decision 17:00): OT_SPLIT_LAND_LIST=results/arch/qw_dieclk2_1019/landing_list.json.
  The GEN's LAND_CROSS mechanism (forwarded lanes) gives every listed cross-region link (446 links / 186,347 b: c_b16 <->
  c_b16, slice -> c_b16, c_b16 -> slice, slice -> slice) a one-frame landing (landh0: ring written on the SENDER's
  region root ck_s, read on the RECEIVER's root ck, fixed E, no backpressure). The landing is placed at the receiver end,
  on the free site that minimises the longer hop. It fails closed when a listed link is not on this GEN.
- R2 one hard instance per region root: OT_SPLIT_REGION_ONE_HARD=1 (tools/qwen_rom_fulldie_b3r2.py
  _gen16_clock_refile). It splits pll_r48 / r90 / r93 / r94 / r95 / r99 (two hard instances each on dv2f18dh2), and
  with it every zero-stage data bus between two hard instances is landed. That covers the R2-split pairs the rA list
  could not see, e.g. dvs_E0 <-> dvs_E1 on pll_r95.
- R3: DC_GRID_CENTER=1 (f3e34c03d) in the chain's regional die clock, which puts clock sites in the 17.28-um gaps.
- MU-DQ-BOOTCTX: mu_ctxrx (qfd_mu_ctx_rx_die) beside sys_face drives tt_ctlm.ctx_x (CTX_SRC 1). No tie.
- RELAY_CHECK runs on THIS die: the die-run table is the netlist walk (tools/qwen_layerbench/netlist_relay_stages.py
  on the bound GEN die.v). The schedule is layer_compile.py recompiled on that table, die.v, fwd_lanes.json and params
  (compiled_L1 is regenerated for this die). The GEN-model export is kept as relay_stages_genmodel.json.
  - QW-DIECHAIN2 found 3 die buses missing from the schedule and 18 scheduled buses missing from the die. They were
    the reset relay lanes, which the GEN-model export (bump_fwd_lrst / rs_bump / phy_rst) and the netlist walk
    (rly_lnk_*) name differently. Both sides are now the netlist walk, so that mismatch is gone by construction.
  - Torn C.rx_record (native_rx_* 2, rx_payload 1) was an exporter bug. The n=1 rule "age = K strap" no longer
    holds under calendars, because K = (E + cal + 1) mod 8. Every landed lane now takes the GEN lane E from
    fwd_lanes.json, as record_bundles.seam_stages does.
- Landing price for the compiler: +3 edges per landed crossing. On the serial token path that is worst case 15
  crossings x 3 = +45 cycles/layer = +1,620 cycles/token (+1.35 us at 1.2 GHz), per the
  landing_list.json price. The relay schedule carries every landed bus at its built age. NO layer-period compiler
  consumes the q3h / dv chain latencies yet (compiled_L1 compiles the D2D seam only), so the +45 cycles/layer is
  recorded as a priced gap for the DV calendar / ME programme compiler (see landing_price.json once phase 2 runs).

## Declared stand-ins (no new safe kit had CLOSED by 17:10; every gate is still live)
| element | new safe kit (state 10-19 17:10) | bound in this GEN |
|---|---|---|
| qfd_d2d_static (+OVL) | sf7 / sf7w gates live (QW-D2D3) | closed r5 view, qfd_d2d_static RTL (no OVL ports) |
| qfd_native59_dv_service | safe4 / safe4b gates live (QW-N59-3) | generated abstract; +1 embedding edge NOT applied (old RTL) |
| qfd_sys_face | bc3 / bc3c gates live (QW-SYSFACE3) | closed MU0 rs3 view; RTL MU=1, MU_HEAD 1 (BOOTCTX); no OVL seq ports |
| qfd_tt_ctlm_dv | safe3/3n (QW-CTLM3), safe4/4n (QW-CTLM4) gates live | generated abstract, RTL with ctx_x (BOOTCTX); hr +4 / tl +2 / inputs +4 NOT applied (lpf_lp not bound) |
| dh_user driver | dhuser k3 leaf CLOSED, but its dh_run[43:0] is a part-select of seq_dh[186:0] | qfd_sys_face_mu_dhobs abstract (wraps the same leaf at OPSEG 0; allowed as a declared stand-in by QW-SYSFACE3). dh_user is driven, not strapped |
| qfd_dv_slice2_e / _w | stn8 / stnrg kits (QW-SLICE3) | generated abstract |
| qfd_c_b16_dv | CB16 landed parent (QW-CLUSTER3) | generated abstract |
| landh0 / rlyh0 wide classes | not closed | generated abstract (1-bit closed views bound) |

## Next GEN obligations
- OVL: bind qfd_d2d_static_ovl_sf7 (.TXDP) + the sys_face OVL sequencer outputs (cal_start_rx, cal_seg_rx,
  cal_user_tx/rx -> d2d; tx_user/rx_user -> face) once sf7 and bc3 close. Both masters change pins, so a closed view is
  needed for each.
- dhuser leaf at die level needs GEN part-select endpoints (seq_dh[43:0] -> dh_run), or a child of the ctlm successor.
- ctlm lpf_lp (two clocks ck_core / ck_hr, native_ret E face): re-derive XPF_TRANSPORT_EDGES and the cmd / hr / dc lane
  ages from its record when it closes. n59 safe4: +1 embedding edge into the compiler.
- DV calendar / ME programme compiler: take the per-crossing landing ages (+3 each) of the q3h broadcast, rs reduction and
  the dv slice chain.
