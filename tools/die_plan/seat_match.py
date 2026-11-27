#!/usr/bin/env python3
"""SEAT-MATCH (SEAT-MATCH-AUDIT 11-24): plan relay_sites keys against the bound RTL, statically (no synthesis).

Why: a plan relay_sites row names a register of the bound module.  When a later bind / RTL event renames, re-depths or drops that
register the row stays in the plan, seats nothing, and the live register falls to free placement; until now only the place log said so
(QC sle_ctl: 16,442 of 70,623 keys; 15,996 of them u_pd<D>_<bus>_<bit> chains the R8 strap pass had replaced by u_r8b_strap_* banks,
whose 3,216 + 9,216 + 4,352 + 1,506 flops had no seat).  The check reads the bound module text only: instance names and, for the station
primitives (ot_dp_dly / ot_dp_dly_keep W D, ot_dp_dly_cnt W DMAX, ot_dp_st W), the registers each instance holds.

Verdict per key (first path component C, rest R):
  OK        C is an instance and R is a register it holds (or C is an instance key)
  UNKNOWN   C is an instance of another module (its inside is not read), or C is a name a kit RTL pass derives from a bound instance
            or from a bound net (__suffix, _u_r<k>_<j> tail copies, u_y_* relays, u_pd<L>_ram_* leads): not judged
  DEAD-INST C is no instance and no identifier of the bound module, and derives from none
  DEAD-REG  C is a station primitive without that register (stage past the depth, bit past the width, q of a strap-count bank)
  CONFLICT  '/' and '.' spellings of one register at DIFFERENT sites (QC st_a x10: 128 registers each, 214 um apart)
A DEAD-REG q[b] of an ot_dp_dly_cnt is OK-CNT (kit_istations RELAY-CNT seats the last kept stage).  DEAD u_pd<D>_<bus>_<bit> rows
carry the strap banks now fed by <bus>_q as a hint.

  seat_match.py PLAN BIND_RTL_DIR [--types T1,T2] [--json OUT] [--fail]      per-type counts, DEAD / CONFLICT groups
  seat_match.py --kit KIT_DIR                                             the same for a generated kit (istations.tcl vs its RTL)
  seat_match.py prune PLAN BIND_RTL_DIR OUT LEDGER [--types ...]             drops DEAD-INST / DEAD-REG rows only (ledger lists each)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

PRIM = {"ot_dp_dly", "ot_dp_dly_keep", "ot_dp_dly_cnt", "ot_dp_st"}
INST = re.compile(r"(?m)^\s*(?:\(\*.*?\*\)\s*)?([A-Za-z_]\w*)\s*(?:#\s*\(((?:[^()]|\([^()]*\))*)\)\s*)?([A-Za-z_]\w*)\s*\(")
PARAM = re.compile(r"\.\s*(\w+)\s*\(\s*(\d+)\s*\)")
NOT_MOD = {"module", "assign", "wire", "reg", "input", "output", "function", "if", "for", "generate", "begin", "case", "always",
           "initial", "localparam", "parameter", "logic", "else", "end", "genvar", "integer"}
DEAD = ("DEAD-INST", "DEAD-REG", "CONFLICT")
# names kit RTL passes / the bind derive from a bound name: the stem decides nothing about the register
DERIVED = re.compile(r"(__\w+|_u_r\d+_\d+)$")
KITPASS = re.compile(r"^(u_y_|u_pd\d+_ram_|u_rg\d|u_ring\b)")
IST = re.compile(r"^u_ist_(.+)_(\d+)$")        # kit_istations inserts u_ist_<bus>_<j> for the plan's internal_stations (not in the bind RTL)


def bound_instances(text):
    """{instance: (module, {param: int})} of every module body of the bound file"""
    out = {}
    for m in INST.finditer(text):
        mod, par, name = m.group(1), m.group(2) or "", m.group(3)
        if mod in NOT_MOD or name in NOT_MOD:
            continue
        out[name] = (mod, {k: int(v) for k, v in PARAM.findall(par)})
    return out


def reg_ok(mod, par, rest):
    """True / False / None (not judged): does the primitive hold register path `rest` (without the leading separator)"""
    W, D = par.get("W", 1), par.get("D", par.get("DMAX"))
    m = re.fullmatch(r"(r|q|eq)(?:\[(\d+)\])?(?:\[(\d+)\])?", rest)
    if not m:
        return None
    reg, i, b = m.group(1), m.group(2), m.group(3)
    i = None if i is None else int(i)
    b = None if b is None else int(b)
    if mod == "ot_dp_st":
        return reg == "eq" or (reg == "q" and (i or 0) < W) or (reg == "r" and None)
    if D is None:
        return None
    if mod == "ot_dp_dly_cnt":
        if reg == "q":
            return "CNT" if b is None and (i or 0) < W else False
        return None if i is None else (i < D and (b is None or b < W))
    if reg == "q":
        return (i or 0) < W
    if reg == "r":
        if i is None:
            return None
        return i < D - 1 and (b or 0) < W
    return False


def judge(relay_sites, text, ist_buses=None):
    """{key: verdict} of one type.  text = the bound module file; ist_buses {bus: stations} = the plan stations the kit adds later (None: the
    text is the kit's own RTL, which has them)"""
    inst = bound_instances(text)
    ident = set(re.findall(r"[A-Za-z_]\w*", text))
    has_y = any(i.startswith("u_y_") for i in ident)
    twin = {}
    for k in relay_sites:
        twin.setdefault(k.replace("/", "."), []).append(k)
    out = {}
    for k, v in relay_sites.items():
        c = re.split(r"[./]", k, maxsplit=1)
        base = re.sub(r"\[\d+\]", "", c[0])
        rest = c[1] if len(c) > 1 else ""
        tw = twin[k.replace("/", ".")]
        if len(tw) > 1 and any(relay_sites[t] != v for t in tw):
            out[k] = "CONFLICT"
            continue
        if base in inst:
            mod, par = inst[base]
            if not rest or mod not in PRIM:
                out[k] = "OK" if not rest else "UNKNOWN"
                continue
            ok = reg_ok(mod, par, rest.replace("/", "."))
            out[k] = "UNKNOWN" if ok is None else ("OK-CNT" if ok == "CNT" else ("OK" if ok else "DEAD-REG"))
        elif base in ident:
            out[k] = "UNKNOWN"
        elif KITPASS.match(base):
            # C-RELAY-SEAT-KEYMISS 11-27: once the text holds u_y_ relays (the relay pass ran), a u_y_ key with no such identifier seats nothing (hub_Eo astk_EN/ES)
            out[k] = "DEAD-INST" if base.startswith("u_y_") and has_y else "UNKNOWN"
        elif ist_buses is not None and IST.match(base):
            m = IST.match(base)
            out[k] = "UNKNOWN" if int(m.group(2)) < ist_buses.get(m.group(1), 0) else "DEAD-INST"
        else:
            d = DERIVED.sub("", base)
            out[k] = "UNKNOWN" if d != base and (d in inst or d in ident) else "DEAD-INST"
    return out


def _bound_file(rtl, tn):
    rtl = Path(rtl)
    for n in (f"{tn}_part.sv", f"{tn}_bound.sv", f"{tn}.sv"):
        if (rtl / n).is_file():
            return rtl / n
    hits = sorted(rtl.glob(f"*p_{tn}.sv"))
    return hits[0] if len(hits) == 1 else None


def group(keys):
    return Counter(re.sub(r"_\d+(?=[./])", "_#", re.sub(r"\[\d+\]", "[]", k)) for k in keys)


def hint(keys, text):
    """strap banks now fed by the buses the dead u_pd<D>_<bus>_<bit> chains carried: {bus: [bank]}"""
    buses = {m.group(1) for m in (re.match(r"u_pd\d+_(.+?)_\d+[./]", k) for k in keys) if m}
    out = {}
    for m in re.finditer(r"(?m)^\s*ot_dp_dly\w*\s+#\(([^;]*?)\)\s+(u_r8b_\w+)\s*\((.*)$", text):
        d = re.search(r"\.d\(([^)]*\)?)", m.group(3))
        for b in buses:
            if d and re.search(rf"\b{re.escape(b)}_q\b", d.group(1)):
                out.setdefault(b, []).append(m.group(2))
    return out


def ist_buses(t):
    """{bus: stations} of the type's internal_stations (conn bus:<name>)"""
    out = {}
    for e in t.get("internal_stations") or []:
        c = str(e.get("conn", ""))
        if c.startswith("bus:"):
            out[c[4:]] = max(out.get(c[4:], 0), len(e.get("regs_um") or []))
    return out


def kit_sites(kit):
    """relay_sites of a generated kit, read from the rs_place_all dict of istations.tcl -> {key: [x, y]}"""
    out = {}
    for n in ("istations.tcl", "istations_post.tcl"):
        f = Path(kit) / n
        if f.is_file():
            for ln in f.read_text(errors="replace").splitlines():
                if ln.startswith("rs_place_all "):
                    for k, x, y in re.findall(r"\{([^{}]+)\} \{(-?[\d.e+]+) (-?[\d.e+]+)\}", ln):
                        out[k] = [float(x), float(y)]
            # C-RELAY-SEAT-KEYMISS (11-27): relay_rank_sites seats are rs_rank_line calls, not rs_place_all keys; the lint ignored them
            for m in re.finditer(r"(?m)^\s*rs_rank_line\s+\{([^{}]*)\}\s+(-?[\d.e+]+)\s+(-?[\d.e+]+)", f.read_text(errors="replace")):
                alts = m.group(1).split()
                if alts:
                    out[alts[0]] = [float(m.group(2)), float(m.group(3))]
    return out


def kit_scan(kit):
    """scan record of one generated kit (its own *_bound.sv / <type>.sv), or None"""
    kit = Path(kit)
    f = next(iter(sorted((kit / "rtl").glob("*_bound.sv"))), None) or next((p for p in sorted((kit / "rtl").glob("*.sv")) if p.stem == kit.name), None)
    rs = kit_sites(kit)
    if not rs or f is None:
        return None
    text = f.read_text(errors="replace")
    v = judge(rs, text)
    dead = [k for k, x in v.items() if x in ("DEAD-INST", "DEAD-REG")]
    return {"n": len(rs), "counts": dict(Counter(v.values())), "dead": dict(group(dead)),
            "conflict": dict(group([k for k, x in v.items() if x == "CONFLICT"])), "hint": hint(dead, text), "keys": v}


def kit_lines(kit):
    """loud lines of a kit read: [] when every seat key has a register"""
    r = kit_scan(kit)
    if not r or not any(x in DEAD for x in r["keys"].values()):
        return []
    n = sum(x in DEAD for x in r["keys"].values())
    grp = Counter({**r["dead"], **r["conflict"]}).most_common(3)
    return [f"SEAT-MISS WARN {n} of {r['n']} plan relay_sites keys seat nothing in this kit's RTL ("
            + ", ".join(f"{g} x{c}" for g, c in grp) + ")" + ("; moved to " + ", ".join(sorted({b for x in r["hint"].values() for b in x})[:4]) if r["hint"] else "")]


def scan(plan_raw, rtl, types=None):
    """{type: {"n", "counts", "dead": {group: n}, "conflict": {group: n}, "hint", "keys": {key: verdict}}} for types with relay_sites + a bound file"""
    out = {}
    for tn, t in sorted((plan_raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict) or (types and tn not in types):
            continue
        rs = t.get("relay_sites") or {}
        f = _bound_file(rtl, tn)
        if not rs or f is None:
            continue
        text = f.read_text(errors="replace")
        v = judge(rs, text, ist_buses(t))
        dead = [k for k, x in v.items() if x in ("DEAD-INST", "DEAD-REG")]
        out[tn] = {"n": len(rs), "counts": dict(Counter(v.values())), "dead": dict(group(dead)),
                   "conflict": dict(group([k for k, x in v.items() if x == "CONFLICT"])), "hint": hint(dead, text), "keys": v}
    return out


def findings(plan_raw, rtl, baseline_raw=None, own_bind=True, max_list=3):
    """WARN SEATMATCH lines of a whole plan against one bind's RTL (REPORT-ONLY, FABLE-RC-QC / COORD 11-24: no FAIL until the re-keys land).
    Rows the baseline plan lacks are named NEW when the RTL is the bind of THIS plan (own_bind)."""
    lines = []
    base_t = (baseline_raw or {}).get("partition_types") or {}
    for tn, r in scan(plan_raw, rtl).items():
        bad = {k for k, x in r["keys"].items() if x in DEAD}
        if not bad:
            continue
        brs = (base_t.get(tn) or {}).get("relay_sites") or {}
        fresh = sorted(k for k in bad if k not in brs) if baseline_raw is not None and own_bind else []
        n = Counter({**r["dead"], **r["conflict"]}).most_common(max_list)
        txt = (f"WARN SEATMATCH {tn}: {len(bad)} of {r['n']} relay_sites keys seat nothing on the bound RTL ("
               + ", ".join(f"{g} x{c}" for g, c in n) + ")")
        if r["hint"]:
            txt += "; moved to " + ", ".join(f"{b}->{'/'.join(sorted(set(x))[:3])}" for b, x in sorted(r["hint"].items()))
        txt += (f"; {len(fresh)} NEW against the baseline (e.g. {fresh[0]})" if fresh else "")
        lines.append(txt + "; re-key or drop (seat_match.py prune, strap_bank_seats.py)")
    return lines


def main(a):
    if a[:1] == ["--kit"]:
        r = kit_scan(a[1])
        print(json.dumps({k: v for k, v in (r or {}).items() if k != "keys"}))
        for ln in kit_lines(a[1]):
            print(ln)
        return 0
    if a[:1] == ["prune"]:
        plan, rtl, out, led = a[1:5]
        types = set(a[a.index("--types") + 1].split(",")) if "--types" in a else None
        raw = json.loads(Path(plan).read_text())
        rec = {}
        for tn, r in scan(raw, rtl, types).items():
            drop = {k: x for k, x in r["keys"].items() if x in ("DEAD-INST", "DEAD-REG")}
            if drop:
                rs = raw["partition_types"][tn]["relay_sites"]
                rec[tn] = {k: {"verdict": x, "site": rs.pop(k)} for k, x in drop.items()}
        from type_relay_seat_io import style_of
        Path(out).write_text(style_of(Path(plan).read_bytes())(raw))
        Path(led).write_text(json.dumps({"tool": "seat_match prune", "plan": str(plan), "bind_rtl": str(rtl), "dropped": rec}, indent=1))
        print(f"seat_match prune: {sum(len(v) for v in rec.values())} dead rows dropped in {len(rec)} type(s)")
        return 0
    types = set(a[a.index("--types") + 1].split(",")) if "--types" in a else None
    r = scan(json.loads(Path(a[0]).read_text()), a[1], types)
    if "--json" in a:
        Path(a[a.index("--json") + 1]).write_text(json.dumps(r))
    n = 0
    for tn, x in r.items():
        bad = sum(v in DEAD for v in x["keys"].values())
        n += bad > 0
        print(f"SEATMATCH {tn} keys {x['n']} {x['counts']}" + (f" dead {x['dead']} {x['hint']}" if bad else ""))
    print(f"SEATMATCH types {len(r)} with dead or conflicting keys {n}")
    return 1 if n and "--fail" in a else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
