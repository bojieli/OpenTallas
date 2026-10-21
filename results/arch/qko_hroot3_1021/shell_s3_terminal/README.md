# Ingest shell s3a/s3b terminal clock failures

Both sourcef102e8cbcb36e0c5f757bb57c44267ee8ea45b38 gates are terminal FAIL. No source/kit changes, retries, submit, merge or REVIEW here. ROOTintegration alone publishes. Current e4a/e4b/n34b and peer admitted runs are preserved.

s3a native max32 PASS; floorplan/pin geometry PASS; textbookdepth366.7ps/reach320.8um. Actual TT boundary ck_core55.1ps PASS, ck_host123.6ps FAIL>80 (587/727sinks); ck_ingest was not reached after first clock failure. s3b native max32 PASS; textbookdepth366.7ps/reach342.3um. Actual TT boundary ck_core58.6ps PASS, ck_host54.8ps PASS, ck_ingest162.3ps FAIL>80 (88/158sinks). Missing final clock-measurement coverage follows the actual CTS stops; it is not a waiver.

Exact actual error extracts are retained beside original final gate JSON and compressed source shipping manifests. Original full CTS logs: ot-agidock128:/srv/opentallas-scratch/claude/ref_gate/qkd_hr_ingest_shell_s3{a,b}-20261021-132655/cts.log. Actual source floorplan images are included only as diagnostic evidence; these are failures, not approval packets. Remaining work is structural per-root clock treatment; no unchanged retry is authorized by this packet.
