#!/usr/bin/env python3
"""Extract QC consumer calendar and SU SRAM ages from a single bind."""
import argparse
import hashlib
import json
import mmap
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


DR_WORD_BITS = 520
DR_SLICES = [f"W{i}" for i in reversed(range(6))] + [f"E{i}" for i in range(6)]
DR_PATH = r"dvs_[WE][0-5]\.u_core\.u_sub\."
DR_PORT = r"(?:u_fdn\.ch_dn_i|u_fup\.chr_c|u_rp\.chd_q|u_suvm\.u_vm8q\.u_vw[abc]\.d)"
DR_RECORD = re.compile(
    (r'"(' + DR_PATH + DR_PORT + r'\[\d+\])":\s*\["pin",\s*"([^"]+)",\s*(\d+),\s*(?:true|false)\]').encode()
)


def common_bit_age(sinks, sink, source, width, sink_offset=0):
    """Check bit identity and one age across a complete named logical bus."""
    ages = set()
    for bit in range(width):
        sink_bit = f"{sink}[{sink_offset + bit}]"
        source_bit, age = sinks.get(sink_bit, (None, None))
        if source_bit != f"{source}[{bit}]":
            raise ValueError(f"{sink_bit}: expected {source}[{bit}], got {source_bit}")
        ages.add(age)
    if len(ages) != 1:
        raise ValueError(f"{sink}: unequal bit arrivals {sorted(ages)}")
    return ages.pop()


def trace_native59(bind):
    """Read native59 DR from logical bind pins, regardless of physical bus names.

    The S8 FDN contributes one register and FUP contributes a wire. The RP input
    and last VM write relay D ages are reported so the caller can account for the
    selected CTL and SRAM implementation separately.
    """
    with (bind / "bind_sinks.json").open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
        sinks = {key.decode(): (driver.decode(), int(age)) for key, driver, age in DR_RECORD.findall(data)}
    rows = {}
    upstream = "native59.dr_o"
    age = 0
    for site in DR_SLICES:
        prefix = f"dvs_{site}.u_core.u_sub"
        ingress = common_bit_age(sinks, prefix + ".u_fdn.ch_dn_i", upstream, DR_WORD_BITS)
        age += ingress + 1
        fdn_out = prefix + ".u_fdn.chd_q"
        ctl = common_bit_age(sinks, prefix + ".u_rp.chd_q", fdn_out, DR_WORD_BITS)
        rows[site] = dict(ingress=ingress, fdn=age, rp_in=age + ctl)
        if site != DR_SLICES[-1]:
            fup = common_bit_age(sinks, prefix + ".u_fup.chr_c", fdn_out, DR_WORD_BITS)
            rows[site]["fup_in"] = age + fup
            age += fup
            upstream = prefix + ".u_fup.ch_up_o"

    # The E5 vwr input packs vm_we+addr+data above the contiguous w16 word.
    e5 = "dvs_E5.u_core.u_sub."
    write_ages = set()
    for bank in "abc":
        dst = e5 + f"u_suvm.u_vm8q.u_vw{bank}.d"
        for port, offset, width in (("w16_data", 57, 512), ("w16_addr", 569, 24), ("w16_we", 593, 1)):
            write_ages.add(common_bit_age(sinks, dst, e5 + "u_ctl." + port, width, offset))
    if len(write_ages) != 1:
        raise ValueError(f"E5 w16 data, address and enable are not aligned: {sorted(write_ages)}")
    return dict(dr_from_native_core=rows, last_ctl_to_vm_relay_d=write_ages.pop())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bind", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--native-dr", action="store_true", help="include bit-exact native59 return-chain transport")
    args = parser.parse_args()
    result = derive(args.bind)
    if args.native_dr:
        result["native59"] = trace_native59(args.bind)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
