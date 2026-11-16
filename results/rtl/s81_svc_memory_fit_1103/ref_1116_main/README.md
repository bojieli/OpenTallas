# MAIN-source svc closure reference, 2026-11-16

ref_1116 was generated from the older G3b lane source (dsdv_svc_att.sv 1016 lines); F2sv/F2s binds use the MAIN-source 1099-line source. Both F2sv pilots therefore refused the old reference. This packet regenerates the reference from the MAIN-source F2sv svc_lo_dsdv_svc_rs__t7 bound. The old reference and failed pilot evidence remain intact. No RTL, arithmetic, interface or cycle count changes.

Regeneration: s81_svc_ref_regen2.py with --drop-loc ot_hdc_v41x_attn_s.sv --drop-loc ot_hdc_v41x_attn_tile_s.sv --modes all,def,any,def,any,all and the original/main dsdv_svc_att.sv + dsdv_svc_rs.sv source-line maps. Original self-check 12605dc2 PASS; current closure 8e3c91c7; closed residual equals preimage residual exactly ([1185,2079]); no transformed token in the residual. ref_map.json and regen.log contain the proof receipt.

All 16 F2sv/main-source bounds CLOSED (family_closure.json). All 16 fresh kit-RTL closures APPLIED, including index-memory fit (family_applied.json). apply_family.py reuses a closed bound only after the canonical preimage SHA and closed SHA both match. The fit bench passes 20,000 edges and catches all five independent mutants (fit_gate.log). The optional pytest unit invocation on epyc8 did not run because pytest is absent; it contributes no passing claim.

Physical svc-ready remains held until coherent current plan/bind/tree pilots pass the macro-placement and routed-RC criteria. The older t6/hi4 synthesis jobs are evidence-only nonclosure forms, not release pilots.
