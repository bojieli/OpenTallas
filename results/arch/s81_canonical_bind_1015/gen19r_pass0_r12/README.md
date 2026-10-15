# GEN19r construction pass 0 port bind (S-DIE r12, 2026-10-15)

Source: EPYC4 src19 synced to main 8cf85bdca (hop-detour fix 0fed0e3ff), recipe s81_layer1_gen19r.opts
(contract v22 HC return columns, --hc-corr 1226.88), --expect-manifest PASS (source_binding.json).
Legality pass 0: 78,288 instances, 0 overlap, 0 outside.

tools/die_port_bind.py on construction_pass0_die.v + die_glue.sv against physical/s81_die_rtl/layer1.f (current main):
FAIL, 4 masters (GEN18r frozen snapshot had 9): width_mismatch 6, input_unconnected 8, 0 unbound/stub/unknown/undriven.
- dsfd_bf_front x519 xb unconnected -> BF x2 static transport (--bf-x2-static) needs a second street for the 1,102-b tree (S-DIE) + BF programme producer (S-BIND)
- dsfd_host_c f_collective 515 vs 516, t_collective 77 vs 81 -> static host (native host owner)
- dsfd_sp_pq_n ra2 12 vs 14 (4-macro stream ROM, S-ELEM-B), t_cnt 456 vs 458, xe/xw 565 vs 1101 (x2 static PQ, same BF item), f_iss (PQ issuer composition dsfd_sp_pq_produced)
- dsfd_sp_vm f_mx_* unconnected -> MIX4 master + home (S-ELEM-C / S-FUNC)
Not a physical or native qualification.
