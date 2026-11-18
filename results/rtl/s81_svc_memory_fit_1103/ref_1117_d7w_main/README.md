# ref_1117_d7w_main: svc memory-closure reference of the S81 D7w bind (FABLE-FIX-S81-SVC2, 2026-11-17)

Why: kit_rtl of svc_lo rs_w__t1 / rs__t2 / t3 / t6 on D7w (plan_h2_2249, src 3c913dbdfb23) failed with
"reference net 673_Y not structurally mapped". The svc sources are byte-identical to the 11-16 main copies, but the
D7w bind stages dsdv_svc_att.sv under digest d233b310c719 (ref_1116_main: 377d1b188a0c), so every src_<hash> net name
differs and the closure signature (which keeps src_ names) finds no unique pair.

How (one command per bind event; the tool then picks the reference by stage digest, see cur_ref()):
  python3 tools/die_plan/bind.py kit-rtl PLAN --out BIND_OUT --asbuilt ASBUILT --type svc_lo_dsdv_svc_rs__t7 \
      --src-tree SRC --kit T7_RTL                      # unclosed T7 bound, no kit_rtl_post step
  python3 -I tools/die_plan/s81_svc_ref_regen2.py T7_RTL/s81p_svc_lo_dsdv_svc_rs__t7_bound.sv \
      results/rtl/s81_svc_memory_fit_1103/ref_<event>_main --old-src OLD --new-src NEW
  (OLD = dsdv_svc_att.sv + dsdv_svc_rs.sv of the 61c902f1 lane bind, NEW = the same two files of the bind source)

Result (epyc7 unit oth-ubuntu-3366712-1794986578, default modes): paired 5618, renamed 4263, residual 1276/2394,
no reference token in the residual, SELF-CHECK PASS 12605dc2, CLOSURE 64bee187 same_as_preimage True.
Family check with this reference (family_closure.json, unit oth-ubuntu-3482800-1794987031): the four failing bounds and
T7 all CLOSED: rs__t2 adafef62, rs__t3 3d11fd5f, rs__t6 711f63d1, rs__t7 72029575, rs_w__t1 1048725c.
NOT run: the Verilator fit gate (run.sh, 20k edges + 5 mutants; children unchanged since 11-16), kit-rtl mode on a live
kit, svc_hi / pvso / lo t1,t4,t5 bounds of D7w, pytest.
