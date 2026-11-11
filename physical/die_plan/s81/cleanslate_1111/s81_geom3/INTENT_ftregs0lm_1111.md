# INTENT FTREGS0LM-1111 (S81-GEOM-3, DO_NOT_COUNT)

Scope: 18 ft slots on the s_2N/s_4N ft lanes (up_s_2N_L0, dn_s_2N_L0, up_s_4N_L0, dn_s_4N_L0) in 10 types:
dsdv_slice_c1x_C__t10, leaf t43, t44__clf6cf8492, t52, t53 x2, t54 x2, t75, slice_station__t45.

Dataflow: each lane is a feed-through bus (up = toward bk_sel/N, dn = back south) crossing the leaf
partitions; inside a type, the in window -> regs[0] -> ... -> out window. The rule: regs[0] sat
more than 5 um from the in window, so the first leg inside the type was long and crossed core
macros (G0 found 598-bit station sites on u_lf.u_vsw and u_lf.u_vn.u_b). The delta re-sites
regs_um only, sliding each stage along the lane path toward its in window, on legal sites.

EQ by construction: positions only; station counts and lane naturals identical (report eq_gate).
Cycles: 0 change. Lane max hop after: <= 402.8 um on all four lanes (reach 405).

Base: r1 534706172e9c (claude/ds85-s4n-ftlane-1111@9f1afc9e, in COMMON). Output a6d6a5e9882e.
Same delta on BASE_1200 b5faa1ba alone -> cdfc906c4f2b (ftregs0lm_on_base1200_report.json).

Gates (epyc4 /srv/opentallas-scratch2/claude/die-s81-85/s4n/out/{c0,c1,rs_*}):
- G0 vs r1: 0 new errors, 1 gone (t54 cl501 dn_s_4N_L0x4 station-in-macro). Vs BASE_1200: 0 new
  for c0; c1 shows only r1's own cut text change (s_4N_L1 0.83 -> 0.71).
- check PASS, legphys PASS (0 new, gap 34.56), identity/taps PASS (5 advisory tap radius targets inherited).
- route_supply p99 identical to r1 on all 10 types (advisory; 8 FLAGs inherited from base, leaf class owns them);
  hot-bin counts +2..+27% on t44/t52/t54/t75, accepted (same p99, same worst region).
- explorer die: 873 links, 37 hop>reach (all svc/ws columns, none on s_2N/s_4N lanes), 0 cross unrelated.
Over-reach accepted: none added by this delta.
