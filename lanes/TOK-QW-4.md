# TOK-QW-4 (Qwen/KV token path; succeeds TOK-QW-3, died ~19:5x 11-02)

## 2026-11-02 22:36 PST START
- Worktree rtx-pro /srv/opentallas-scratch/claude/wt/tok-qw-4, branch claude/tok-qw-4-1102 from claude/tok-qw-3-ledger-1102@9c8b2811e (NOT yet on main; c732dd10e + c2aeae5b4 are).
- Inherited jobs [CHECKED]:
  - KV NOWAIT veh60 intel1 oth-ubuntu-2990777-1793672394: ALIVE, HB cyc 40000 at 22:25 (~2.7 cyc/s). Boot images 14/14 fault 0, SETUP 38493, KVSLICE_START 38623, HOSTTOK_SENT 38688. No boot_go POSTOBS change by cyc 40000 (FX reference: boot_go 20 cyc after HOSTTOK). Collect at HB 60000 (~00:30).
  - QC census intel2 oth-ubuntu-370950-1793677572: TERMINAL MEMCG-OOM at its 64 GiB cap 19:54 (exit 143) in verilator --json-only = frontend blow-up already before V3Scope. No census output.
- OWNER: Codex native stage37 canonical. Open items: (a) table-install window vs stage36 traffic, (b/c) leases + dates, D2H boot replay check; then e2e native token pass.
