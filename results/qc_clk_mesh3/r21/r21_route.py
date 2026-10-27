"""INFRA-FIRST-QC-R21: regenerate the kit GRT route netlist (ft + reset + channel-crossing die-top nets) for plan_d43
and run the abutted pin coincidence check.  Usage: r21_route.py PLAN OLD_ROUTE_V OUT_DIR"""
import hashlib, json, sys
from collections import defaultdict
from pathlib import Path
import die_trial as DT, gen_phys, schema as S
plan, old, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
P = S.Plan(S.load(plan))
type_bits = {}
for tn in sorted(P.types):
    if not any(p["type"] == tn for p in P.parts.values()):
        continue
    b = defaultdict(int)
    for bus, bit, *_ in gen_phys.type_pins(P, tn):
        b[bus] = max(b[bus], bit + 1)
    type_bits[tn] = dict(b)
v0, nft0 = DT.route_netlist(P, type_bits, channel_nets=False)
v, nft = DT.route_netlist(P, type_bits)
ch = dict(DT.route_netlist.channel)
(out / "route.v").write_text(v)
cp = DT.channel_ports(P)
chk = DT.abutted_pin_check(P)
rec = dict(plan=plan, plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(), ft_bits=nft,
           old_route_v_identical_without_channel=(v0 == old.read_text()), channel_nets=ch,
           channel_pairs=len({tuple(sorted((a, b))) for _, a, _, b, _, _ in cp}),
           channel_prefix=dict(sl=sum(1 for c in cp if c[0].startswith(("sl_", "c_"))), coll=sum(1 for c in cp if c[0].startswith("coll"))),
           abutted_pin_check=chk, checked="UNCHECKED")
(out / "route_meta.json").write_text(json.dumps(rec, indent=1))
print(json.dumps({k: (v_ if k != "abutted_pin_check" else {x: y for x, y in v_.items() if x != "examples"}) for k, v_ in rec.items()}, indent=1))
print("examples", chk["examples"][:5])
import re as _re
dup = 0
for m in _re.finditer(r"^\s*(\w+)\s+(\w+)\s*\((.*?)\);\s*$", v, _re.M | _re.S):
    pins = _re.findall(r"\.(\w+)\(", m.group(3))
    dup += len(pins) != len(set(pins))
print("instances with a pin connected twice:", dup)
