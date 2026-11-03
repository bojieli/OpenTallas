# TOK-QW-4 (Qwen/KV token path; succeeds TOK-QW-3, died ~19:5x 11-02)

## 2026-11-02 22:36 PST START
- Worktree rtx-pro /srv/opentallas-scratch/claude/wt/tok-qw-4, branch claude/tok-qw-4-1102 from claude/tok-qw-3-ledger-1102@9c8b2811e (NOT yet on main; c732dd10e + c2aeae5b4 are).
- Inherited jobs [CHECKED]:
  - KV NOWAIT veh60 intel1 oth-ubuntu-2990777-1793672394: ALIVE, HB cyc 40000 at 22:25 (~2.7 cyc/s). Boot images 14/14 fault 0, SETUP 38493, KVSLICE_START 38623, HOSTTOK_SENT 38688. No boot_go POSTOBS change by cyc 40000 (FX reference: boot_go 20 cyc after HOSTTOK). Collect at HB 60000 (~00:30).
  - QC census intel2 oth-ubuntu-370950-1793677572: TERMINAL MEMCG-OOM at its 64 GiB cap 19:54 (exit 143) in verilator --json-only = frontend blow-up already before V3Scope. No census output.
- OWNER: Codex native stage37 canonical. Open items: (a) table-install window vs stage36 traffic, (b/c) leases + dates, D2H boot replay check; then e2e native token pass.

## 2026-11-03 00:13 PST RESULTS
- (a) stage37 install window MEASURED: results/token_pass/qwen_head37_install_window_1102 (branch claude/tok-qw-4-1102@75c22e1fa, results-only). Loader occupancy 90 edges between LOCAL4/LOCAL37 range starts (89 faults all 12 slices; CTLM never faults). CTLM37 gate's 65-edge spacing faults all 12 slices. e2e: CTLM start E -> load E+9 -> writes E+15..E+94. Native s_we = 0 (no TLOAD entries in nent1021). Boot 148 ranges at 90: 0 faults, exact writes. RULING: BOOT install after stage36, resident, >=90 spacing.
- D2H boot replay check MEASURED: results/token_pass/kv_boot_d2h_check_1102/summary.json. 4 STATUS ready=0 words (1191..1872), none during replay or after START. Native veh60: boot_go_d1_hgi_WN_7 never rises after pad START (FX: START+18). NOWAIT run = defined FAIL (left running, 1 core). Owner: KV vehicle START provider join (pst_hroot_*, held per Codex 11-01).
- QC whole-die vehicle: static census (intel2 tok-qw-3/qc_census/static_census.txt) + ROM_TILE finding: 768 distinct ROM_TILE defparams (veh0/rom_bind.vh) specialise the whole compute-tile subtree 768x. Test census2 (json-only without the defparams, 64G) LAUNCHED intel2 /srv/opentallas-scratch2/claude/tok-qw-4/qc_census2.
