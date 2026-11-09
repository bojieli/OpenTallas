# rest_1c counted RTL onto main source paths (HBM-HARD-9, 2026-11-09, COORD 03:07 HOLD row)

The counted ot_hgi_sfu_split3_ctl_rest_1c record (epyc4 hbm-hard-3/eco/rest1c_rrfix_e1/i1) was built from kit RTL that never sat on main's source paths (COUNT-DNC-RTL-1109: NEVER). This commit puts those two files on main:

- ot_hgi_sfu_split3_ctl_rest_1c.sv = kit file, with only the face-shell rename __fcore reverted to the main module name.
- ot_hgi_sfu_split3_ctl_rest_core.sv = kit file, byte-equal (md5 fa54d250).

The additions are parts 50/56 (gen_p50.py; Codex a900579ec84 RR fix), all behind `ifdef OT_REST1C_SCALAR_OPIPE / OT_REST1C_SCALAR_PIPE1. Default build, no define: pp.py strips the guards. Result: core equals main with all whitespace removed. rest_1c differs only by a wire alias: __p50_scalar_d assigned to u_core_u_vm_scalar_data and used in its place. So no build without the define changes function. The counted kit builds with -DOT_REST1C_SCALAR_OPIPE, a +1 scalar pin cycle declared by its form. Its routed LEC is EQUIVALENT against exactly these files.
