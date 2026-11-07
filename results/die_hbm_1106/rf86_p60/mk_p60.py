#!/usr/bin/env python3
"""DIE-HBM-86 d44v part 60 (COORD 11-07 08:41 injector (B)): ot_hgi_coll_inj_idx_join_rg drops 31 read-nothing pins from its table.
mk_p60.py PLANDIR KIT_PINS_JSON RTL   (in place on PLANDIR; PLANDIR holds .json.gz as on main)"""
import gzip, hashlib, json, re, sys
d, kit, rtl = sys.argv[1:4]
OLD = "cores/ot_hgi_coll_inj_idx_join_rg__211.68x207.36__content_trial__d16f__codex_g21__centry.json"
NEW = OLD[:-5] + "__r1drop.json"
DROP = ["inj_rd_r1[1]"] + [f"idx_tx_h_r1[{b}]" for b in range(102, 132)]
READ = ["inj_rd_r1[0]"] + [f"idx_tx_h_r1[{a*33+k}]" for a in range(4) for k in range(3)]  # gs[a*3+:3] <= p_tx[a*545+512+:3]; r0 keeps all
src = open(rtl).read()
assert "gs[a*3+:3]<=p_tx[a*545+512+:3]" in src and "if(r==0)begin:g_chk" in src
def gzw(path, obj):
    raw = (json.dumps(obj) + "\n").encode()
    with open(path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g: g.write(raw)
    return hashlib.sha256(raw).hexdigest()
t = json.load(gzip.open(f"{d}/{OLD}.gz"))
names = [p["name"] for p in t]
assert set(DROP) <= set(names) and len(names) == 4761
keep = [p for p in t if p["name"] not in set(DROP)]
assert len(keep) == 4730 and set(READ) <= {p["name"] for p in keep}
k = json.load(open(kit))
kn = {(p["bus"] if p["bit"] is None else f"{p['bus']}[{p['bit']}]"): p for p in k}
assert set(kn) == {p["name"] for p in keep}, "kit pins != new table"
bad = [p["name"] for p in keep if kn[p["name"]]["layer"] != p["layer"] or abs(kn[p["name"]]["x"] - p["x"]) > 0.1 or abs(kn[p["name"]]["y"] - p["y"]) > 0.1]  # kit: edge point; table: pin centre
print("kit pin sites differing from table:", len(bad), bad[:5])
ts = gzw(f"{d}/{NEW}.gz", keep)
p = json.load(gzip.open(f"{d}/die_plan.json.gz"))
inst = []
for q in ("q_hub_nw", "q_hub_ne"):
    for c in p["partition_types"][q]["hard_cores"]:
        if c.get("pins_file") == OLD:
            c["pins_file"] = NEW; inst.append(f"{q}.{c['inst']}")
assert len(inst) == 4, inst
ps = gzw(f"{d}/die_plan.json.gz", p)
ev = {"schema": "opentallas.hbm_p60_injdrop.v1", "by": "DIE-HBM-86", "ruling": "COORD 2026-11-07 08:41 (1) injector (B)", "module": "ot_hgi_coll_inj_idx_join_rg",
      "instances": inst, "pins_removed": DROP, "pins_read_kept_r1": READ, "old_table": OLD, "new_table": NEW, "table_pins": [4761, 4730],
      "pin_sites_moved": 0, "pin_cycles": 0, "macros_outline_clock": "unchanged", "kit": "eco/inj_e2 (pins.json 4730)",
      "why_read_nothing": "region 1 reads the header only via gs[a*3+:3]<=p_tx[a*545+512+:3]; tx_h and rq_rd feed g_chk, which exists only if(r==0). So r1 bits 102..131 and inj_rd_r1[1] drive nothing; face_shell dropped them.",
      "fan_out": "Parent passes identical wires to idx_tx_h and idx_tx_h_r1, and to inj_rd and inj_rd_r1. Only the r1 branch goes. idx_tx_h and inj_rd keep all bits, so no driver is orphaned and no station, ft slot, or bus width changes. The plan has no per-bit row to edit.",
      "other_unread_r1_bits": "idx_tx_h_r1 3..32, 36..65, 69..98 and inj_rd_r1[0] are also unread but stay as kept pins: the built kit has them.",
      "die_rtl": "parent still passes 132 and 2 bits to ports 102 and 1 wide; elaboration drops the MSBs, same bits. Same form as q2r in512."}
json.dump(ev, open(f"{d}/part60_event.json", "w"), indent=1); open(f"{d}/part60_event.json", "a").write("\n")
s = open(f"{d}/SHA256SUMS").read().splitlines()
out = []
for l in s:
    h, n = l.split(None, 1)
    out.append(f"{ps}  {n}" if n.strip() == "die_plan.json" else l)
out.append(f"{ts}  {NEW}")
open(f"{d}/SHA256SUMS", "w").write("\n".join(out) + "\n")
print("OK", inst, ts[:12], ps[:12])
