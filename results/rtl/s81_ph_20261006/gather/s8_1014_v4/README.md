Gather v4 'direct' (claude/s81-gather-1014 @5de8be14f RTL), EPYC1 2026-10-14, Verilator 5.050:
full 128-root / 32-leaf cluster (SSA2 LOCAL_BANKS DIE_CLOCKS CONTROL_STRIP; 48 lane/result relays, strip v2) vs flat
dsfd_sp_gather_c, shift R(c)+R(k)-2 (R = 0,0,1,2): GATHER_CL_GATE PASS (15 runs) -- real_L2 37,440 / real_L20 37,312 rows
0 mismatch, stress, orphan PASS, ovf fault observed, refuse REFUSED; mutants lane/chain/nofwd/xgo/ovf/heap/decision/
select/rstreg FAIL (own_co dropped: the v4 leaf has no own-output role).  Startup (startup.sh): 6/6 PASS (early command
1/4 x reset phase 0/2/6, drained restart); EARLYSTART mutant FAIL 2/2.  cluster/sources.sha256 = exact inputs.
First v4 run (before c2c994bfd's E-half lane fix) failed 4/15: E leaves took the wrong lanes -- fixed in the generator.
