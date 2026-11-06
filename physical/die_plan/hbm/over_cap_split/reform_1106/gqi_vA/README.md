# gqi_issue vA (DIE-HBM-82-COLL 11-06)

Routed Codex vB2 (registered faces, util 0.45) missed TT by -135 ps on 1,524 endpoints. Measured on the routed DB:
930 end at the aq_x output faces (start g_src), about 400 at p_d (start g_r2 / ev_k), and the rest are about -50 ps or better (rf, b1, vm_rq, ex, a1, g_src).
The worst path spends about 520 ps in the select/mode decode of g_src, g_r2 and ev_k and on its 43- and 64-fanout nets (slew 160-220 ps) before it reaches the 8:1 read mux. The mux itself takes about 350 ps.

Fix (rtl/hbm_accel/cores_split/reform_1105s/gq/ot_hgi_coll_gqi_issue.sv): the aq_x and p_d bank selects, the p_d source mode and the exponent-byte write enables are registered one edge early. They are computed from the next state of the gather registers (fire ? rc : g_*) and of the event pipeline. The 512-bit ex clear on fire becomes a 1-bit ex_z flag that is applied on read. The retiming is exact and adds 0 cycles, so the pins and schedule are unchanged.

Proof: runbench.sh runs a Verilator lock-step of the original (git HEAD) against vA. Every output is compared on every edge. The internal programme-target outputs are forced to random F20 rows and starts, and every other input is random.
Mutants of the change (stale g_src, no ex_z, ex_we one stage late, stale g_bs, aq_sel one stage late) and the original MUT 2 must all mismatch.
