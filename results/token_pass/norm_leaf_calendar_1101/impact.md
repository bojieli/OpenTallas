# PDSK512 candidate impact (COORD approved preparation only, 2026-11-01)

The actual current XRT collector requires all five partial valids on one edge. In `ot_s81sl_xrt.sv`, any `pv` starts the five-word serialization (line819), and line884 faults on `(|pv) && pv != 5'b11111` or another partial while `prun`. Independent staggered leaf arrival is not supported by this source. No additional gate is proposed.

Current kva3 80-leaf extraction proves duplicate aligned-command slots in u_s_0S leaves2/3 (effective boundary+PDSK ages23/23), and u_s_2N leaves2/3 (25/25). A native issuer has only one control body per engine/edge, so the exact source cannot receive the needed five-partial aligned cohort under these parameters.

The proposed single shared profile is PDSK=[0,0,0,1,0] (15'd512), replacing [4,3,2,1,0] (15'o01234). It is the minimum maximum-depth then total-depth uniform profile over the existing five3bit fields that removes all local duplicate slots for all16 actual slices. The profile remains unadopted.

Affected source instances:14 ot_s81sl_xrt1 and2 ot_s81sl_xrt3, in16 C-wrapper types listed below. Pins, widths, source straps, clocks, reset interfaces, outlines, all leaf/native macros and external buses are unchanged. PDSK changes internal returning-partial timing, not clock insertion. Logical partial pipeline storage drops9 stages×33bits=297FF per XRT,4752FF across16instances. Both profiles remain nonzero, so the existing deskew reset relay remains. Sign-off timing/netlist views must match the new parameter; fresh XRT1/XRT3 hard-core views and affected C-type kit views are required. Existing old-profile jobs continue; no old verdict is erased or re-labelled.

Exact stage deltas per returning leaf0..4 are[-4,-3,-2,0,0]. For any chosen fixed partial-cohort output anchor, shifting corresponding NORMR commands by[+4,+3,+2,0,0] preserves that anchor exactly: candidate output adds0edges. This is a conditional source equation, not an achieved global-token cycle price. Current source has no executable aligned global baseline for these two cohorts. The finite necessary per-slice command span is at most51edges; global engine/NX/GO/VQ/calendar/retirement and physical START composition must determine any actual model delta before adoption. Do not report either a global gain or a global0cycle result from this local equation.

Required before production adoption: actual current source-aligned return lockstep and wrong-depth mutant, current-manifest seqhost timing, one separate S81 batched PDSK plan event, exact current compiler calendar, affected views re-sign. This work does not delay the approved t48+PG event.

The current-control relative-date probe found five added actual seqhost defines vs the old receipt: OT_S81_SH_SRAM/RSZ/P192/APIPE9/APIPE10. It is re-measuring the current source. First frontend failure was missing selected P192 functional macro models16x257/16x289, not a logic verdict; corrected selected models are included in the fresh v2 probe. Old failed output is preserved.

Affected C-wrapper types:

- s81p_dsdv_slice_lepw_mus_C__t1 (u_s_0S, ot_s81sl_xrt1)
- s81p_dsdv_slice_lepw_mu_C__t1 (u_s_0N, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t1 (u_s_1S, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t10 (u_s_1N, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t3 (u_s_2S, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t4 (u_s_2N, ot_s81sl_xrt1)
- s81p_dsdv_slice_iq_C__t1 (u_s_3S, ot_s81sl_xrt3)
- s81p_dsdv_slice_kv512_C__t1 (u_s_3N, ot_s81sl_xrt1)
- s81p_dsdv_slice_c3x_C__t1 (u_s_4S, ot_s81sl_xrt3)
- s81p_dsdv_slice_c1x_C__t5 (u_s_4N, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t6 (u_s_5S, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t7 (u_s_5N, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t8 (u_s_6S, ot_s81sl_xrt1)
- s81p_dsdv_slice_c1x_C__t9 (u_s_6N, ot_s81sl_xrt1)
- s81p_dsdv_slice_lepe_nh_mus_C__t1 (u_s_7S, ot_s81sl_xrt1)
- s81p_dsdv_slice_lepe_mu_C__t1 (u_s_7N, ot_s81sl_xrt1)

Actual candidate aligned-return lockstep now PASS:3,220 edge checks,320 words on each XRT1/XRT3, errors0; wrong-depth576 mutant raises faults in both. The distinct-command-body requirement comes from actual VP NORMR a1→dmq→m_i global index5sid+k; a common multi-leaf mask cannot issue two different indices in one edge.
