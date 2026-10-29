SYS_C historical LEC failure diagnosis, 2026-10-29

The old sys_c_directed/out verdict NOT EQUIVALENT 33,164/37,725
(4,561 differs, 3,555 compare failures) was produced by pre-monotone
lec.py 0d1e7a780. Its log shows round63 still had5,496 hypotheses,
6 counter constants failed, then the expired refinement budget cleared
all correspondence. The broad final failures are fallout of that collapse;
they do not demonstrate 4,561 independent RTL errors.

Current origin/main already implements LEC-FPREG-3 monotone finish:
drop the failed candidate and transitive raw-next-state dependents,
then require the surviving full set to prove inductive. The existing
regression test includes a long false-constant chain and a wrong-data
mutant. No new shared tool change is needed.

This diagnostic loads exact retained gold/gate AIG+maps, creates ONLY
untrusted constant candidates for the3actual failed counter families,
and inspects the current raw_support/cascade_drop functions. In3.17s,
3failed counter seed bits remove32 dependent candidates while29 unrelated
counter candidates remain. No candidate is accepted, no equivalence
proof or current-source qualification is claimed. The current code avoids
the old global-clear mechanism on this actual dependency graph.

KV owner agrees: no 2h historical fullproof rerun. Old kv5-i2 q3 is
not a regenerated current release kit. KV-KITS uses current lec.py on
its next current sys_c kit. Old failed records remain unchanged.
