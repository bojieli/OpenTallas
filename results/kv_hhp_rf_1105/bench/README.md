# qkd_kvs_pcc_h_head_p form bench

run.sh runs random lockstep benches of the form RTL against base, plus control mutants.
Last result (b6): 30 lockstep PASS, 39 mutants CAUGHT, 0 MISSED. No formal old-vs-form proof.

## After a fault (form B, COORD ruling 2026-11-05, no !fault_schedule gate)

- Recovery is by reset only [CHECKED RTL].
- The faulting slot stays off the column pins, and the fault reports on the same edge [CHECKED RTL].
- Later commands after a fault may carry different addresses than base [CHECKED RTL].
- The parent has no calendar stop on fo: the current calendar keeps issuing after fo until the host ends the run, same exposure as base.
- NOT TRACED: the link "abort token stops the next stage start" is [inferred].
