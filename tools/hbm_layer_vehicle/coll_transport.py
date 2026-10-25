#!/usr/bin/env python3
"""TOKg 10-23: COLL.ALL_GATHER transport profile of a die revision (compiler calendar input for coll_images.py).

The canonical two-ring schedule in coll_images.py (collq_gather_1018 / ot_hgi_coll_gq.sv header) assumes the GEN2
timing: the launch reaches hcollgi_SW in 0 extra edges, and a far-end neighbour flit reaches SW's ring stop the edge
after the slice pin.  A post-relay die (r18h5: L12 pads + forwarded relay chains) adds per-lane transport:

  launch_edges            slice pin host_cp_ingress__launch_v -> hcollgi_SW.launch_v (every gather edge moves by it)
  calendar_launch_edges   same for calendar_SW.launch_v (the VM grant window must still cover the moved writes)
  ingress_edges[port]     far-end slice pin (hb_coll_NW__pr_cw_o, ...) -> SW ring stop input; the far-end drive is
                          issued that many edges EARLIER so the flit reaches the stop on its scheduled edge.

Each lane is traced through the relay wrappers in die.v (rf*/rh*/l12p_* instances, source -> sink) and priced with
d4g_bank_latency.Graph.lane_latency (relays 1 edge; half-cycle hops + landing ceil(N/2)+1+E with E from the contract's
K/N note).  Landings whose contract note carries NO_E are listed in `notes` (E derived from K; source-functional
timing, not a physical-clock qualification).

Validated (rec2 of DS L0, r18h5 source slice, binary 273a0824): launch 48 / ingress 6, 18, 4, 20 -> all 120 ring-output
checks PASS and the ring-B fault clears; omitting the B-CCW term (20) FAILS exactly those 20 checks + hcollb fault
(results/arch/hbm_token_hcollgl_skew_1023).

  PYTHONPATH=tools python3 -m hbm_layer_vehicle.coll_transport --contract contract_func.json --die-v die.v --out t.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / "hbm_die_v16"))

SCHEMA = "opentallas.hbm_coll_transport.v1"
# far-end slice pin -> SW ring stop input it feeds (coll_images.IN_PORTS)
INGRESS = {"hb_coll_NW__pr_cw_o": ("hb_coll_SW", "pr_cw_i"), "hb_coll_SE__pr_ccw_o": ("hb_coll_SW", "pr_ccw_i"),
           "hcollb_NW__cw_o": ("hcollb_SW", "cw_i"), "hcollb_SE__ccw_o": ("hcollb_SW", "ccw_i")}
LAUNCH = ("hcollgi_SW", "launch_v")
# TOKj-HBM 10-23: landing WRITE lanes.  hcollgl_SW publishes each landed sector on vm_kq_lo/hi; the kq share leaf
# hcollks_SW_p<p> (b_kq) forwards it to VM banks 2p / 2p+1 (vmb_SW<b>.kq).  Both legs are relayed on r18h5 (b_kq 5-7,
# vm_kq 22-32 edges, unequal per bank), so a landed sector reaches its bank kq_write_edges[bank] edges after the GEN2
# publish write edge; the VM checks and the composed calendar's write reservations move by it (land-direct r18h5 rec2:
# every one of the 72 failing checks was a VM word read 0 at the GEN2 check edge; the same checks at +74 PASS 287/287).
KQ_LEAF = {p: (f"hcollks_SW_p{p}", "b_kq") for p in range(4)}
KQ_BANK = {b: (f"vmb_SW{b}", "kq") for b in range(8)}
CAL_LAUNCH = ("calendar_SW", "launch_v")
RELAY = re.compile(r"(rf|rh)\d+_|l12p_")
HOP = re.compile(r"\b((?:rf|rh)\d+_\w+?|l12p_\w+?)__(o|b|eb|ck_o)\b|\b(codex_r8_\d+)\b")


def parse_instances(die_v, names):
    """{instance: (module, {port: expr})} for relay wrappers and the named sink instances."""
    inst, cur, buf = {}, None, []
    for line in Path(die_v).open():
        # balance_programme_transport emits these complete instances on one line,
        # with a plain output net rather than the relay's <instance>__o naming.
        # Index by that output so trace can walk through the corrective stages.
        pad = re.match(r"\s*ot_codex_prog_r8_pad\s*#\((.*?)\)\s+\w+\s*\((.*)\);\s*$", line)
        if pad:
            pp = dict(re.findall(r"\.(\w+)\(([^()]*)\)", pad[2]))
            depth = re.search(r"\.D\((\d+)\)", pad[1])
            if depth and re.fullmatch(r"codex_r8_\d+", pp.get("y", "")):
                pp["_transport_depth"] = depth[1]
                inst[pp["y"]] = ("ot_codex_prog_r8_pad", pp)
            continue
        if cur is None:
            m = re.match(r"\s*(\w+)\s*(?:#\(.*?\))?\s+(\w+)\s*\(\s*$", line)
            if m and (RELAY.match(m[2]) or m[2] in names):
                cur, buf = m.groups(), []
        elif re.match(r"\s*\);", line):
            inst[cur[1]] = (cur[0], dict(re.findall(r"\.(\w+)\((.*?)\)\s*,?\s*$", "".join(buf), re.M)))
            cur = None
        else:
            buf.append(line)
    return inst


def trace(inst, name, port):
    """relay hops feeding inst.port, source -> sink order, and the root expression."""
    expr, hops, seen = inst[name][1][port], [], set()
    while True:
        m = HOP.search(expr)
        if not m:
            break
        h = m[1] or m[3]
        if h not in inst:
            break
        if h in seen:
            raise ValueError(f"relay loop at {h}")
        seen.add(h)
        hops.append(h)
        pp = inst[h][1]
        expr = pp.get("i") or pp.get("a") or ""
    return hops[::-1], expr


def profile(contract, die_v):
    import d4g_bank_latency as L
    G = L.Graph.__new__(L.Graph)
    G.I = json.loads(Path(contract).read_text())["instances"]
    sinks = [LAUNCH, CAL_LAUNCH] + list(INGRESS.values()) + list(KQ_LEAF.values()) + list(KQ_BANK.values())
    inst = parse_instances(die_v, {s[0] for s in sinks})
    lanes = {}
    for name, port in sinks:
        hops, root = trace(inst, name, port)
        lat, notes = G.lane_latency(hops)
        lanes[f"{name}.{port}"] = dict(latency_edges=lat, wrappers=len(hops), root=root[:160], notes=notes,
                                       hops=hops)
    for pin, (name, port) in INGRESS.items():
        # the traced root must be the far-end pin itself (the slice boundary), else the lane map is wrong
        if pin not in lanes[f"{name}.{port}"]["root"]:
            raise ValueError(f"{name}.{port} root {lanes[f'{name}.{port}']['root']!r} is not {pin}")
    kq = {}
    for p, (name, port) in KQ_LEAF.items():
        if "hcollgl_SW__vm_kq" not in lanes[f"{name}.{port}"]["root"]:
            raise ValueError(f"{name}.{port} root {lanes[f'{name}.{port}']['root']!r} is not hcollgl_SW.vm_kq")
    for b, (name, port) in KQ_BANK.items():
        leaf = KQ_LEAF[b // 2]
        if f"{leaf[0]}__vm_kq" not in lanes[f"{name}.{port}"]["root"]:
            raise ValueError(f"{name}.{port} root {lanes[f'{name}.{port}']['root']!r} is not {leaf[0]}.vm_kq")
        kq[str(b)] = lanes[".".join(leaf)]["latency_edges"] + lanes[f"{name}.{port}"]["latency_edges"]
    return dict(schema=SCHEMA, contract=str(contract), die_v=str(die_v),
                launch_edges=lanes[".".join(LAUNCH)]["latency_edges"],
                calendar_launch_edges=lanes[".".join(CAL_LAUNCH)]["latency_edges"],
                ingress_edges={pin: lanes[f"{n}.{p}"]["latency_edges"] for pin, (n, p) in INGRESS.items()},
                kq_write_edges=kq,
                scope="source-functional lane timing (K/N model); NO_E landings listed in lanes[*].notes",
                lanes=lanes)


def load(path):
    t = json.loads(Path(path).read_text())
    if t.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema {t.get('schema')!r} != {SCHEMA}")
    if set(t["ingress_edges"]) != set(INGRESS):
        raise ValueError(f"{path}: ingress ports {sorted(t['ingress_edges'])} != {sorted(INGRESS)}")
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--die-v", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    t = profile(a.contract, a.die_v)
    a.out.write_text(json.dumps(t, indent=1) + "\n")
    print(json.dumps({k: t[k] for k in ("launch_edges", "calendar_launch_edges", "ingress_edges", "kq_write_edges")}))


if __name__ == "__main__":
    main()
