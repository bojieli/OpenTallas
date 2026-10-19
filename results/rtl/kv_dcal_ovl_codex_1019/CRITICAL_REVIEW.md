# ROOT critical review: KV-DCAL-OVL-CODEX

Status: READY FOR ROOT LAYOUT REVIEW; not submitted, no REVIEW.json. Branch codex/kv-dcal-ovl-1019; executed source4f2c3e710. Gate PASS,0fail/0warn; source_binding commit=None, remoteot-epyc7.

PNG files (both visually inspected):
- /home/ubuntu/wt/codex-kv-dcal-ovl-1019/physical/ref_tile/qkd_d2d_cal_seq_pin_ovl_bc/gate_layout/floorplan.png
- /home/ubuntu/wt/codex-kv-dcal-ovl-1019/physical/ref_tile/qkd_d2d_cal_seq_pin_ovl_bc/gate_layout/density.png

Gate result: physical/ref_tile/qkd_d2d_cal_seq_pin_ovl_bc/gate_result.json. SPEC_SHA256 cdc6e0d95d1a3e4881d609006d62c62bef4bef7cf4286b4aec34e15968480bc1. Flow log /home/ubuntu/claude-takeover-20261007/kv-dcal-ovl-codex-gate/gate4.log.

## Safe checklist and measured facts

1. PASS pins: all functional inputs explicitly captured, all outputs registered, reset_landing2 plus RTLrelease2.97signal/clock pins all have legal accessible geometry, no missing/outside pins. Exact full-face ascending bit plan W outputs/E boot+status/S control. W/E density<0.5pins/um, below6. Clock at S centre(108.009,0).
2. PASS reach:216x129.6um outline, all distances below405um. Standard local buffered clock spine, no long direct data links.
3. PASS fanout/depth: textbookPASS,1888cells/456flops/depth308.4ps. Existing approximate32load cfgselect guidance exception remains the bootcfg narrow merge; measured reg-reg+222.1ps. No high_fanout warning.
4. PASS depth: ROM output reaches only64plain capture registers; macro->reg+228.4ps. Reg->reg+222.1ps, reg->out+300.8ps. No combinational functional in->out path. All mux/count logic local.
5. PASS storage: two hard ot_rom_4096x72_m8,589824physicalbits, logical2x1703x32. Only current/next words in flops; no indexed list flop array or deep delay chain.
6. REVIEW REQUEST density exception: two38.016x62.910um ROMs at(43.2,43.2)/(129.6,43.2),43.2lattice,5.4halos,48.384um macrochannel and>=20um pin-face core-edge margins. Total macro area4783um2; synth standard area298um2/core26519/placeable19323 gives1.5%std density,total19.2%fill. Outline is macro-lattice/channel/edge bounded, not squeezed. Smaller129.6square was refused before synthesis for5.184um channel/3um edge margin. Density PNG shows the main logic below the ROM fronts plus the required full-face pin registers; no isolated power island. Accept the low-util rationale or direct a structural packaging change.
7. PASS measured clock: one1:1clock, standard balanced clock_spine with69leaves,<=8sink regional leaves,498sinks in spine/458largest root report,214spinecells. Each hardROM owns its clockleaf (OT_SPINE_MACRO_LEAF=1), memory TT/SS/FFlibs supply actual clockQ arcs; no guessed child insertion is substituted. TT/FF pin-flop spread31.1/28.5ps. All-clock arrival TT223.9..265.4ps,FF177.6..214.4ps; boundary means244.4/195.7ps. SS insertion301.0..350.2ps. io_hold_margin.03. No masks or changed uncertainty/budgets.
8. PASS schedule: inputcapture1+innerEP1+outputcapture1=KV boundaryEP3; ROM read1/capture1/prefetch1 fits4edge minimum. Zero added runtime edge. Shared codec2 artifact1a73e1e7a actual seam2,2,2,3,2,2/11,11,9,9,9,9,9:K_TXDP0x03030416,C0x0a010308,admission16,FIRST1176,X8,H4026800,composed13708.2tok/s. No static stalls/credits/backpressure.

## Validation and limits

Verilator5.050 fleet fullF16+wrap+halt/new-epoch restart PASS1708TX/1710RX/66bootwords. Explicit first-event relative-time/segment/user rewind oracle; rawEP3 exact boundary comparison. Six negative controls FAIL with committed witnesses: lost runtimecfg,staleadmission,anchorcollision,bootduringadmission,missingRXbase,oldhaltpointer. Old-source rewind failure is preserved separately.

Trial GRT overflow0,worst M2use4.35%. Diagnostic placementRC setup+222.1ps/hold+26.6ps. This is a pre-route gate, not SS/FF routed closure. Gate3 full-face clockspread84.0/75.1 FAIL is preserved; structural spine successor is gate4 PASS. Gate2 old-rewind/clusteredpin PASS stays diagnostic only.

## Integration obligations

New master qkd_d2d_cal_seq_pin_ovl_bc and two exact listROM instances; OVL_DCAL slot216x129.6um. Ordinary bootcfgbc2 untouched. Boot target11 must interleave shared OVL_K_TX_IMG[i]/OVL_K_RX_IMG[i] for32entries, then16/16 admission bases (not ordinary MU image/SEG2=9). Drive separate cal_start_rx/cal_seg_rx/cal_user_tx/cal_user_rx with matching OVL link-end master and exact codec2TXDP. On routed CLOSED run native/neighbor pin audit and match die boundary compensation to real delivered clocks before binding. KV coordinator/d2d_overlap own strict GEN.

No submission was made. ROOT owns density exception/layout approval and final REVIEW.json/submission.
