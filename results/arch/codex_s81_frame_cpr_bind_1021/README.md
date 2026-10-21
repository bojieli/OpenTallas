# CPR frame source integration

Source generator `tools/s81_dv/frame_cpr_bind.py` emitted distinct `col_h9_l4_lp_cpr` and `col_h10_l4_lp_cpr` from exact FRRST2 functional twins at 21b97190e. Each retains all twelve actual Q instances, their INSTANCE expressions, the full reset-landed ABI, and three receiver roots. Only Q parameter lists take the complete CLOSED cc0ec1c19 receipt profile (including CPR=1); BF instances and wiring are unchanged. Matching XS compilation requires OT_XS_Q_CPR=1, already supported by main's Q-only launch advance.

The emitted source and exact parameter contract are under `rtl/dsrom_sys/s81_dv/frame_lp/cpr/`. `overlay()` composes these distinct module names onto the explicit72 table, preserves raw pin plans and orientations, and deliberately supplies no old non-CPR parent kit/view as qualification. There are 864 Q children for the selected72 population.

CPR physical leaf export is being recovered separately from the actual closing routed ODB. No parent physical closure or CPR-parent functional qualification is claimed. Existing rf3rlfs1 gates remain non-CPR and continue independently. Source generation only; no new test, audit, or gate was launched.
