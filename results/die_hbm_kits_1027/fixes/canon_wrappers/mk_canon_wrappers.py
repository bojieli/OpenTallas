#!/usr/bin/env python3
"""DIE-HBM/KITS 10-27 helper: canon pgslice wrappers from the proven per-member sw2.py wrappers (pure renaming).
Each member wrapper (wrappers/<member>.sv, ELEM-HBM/SPLIT2 a02e858e91, equiv+mutant proven) is normalised:
 module -> canon name; g_bank_<n>/g_lane_<n> -> g_bank_k<i>/g_lane_k<i> (i = rank of n among the member lane indices);
 the constant lane id straps -> plan pin lane_lane_id (lane_exp: whole 11-bit id; lanes4: id = {lane_lane_id[8:0], 2'd<k>}).
All members of a canon family must normalise to byte-identical text (else REFUSE), and the port list must equal the
C19 canon pin table (bus names + widths).  Writes <canon>.sv + canon_wrappers_report.json.
usage: mk_canon_wrappers.py WT C19 OUTDIR"""
import json, re, sys
from pathlib import Path
WT = Path(sys.argv[1]); C19 = Path(sys.argv[2]); OUT = Path(sys.argv[3])
W = WT / "physical/die_plan/hbm_arch_cores/wrappers"
TR = json.load(open(C19 / "type_reduce_report.json"))
fams = [g for g in TR["groups"] if "__canon_" in g.get("canonical", "") and "pgslice" in g["canonical"]]


def buses(f):
    b = {}
    for p in json.load(open(f)):
        m = re.fullmatch(r"(.*)\[(\d+)\]", p["name"])
        if m:
            b[m[1]] = max(b.get(m[1], 0), int(m[2]) + 1)
        else:
            b[p["name"]] = 1
    return b


def bits(s):
    return "".join(re.findall(r"1'b([01])", s))


rep = {}
for g in fams:
    canon = g["canonical"]
    texts, ids = {}, {}
    for mem in g["members"]:
        t = (W / f"{mem}.sv").read_text()
        body = t[t.index("`default_nettype none"):]
        idx = sorted({int(x) for x in re.findall(r"\bg_(?:bank|lane)_(\d+)_", body)})
        rk = {n: i for i, n in enumerate(idx)}
        body = re.sub(r"\bmodule\s+" + re.escape(mem) + r"\b", "module " + canon, body)
        body = re.sub(r"\bg_(bank|lane)_(\d+)_", lambda m: f"g_{m[1]}_k{rk[int(m[2])]}_", body)
        mid = {}

        def sub_id(m):
            k = m[1]
            mid[k] = bits(m[2])
            if k == "":
                return ".lane_lane_id(lane_lane_id)"
            return f".lane{k}_lane_id({{lane_lane_id, 2'd{k}}})"
        body = re.sub(r"\.lane(\d?)_lane_id\(\{([^}]*)\}\)", sub_id, body)
        # port declaration order differs between members (sw2.py emits in pin-table order); sort it (named binding)
        h0 = body.index(f"module {canon} (\n") + len(f"module {canon} (\n")
        h1 = body.index("\n);", h0)
        decl = sorted(x.strip().rstrip(",") for x in body[h0:h1].split("\n"))
        body = body[:h0] + ",\n".join("    " + x for x in decl) + body[h1:]
        # continuous-assign order also differs (independent statements): sort each contiguous run of assigns
        body = re.sub(r"(?m)(?:^    assign [^\n]*\n)+", lambda m: "".join(sorted(m[0].splitlines(True))), body)
        ids[mem] = mid
        texts[mem] = body
    uniq = set(texts.values())
    r = dict(members=g["members"], identical=len(uniq) == 1, member_ids=ids)
    if any(k for m in ids.values() for k in m):
        wid = 9
        r["id_ok"] = all(v[-2:] == format(int(k), "02b") and len({w[:-2] for w in m.values()}) == 1
                         for m in ids.values() for k, v in m.items())
        r["pin_value_per_member"] = {mem: next(iter(m.values()))[:-2] for mem, m in ids.items()}
    else:
        wid = 11
        r["id_ok"] = all(len(v[""]) == 11 for v in ids.values())
        r["pin_value_per_member"] = {mem: m[""] for mem, m in ids.items()}
    if len(uniq) != 1:
        r["REFUSE"] = "members differ after normalisation"
        rep[canon] = r
        continue
    body = uniq.pop()
    body = body.replace(f"module {canon} (\n", f"module {canon} (\n    input wire [{wid - 1}:0] lane_lane_id,\n", 1)
    ports = {m[3]: (int(m[1]) - int(m[2]) + 1 if m[1] else 1)
             for m in re.finditer(r"^\s*(?:input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)", body, re.M)}
    pf = C19 / g["pins_file"]
    pb = buses(pf)
    diff = sorted(set(pb.items()) ^ set(ports.items()))
    r["port_diff_vs_plan"] = diff
    r["plan_pins_file"] = str(pf)
    hdr = (f"// DIE-HBM/KITS 10-27 (UNCOMMITTED PROPOSAL): canon wrapper {canon} = pure rename of the proven sw2.py member\n"
           f"// wrappers {g['members']} (byte-identical after renaming g_*_<n>_ -> g_*_k<i>_ and lane-id straps -> pin).\n"
           f"// Plan pins: {g['pins_file']} (C19).  Pure wiring; re-run split/miter.py equivalence before sign-off.\n")
    if not diff:
        (OUT / f"{canon}.sv").write_text(hdr + body)
        r["written"] = str(OUT / f"{canon}.sv")
    rep[canon] = r
json.dump(rep, open(OUT / "canon_wrappers_report.json", "w"), indent=1)
for k, r in rep.items():
    print(k, "identical", r["identical"], "id_ok", r.get("id_ok"), "diff",
          r.get("port_diff_vs_plan", r.get("REFUSE")), r.get("written"))
