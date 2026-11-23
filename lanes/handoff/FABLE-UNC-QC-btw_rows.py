#!/usr/bin/env python3
"""FABLE-UNC-QC STA-BTW-1 (rc96): R8 extra members that put PAD cycles on the stn_cfg bits of b_tw_data_i at the four
region cores of every st_a partition.  usage: btw_rows.py R8_TABLE EXTRA1_IN OUT_EXTRA1 OUT_ROW.json [PAD]"""
import sys, json, re, hashlib, collections
r8, x_in, x_out, row_out = sys.argv[1:5]; PAD = int(sys.argv[5]) if len(sys.argv) > 5 else 3
R = json.load(open(r8)); X = json.load(open(x_in))
sel = [m for m in R["members"] if re.fullmatch(r"sl_[EW]\d_st_a", m.get("sink_part", "")) and m["sink_port"].startswith("cfg_")
       and re.search(r"\.u_r[0-3]$", m["sink"]) and m["lane"].endswith("__b_tw_data_ctl_st_a")]
assert sel and all(m["pad"] == 0 and m["asbuilt"] == 0 for m in sel), "unexpected table state"
parts = collections.Counter(m["sink_part"] for m in sel)
assert set(parts.values()) == {24}, parts
new = []
for m in sel:
    n = dict(m); n["pad"] = PAD; n["landed"] = m["bound"] + PAD
    n["why"] = f"STA-BTW-1 (FABLE-UNC-QC 11-23, rc96): stn_cfg broadcast bin -> u_r0..u_r3, {PAD} pad cycles = stations (tail split copies per core)"
    new.append(n)
ids = {m["id"] for m in X["members"]}
assert not ids & {m["id"] for m in new}
X["members"] = X["members"] + new
open(x_out, "w").write(json.dumps(X, indent=1) + "\n")
json.dump(dict(row="STA-BTW-1", lane="FABLE-UNC-QC", item="rc96", pad=PAD, members=len(new), partitions=sorted(parts),
               r8_table_sha=hashlib.sha256(open(r8, "rb").read()).hexdigest()[:12], extra1_in_sha=hashlib.sha256(open(x_in, "rb").read()).hexdigest()[:12],
               extra1_out=x_out, extra1_out_sha=hashlib.sha256(open(x_out, "rb").read()).hexdigest()[:12],
               landed={p: sorted({m["landed"] for m in new if m["sink_part"] == p}) for p in sorted(parts)},
               apply="chain env EXTRA1=<extra1_out> (asbuilt land_r8_extra[1]); no plan key changes",
               ids_sample=[m["id"] for m in new[:3]]), open(row_out, "w"), indent=1)
print("STA-BTW-1 members", len(new), "partitions", len(parts), "pad", PAD, "bounds", sorted({m["bound"] for m in new}), "->", x_out)
