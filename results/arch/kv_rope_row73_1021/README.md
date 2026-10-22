# Actual RoPE HBM and73-record source packet

Base8ad0401af. Source implementation only; no new tests/audits launched under owner closure-first steering.

The accepted O61 owner supplies realposition13,embeddingtoken18,epoch16 (user retained inepoch). A second fixed HBM sweep starts1024edges after the first, with pseudoID151936+position//8. The existing128PC code sweep returns all64words; eight withword_index[5:3]==position[2:0] enter a separate real64x512 SRAM (only8rowsused). This deliberate fullrow overfetch reuses actual controller issue/return/train reservations; no reference values enter runtime RTL.

Existing code/scale logicalsectors and physical locations are preserved. Appended RoPE E19457304..19588375 maps rowoffset149,p=pseudoID-151936. This avoids both logicalscale and physicalrow148scale collision. tools/qwen_embedding_hbm/rope_image.py exports exact4MiB table using canonical dv_lower_vec.rope_words@6ff5be90f; emit_boot.py --rope DIR appends131072sectors before singlecombinedcount/checksum marker. Actual HOST boot dispatch/ingress plus package map are extended together.

New rowTX requires64code+scale+8RoPE resident atheader, verifies both trueepoch and expectedpseudoID, retainsactualembeddingtoken in all73payloads, sendsheader then64code then8flaggedRoPE. Bit512=1 onlyforRoPE,index529:524=0..7,reserved523:513zero. No wait/credit/admission workaround.

ONE generated pairimage: rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew1627_r16_rope.svh. Compile inputs MU1,EW1627,ROPE1,R16TX_SHIFT1,STATUS_DELAY213,KV_CODEC2,canonicalseam2,2,2,3,2,2/11,11,9,9,9,9,9. EW grows1032=1024actualtraversalreservation+8TX; rowheader/code shifts1024 andL0shifts1032. Programme rejects first actual traversal+PIPE_JOIN+8>=1024 or insufficient actualheaderdeadline. It must use actual O61context paths supplied by KVlead, not old RESULT baseline. Physicalviews/schedule/OVL-MU composition still require actualsuccessor; old595andoldviews do not qualifythissource.

## Final canonical cadence and OVL source outputs

Source8a52b11a1 actual pair-calendar compiler grows each layer to8012edges, reserves shared actual2003-edge kernel plus full1627-edge HBM embedding/single-row resource, paddedperiod293376. ONE pairimage filename unchanged. F16 frameH4694016; usertoken counts16/15/8/7; modeledrate11759.7tok/s, not measuredphysicalthroughput. Each of4startlists has1703words and1702starts; SEG1C_TX/K_RX4,C_RX/K_TX2; releaseadmissionbase16,FIRST_OFS1176. Sourceframes/listcalendars nowunder ovl/, fullframe compressed, release4ROMs and image under rtl/qwen_sys/d2d_static_20261015/ovl_release_rope.

Compilation was actualsourcegeneration only. Fleetcompile unitoth-ubuntu-410935-1792572276 ep9 (unpinned spillfromep6), releasegenerationoth-ubuntu-1569721-1792572366 ep6. Earlieractualfailedattempts:1557630-1792572084 missingpackdependency;1559066-1792572122 caughtL0STATUSwronglyincludedintokenhead (fixedcf23d6af2);1561361-1792572185 successfulframe thenoldcomparisonrate usedlegacyperiod (fixed8a52b11a1). Failures remain underfleetlane codex-kv-rope-ovl-1021. No tests/RTLvalidators/auditcampaign.

StillsourcefunctionalOPEN: actual all-user newO61 descriptor delivery and filltrigger semantics. HOSTrecord_port_mu currently sendsfillerINITIALcontext only; RESULTtag isoldterminalowner whileRESULTtoken isnext. No rawfullownercomparison or inventedposition is adopted. ActualKV OVLsequencer needed toplay K lists; include-onlyBC4 onnewpairimageis not MUframeplayback. ActualcomputeEprogramme localpin/seam composition, source/view binding and allnativeclock/phase/physicalclosures remain ownedintegration prerequisites.
