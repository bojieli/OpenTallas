# bind_p4l3_g8 + SVCP (TOK-S81-GAPS/SVCP, 10-19)

= bind_p4l3_g8 (G8) + the abutted P-path lane **pr_09_07** (514 b, 110 um: rsv_09 ro W face -> rsv_07 ri E face; dsdv_svc_rs P PATH).
die.v differs from s81-lbgap-g8 bind/die.v ONLY in that net (u_rsv_09 .ro W face, u_rsv_07 .ri E face).
`python3 tools/s81_dv/dv_diecase.py --plan results/arch/s81_dv_1016/p4l/plan.json --out <scratch>/bind --bind real --bind-table results/arch/s81_dv_1016/bind/bind_table_p4l3.json` (plan p4l + pr_09_07; table p4l3 + svc_rs `unlinked_out_bits` spare-output rules), branch claude/tok-s81-svcp2-1019.
Strict die_port_bind with the unread / open-output check: **FAIL** (unread_net_bits 3,202, output_open_ports 43, spare_out_bits 191,426 declared).
The remaining findings are classified in unread_audit.json: svc w_* = real gap G9b (SO o rows), the rest are other owners' classes
(unit fault outputs, slice band spares, landing lane padding, PHY model outputs, forwarded clocks) -- none is svc P path.
