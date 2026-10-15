#!/usr/bin/env python3
"""SU / HC slab contract v2 (stream s81-suhc-1011): the die pins of the real masters dsfd_sp_su / dsfd_sp_hc at
production parameters, read from their RTL port lists, with the peer each group binds to.  Replaces the placeholder
pins of su_hc.layer1.json v1 (f_vm 1024 / t_hc 512 / exchange 1024): SU results go straight to the VM, HC keeps h
resident (no hc_s <-> hc_n exchange: one logical master), and both slabs run on the stream 1.2 GHz clock.

    python3 tools/s81_suhc/contract_v2.py --out physical/s81_ph_views/contracts_1011/su_hc.v2.json
"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = dict(dsfd_sp_hc=dict(NG=256, D=5120, S_RD=2, S_WR=8),
            dsfd_sp_su=dict(QN_N=256, KV_N=512, QB_NB=32, SW_W=1024, SM_H=16, SM_LPH=16, S_RD=16, S_WR=16))
PEER = {"cck": "dsfd_sp_ctrl ck (stream 1.2 GHz)", "crs": "ctrl reset", "sk": "stream 1.2 GHz slab clock",
        "srs": "slab reset", "c_cmd_v": "dsfd_sp_ctrl cv[e] (85-b pulse group with c_cmd_d)", "c_cmd_d": "dsfd_sp_ctrl cd[e*84 +: 84]",
        "c_done_v": "dsfd_sp_ctrl dv[e] (9-b pulse group with c_done_tag)", "c_done_tag": "dsfd_sp_ctrl dt[e*8 +: 8]",
        "inp": "die dependency net (s81-ctl): head descriptor's operands present",
        "y_v": "sp_collective all-reduce result stream (direct coll -> HC bus)", "y_rdy": "sp_collective", "y_d": "sp_collective",
        "rq_v": "sp_vm read request slots (row-addressed, fixed-latency response)", "rq_row": "sp_vm",
        "rs_v": "sp_vm read response slots", "rs_d": "sp_vm",
        "wq_v": "sp_vm write request slots (ot_s81ph_vm_mem {v, row, mask16, d512})", "wq_row": "sp_vm", "wq_mask": "sp_vm", "wq_d": "sp_vm",
        "flt": "die fault vector", "online": "die status", "fcode": "die status"}


def width(expr, p):
    if not expr:
        return 1
    hi, lo = expr.split(":")
    env = dict(p)
    return eval(hi, {}, env) - eval(lo, {}, env) + 1


def ports(master):
    src = (ROOT / f"rtl/dsrom_sys/s81_suhc/{master}.sv").read_text()
    hdr = re.sub(r"//[^\n]*", "", src).split(");", 1)[0].split(") (", 1)[1]
    out = []
    for d, w, names in re.findall(r"\b(input|output)\s+wire\s*(?:\[([^\]]+)\])?\s*([\w\s,]+?)(?=,\s*(?:input|output)|\s*$)", hdr):
        for n in [x.strip() for x in names.split(",") if x.strip()]:
            out.append(dict(name=n, dir=d, bits=width(w, PROD[master]), peer=PEER.get(n, "?")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ms = {m: dict(params=PROD[m], ports=ports(m)) for m in PROD}
    for m, v in ms.items():
        v["total_bits"] = sum(p["bits"] for p in v["ports"])
    rec = dict(schema="opentallas.s81.slab-contract.v2", slab="su_hc", owner="s81-suhc-1011", supersedes="su_hc.layer1.json v1",
               domain="stream_1p2 (both slabs; the adapter CDC stays at the boundary)",
               instances=dict(sp_su=dict(master="dsfd_sp_su", engine="su (ENG 1)", note="one logical SU: the v1 su_s / su_n split "
                                         "becomes two halves of the wide VM port only if the floorplan needs it"),
                              sp_hc=dict(master="dsfd_sp_hc", engine="hc (ENG 2)", note="one logical HC: h resident, no s/n exchange")),
               masters=ms,
               vm_ports_required=dict(sp_su="16 read row slots + 16 write row slots (8 kb each way)",
                                      sp_hc="2 read row slots + 8 write row slots"),
               die_buses_new=["sp_collective -> sp_hc y 8192 b + valid / ready (the all-reduce result, NG words a beat)"],
               retired=["su_s/su_n t_hc 512", "hc f_su_s / f_su_n 512", "hc_s <-> hc_n t_n/f_s 1024", "hc_n t_vm 1024 (replaced by wq slots)"])
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for m, v in ms.items():
        print(m, v["total_bits"], "bits", [(p["name"], p["bits"]) for p in v["ports"]])


if __name__ == "__main__":
    main()
