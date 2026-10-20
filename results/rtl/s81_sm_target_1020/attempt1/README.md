# S81 local SM SO target, operator bench attempt1 (collected by LEAD2-S81/SMT, 10-19 18:03 PT)

Source 90917d90d (codex/s81-sm-target-1020, TAKEOVER3), declared bill fdba3814c. Bench tools/s81_dv/sm_target/run.sh,
Verilator 5.050 (tool.txt), ot-run unit oth-ubuntu-306475-1792456901 on ot-epyc8, exit 0 (attempt1.client.log).

| run | result |
|---|---|
| run_0 MUT 0 | SMS PASS checks=609; TARGET beats=192 retires=24 bad_retires=0 operator_elements=12288 |
| run_1..5 MUT 1..5 | TARGET CAUGHT (fault_code cc0cc0 / c40c40 / d40d40 / c00c00 / c48c48), all 24 retires bad, 0 beats (fail witnesses) |

What this does not show: the target is not instantiated on the die. Its cfg_* / op_* authority inputs and g_* gather-beat
outputs have no die driver or consumer (the WO_A gather route, window issuer and joined retirement are missing), so the
10 strict-bind opens on mu4c 19bf4121e are still open. There is no synthesis area and no physical gate.
