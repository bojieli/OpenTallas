# Actual mu4 main-checker failure beneath wrapper exit0

Collected 2026-10-20T00:43:37+00:00 from the original live diagnostic on ot-epyc7. No source, job, objects or live process was changed.

The runner explicitly calls the second check non-fatal and labels the physical case PILOT_NOT_A_GATE. BIND_RC0 uses the old binder. MAINCHK_RC0 is the dv_diecase wrapper status, not the strict checker verdict. The actual main-checker port_bind.log and JSON say DIE_PORT_BIND FAIL: unread_net_bits1182, output_open_ports28, all other structural counters0. Missing roles include col_h9/h10_l4, svc_rs/entry, HBM PHY and four LEP masters.

This progressing mu4 physical chain remains useful diagnostic evidence of corridor repeaters and405um census. It cannot establish current strict binding or release-die qualification. The separately repaired mu4c19bf4121e source is unread0/open10 and still needs the genuine SM target/return composition. Neither result is a strict-current-clean die.
