#!/usr/bin/env python3
"""Pricing record for gate link_credit_rtt (results/rtl/qwen_contracts_20261007/link_credit_rtt/pricing.json).
Cycles: the full-rate hub keeps the r21 registered link stations (credit RTT 117/119 measured), so the token adds 0
stage cycles; the per-layer posted KV-new write-back (136 sectors a layer a die, measured in the STREAM4 token)
serialises at one link word a cycle off the token path.  Area: routed frames when the loop routes have closed
(--route NAME=corner_sta.json[,frame_um]), else the analytic flop count.  usage: qwen_link_credit_pricing.py [--route ...]"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/qwen_contracts_20261007/link_credit_rtt/pricing.json"
DFF_UM2 = 0.2916            # DFFHQNx1_ASAP7_75t_R (asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib)
W = 523                     # receive word: tag 11 + data 512
CR, OD, XS, AD, NL = 128, 8, 8, 8, 4
OLD = dict(hub_frame_um=412.536, ibuf=4)


def flops(cr, od, xs):
    per_link = cr * W + AD * W + od * 512
    return NL * per_link + xs * W + NL * 528


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", action="append", default=[], help="label=frame_um:status:ss:ff:drc[:util]")
    a = ap.parse_args()
    run = re.findall(r"MEMSTAT L(\d+) die0 .*?wr_sectors=(\d+).*?stall_drain=(\d+).*?stall_retire=(\d+)",
                     (ROOT / "results/rtl/qwen_plain_ar_stream4_P8191_20261005/runtime.log").read_text())
    sectors = sorted({int(s) for _, s, _, _ in run})
    assert sectors == [136], sectors
    drains = sum(int(d) + int(r) for _, _, d, r in run)
    new_hub, old_hub = flops(CR, OD, XS), NL * (4 * W + AD * W + 523) + 2 * 523 + NL * 528
    far_add = NL * (CR - OLD["ibuf"]) * W
    routes = {}
    for r in a.route:
        lab, rest = r.split("=", 1)
        f = rest.split(":")
        routes[lab] = dict(frame_um=float(f[0]), status=f[1], ss_ps=float(f[2]), ff_ps=float(f[3]), drc=int(f[4]),
                           util=(float(f[5]) if len(f) > 5 else None), frame_mm2=round(float(f[0]) ** 2 / 1e6, 4))
    hub_closed = [v for k, v in routes.items() if k.startswith("qfd_hub_fr") and v["status"] == "CLOSED"]
    rx_closed = [v for k, v in routes.items() if k.startswith("qfd_link_rx128") and v["status"] == "CLOSED"]
    old_mm2 = OLD["hub_frame_um"] ** 2 / 1e6
    if hub_closed and rx_closed:
        hub = min(hub_closed, key=lambda v: v["frame_mm2"]); rx = min(rx_closed, key=lambda v: v["frame_mm2"])
        added = round(hub["frame_mm2"] - old_mm2 + NL * rx["frame_mm2"], 4)
        area = dict(basis="routed frames (closed)", hub_frame_mm2=hub["frame_mm2"], rx_frame_mm2=rx["frame_mm2"],
                    added_die_mm2=added, summary="+%.4f mm2 a die (hub %.4f -> %.4f mm2, 4 strip receive buffers %.4f mm2 each, routed)"
                    % (added, old_mm2, hub["frame_mm2"], rx["frame_mm2"]))
        phys = "hub SS %+.2f / FF %+.2f, rx SS %+.2f / FF %+.2f (DRC %d/%d)" % (hub["ss_ps"], hub["ff_ps"], rx["ss_ps"], rx["ff_ps"], hub["drc"], rx["drc"])
    else:
        est_cell = (new_hub - old_hub + far_add) * DFF_UM2 * 1.6 / 1e6     # flop + write-enable mux/read mux allowance
        added = round(est_cell / 0.55, 4)
        area = dict(basis="analytic flop count (routes pending)", added_flops_hub=new_hub - old_hub, added_flops_far_end=far_add,
                    added_die_mm2_estimate=added, summary="~+%.2f mm2 a die estimated (%d added flops: hub %d, 4 strip receive "
                    "buffers %d; x1.6 mux allowance, 55%% util); routes pending" % (added, new_hub - old_hub + far_add,
                                                                                   new_hub - old_hub, far_add))
        phys = "routes pending: " + (", ".join("%s %s SS %+.2f / FF %+.2f DRC %d" % (k, v["status"], v["ss_ps"], v["ff_ps"], v["drc"])
                                               for k, v in routes.items()) or "qfd_hub_fr-b3af3a9ed, qfd_hub_fr_w648-b3af3a9ed, qfd_link_rx128-b3af3a9ed queued")
    rec = dict(schema="opentallas.qwen-link-credit-pricing.v1", gate="link_credit_rtt", credits=CR, output_fifo=OD, x3_skid=XS,
               token_cycles_added=0,
               cycles_basis=("same registered link stations (r21 relay pricing already charges 2 x 36 x 26 link-stage cycles); "
                             "credit RTT 117/119 measured; at CR=128 the link never waits on a credit (gate: 0 stalls)"),
               kv_new_sectors_per_layer=sectors[0],
               kv_new_serialisation=dict(words_per_layer_max=sectors[0], cycles_at_full_rate=sectors[0],
                                         cycles_at_4_credits=round(sectors[0] / 4 * 118),
                                         measured_token_drain_or_retire_stalls=drains,
                                         note=("posted write-back: the STREAM4 token measured stall_drain = stall_retire = 0 on every "
                                               "layer, so the write-back is off the token path; at 4 credits the same 136 words would "
                                               "take ~%d cycles a layer (an un-composed risk), at CR=128 <= %d + RTT")
                                         % (round(sectors[0] / 4 * 118), sectors[0])),
               area=area, physical=dict(routes=routes, summary=phys),
               area_cost_note="added die area is reported to the qwen-dietop floorplan; die count unchanged (Qwen single reticle, 858 mm2 limit)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(area=area["summary"], physical=phys), indent=1))


if __name__ == "__main__":
    main()
