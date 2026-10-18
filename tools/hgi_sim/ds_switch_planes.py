#!/usr/bin/env python3
"""HBM-NET (10-16): multi-plane one-tier fabric arithmetic for the HBM-accelerator arrays (analytic, no simulation).

Per die 32 x 100G lanes (4 x 800G equivalent) to the scale-up switch; one switch chip per plane, 512 x 100G SerDes
(Tomahawk-Ultra class).  Port width w lanes -> P = 32 / w planes, 512 / w ports a chip = max dies.
For each on-path gather class (bytes = the gathered output, as perf.coll_cycles) it prices, per plane and receiver:
  fragment a source = bytes / G; striped over planes only when the stripe is >= STRIPE_MIN bytes, else the whole
  fragment goes to plane (source mod P) (static, compile-time assignment: G / P sources a plane, integer here);
  wire bytes a packet = payload padded to MIN_FRAME + OVH (preamble/IFG 20 + SUE/AFH header 12 + CRC 4 + transport 4);
  output-port drain (the incast burst of all G - 1 sources at one receiver port) = wire bytes / port rate;
  the model's delivery term (G - 1) ceil(bytes / G / 64) / 4 cycles at 1.2 GHz (4 COLL delivery lanes).
FEC accumulation: one RS(544,514) codeword = 5440 bits striped over the port's lanes at 106.25 Gb/s a lane.
"""
import json, math, sys
from pathlib import Path

CLK = 1.2e9
LANE_GBPS = 100.0
OVH, MIN_FRAME, STRIPE_MIN = 40, 64, 256
CLASSES = {  # name: (bytes at G 96, scales with G (merge))
    "router_gather.gsc": (768, False), "x_proj kvraw": (1024, False), "x_proj cmp": (2048, False),
    "o-group reduce (x2 crossings)": (2048, False), "x_proj qa": (2560, False), "expert_intermediate": (4608, False),
    "indexer.q_gather": (8192, False), "attn_out / ffn_out": (10240, False), "engram rows": (12288, False),
    "engram kv": (51200, False), "index TOPK_MERGE (96x512 -> Gx512)": (393216, True)}


def plane_rows(G, w):
    P = 32 // w
    port_Bps = w * LANE_GBPS * 1e9 / 8
    rows = []
    for name, (b96, merge) in CLASSES.items():
        nb = b96 * (G / 96 if merge else 1)
        frag = nb / G
        stripe = frag / P
        if stripe >= STRIPE_MIN:
            pk_payload, pk_per_src_plane, srcs = stripe, 1, G - 1
        else:
            pk_payload, pk_per_src_plane, srcs = frag, 1, math.ceil((G - 1) / P)
        # split a payload into <= 4 KB packets
        npk = max(1, math.ceil(pk_payload / 4096))
        wire = srcs * npk * (max(MIN_FRAME, pk_payload / npk) + OVH)
        drain_ns = wire / port_Bps * 1e9
        f = max(1, math.ceil(nb / G / 64))
        model_ns = (G - 1) * f / 4 / CLK * 1e9
        rows.append(dict(cls=name, bytes=int(nb), frag_B=round(frag, 1), per_plane_payload_B=round(pk_payload, 1),
                         striped=stripe >= STRIPE_MIN, pkts_per_rx_port=srcs * npk, wire_B_per_rx_port=round(wire),
                         payload_eff=round(srcs * pk_payload / wire, 3), port_drain_ns=round(drain_ns, 1),
                         model_delivery_ns=round(model_ns, 1),
                         switch_buffer_if_unpaced_KB=round(wire * (1 - 1 / max(1, srcs)) * G / 1024, 1)))
    return rows


def main():
    out = dict(schema="opentallas.hbm_switch_sensitivity_1016.planes.v1", rule=__doc__, cases={})
    fec = {w: round(5440 / (w * 106.25), 1) for w in (1, 2, 4, 8)}
    out["fec_codeword_accumulation_ns_per_rx"] = fec
    for G, ws in ((96, (4, 2, 1)), (192, (2, 1))):
        for w in ws:
            out["cases"][f"G{G}_w{w}_P{32 // w}"] = dict(G=G, port_lanes=w, planes=32 // w, chips=32 // w,
                                                          ports_used_per_chip=G, ports_per_chip=512 // w,
                                                          cables=G * 32 // w, rows=plane_rows(G, w))
    print(json.dumps(out, indent=1))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
