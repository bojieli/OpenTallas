# DIE-KV-49 one-block RX pin fix (2026-10-30)

COORD 20:48 ruling (RX ASK (a)): put the held qkd_hr_core_rx pin change into the KV plan of record (event28w_c) so the
signed core_rx e2 view (TT +1.13 / FF +9.07 / LEC EQ 19250) can be re-signed and counted.

- mk_rxpin.py writes plan_of_record/pins/qkd_hr_core_rx_pins_r26q5d.json (r26q5 + 4 pins: ownership_valid[0] <-> rx_d[263]
  swap on the W face; die_id[0]/[2] to the E-face centre beside die_id[1]) and repoints the one RX hard_cores entry in plan_c.json.
  Fail-closed: exactly those 4 pins and that one string change.
- Gates (proofs.json): G0C 28 -> 28 errors, 0 new / 0 gone findings; KV die clock replay IDENTICAL to sd47b (tree.json + ctree.v).
- Caveat (pre-existing, not a G0C finding): parent reach of ownership_valid (Codex 04:24 diagnosis) grows 1102.56 -> 1227.6 um.
