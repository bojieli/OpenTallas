#!/usr/bin/env python3
"""TYPE-REDUCE-3/HBM 10-25: strap wrappers that implement the TEMPLATE PIN TABLE (root-cause fix).

core_templates.py (TYPE-REDUCE-2) wrote every *_strap wrapper as the canonical master's port list with the ID ports
renamed strap_*.  That is the plan module only when every cut pin of every member is one whole canonical port (sfu
lane).  For pg_lane_exp / pg_lanes4 the template pin table keeps the position-neutral CUT pins (concatenated buses such
as bank_read_addr__lane_rd_addr, g_bank_N_u_bank_read_addr, inj_q = bank_read_data[159:128]), so the generated wrapper
ports != plan pins (gen_core_kit_hbm.py: PORT_MISMATCH) and the B2n bind could never connect it.
Fix: the strap wrapper = the hand-checked split wrapper of the old variants (physical/die_plan/hbm_arch_cores/wrappers/
<old>.sv, the wrapper every old kit used), its port buses renamed with core_templates.renamer (the SAME rename that
built the template pin table) and its ID constants replaced by the strap_* ports.  Fail-closed checks: every member
(old variant) must give the IDENTICAL wrapper text after the rename (else the members do not share one bit map); the
wrapper ports must equal the template pin table (names + widths); a renamed port must not collide with a wrapper
internal identifier.  Run from the repo root:  python3 results/type_reduce3_1025/hbm/strap_wrap_from_hand.py
"""
import json, re, sys
from pathlib import Path
R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / "physical/die_plan/hbm_arch"))
import core_templates as CT
canon = json.load(open(R / "physical/die_plan/hbm/cores/harden/canonical_ports_split.json"))["types"]
variants = json.load(open(R / "results/type_reduce3_1025/hbm/variants.json"))
views = {v["module"]: v for v in json.load(open(R / "physical/die_plan/hbm_arch_cores/views_b2n_strap.json"))["view_list"]}
PD = R / "physical/die_plan/hbm_arch/B2n"
HAND = R / "physical/die_plan/hbm_arch_cores/wrappers"
PORT_RE = re.compile(r"^\s*(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?([A-Za-z_][A-Za-z0-9_$]*)\s*,?\s*$", re.M)
rc = 0
report = {}
for master in ("ot_hbm_su_pg_lane_exp_core_strap", "ot_hbm_su_pg_lanes4_core_strap"):
    ct = views[master]["strap_master"]["canonical_type"]
    c = canon[ct]
    texts = {}
    for var in variants[master]:
        old = var["old_module"]
        tid = next(t for t in c["type_ids"] if re.sub(r"__[\d.]+x[\d.]+$", "", t) == old)
        v = c["type_ids"][tid]
        rn, rb = CT.renamer(v["cut_pins"], c["ports"])
        t = (HAND / f"{old}.sv").read_text()
        hdr_end = t.index(");")
        ports = [(m.group(4), m.group(1), int(m.group(2)) + 1 if m.group(2) else 1) for m in PORT_RE.finditer(t[:hdr_end])]
        ren = {n: rb(n) for n, _d, _w in ports}
        body_ids = set(re.findall(r"(?<![.\w$])[A-Za-z_][A-Za-z0-9_$]*\b", t[hdr_end:])) - set(ren)   # not .port keys
        clash = sorted(set(ren.values()) & body_ids)
        if clash:
            raise SystemExit(f"{old}: renamed ports collide with wrapper identifiers {clash[:5]}")
        if len(set(ren.values())) != len(ren):
            raise SystemExit(f"{old}: rename not injective")
        t2 = re.sub(r"(?<![.\w$])(" + "|".join(map(re.escape, sorted(ren, key=len, reverse=True))) + r")\b", lambda m: ren[m.group(1)], t)
        sv = {s["port"][len("strap_"):]: s["value"] for s in [dict(port=k, value=x) for k, x in var["straps"].items()]}
        for p, val in sv.items():
            w, bits = re.fullmatch(r"(\d+)'b([01]+)", val).groups()
            m = re.search(r"\.(" + re.escape(p) + r")\((\{[^}]*\}|[^)]*)\)", t2)
            if not m:
                raise SystemExit(f"{old}: no .{p}(...) connection in the hand wrapper")
            got = "".join(re.findall(r"1'b([01])", m.group(2))) if m.group(2).startswith("{") else None
            if got != bits:
                raise SystemExit(f"{old}: hand wrapper ties {p} = {m.group(2)}, plan strap says {val}")
            t2 = t2[:m.start()] + f".{p}(strap_{p})" + t2[m.end():]
        decl = "".join(f"    input wire [{int(re.fullmatch(r'(\d+)' + chr(39) + r'b[01]+', x).group(1)) - 1}:0] strap_{p},\n"
                       for p, x in sorted(sv.items()))
        t2 = re.sub(r"(?m)^module\s+" + re.escape(old) + r"\s*\(\n", f"module {master} (\n" + decl, t2, count=1)
        t2 = "\n".join(l for l in t2.split("\n") if not l.startswith("//"))     # per-variant provenance comments
        # port declaration order differs between the hand wrappers: emit the ports sorted by name (same set, same widths)
        mh = re.search(r"(?s)(module\s+\w+\s*\(\n)(.*?)(\n\);)", t2)
        dl = sorted(l.strip().rstrip(",") for l in mh.group(2).split("\n") if l.strip())
        t2 = t2[:mh.start(2)] + ",\n".join("    " + l for l in dl) + t2[mh.end(2):]
        texts[old] = t2
    ref = next(iter(texts.values()))
    diff = [o for o, x in texts.items() if x != ref]
    if diff and "--dump" in sys.argv:
        for o, x in texts.items():
            (Path("/tmp") / f"tr3h_{o}.sv").write_text(x)
    pins = json.load(open(PD / views[master]["pins_file"]))
    pb = {}
    for q in pins:
        b, i = CT.split_bit(q["name"])
        pb[b] = max(pb.get(b, 0), (i or 0) + 1)
    hdr = ref[:ref.index(");")]
    wp = {m.group(4): (int(m.group(2)) + 1 if m.group(2) else 1) for m in PORT_RE.finditer(hdr)}
    bad = sorted(set(pb.items()) ^ set(wp.items()))
    report[master] = dict(members=len(texts), members_differing=diff, port_vs_pins_mismatch=bad[:20], ports=len(wp))
    if diff or bad:
        rc = 1
        continue
    out = R / views[master]["strap_master"]["wrapper"]
    hdrc = ("// GENERATED by results/type_reduce3_1025/hbm/strap_wrap_from_hand.py (TYPE-REDUCE-3/HBM 2026-10-25). Do not edit.\n"
            f"// One hardened design for every replica of {c['top']}: the template pin table (core_templates.renamer) wired to the\n"
            "// master exactly as the old variants' hand-checked split wrappers (physical/die_plan/hbm_arch_cores/wrappers/"
            f"{'|'.join(sorted(texts))[:60]}...);\n"
            "// the ID constants are declared strap_* input pins (OWNER option B): tied at the parent, set_false_path, no pin register.\n")
    out.write_text(hdrc + ref)
print(json.dumps(report, indent=1))
sys.exit(rc)
