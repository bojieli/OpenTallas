Fresh scope-only RAWLEAF continuation recipe. No AP row, P&R, STA or route is launched by staging.

Stage on intel2 from the original static kit and reviewed exact local successor using stage.py. It copies only static inputs (~15MB RTL plus helpers), one reviewed3_place.odb and its original SDC; no old run tree, reports, stale failures or signoff are inherited. The original kit and successor remain unchanged. The runner supports only normal trial CTS/GRT; it validates the reviewed input hashes and marks3_place.odb/SDC as immutable Make resume inputs, preventing re-placement. Normal existing config pre-CTS/GRT hooks and833ps/60/25 constraints stay in force. No routed-signoff or route-ready claim.

New tag: [QC-A0-KITS-RAWLEAF rst145 continuation]. Source anchor95444301f/924a35894; independent geometry1110109e1. Prior original150.963um FAIL and first global-DPL locality FAIL remain preserved.

Before any queue entry: ROOT reviews/integrates source, resolves exact-source QC canary and current plan/slice/preflight gates, and posts a matching fresh GEOM verdict for this kit. Source changes after staging invalidate the manifest and require restaging; the runner does not override gates. Proposed eventual CLI (do not execute until ROOT source gates clear):

python3 tools/autopilot/enqueue.py --die qwen_compute --type ot_qwen_tile_lsl_rawfault_m3 --kit intel2:NEW_KIT --src codex/pv-review-1351-1027@PACKAGING_SHA --geom REQ --geom-ref 'QC-A0-KITS-RAWLEAF rst145 continuation' --mem 24 --cells 57137 --lane QC-A0-KITS --goal grt --runner NEW_KIT/resume.sh --threads 8 --mode trial
