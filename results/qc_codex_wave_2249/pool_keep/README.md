# Preserve the two existing XH3 epoch pool-state bits

Inherited slw_hc2__cl6bcaba89 actual LEC FAIL:109446/109455 points prove,9POOLc bits differ; the only gold unmatched live state is e_pool[0:1]. RTL writes these2unkept array bits and kept per-epoch replicated e_poolc0/c1 on the same selected write; native synthesis merges the unkept bits into replicas, while independent gold retains separate cutpoints. No failed result is relabelled.

Candidate adds only keep=true to the existing2-bit state array in qfd_dv_s5_xhead3.sv. No statement, port, reset, clock, arithmetic or pipeline cycle changes. Expected physical cost2retained FF (~0.5832um2), to be measured on actual synthesis. This is a structural preservation candidate, not a LEC waiver or generic correlation relaxation.

run_lockstep.py extracts the real3epoch-write statements, realforwarded pool selector and real9bitPOOLc update from baseline and candidate. Lockstep4096edges/12288checksPASS at833ps; a wrong-epochwrite mutant is caughtedge3. This qualifies the altered mechanism only. Actual full-size native synth + full LEC --jobs4 is live intel1:/srv/opentallas-scratch2/claude/codex-qc-wave-2249/hc2_pool_keep/slw_hc2__cl6bcaba89 (unit3640963, outputlec_pool_keep). At commit time synth in ABCtop; retention/fullLEC pending. OriginalLECFAIL remains in inherited kit and own copiedlec/lec.json. NoPLACE/ROUTE/SIGNED claim or source adoption until actual gates pass.

## Explicit-reset parked update 2026-10-30 00:03 PDT

Attribute-only version fb646e7df measured native retention FAIL: no e_pool[0/1] state wires or FF and total84222FF unchanged. It is not adoption eligible. Its fullLEC diagnostic control remains live (unit3640963 on intel1); ot-run --cancel detached only its hub client, explicitly reported that started commands continue. No inherited job was killed.

Current candidate changes the two existing unpacked bits into a kept packed reg[1:0] e_pool, as the nearby kept vector replicas already use. Indexed reads/writes unchanged. Actual array->packed mechanism lockstep4096edges/12288checksPASS; wrong-epochmutant caughtedge3;0addedcycles. Full actual native synth + fullLEC --jobs4 launched before reset on intel1 unit3883783-1793343469, path /srv/opentallas-scratch2/claude/codex-qc-wave-2249/hc2_pool_packed/slw_hc2__cl6bcaba89, outputlec_pool_packed. At explicitreset synth is in ABCtop; native2FFretention/fullLEC PENDING. Shared source adoption waits root approval plus actual gates. All live jobs preserved, engineering stopped on reset. No post-reset engineering or new jobs.
