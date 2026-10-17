# q3h2 diagnostic source packet, Codex 2026-10-16 20:00 PT

This packet introduces the opt-in hierarchical generator on current main. It preserves the main per-bus relay-stage exporter. It includes the exact pin-plan files read by the selected grants, without the unrelated SU RTL or physical kit. All generated cluster abstracts remain diagnostic.

The original advancing runs use source branch claude/q-dieplan3-1016 at b7dbee919 plus the exact corridor fix committed as 8f4004ea3. E4 paths are /srv/opentallas-scratch/claude/qwen-split-compute/q3h2 and q3h2_w; generator PIDs 4106755 and 4071628, admitted units oth-ubuntu-4062501-1792204877 and oth-ubuntu-4062490-1792204877. No advancing source was changed. The integration smoke uses /srv/opentallas-scratch/codex/q3h-packet-1956, current main tools over preserved physical inputs, and OT_RELAY_SKIP=1. It proves generator compatibility only.

| Class | Current evidence | Required next step |
|---|---|---|
| Relay site | Original q3h2 bword_1 tree_spine vertical at x12512.88 hit C_B16 interiors; source corridor override fixes planning lanes | Collect advancing full GEN hard373 and warning twin; never qualify warning output |
| Cut / area | Historical subset-only cut0.475 omitted narrow overlapping-face channels without per-bit occupancy proof; NOT total demand;741.65mm2; max chain estimate37 | Packet restores main conservative cut model; recalculate all demand, then full GEN/GRT arbitration |
| Reach | Measured xcst launch192.6/capture186.1 gives414um at80ps skew;373um chosen planning margin | Audit every generated hop plus die STA with real clocks; flat reach alone is insufficient |
| Native cluster / clocks | qfd_c_b16 provisional abstract, single ck across5.2mm; no closed/native cluster | Q-ROM actual regional-root cluster and parent native closure; no die binding yet |
| Native D2D | r5 capture491.3ps; successor r7f capture239.9ps nativeFAIL, r8b hold-margin successor in CTS | Bind only CLOSED + nativePASS replacement |
| Reset / PHY | Regional reset intent and declared registered PHY contracts; final generated per-pin audit pending | Audit actual generated source and measured regional reset reaches |
| Die timing | GRT and TT/FF not yet available | Regional forwarded physical clock delivery, GRT0 and TT/FF>=0 required |
| Compiler price | Legacy flat cost helper defaults retired cor/tap/tree ages; explicitly refused for q3h in this packet | Export selected full GEN stage table, join actual cluster timing contract and compiler schedule; compare shared digest |

Viewed q3h2_readout.png directly: symmetric four-band six-column cluster arrays; usable central white region, distinct head corridor and VM/SU seam. Long reduction trunks funnel into centre-edge ports; vertical relay lanes must stay outside cluster bodies. This image is a relay-skip floorplan, not routed evidence.

Reproduce the integration smoke with tools/qwen_split/q3h_diagnostic_smoke.sh ABSOLUTE_OUTDIR. Heavy runs use ot-run with measured admission. Full future runs should set OT_DIE_RELAY_STAGES_OUT and OT_DIE_RELAY_STAGES_PLAN_ID; the selected compiler must consume that table, not private stage literals. Actual cluster fabric e7e22d5b6 is a separate sibling intake and remains provisional.

Root review correction: the original branch cut model omitted all overlapping-face channel nets up to50um without actual per-bit track proof. This packet removes that change entirely. Historical .475 is an incomplete-demand diagnostic, not an actual total cut. The first packet compatibility smoke inherited that diagnostic cut model; only its generator topology is usable. Rescaled xcol clock coordinates carry an explicit provisional diagnostic marker. Assigned pin grants reject VIEWS masters; late pin grants now do the same, preserving closed-view geometry.
