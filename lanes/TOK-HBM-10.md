# TOK-HBM-10 Codex continuation 2026-10-29 08:33 PDT

CODEX took over HBM token/source timing on codex/hbm-token-0830. All inherited token component jobs already terminal and collected; no duplicate jobs.

## CODEX notes 2026-10-29 08:33 PDT
- READY08db45f04+e2281512d: exact added-lane LAT ABI export using canonical Plan.lane_latency; D17 60lanes/98239bits,54complete/104incomplete missing strict pairs,81148bits remain. Both halfbuilt su30->su31 pairs preserved incomplete1678/3356. Cycles/width/endpoint negative controls caught. Parent DIE-HBM fixing D18 reach/partial capacity; D17 not adopted.
- Conditional S2 fixed per-record exposure: +1VM-dependent record0.356%DS/.080%QW; deliberately pessimistic6serialperrecord2.171%DS/.477%QW. Actual source traversal remains unqualified; no rate claim.
- Exact source diagnosed: current intel1 codex-hbm-bind-0300/top_native.sv has DIRECT NWbank4rr1->DMAback257bits and DIRECT NEbank7eg/pr/status/done. Plan3stagesNW and6stages+serial_k2NE are not in source yet. Six+1 physical differences are NOT a source-ready six-cycle update. /root/coverage owns samewidthNW3stage opt-in materializer. TOK-HBM owns sourceII proof for NE serializer; body allows consecutive mirror egress. Current4rolecalendar remains blocked on actual source/K/reset/START.
- LIVE own minimum EG sourceII probe: ot-run intel2:/srv/opentallas-scratch2/claude/codex-hbm-token-0830/eg_ii, current actual body same SHA as manifest source, native SRAM model,24consecutive legal mirrorwrites. Collect EG_II1_PASS or diagnose simulator failure. No P&R/STA.
- Next: send sourceII result to HBM owner; apply D18 LAT export; regenerate actual transport/calendar only after authoritative signal map+source materialization.
- OWNER?: none.

## CODEX notes 2026-10-29 08:37 PDT — actual NE source II failure and selected fix
- READY4fea3d46b exact six source link/bit contract + actual nativebank proof. Unit intel2 oth-ubuntu-2189907-1793288032 terminalPASS:24legalconsecutive mirrorwrites,24consecutive EG responses,distinctpayload correct,status0at833ps. Selectedbody SHA identical currentmanifest. Initial2150410 missingCEcountermodule elaborationfailure diagnosed/fixed using exactexistingmodule. Allownjobs terminal.
- SourceNEII1 disproves transparentserial_k2; parentHBM selects fullwidthk1plan candidate fiveNEoutputs. Coverageworker owns optionalNW3stage/NE6stage samewidthpipeline materializer. Sourceembeddedvalidresetmasks sent; no inventedepochbits. Source/currentplan timingadoption stillheld.
- ConsumerNW hb_dbk_NW RR_RT80 checks all8returnvalidbits simultaneously and usescommontag; isolatedbank4+3pipe cannotcomplete returncontract. All8request/replydelays+padtobudget must becomposed. Foundpreexistingwrongdirectionplanrows bank.rq1(INPUT)->dbk anddbk.rr(INPUT)->bank, pluswholebuswidths vsactual17/257slices; HBMowner informed toconsume actualdirectedbitgraph. No source budgetchanged blindly.

## CODEX notes 2026-10-29 08:49 PDT — actual source-directed VMS fix prepared
- READY73a128163+aa06f3c6b codex/hbm-token-0830: exact actualVMS sourcebitgraph256links;128Northlinks->64planrows/hub(120->64),112wrong/redundantaliasrowspruned,q1selectedexplicit;128South_mu1linksMISSINGgeometryretained. Optionalfullwidthk1actualbits,nofakeepochs. NWwire*stage108458->87016,NE110100->89782inventoryonly. Inputplanunchanged;dieownerrecomposesactualpins/clock/cut. D18LATexact60newlanes95311b/55complete103incompletepairs84076uncoveredbits.
- ActualRR1sourceprobePASS unit2548544:bankrqsample62/rrNBA68/receiver69,data24/status0. RR_RTABIproducerrequestlaunch61->replylaunch68=7,receivercapture8;coverageownsall16DMA/RR80coherentpadding.
- Export128pipeline recipes176798FF/3074controlbits,stages2..31. CoverageactualmaterializationPASS379originalinst/master/paramsunchanged,128groups93sinkportsrewritten,allotherports/bitsunchanged;27wrongstage/bit/resetmutantscaught. Actualcandidateintel1codex-hbm-direct-station-0822/top_vms128_stationed.sv. Thisiscomponent/sourceprep;noSouthgeometry/reset/calendar/physicaladoptionclaim.
- Noownlivejobs;nextactualSouthgeometry/cutwithHBMowner,sourcecalendardatesafterbinding. OWNER?:none.
