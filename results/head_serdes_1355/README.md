# SerDes actual CTS continuation

Collected13:57: quarter+keep strictLEC EQUIVALENT4217/4217, trialPLACEexit0.
No inheritedCTS/GRT or LEPV1/V2PLACE jobs were present in die-head28/29/30
run directories/docker inventory. LEP coupled378 model5d47d7bcee8 exists at
intel2 die-head-29/lep_repl/sites_legal_378_push.json (0modelviolations,0cycles),
but needs a fresh physical kit and actual placement, not another model run.

Actual next step submitted13:59: own SerDes diagnosticCTS, source-preserved
clone,32GB8threads viaot-run. Check cts.otrun.log and cts.log at
intel2:/srv/opentallas-scratch2/claude/codex-head-serdes-1355. The existing
source/proof/placement are reused; no second LEC. No GRT/DRT/SIGNED claim.
Image and personal review are in results/geom_review/head_serdes_1355.md.

At explicit14:02 Claude reset, CTS finalmetrics were still writing (job left
untouched). Already-collected diagnostic placed-RC numbers, independently
UNCHECKED: TT setup WNS -2.51ps, TNS -4.36ps, estimatedperiod835.51ps vs833;
worstsetup e1_dv[29][1] -> crc[251], so the earlier nrc popcount bottleneck
is gone (old -166.73ps). FF hold -2.35ps on pl[7] -> pl[8] throughNOR2,
clockarrivals142.72/157.49ps,25psuncertainty. Clockdepth5-6,179dummyloads;
legalization maxdisplacement5.5um. NoGRT/DRT/finalcorner/signoff claim.

Next: collect terminalCTS/4_cts.odb, run canonical HEAD-flow GRT and FFhold
repair with10psmargin, then diagnose actual routed residuals. Keep the320
internal-input parent STA and150um launchreach conditions. No newcycle or
RTL change is justified by this tiny placement-RC miss alone. All engineering
stopped on explicit14:02 reset; only this parking record was added.
