PV native core view canonical proof-metadata correction

Reader 813a380fc uses canonical superset_vec.all_shown and falls back to the legacy top-level field only when the canonical field is absent. Canonical false/None is retained. Four exporter tests pass, including six coverage cases, normal view export, and stale-signoff rejection.

The new complete view is on Intel1 at /srv/opentallas-scratch2/claude/codex-pvb-tt-0108/native_view_w80_superset/ot_qwen_tp8_pv_join_t. The old native_view_w80 remains intact. All 26 payload files, including native LEF, TT/FF models, pins, separately measured native clock witness and pair tables, are byte-identical. Only provenance and gates metadata differ; every gate except routed_lec_all_shown is identical. The corrected value is true from the actual EQUIVALENT18181/18181 final mapped proof. No CAD or proof was rerun.

Physical source remains d0418b5a0, source build e8cbe5f6c704931d26fe9a4c547aa93a74977981; reader capsule copies that source and changes only export_view.py to 813a380fc. Native final proof/readset/DB/SPEF/RTL/clock graph remain under t10_w80 and the original 79b8fe891 closure packet. No released flow tag or parent expansion is asserted. Historical physical failures and the original null-metadata export remain preserved.
