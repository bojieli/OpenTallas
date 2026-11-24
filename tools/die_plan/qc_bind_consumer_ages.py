#!/usr/bin/env python3
"""Extract QC consumer calendar and SU SRAM ages from a single bind."""
import argparse
import hashlib
import json
import re
from pathlib import Path

LRLY = re.compile(r"dvs_([WE][0-5])\.u_core\.u_sub\.u_lrly([0-7])")
SEAM = {"CS_TXS", "CS_RXV", "CS_RXP", "CS_X3S", "SC_TX", "SC_X3"}


def load(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def derive(bind):
    param, param_sha = load(bind / "param_regen.json")
    contracts, contract_sha = load(bind / "bind_latency_consumers.json")
    d2d = param["record"]
    seam = d2d["D2D_SEAM_C"]
    if set(seam) != SEAM or any(not isinstance(v, int) or v < 0 for v in seam.values()):
        raise ValueError("invalid QC D2D seam-stage record")
    txdp = re.fullmatch(r"32'h([0-9a-fA-F]{8})", d2d["D2D_TXDP_C"])
    if txdp is None:
        raise ValueError("invalid QC D2D TXDP record")
    out = {}
    for row in contracts["contracts"]:
        m = LRLY.fullmatch(row["inst"])
        name = row["param"]
        if m is None or name not in {"ML", "CROM_ML"}:
            continue
        site, lane = m.groups()
        req, resp = row["req"], row["resp"]
        if row.get("torn") or len(req) != 1 or len(resp) != 1 or row.get("design_loop") != 0:
            raise ValueError(f"{site}.{lane}.{name}: nonuniform, incomplete or nonzero reference")
        age = req[0] + resp[0]
        if age != row["landed_loop"] or age != row["required"]:
            raise ValueError(f"{site}.{lane}.{name}: request/response ages disagree with landed loop")
        p = out.setdefault((site, int(lane)), {})
        if name in p:
            raise ValueError(f"{site}.{lane}: duplicate {name}")
        p[name] = dict(request=req[0], response=resp[0], memory_read_extra=age)
    expected = {(f"{side}{site}", lane) for side in "WE" for site in range(6) for lane in range(8)}
    missing = expected - out.keys()
    if missing:
        raise ValueError(f"incomplete SU contract: missing {sorted(missing)}")
    rows = {}
    for (site, lane), pair in sorted(out.items()):
        if set(pair) != {"ML", "CROM_ML"}:
            raise ValueError(f"{site}.{lane}: missing ML or CROM_ML record")
        vm, crom = pair["ML"], pair["CROM_ML"]
        if vm["memory_read_extra"] != crom["memory_read_extra"]:
            raise ValueError(f"{site}.{lane}: VM and CROM read ages disagree")
        rows.setdefault(site, {})[lane] = dict(vm, crom_request=crom["request"], crom_response=crom["response"])
    packed = int(txdp[1], 16)
    return dict(schema="opentallas.qc_bind_consumer_ages.v1", bind=str(bind),
                source_sha256={"param_regen.json": param_sha, "bind_latency_consumers.json": contract_sha},
                d2d_txdp_c=d2d["D2D_TXDP_C"], d2d_txdp_port_order=[(packed >> (8*i)) & 255 for i in range(4)],
                d2d_seam_c=seam, su_mem_read_ages=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bind", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = derive(args.bind)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
