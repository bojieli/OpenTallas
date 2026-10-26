# Dry run on PATH-KV-BIND probe p1 (in-progress strict-bind attempt, 149 bind errors; diagnostic only, 2026-10-25 20:50)
Snapshot of epyc1:/srv/opentallas-scratch2/claude/path-kv-bind/p1/bus_groups.json (sha256 in bus_groups.sha256), run with
`NO_CONTRACT=1 KST=56,55,53,53,53,54,54 run_mu833.sh` (KST forced: kst.py refuses the bind, see 2).
1. Boot ABI bounds still overflow on the folded plan: PV RL/FIRST_INPUT_AGE 130/131 (> 127), V port RT max 50 (> 31),
   W request pads up to 60 stages. Same cause as dry_run4: the PV lanes, not the bind errors.
2. Seam landing not uniform per bus (kst.py needs one depth per bus): kvs_attn d2d__srx {54,55,56}, d2d__rx_payload
   {50,51,56}; d2d_kv att_tx_v 55 vs att_tx_payload 45 (valid and payload of one bus 10 stages apart). kv41 had one value
   per bus (34,34,32,32,32,31,31). A strict bind must land each seam bus at one depth (or the pair image needs per-bit stages).
3. Compile stops in emb_fill: "join start 6 edges after the fan root start" (embedding fill fan relays unequal) - re-check
   on the strict bind.
