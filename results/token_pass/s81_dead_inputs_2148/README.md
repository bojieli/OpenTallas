S81 declared-dead input implementation, COORD2026-10-25 21:21.

Yosys read_slang, proc and opt prove 126082 current tied bits have no fanout after optimization. The36 declarations cover16 actual partition types;21 distinct module/parameter specializations. Every child input is conservatively live, and top outputs are live. Exact source module SHA, full parameter map, partition type, port and bit must match before the binder accepts a declaration. Functional/changed-source/type/parameter controls are rejected. No new type or latency cycle. The864 cfifo.lk bits are exact known per-position ID words (72 instances), preserved as declared straps.

Reproduce: `PATH=$HOME/.local/opentallas-tools/bin:$PATH python3 tools/die_plan/s81_dead_prove.py --root . --instances results/token_pass/s81_dead_inputs_2148/instances.json --stubs results/token_pass/s81_dead_inputs_2148/blackbox_interfaces.sv --out /fresh/output/path`

This is source binding evidence; no physical or full token signoff. Original v10 strict failures remain preserved. The current whole bind must be regenerated with all source fixes.
