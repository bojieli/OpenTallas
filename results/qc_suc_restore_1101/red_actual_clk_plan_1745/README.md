RED actual NEW PLACE native clock-pin planning

No ODB/source edits or CTS. Actual placed seed has8269 FIRM BUF8 and34225nativeCLKpins. Current binding fails nativeY-to-CLK reach74.954um (143sinks/20leafs>40) andrelativeTT/FFwindow24.29/21.04ps. The cap16 same-fixed-node planning rebind preserves allnodes and3452leafdrivers, covers34225uniqueactualCLKpins exactlyonce andchanges24516sink-driver assignments. Maxreach15.77um/zero>40, leafpopulation1..16,relativeTT/FFwindows13.08/10.31ps,outslew19.7/14.9ps.

Actual HQN/ASRH CLKcaps are typed. Estimatedwirecap11.346934pF; bufferinput7.045560/7.758001pF; DFF16.244158/17.859927pF. Wirecap is model estimation, not routed extraction. Rootinput0/20/40/60ps slew cases are conditional hypotheses. Zero-slew absoluteTT/FFmean296.37/231.92ps is not qualified against unchanged common250/202.5reference. No hidden frame compensation. Native rootport138.252,138.240 measured;0.413um modeled rootstub, inputcap0.915743/1.001901fF.

SharedR7 NLDM/Elmore equations reused. Results-only adapter exposes previously hardcodedrootboundary; exactboundary_adapter_receipt.json records change. Internal wire geometry uses actual newbuffercentres, endpoints actualnativeCLKpins; actual Y-to-CLK reach independently censused. cap12 greedyassignment failed, not mathematical infeasibility.

Image personally LOOKED: unchanged regularfixednodes, allactualsinks preserved; oldlongredsegments concentratedsouthcentral andfewcentraloutliers disappearunderlocal rebind. This is planning-onlygeometry, not legalrouting/CTS/commonframe proof. Original placement andnativeidentities preserved. Runtime epyc2:/srv/opentallas-scratch2/claude/codex-qc-red-new-model-1620; modelunit2612319-1793579711 exited0.
