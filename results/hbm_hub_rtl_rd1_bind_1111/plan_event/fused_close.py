"""HBM-HUB-RTL-1 11-12 (DIE-HBM-100 ruling: the cached Nov-8 elaboration is canonical): close the lower FUSED tree the way
the cached as-built has it, after tools/hbm_b2/fused_lower_tree_splice.py.

    python3 -I fused_close.py CACHED_ASBUILT SPLICED_ASBUILT OUT_ASBUILT RECEIPT

The repo splice leaves three groups of top input ports that the cached as-built does not have:
  fvp_in__<k>_<side>__{rq,wq}_*            hb_fvp_* request inputs   -> the lane outputs u_mu_fused_<k>_<side>__*
  native_required__u_mu_fused_*__rr_{v,d}  lane response inputs      -> the hb_fvp_* a_rr / b_rr outputs
  native_required__u_mu_fused_*__pad_{k,b} lower tnode pad straps    -> the cached constants
For every top input port the cached top lacks, each reader pin (cell, port, bit) takes what drives the same pin in the
cached top: a constant, or the bit of the net of the same name in this top.  Fail closed if a reader pin is missing in
the cached top or its net does not exist here; the port is then removed.  Ports the cached top has are not touched.
"""
import json
import sys

TOP = "hbm_current_native_top"
cached, spliced, out, receipt = sys.argv[1:5]
C = json.load(open(cached))["modules"][TOP]
B = json.load(open(spliced))
T = B["modules"][TOP]


def bitname(top):
    m = {}
    for n, v in top["netnames"].items():
        for i, b in enumerate(v["bits"]):
            if isinstance(b, int) and (b not in m or m[b][0].startswith("$")):
                m[b] = (n, i)
    return m


cbit, tnet = bitname(C), {n: v["bits"] for n, v in T["netnames"].items()}
extra = sorted(p for p, v in T["ports"].items() if p not in C["ports"])
assert all(T["ports"][p]["direction"] == "input" for p in extra), "non-input extra port"
gone = {b: p for p in extra for b in T["ports"][p]["bits"]}
subst, rec, err = {}, {"ports_removed": len(extra), "const": 0, "net": 0, "by_group": {}}, []
for cn, c in T["cells"].items():
    for pn, bits in c["connections"].items():
        for i, b in enumerate(bits):
            if b not in gone:
                continue
            cc = C["cells"].get(cn)
            if cc is None or pn not in cc["connections"] or len(cc["connections"][pn]) != len(bits):
                err.append(f"{cn}.{pn}: no matching pin in the cached top"); continue
            ref = cc["connections"][pn][i]
            if isinstance(ref, str):
                nb = ref; rec["const"] += 1
            else:
                nm = cbit.get(ref)
                if nm is None or nm[0] not in tnet or len(tnet[nm[0]]) <= nm[1]:
                    err.append(f"{cn}.{pn}[{i}]: cached net {nm} not in this top"); continue
                nb = tnet[nm[0]][nm[1]]; rec["net"] += 1
                if nb in gone:
                    err.append(f"{cn}.{pn}[{i}]: cached net {nm[0]} is itself a removed port"); continue
            bits[i] = nb
            g = gone[b].split("__")[0] if gone[b].startswith("fvp_in") else gone[b].rsplit("__", 1)[1]
            rec["by_group"][g] = rec["by_group"].get(g, 0) + 1
if err:
    print(json.dumps({"errors": len(err), "first": err[:8]})); sys.exit(1)
for p in extra:
    del T["ports"][p]
    T["netnames"].pop(p, None)
left = {b for c in T["cells"].values() for bs in c["connections"].values() for b in bs if b in gone}
assert not left, "removed port bit still read"
assert set(T["ports"]) == set(C["ports"]), (len(T["ports"]), len(C["ports"]))
json.dump(B, open(out, "w"))
rec["ports_now"] = len(T["ports"])
json.dump(rec, open(receipt, "w"), indent=1)
print(json.dumps(rec))
