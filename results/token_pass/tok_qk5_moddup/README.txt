TOK-QK-5 2026-10-27 10:32 PDT: check_moddup.py on the actual B48 Verilator list (intel2 tok-qk-b48/build3/vl.f, copy b48_vl.f) with --drop-redundant (build.sh mode).
base:       FAIL rc=1, 3 identical later copies dropped, 1 real duplicate: ot_qkvd_kcmd_tap defined in ot_qkvd_kcmd_tap.sv (1 register stage, n=1024)
            AND ot_qkvd_kv_desc.sv (2 register stages, per-PC n) with DIFFERENT text. Verilator keeps the first listed (kcmd_tap.sv);
            yosys read_verilog -overwrite (bind_elab.py) keeps the last read. Owner must delete one definition (RTL cleanup).
base_allow: PASS rc=0 with --allow ot_qkvd_kcmd_tap (control: nothing else duplicated).
mut:        base + the boot-window qkd_ctrl_pc_nc.sv appended (the r4 old-vehicle4 + fixed-copy mix): FAIL rc=1, qkd_ctrl_pc_sched_nc DIFFERENT text
            (3a71f56bf1cc vehicle4 vs df4a9ca3fbef boot window) caught; 3 identical-text siblings also reported (same file listed from two trees).
Unit tests: test_check_moddup.py 9/9 PASS. Work dir intel2:/srv/opentallas-scratch2/claude/tok-qk5.
