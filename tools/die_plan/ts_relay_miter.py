#!/usr/bin/env python3
"""TYPE-SAFE-2 11-08: latency miter of the relay constructor on BOUND RTL (structural, exact), per LANE.

Inputs: the plan the event produced (NEW_PLAN), the event JSON, and two bind output rtl dirs from the same bind tool:
OLD (base plan) and NEW (event plan).  For every .sv that differs, every differing line must be a register stage of a
declared lane's bus, and per lane the stages added in the source type (out bus) plus the receiver type (in bus) must
equal the declared pin-cycle delta:
  stage forms counted: `ot_dp_dly #(.W(w), .D(d)) u_lpad_<bus>` (D, the native lane pad, right after u_bin_<bus>) and
  `ot_dp_st #(.W(w)) u_ist_<bus>_<j>` (one station; kit_istations / native_istations)
  tolerated: the u_bin_/u_bout_ face register line of that bus re-pointed onto the first/last stage, the stage wires,
  comments and the `// lane ... N cycles` port notes (they restate the latency).
Lines compare as a multiset (declaration order carries no hardware).  bind names unique glue cells `$src_<hash of the
source span>`, so a source file whose line numbers moved renames those cells with no hardware change: a name present on
one side only is paired with a one-side-only name of the same connectivity signature (every line it appears on, other
unpaired names masked, refined until stable); anything left unpaired stays a reported difference.
Each stage is one register on the whole bus (data + epoch), so a lane whose only change is k added stages is the old
lane delayed by exactly k cycles (new == old delayed k), and every other line is identical.

usage: ts_relay_miter.py NEW_PLAN.json EVENT.json OLD_RTL_DIR NEW_RTL_DIR [OUT.json] [--r8 EXTRA.json] -> exit 0 PASS / 1 FAIL"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


SRC_NAME = re.compile(r"src_[0-9a-f]{20}")


PAD_INST = re.compile(r"^ot_dp_dly #\(\.W\(1\), \.D\((\d+)\)\) u_pd\d+_(\w+)_(\d+) \(\.clk\(clk\), \.d\((\w+)_q\[(\d+)\]\), "
                      r"\.q\(pd\d+_\w+\)\);$")
PAD_WIRE = re.compile(r"^wire \[0:0\] pd\d+_\w+;$")
PAD_NET = re.compile(r"\bpd\d+_(\w+)_(\d+)\[0\]")


Q_RANGE = re.compile(r"\b(\w+_q)\[(\d+):(\d+)\]")


def _expand_range(m):
    hi, lo = int(m.group(2)), int(m.group(3))
    return ", ".join(f"{m.group(1)}[{i}]" for i in range(hi, lo - 1, -1))


def split_r8_pads(lines):
    """R8 per-bit landing pads out of the lines: -> (other lines with a pad output read as the bit it delays, {(bus, bit): D})"""
    depth, rest = {}, []
    for ln in lines:
        m = PAD_INST.match(ln)
        if m and m.group(2) == m.group(4) and m.group(3) == m.group(5):
            depth[(m.group(2), int(m.group(3)))] = int(m.group(1))
        elif not PAD_WIRE.match(ln):
            ln = PAD_NET.sub(lambda x: f"{x.group(1)}_q[{x.group(2)}]", ln)
            rest.append(Q_RANGE.sub(_expand_range, ln))
    return rest, depth


def norm(txt):
    out = []
    for ln in txt.splitlines():
        s = re.sub(r"//.*$", "", ln).strip()
        if s:
            out.append(re.sub(r"\s+", " ", s))
    return out


def _src_names(lines):
    return {m for ln in lines for m in SRC_NAME.findall(ln)}


def pair_src_names(A, B):
    """old->new map for bind source-hash names present on one side only, by connectivity signature."""
    only_a, only_b = _src_names(A) - _src_names(B), _src_names(B) - _src_names(A)
    if not only_a or not only_b:
        return {}
    pairs = {}

    def signatures(lines, names, known):
        sig = defaultdict(list)
        for ln in lines:
            hit = [n for n in SRC_NAME.findall(ln) if n in names]
            if not hit:
                continue
            for n in set(hit):
                sig[n].append(SRC_NAME.sub(lambda m: "@self" if m.group(0) == n else known.get(m.group(0), "@open")
                                           if m.group(0) in names else m.group(0), ln))
        return {n: tuple(sorted(v)) for n, v in sig.items()}

    while True:
        ia = {a: b for a, b in pairs.items()}
        ib = {b: b for b in pairs.values()}
        sa = signatures(A, only_a, ia)
        sb = signatures(B, only_b, ib)
        by_a, by_b = defaultdict(list), defaultdict(list)
        for n, v in sa.items():
            if n not in pairs:
                by_a[v].append(n)
        taken = set(pairs.values())
        for n, v in sb.items():
            if n not in taken:
                by_b[v].append(n)
        new = {by_a[v][0]: by_b[v][0] for v in by_a if len(by_a[v]) == 1 and len(by_b.get(v, ())) == 1}
        if not new:
            # names still sharing one signature are interchangeable so far: pair them in order, the multiset test decides
            for v in by_a:
                for a, b in zip(sorted(by_a[v]), sorted(by_b.get(v, ()))):
                    pairs[a] = b
            return pairs
        pairs.update(new)


def rename_src_names(A, B):
    m = pair_src_names(A, B)
    return [SRC_NAME.sub(lambda x: m.get(x.group(0), x.group(0)), ln) for ln in A] if m else A


def main(argv):
    # --r8 EXTRA.json: the die's R8 table was re-derived: a per-bit pad may give back a stage of its bus one for one (landed
    # unchanged); a pad that grows is accepted only if listed in EXTRA.json = [{"type":, "bus":, "delta":}, ...]
    argv = list(argv)
    r8_extra = None
    if "--r8" in argv:
        i = argv.index("--r8")
        r8_extra = {(x["type"], x["bus"]): x["delta"] for x in json.load(open(argv[i + 1]))}
        del argv[i:i + 2]
    plan_f, ev_f, old_d, new_d = argv[1:5]
    out_f = argv[5] if len(argv) > 5 else None
    r8_moves = defaultdict(int)
    P = json.load(open(plan_f))
    ev = json.load(open(ev_f))
    ports = {p["id"]: p for p in P["ports"]}
    ptype = {p["name"]: p["type"] for p in P["partitions"]}
    # bound file stems: <type>, s81p_<type>, the plan module, or the cloned <module>__<type>
    stem_type = {}
    for t, rec in (P.get("partition_types") or {}).items():
        mod = rec.get("module", t) if isinstance(rec, dict) else t
        stem_type.update({t: t, f"s81p_{t}": t, mod: t, f"{mod}__{t}": t})
    declared = defaultdict(int)
    for e in ev["edits"]:
        for lid, v in e["lanes"].items():
            declared[lid] = max(declared[lid], v["delta"])
    # (type, bus) -> lanes through it (source out bus / receiver in bus)
    tb = defaultdict(set)
    for ln in P["lanes"]:
        if ln["id"] not in declared:
            continue
        a, b = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        if a["src"]["part"] in ptype:
            tb[(ptype[a["src"]["part"]], a["src"]["bus"])].add(ln["id"])
        if b["dst"]["part"] in ptype:
            tb[(ptype[b["dst"]["part"]], b["dst"]["bus"])].add(ln["id"])
    # a type's bus stage delta is shared by all its instances' lanes: count it once per (type, bus) and attribute it to
    # each lane through it (instances of one type are identical)
    realised = defaultdict(int)
    bad, files = [], 0
    for nf in sorted(Path(new_d).glob("*.sv")):
        of = Path(old_d) / nf.name
        if not of.exists():
            bad.append(f"new file {nf.name}")
            continue
        A, B = norm(of.read_text()), norm(nf.read_text())
        if A == B:
            continue
        tn = stem_type.get(nf.stem, nf.stem[5:] if nf.stem.startswith("s81p_") else nf.stem)
        buses = {b for (t, b) in tb if t == tn}
        A = rename_src_names(A, B)
        pads = None
        if r8_extra is not None:
            A, pad_a = split_r8_pads(A)
            B, pad_b = split_r8_pads(B)
            pads = {k: (pad_a.get(k, 0), pad_b.get(k, 0)) for k in set(pad_a) | set(pad_b) if pad_a.get(k, 0) != pad_b.get(k, 0)}
        ca, cb = Counter(A), Counter(B)
        if ca == cb and not pads:
            continue
        files += 1
        delta = defaultdict(int)
        for sign, lines in ((-1, list((ca - cb).elements())), (1, list((cb - ca).elements()))):
            for ln in lines:
                m = re.match(r"^ot_dp_dly #\(\.W\(\d+\), \.D\((\d+)\)\) u_lpad_(\w+) \(", ln)
                if m and m.group(2) in buses:
                    delta[m.group(2)] += sign * int(m.group(1))
                    continue
                if re.match(r"^ot_dp_st #\(\.W\(\d+\)\) u_ist_\w+_t\w+ \(", ln) and any(
                        re.match(rf"^ot_dp_st #\(\.W\(\d+\)\) u_ist_{re.escape(x)}_t", ln) for x in buses):
                    continue    # HBM-KITIST-1 station_trees node: tree depth is gated by kit_topology, not a cycle delta here
                m = re.match(r"^ot_dp_st #\(\.W\(\d+\)\) u_ist_(\w+)_(\d+) \(", ln)
                if m and m.group(1) in buses:
                    delta[m.group(1)] += sign
                    continue
                m = re.match(r"^ot_dp_st #\(\.W\(\d+\)\) u_b(?:in|out)_(\w+) \(", ln)
                if m and m.group(1) in buses:
                    continue
                if re.match(r"^wire ", ln) and any(re.search(rf"\b{re.escape(b)}_(?:is\d+_e?q|b|eb|q|eq)\b", ln)
                                                   for b in buses):
                    continue
                bad.append(f"{nf.name}: {'+' if sign > 0 else '-'} {ln[:180]}")
        for (bus, bit), (d0, d1) in sorted((pads or {}).items()):
            give = -delta.get(bus, 0)
            kind = "trade" if delta.get(bus, 0) and d1 - d0 == give else "extra" if r8_extra.get((tn, bus)) == d1 - d0 else None
            if kind:
                r8_moves[f"{tn}.{bus} {kind} {d1 - d0:+d}"] += 1
            else:
                bad.append(f"{nf.name}: R8 pad {bus}[{bit}] {d0}->{d1}, stages {delta.get(bus, 0):+d}")
        for b, d in delta.items():
            for lid in tb[(tn, b)]:
                realised[lid] += d
    mism = {lid: dict(declared=declared[lid], realised=realised.get(lid, 0))
            for lid in declared if realised.get(lid, 0) != declared[lid]}
    ok = not bad and not mism
    rec = dict(verdict="PASS" if ok else "FAIL", lanes=len(declared), files_changed=files,
               lanes_matching=len(declared) - len(mism), mismatch=dict(list(mism.items())[:60]), n_mismatch=len(mism),
               undeclared_changes=bad[:60], n_undeclared=len(bad), r8_moves=dict(sorted(r8_moves.items())))
    if out_f:
        Path(out_f).write_text(json.dumps(dict(rec, realised=realised, declared=declared), indent=1) + "\n")
    print(json.dumps(rec, indent=1)[:4000])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
