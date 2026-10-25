# ot_s81eng_aq_n32 implicit-net fix (41f01591c2): verification record (S81-CORES3, 2026-10-25)

Fix: `ce`, `ep_next` and `dm_next` are now declared above the `g_ec` instance loop (rtl/ and the eng_rr_e kit rtl/ copy).
Before the fix, yosys-slang made them implicit undriven nets, so all 8 `u_xq.u_aq.g_ec[i].u_e` dm/ep exponent registers were TIELO.

## Scope
- `ot_s81sl_aq12x_eng_n32` is instantiated only by `ot_s81eng_xq_n32` (u_xq). Only `dsdv_eng_rr_e` holds u_xq; `dsdv_eng_rr_h0` and `dsdv_eng_rr_h1` do not.
- Eng views on main: only `physical/ref_tile/dsdv_eng_rr_h1` changed after aq_n32 landed (e684da414, 10-23). h1 has no u_aq.
  So no signed-off view on main needs a new sign-off. eng_rr_e has no view yet.
- Every eng_rr_e netlist synthesised before 41f01591c2 is invalid: the e1 kit, and the krepin c / m5 runs, which are already deleted.

## Bench: eng split lockstep (tools/s81_dv/eng_rr/bench_rr_split.sh, Verilator 5.050, ot-run epyc1)
- Fixed RTL (41f01591c2), base: `ENG_RR_SPLIT PASS base`. Lockstep 6823 cycles, 0 mismatches; ENG_RR_PY 288 rows, 0 errors.
- Fixed RTL, sm1 negative control: `ENG_RR_SPLIT FAIL sm1`, as required.
- Pre-fix RTL (26028effc), base: also PASS. The bug is synthesis-frontend-only: Verilator and read_verilog bind to the module wires.
  Only LEC can see it, and LEC is the gate.

## LEC (lec.py from claude/lec-eng-1025@ed2e798b6, diagnostic docker on epyc2)
- Netlist: e1r 1_2_yosys.v, synthesised from the fixed RTL.
  The yosys log has 0 'has no driver' warnings (the pre-fix log had 16).
- u_aq dm/ep compare points: all proved. 0 of the 120 points that differed before still differ or are unproven.
- Overall verdict is still NOT EQUIVALENT: 28614 points, 27263 proved, 1316 differ, 35 undecided, 155 failing.
  This is the residue the LEC lane already knows about:
  - u_lkp.u_e.r8: 148 points. LEC-CP1-INFRA 05:39 classed these as tool false negatives (missing pairings) on its an3 run; this netlist needs the same pairing.
  - head g_hw row / g_roff: depend on the gold-only hq_atom[30] and q_off; the q_off X is fixed by 99c01e3d9.
  - FSM recode (acnt/fcnt/icnt/ej/ek/slot/g_iss).
  - u_xq.g_cur: unproven, gate-only fck.
- Record: lec_eng_rr_e_e1r_aqfix.json.
