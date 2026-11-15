# TYPE-HDCTL-REGS handoff (11-14 successor)
- Base plan rp21z18d: epyc7 /srv/opentallas-scratch2/claude/type-hdctl-regs/base.json (sha 32af9289b04f).
- Mechanism: plan internal_stations conn bus:NAME bit_route per_bit leaf_um regs_um; realize_internal_stations true (see hd_spn). Latency via gen.py latency.
- Buses: h_tx_o, h_rx_i, lepk_o0, n_rx_i + landing monitors. State: delta script not yet written.
