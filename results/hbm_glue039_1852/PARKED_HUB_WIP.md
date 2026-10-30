EXPLICIT RESET PARK 2026-10-29 19:03 PDT

Qualified source milestone is parent c79088880 (ring/status). This child commit is WIP, not qualified for adoption.

Hub candidate: four64bit return-data regions. Each independently captures original bank pr/ringcco client+seq+valid and its own64bit payload on the SAME original br/rr capture edge. Then region-local decode/OR produces per-client/per-slot returned_data; central arrival/fault/expected/writes logic remains original. Default LOCAL_RETURN_REGIONS=0; NW LOCAL_CTRL_REPLICAS opt-in forwarded to it through slice+generated glue. Added output/calendar cycles0. Payload captureFF expected near-neutral after dead oldbr data pruned; tag/valid replication up to280FF (10sources x7bits x4), estimate only, not synthesized.

LIVE pre-reset proof: intel1 /srv/opentallas-scratch2/claude/codex-hbm-glue039-1852, ot-run unit oth-ubuntu-3349133-1793325815, local client session41106; current full-width hub4000edges for NC0,1,2 plus payloadbit mutant. Check local /srv/opentallas-scratch/claude/codex-hbm-glue039-1852/hub.log; remote command uses hub_sim0/1/2 with hub_tb.sv+hub_reference.sv+hub_mutant.sv. No proof verdict at reset. Preserve process; do not duplicate. No new proof/engineering/jobs after reset.

Next after collection: diagnose any mismatch; run generator check after new propagation and actualNW elaboration only if needed; prove distinct helper instances through synthesis; hub be/pq broadcast remains separate. No physical adoption; per-bay input/control reach and N->Sstatuspins unresolved HBM039.
