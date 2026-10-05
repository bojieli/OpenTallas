# Corrected E1 current CTS boundaries

Corrected-source CTS placement-estimated SS/FF under unchanged declared vehicle IO contract; no global route/SPEF/signoff/power. Source `39c3000980824007e1c48309dc7a8fabfb54523e`; prefix and both focused queries exit 0. Physical timing fails. The completed supervisor has no live flow.

| Port family | SS setup (ps) | FF hold (ps) |
|---|---:|---:|
| xs_q0 | 204.96 | -112.19 |
| xs_q1 | 173.34 | -100.9 |
| xs_e0 | 225.08 | -99.91 |
| xs_e1 | 223.32 | -92.67 |
| pval | -19.53 | 38.05 |
| prow | -123.53 | 6.91 |
| pseg | -93.62 | 66.42 |
| pnseg | -88.3 | 64.97 |
| ppos | -128.43 | 74.0 |
| pv | -119.06 | 37.08 |
| perr | -5.54 | 71.05 |
| busy | -163.49 | 67.72 |
| fault | -202.47 | 1.02 |
| xs_v | 244.47 | 133.15 |
| xs_p | 220.62 | -100.53 |
| xs_b | 221.49 | -100.49 |
| xs_sv | no timed path | no timed path |
| xs_pos | 225.24 | 118.9 |
| cfg_v | -196.74 | 160.63 |
| cfg_a | -160.01 | 153.44 |
| cfg_d | 4.1 | 141.92 |
| go | -311.95 | 157.23 |
| rst_n | -154.46 | 191.53 |
| pg_en | -116.51 | 279.09 |
| sched_v | 72.35 | 268.02 |
| sched_gap | 96.78 | 252.05 |
| pg_lead | -372.83 | 224.78 |
| pg_bet | -372.04 | 223.47 |
| pg_idle | -337.37 | 275.5 |
| pg_step | -371.71 | 224.47 |
| pg_rst | 69.46 | 234.54 |
| pg_ack_to | -387.9 | 275.07 |
| sw_ack | -278.62 | 272.92 |
| pg_ready | 217.48 | 10.03 |
| pg_late | 212.35 | 22.55 |
| pg_fault | 159.48 | 30.53 |
| sw_en | 218.41 | 13.08 |

Margins are worst across every returned clock path group. Raw reports and JSON retain the endpoints; `xs_sv` has no reported timed path and is not claimed closed. Reset includes clock-gating checks, not an ordinary data-only contract. There is no `done` port: result completion is `pv`/`perr` with `busy` debt; `pg_ready` denotes wake admission.

The pin-spread recipe is blocked by actual current Q hold, independently of output/control setup failures. Maxwell owns the actual parent launch/capture binding. Diagnostic required input minima are not adopted constraints.

`fault` setup is −202.47 ps from the sticky segment-tree register; hold is +1.02 ps from AO `late`. The fault tree has 754.32 ps launch clock insertion, 80.63 ps clk→Q and 333.52 ps downstream logic/wire. It is a combinational OR/isolation merge of separate fault sources, not a sequential passage through the `late` register. `pg_late` and `pg_fault` themselves meet this declared vehicle budget.

A fault-only register adds one fault-blind acceptance cycle. Paired publication retiming adds at least one 0.833 ns result/debt cycle and 128 registers per K1/NB2 instance (309,376 at 2,417 elements), before quarantine/clock/mux cost. Neither is admitted: the real parent fault-stop/acceptance contract and finite ownership behavior are absent. Existing exactness checks compare control every cycle. See `fault_control_diagnosis.json` for precise missing fields and modeled restrictions. No RTL change, falsepath, new route or power credit. These are current CTS placement estimates, not R4 qualification or full SS/FF routed closure.
