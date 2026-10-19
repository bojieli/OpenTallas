FACES terminal witnesses

Both existing r3 MU_NU=4 builds completed on ot-pve1 without restart. MUT11 reports XC cc count 1 and FACES MUT=11: FAIL 1; MUT12 reports GATHER tokens 5007 instead of 2007 and FACES MUT=12: FAIL 1. Both finish at 162 ns with Verilator 5.050. Bench $finish and outer job exit 0 are expected packaging behavior; the behavioral FAIL lines are the mutant witnesses. The original 143/empty outputs are not used as witnesses.

This closes collection of these two legs only. The complete 44-leg table and the separately classified stale coll_mu_bi recipe correction must be composed by the regression owner before Q.STA.MU.REG can be marked done.
