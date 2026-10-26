# KV MU833 image on the PATH-KV-BIND strict bind b12 (2026-10-25 21:20, TOK-QK): NOT COMPILABLE yet
Bind: epyc1:/srv/opentallas-scratch2/claude/path-kv-bind/b12 (bind.py --strict rc=0: 160 partitions, 51 types, 2545
crossings, 0 errors/unbound/tied/undriven/multiply-bound; recipe kvbind1025/recipe_b3.json lives in the uncommitted BIND
tree, so this is not yet rule-3 evidence). bus_groups sha256 in bus_groups.sha256. Flow: run_mu833.sh (NO_CONTRACT=1, KST
forced to the per-bus max 56,56,50,50,50,55,45 only to look past item 1).
1. SEAM BUS SKEW (bind item, blocks the pair image): one source bus lands at several depths:
   d2d_kv.rx_payload -> kvs_attn.d2d__rx_payload: L345 bits 0-1 at 50, L346 bits 2-60 at 51, L351 bits 61-547 at 56;
   d2d_kv.kvn_word_data -> kvs_attn.d2d__srx: L351 bits 10-60 at 56, L352 61-72 at 55, L353 73-521 at 54;
   d2d_kv.att_tx_v 55 vs att_tx_payload 45 (kv41: equal, 31/31). A word whose bits arrive on different edges is corrupt
   under the static schedule: the bind must equalise the lanes of one bus (pad the short lanes to the longest) or the
   plan must carry one lane per bus. kst.py fails closed on it (correct).
2. BOOT ABI BOUNDS (RTL/plan item): PV RL/FIRST_INPUT_AGE 130/131 > 127, V port RT max 50 > 31, W request pads up to 60.
3. emb_fill: "join start 6 edges after the fan root start" (embedding fill fan relays unequal); the compile stops here.
