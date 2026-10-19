# Existing S81 run pickup, 2026-10-19 14:46 PT

Artifact only; no source edit, launch, restart, cancellation, submission, or qualification. Extends artifact907aa1fc4. Raw captures are attached; clocks use America/Los_Angeles.

| Frozen run | Actual state | Next dependency |
|---|---|---|
| mu2, source6050bfac9, ep7 unit2329132-1792417844 | GRT extra12/30, PID2329250 ~109%CPU/45.8GiB | Preserve chain; final GRT/STA/pair-clock and native electrical/reach classification |
| mu1, sourcea218435f6, ep8 unit724034-1792409869 | GRT extra21/30, PID724195 ~111%CPU/45.9GiB | Preserve historical comparison chain |
| case_mab, ep8 | GRT extra17/30, PID1174997 ~110%CPU/47.5GiB | Final route/STA classification, not production proof |
| mu3c, source3158fce1e, ep7 unit91011-1792434967 | GRT extra2/30, PID3654923 ~105%CPU/40.8GiB | Source strict1182/open39 remains FAIL; finalceaed1182/open28 separate |
| SVC lp/lp_np/entry_lp source53ccd5927 | Three synth.tcl FSM_DETECT processes3743383/3743357 ep7 and4069913 ep6, ~103%CPU/31–32GB | Whole-storage/contact/native qualification remains open; stale sources-error JSON not terminal |
| oldHOP base_tagdrop, ep7 unit2522427-1792419861 | Terminal14:29 exit0,64286edges,687events,out_checks0 | Existing endpoint and strict trace check chain must finish; simulator PASS is not numerical or mutant qualification |
| oldHOP base_wrongcopy, same unit | Existing binary reused; PID120653 ~99.9%CPU/707MiB, started14:29 | Existing chain449774 waits on client4150465, no duplicate |
| TOPK succb source07fb519c3, ep4 directory114414 | CTS finished14:44, ck_insertion active; raw setup−59.0555ps/hold−60.3795ps,16macros | Await final source-pinned gate verdict and classify; no submit |
| TOPK succ source88450eee4 ep7 directory113938 | CTS repair live PID4089104, ~117%CPU/3.68GiB | Last CTS progress setup−85.602ps; not final gate |
| SHs10 source40261329f ep6 directory115854 | GRT PID4183827 ~133%CPU/2.3GiB | Native/depth/PG/SAFE and final gate open |
| SHs10b source3ebb699a9 ep7 directory122430 | GRT PID55684 ~167%CPU/2.3GiB | Last repair setup−178.614ps to host.hr_d401; not terminal |
| C199rq sourceb4648a6e2 ep7 directory114903 | CTS PID4043172 ~104%CPU/3.36GiB | Last repair setup−25.519ps to g_l7.w_r6; data fanout1060 unsafe |

Paths: die runs /srv/opentallas-scratch/claude/mu-die-s81/case_{mu1,mu2,mab}/out/run.log; mu3c /srv/opentallas-scratch/claude/s81-diechain/mu3c/case_mu3/out/run.log. Element runs /srv/opentallas-scratch/claude/ref_gate/<name>-20261019-<directory>/routes/gate/work/orfs/logs/asap7/<design>/base/. HOP /srv/opentallas-scratch/claude/mu-die-s81-hop/out_{base,base_tagdrop,base_wrongcopy,rtl_tagdrop}; local chain /home/ubuntu/scratch/mu-die-s81/hop/logs/chain_ep.log.

SHs10w907aa1fc4 terminal WARN and unsafe depth/native remains separate; no receipt transfer. CAPC/selected leaves b3ca80895 PG_HOLD remains. Original strict SU/MU1324/2628 and strict bind1182/open28 failures remain immutable; no full token or multi-user qualification. REFILL023389, rawQF3254c1060 and HB1357fb55e2 already collected and deliberately not repeated.
