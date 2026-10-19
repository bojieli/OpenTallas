# S81 existing fleet pickup, 2026-10-19 16:01–16:02 PT

Read-only continuation of 38ac12f1f. No source changes, launches, submissions, cancellation, rerun or native/STA engine. Four per-host JSON records include actual UTC snapshots, selected PIDs/commands/RSS/CPU, exact log path/size/mtime/SHA256, bounded text extracts and full selected machine-readable metrics.

| Existing frozen run | Actual status | Remaining scope |
|---|---|---|
| mu2 6050bfac9, ep7 PID2329250 | GRT extra15/30, live109% CPU | final routing/STA/native/PG/pair-clock |
| mu1 a218435f6, ep8 PID724195 | GRT extra24/30, live111% | historical comparison only |
| case_mab ep8 PID1174997 | GRT extra21/30, live110% | final source-pinned verdict |
| mu3c3158fce1e, ep7 PID3654923 | GRT extra6/30, live112% | strict1182/open39 FAIL remains separate from finalceaed1182/open28 |
| SVC lp/lp_np/entry_lp53ccd5927 | three original Yosys PIDs3743357/3743383/4069913 live108–112%,32.6–34.6GiB | no terminal receipt; stale JSON is not liveness |
| old HOP wrongcopy ep7 | terminal64286 cycles,693 inputs, **0 output checks**,0 fault cycles | unqualified like the three earlier zero-check runs; no numeric/mutant PASS |
| TOPK succ88450eee4 ep7 directory113938 | **CTS_RC137**, clock/path/layout/GRT skipped; SCRIPT_RC0/GATE_DONE | terminal CTS FAIL, cause UNKNOWN; no OOM attribution or automatic rerun |
| TOPK succb07fb519c3 ep4 directory114414 | GRT extra14/30, PID541823 live162%,5.5GiB | existing TT/FF158.6/138.1ps spread FAIL80; full SAFE/native/PG remains open |
| SHs10 source40261329f ep6 directory115854 | terminal: **ERROR GRT-0232 congestion too high**,146 congestion; flow_errors1 | GRT_RC0/SCRIPT0 do not erase failure; no final timing fields, native/PG/scene qualification open |
| C199rq b4648a6e2 ep7 directory114903 | CTS_RC0, original CTS PID exited; post-CTS ck.log created15:59, no ck.json yet | CTS raw setup+0.450/hold−40.816ps,7 slew violations; data fanout1060 unsafe; no final gate verdict |

SHs10 identity is the exact ep6 running source archive `a5bc886ad0136b86f7f0890265fab0b13283d88e4bda654038a00b4b13af4404`, not historical SHs10w archive36b2f4a7/source9c5 or current SHs10b3ebb/archive887920a7. Its final GRT metrics SHA `7f663c558c8b87d44bca6aeb06ef54b8e8b84b44a1ebd72cf668e6212ed98eec` report flow_errors1 and lack final setup/hold measurements. Actual read_liberty records explicitly load TT+FF cell/macro files. WC is a label overridden to TC in this frozen flow (prior exact configuration retained in38ac); this is not SS signoff. Separate placement-RC TT GATE_PC setup−35.2427/hold+33.3936ps and TT/FF spread78.1/70.3ps remain their own diagnostic scope, not successful route or matched-neighbour qualification. No canonical scene-load helper fix was applied or rerun; current helper49f qualification does not transfer to these frozen jobs. SHs10b terminal/native results are separately owned and untouched.

TOPK CTS137 is retained as a stage failure; wrapper zero only reflects the script. Cause is UNKNOWN: this packet does not join boot ID, native cgroup, actual process incarnation and stage interval and makes no OOM claim. C199 post-CTS top-level inventory and broad read-only process listing are supplemental; unrelated listed processes are not assigned to C199 without a native identity join. No unqualified process disappearance is promoted to an exit code.

The bounded collector's first attempt failed locally while requesting a nonexistent historical ep8-progress capture, after three remote reads; no remote job changed. It was corrected to accept absent historical capture files, then all four selected reads completed. The final snapshot is immutable here. Oversized embedded image lines are shortened with original character count; log hashes identify full remote bytes, not image contents or saved full logs. Completed terminal receipts and all actual failure lines remain; temporary files disappearing after rename are recorded as absences, not new failures.

Next pickup: same die run.log paths and selected live PIDs; TOPK succb final GRT; C199 ck/placement/GRT and true final wrapper verdict; three SVC terminal outputs. Preserve all existing jobs. No automatic rerun, scene reload, native qualification, SU/MU token or release claim follows this packet.
