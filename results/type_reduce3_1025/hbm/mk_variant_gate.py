#!/usr/bin/env python3
"""TYPE-REDUCE-3/HBM 10-25: gate netlist of ONE old constant variant from the strap master's synthesised kit netlist.

    python3 results/type_reduce3_1025/hbm/mk_variant_gate.py MASTER_KIT NETLIST OLD_KIT CANON_TYPE 'strap=VAL,..' OUT.v

gate = the master netlist (flattened ORFS synth of the strap kit) with
  * every strap_* input removed from the port list and driven by its constant (the parent's TIEHI/TIELO ties);
  * the module renamed to the old variant's plan module (the old kit DESIGN_NAME);
  * the template pin buses renamed back to the old variant's plan buses (core_templates.renamer, the same rename that
    built the template pin table: bus name only, bit indices unchanged), together with the face-shell register names
    the shell derives from them (u_bin_<bus> / u_bout_<bus> / <bus>__fq / <bus>__fc) so key points match by name.
Fail-closed: the edited port set (name, width) must equal the old kit's pin table, every master pin must map.
Then: lec.py OLD_KIT --netlist OUT.v  (gold = the OLD kit RTL: old wrapper + face shell + master with the ID tied)."""
import json, re, sys
from pathlib import Path
R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / "physical/die_plan/hbm_arch"))
import core_templates as CT
mk, net, ok, ct, straps, out = sys.argv[1:7]
straps = dict(x.split("=", 1) for x in straps.split(","))
canon = json.load(open(R / "physical/die_plan/hbm/cores/harden/canonical_ports_split.json"))["types"][ct]
mf = json.load(open(Path(mk) / "freeze.json")); of = json.load(open(Path(ok) / "freeze.json"))
mmod, omod = mf["design"], of["design"]
tid = next(t for t in canon["type_ids"] if re.sub(r"__[\d.]+x[\d.]+$", "", t) == omod)
rn, rb = CT.renamer(canon["type_ids"][tid]["cut_pins"], canon["ports"])
def buses(pins):
    b = {}
    for p in pins:
        n, i = CT.split_bit(p["name"]); b[n] = max(b.get(n, 0), (i or 0) + 1)
    return b
ob = buses(json.load(open(Path(ok) / "pins.json"))); nb = buses(json.load(open(Path(mk) / "pins.json")))
new2old = {}
for o in ob:
    n = rb(o)
    if n in new2old:
        raise SystemExit(f"rename not injective: {o}, {new2old[n]} -> {n}")
    new2old[n] = o
miss = sorted(set(nb) - set(new2old) - set(straps)); extra = sorted(set(new2old) - set(nb))
if miss or extra:
    raise SystemExit(f"pin tables do not correspond: master-only {miss[:6]}, old-only {extra[:6]}")
bad = [n for n in new2old if nb[n] != ob[new2old[n]]]
if bad:
    raise SystemExit(f"width mismatch {bad[:6]}")
t = Path(net).read_text()
m = re.search(r"(?m)^module\s+" + re.escape(mmod) + r"\s*\(", t)
if not m:
    raise SystemExit(f"no module {mmod} in {net}")
end = t.index("endmodule", m.end())
top = t[m.start():end]
for s, val in straps.items():
    w, bits = re.fullmatch(r"(\d+)'b([01]+)", val).groups()
    top, k = re.subn(r"(?m)^(\s*)input\s+(\[\d+:\d+\]\s+)?" + re.escape(s) + r"\s*;", lambda q: f"{q.group(1)}wire {q.group(2) or ''}{s};\n{q.group(1)}assign {s} = {w}'b{bits};", top)
    if k != 1:
        raise SystemExit(f"strap {s}: input declaration not found once ({k})")
    hdr_end = top.index(");")
    h2, k = re.subn(r"(?<![\w$\\])" + re.escape(s) + r"(?![\w$])\s*,\s*|,\s*" + r"(?<![\w$\\])" + re.escape(s) + r"(?![\w$])", "", top[:hdr_end], count=1)
    if k != 1:
        raise SystemExit(f"strap {s}: not in the port list")
    top = h2 + top[hdr_end:]
ren = {n: o for n, o in new2old.items() if n != o}
if ren:
    alt = "|".join(map(re.escape, sorted(ren, key=len, reverse=True)))
    top = re.sub(r"(?<![\w$.\\])(" + alt + r")(?![\w$])", lambda q: ren[q.group(1)], top)          # ports (plain identifiers)
    sid = {CT.re.sub(r"[^A-Za-z0-9_]", "_", n): CT.re.sub(r"[^A-Za-z0-9_]", "_", o) for n, o in ren.items()}
    alt2 = "|".join(map(re.escape, sorted(sid, key=len, reverse=True)))
    top = re.sub(r"(?<![A-Za-z0-9_])(u_bin_|u_bout_)(" + alt2 + r")(?![A-Za-z0-9_])", lambda q: q.group(1) + sid[q.group(2)], top)
    top = re.sub(r"(?<![A-Za-z0-9_])(" + alt2 + r")(__fq|__fc)(?![A-Za-z0-9_])", lambda q: sid[q.group(1)] + q.group(2), top)
top = re.sub(r"^module\s+" + re.escape(mmod), "module " + omod, top, count=1)
# fail-closed port check of the edited top
hdr = top[:top.index(");")]
plist = re.findall(r"[\\]?[\w$]+", hdr[hdr.index("(") + 1:])
decl = {}
for d, rng, n in re.findall(r"(?m)^\s*(input|output)\s+(\[\d+:\d+\]\s+)?([\w$]+)\s*;", top):
    decl[n] = (int(re.match(r"\[(\d+):(\d+)\]", rng).group(1)) - int(re.match(r"\[(\d+):(\d+)\]", rng).group(2)) + 1) if rng else 1
if set(plist) != set(decl) or decl != ob:
    d1 = sorted(set(decl.items()) ^ set(ob.items()))
    raise SystemExit(f"edited port set != old kit pins: {d1[:8]} (plist {len(plist)} decl {len(decl)} old {len(ob)})")
t = t[:m.start()] + top + t[end:]
Path(out).write_text(t)
print(json.dumps(dict(gate=out, master=mmod, old=omod, straps=straps, renamed_buses=len(ren), ports=len(decl))))
