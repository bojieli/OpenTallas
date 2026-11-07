#!/usr/bin/env python3
"""DIE-KV-84 11-06 (COORD 16:2x(b)): kv3_sys_SD + kv3_sys_SD_v1 edge clock clk_clk_phy declared asynchronous
(edge_clocks[].cdc = synchronized + cdc_evidence; gen_phys.edge_cdc_sdc: max delay T/2 latency ignored, no hold,
clk_clk_phy <-> clk only).  sd_vA2 CTS: clk -> clk_clk_phy hold -305 ps on u_fdi_cdc mem -> p_tx_d (FIFO storage read)
under the synchronous model; hold repair HB4 then cost setup -46 on the read mux.  Idempotent.
usage (repo root): event.py PLAN_IN PLAN_OUT"""
import json, sys
TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
EVIDENCE = ("rtl/physical/ot_fdi_phy_cdc.sv header (TOK-QK/C 10-24): clk and clk_phy (PLL pll_phy, 1043 ps) are "
            "asynchronous; the only clk <-> clk_phy arcs are inside the two ot_async_fifo instances (Gray pointers, "
            "2-flop synchronisers, storage read in the read domain) and the tx_up / reset synchronisers")
a, b = sys.argv[1:3]
p = json.load(open(a))
for tn in TYPES:
    ec = [e for e in p["partition_types"][tn]["clock"]["edge_clocks"] if e["port"] == "clk_clk_phy"]
    assert len(ec) == 1, tn
    ec[0]["cdc"] = "synchronized"
    ec[0]["cdc_evidence"] = EVIDENCE
json.dump(p, open(b, "w"), indent=1); open(b, "a").write("\n")
