# S81 gather FLATTEN composition bench (214 CLOSED children), source 46ce57d97

Command (ot-run, ot-epyc1tb unit oth-ubuntu-3962075-1792081165, 2026-10-15 09:13-09:25 PDT):
`SSA2=1 LOCAL_BANKS=1 CONTROL_STRIP=1 DIE_CLOCKS=1 RESTART=1 J=4 bash rtl/dsrom_sys/s81_ph/test/run_gather_cl.sh <snap> <snap>/gcl rtl/dsrom_sys/s81_ph/test/real_order_trace.json '0 2 14 20'`
(the trace holds layers 2 and 20 only; L0/L14 stimulus generation is skipped by the script).

DUT: `dsfd_sp_gather_c_cl` (generated, `gen_gather_cl.py --check` current) = exactly the 214 children of the flatten plan
(32 leaves + 48 lane/result relays + dsfd_gth_ctl + 133 strip relays, 214 clock entries) in lockstep with the flat
`dsfd_sp_gather_c`. Verdict: `GATHER_CL_GATE PASS (15 runs)`: 6 positive (real L2 37,440 rows / L20 37,312 rows exact,
stress, orphan, ovf fail-closed, refuse) and 9 mutants all FAIL as required (chain, decision, heap, lane, nofwd, ovf,
rstreg, select, xgo).
Static schedule (open-loop driver, deterministic=1, issue_wait 0): c_cmd -> t_xgo 9 cycles always; drain -> c_done
10..11 cycles, fixed per ck/ckv related-clock hyperperiod phase (phase 0: 11, phase 1: 11, phases 2/3: 10) -- the
compiler must take the phase-keyed value.
