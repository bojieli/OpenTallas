# DIE-QC-57 QC landed value event (COORD 18:0x (5) + 21:4x: variant A2 approved)
On top of claude/die-qc-56-ptw-1031@345b2ee7941 (per-type windows + seam_ps 110). plan_qc52 clock.landing_network.count_aligned_cycles:
+1 on 178 crossings (plus1_A.json; ring-guard low side on the gen55a die clock) and -1 on 8 sl_*_hc3 crossings (delta_A2.json; hi side
at the as-built DEPTH 4). DEPTH unchanged, no tree ports moved, latency.lanes recomputed (main gen.latency_table), rest byte-identical.
Proof: gen55a (intel2 die-qc-52/r55a) --physical-paths proof (51,476 nodes): START hop 400 um reach_fail 0, 3380 edges clean (evidence/start_P400_run.log).
Derived RTL K: bind/sidecar.json (= qc_die33 sidecar, sched_lat/K/added_cycles moved on the 186 ports), fresh R8 + CB16 via run57.sh (DIE-QC-33 chain).
12.25 gate (main die_sta_related, nominal, --count-align, as-built depth): BLOCKED(kits), contracts 0, TT +156.79 (evidence/).
Strict bind final: 1 error = EMIT collector rst_n_t18 (pre-existing on the base plan; base = 31 incl. 30 R8_STALE), 0 new, 0 type splits.
