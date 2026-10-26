#!/usr/bin/env python3
"""S81-P9-FACE (2026-10-23): bind the regional service slices of an S81 die netlist to their FACE PORT VARIANTS.

The die generator (tools/s81_dv/dv_bind.py) instantiates every rsv slice as the all-faces master (dsdv_svc_rs /
dsdv_svc_rs_pvso_entry) and ties the faces its role never uses (`unlinked_bits` pads: 0 on inputs, _nc nets on outputs) --
195k tied bits on the cap30 die (owner rule: no tie-offs).  This pass rewrites each `u_rsv_NN` instance to the variant of its
role (svc_rs_faces.py: dsdv_svc_rs_fv_<FM> / dsdv_svc_rs_pvso_entry_fv_<FM>), whose ports are the used faces only
(<bus>_<n|e|s|w>), and removes the tied / open face segments.  It PROVES the role mask against the netlist: a dropped face
must be all constant 0 (input) or all _nc (output); a kept input face must carry no constant bit.

  rewrite(text) -> (text, report)        the die netlist (dv_bind.py calls it when the bind table sets svc_face_variants)
  r8_translate(r8, report)               an R8 landing table (tools/die_plan/r8.py) to the variant port names / bits
CLI: svc_rs_face_bind.py DIE_IN.v DIE_OUT.v [--report R.json] [--r8 IN.json OUT.json]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svc_rs_faces as F  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
INST = re.compile(r"^(\s*)(dsdv_svc_rs|dsdv_svc_rs_pvso_entry)(\s*#\((?:[^()]|\([^()]*\))*\))?\s+(u_rsv_(\d+))\s*\((.*)\);\s*$")
TOK_RANGE = re.compile(r"^([A-Za-z_][\w$]*)\[(\d+):(\d+)\]$")
TOK_BIT = re.compile(r"^([A-Za-z_][\w$]*)\[(\d+)\]$")
TOK_CONST = re.compile(r"^(\d+)'([dhb])([0-9a-fA-F_]+)$")
GROUP_OF = {p: g for g, ps in F.PORTS.items() for p, _d, _w in ps}
WIDTH = {p: w for g, ps in F.PORTS.items() for p, _d, w in ps}
DIR = {p: d for g, ps in F.PORTS.items() for p, d, _w in ps}


def split_top(s, sep=","):
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def conns(body):
    res = []
    for c in split_top(body):
        m = re.match(r"^\.(\w+)\s*\((.*)\)$", c, re.S)
        assert m, c
        res.append((m.group(1), m.group(2).strip()))
    return res


def expand(expr):
    """expr -> bit list LSB first; a bit = ('net', name, idx) | ('const', v)."""
    e = expr.strip()
    parts = split_top(e[1:-1]) if e.startswith("{") and e.endswith("}") else [e]
    bits = []
    for p in parts:                      # MSB first
        m = TOK_RANGE.match(p)
        if m:
            n, hi, lo = m.group(1), int(m.group(2)), int(m.group(3))
            bits.append([("net", n, i) for i in range(hi, lo - 1, -1)])
            continue
        m = TOK_BIT.match(p)
        if m:
            bits.append([("net", m.group(1), int(m.group(2)))])
            continue
        m = TOK_CONST.match(p)
        if m:
            w, b, v = int(m.group(1)), m.group(2), int(m.group(3).replace("_", ""), {"d": 10, "h": 16, "b": 2}[m.group(2)])
            bits.append([("const", (v >> i) & 1) for i in range(w - 1, -1, -1)])
            continue
        raise ValueError(f"cannot expand {p!r} in {expr[:120]!r}")
    flat = [b for grp in bits for b in grp]
    return flat[::-1]


def compress(bits):
    """bit list LSB first -> concatenation expression (MSB first)."""
    segs = []
    for b in bits:
        if segs and b[0] == "net" and segs[-1][0] == "net" and segs[-1][1] == b[1] and segs[-1][3] + 1 == b[2]:
            segs[-1][3] = b[2]
        elif segs and b[0] == "const" and segs[-1][0] == "const" and b[1] == 0 and segs[-1][1] == 0:
            segs[-1][2] += 1
        elif b[0] == "net":
            segs.append(["net", b[1], b[2], b[2]])
        else:
            segs.append(["const", b[1], 1])
    out = []
    for s in reversed(segs):
        if s[0] == "net":
            out.append(f"{s[1]}[{s[3]}:{s[2]}]")
        else:
            out.append(f"{s[2]}'d{s[1]}" if s[1] == 0 else "1'b1")
    return out[0] if len(out) == 1 else "{" + ", ".join(out) + "}"


def rewrite(text, root=ROOT):
    ms = F.masks(root)
    lines = text.split("\n")
    rep = dict(instances={}, dropped_in_bits=0, dropped_out_bits=0, bitmap={}, src_faces={})
    for li, line in enumerate(lines):
        m = INST.match(line)
        if not m:
            continue
        ind, mod, prm, inst, nn, body = m.groups()
        cs = conns(body)
        sid = [e for p, e in cs if p == "sid"]
        sv = int(re.match(r"4'd(\d+)", sid[0]).group(1))
        assert sv == int(nn), (inst, sid)
        mk = ms[sv]
        entry = mod == "dsdv_svc_rs_pvso_entry"
        assert entry == (sv in F.ENTRIES), (inst, mod)
        var = F.variant(sv, mk)
        out, drop_in, drop_out, kept = [], 0, 0, {}
        for p, e in cs:
            if p == "q" and entry:
                # the entry variant's q is the 513-b die q lane; the all-faces port's q[514:513] must be the 0 pad
                qb = expand(e)
                assert len(qb) == 515 and qb[513:] == [("const", 0)] * 2, (inst, "q upper bits not a 0 pad")
                assert all(b[0] == "net" for b in qb[:513]), (inst, "q lane carries a constant")
                out.append(f".q({compress(qb[:513])})")
                drop_in += 2
                continue
            if p not in GROUP_OF:
                out.append(f".{p}({e})")
                continue
            g, w, d = GROUP_OF[p], WIDTH[p], DIR[p]
            bits = expand(e)
            assert len(bits) == 4 * w, (inst, p, len(bits))
            for f in range(4):
                fb = bits[w * f: w * (f + 1)]
                if mk[g] >> f & 1:
                    if d == "input":
                        nconst = sum(1 for b in fb if b[0] == "const")
                        assert nconst == 0, f"{inst}.{p} face {F.FACES[f]} is a role face but carries {nconst} constant bits"
                    np_ = f"{p}_{F.FACES[f]}"
                    out.append(f".{np_}({compress(fb)})")
                    kept[np_] = fb
                    for k in range(w):
                        rep["bitmap"][f"{inst}.{p}[{w * f + k}]"] = [np_, k]
                    if d == "output":
                        for b in fb:
                            if b[0] == "net" and b[1].endswith("_src"):
                                rep["src_faces"][f"{b[1][:-4]}[{b[2]}]"] = f"{inst}.{np_}"
                else:
                    if d == "input":
                        bad = [b for b in fb if b != ("const", 0)]
                        assert not bad, f"{inst}.{p} face {F.FACES[f]} is not a role face but is driven ({bad[:2]})"
                        drop_in += w
                    else:
                        bad = [b for b in fb if not (b[0] == "net" and "_nc" in b[1])]
                        assert not bad, f"{inst}.{p} face {F.FACES[f]} is not a role face but is read ({bad[:2]})"
                        drop_out += w
        # every role face must be present in the netlist connection list (outputs may be absent when the port was unbound)
        lines[li] = f"{ind}{var}{prm or ''} {inst} ({', '.join(out)});"
        rep["instances"][inst] = dict(sid=sv, old=mod, new=var, fm="40'h" + F.fm_hex(mk), dropped_in_bits=drop_in,
                                      dropped_out_bits=drop_out, ports=sorted(kept))
        rep["dropped_in_bits"] += drop_in
        rep["dropped_out_bits"] += drop_out
    assert len(rep["instances"]) == 16, sorted(rep["instances"])
    # drop declarations of _nc nets nothing references any more
    txt = "\n".join(lines)
    used = set(re.findall(r"\b(u_rsv_\d+_\w+_nc\d+)\b", "\n".join(l for l in lines if not l.lstrip().startswith("wire"))))
    keep, gone = [], 0
    for l in lines:
        m = re.match(r"^\s*wire\s*(\[\d+:\d+\])?\s*(u_rsv_\d+_\w+_nc\d+);\s*$", l)
        if m and m.group(2) not in used:
            gone += 1
            continue
        keep.append(l)
    rep["nc_decls_removed"] = gone
    return "\n".join(keep), rep


def r8_translate(r8, rep):
    """Rename svc face pins in an R8 landing table (sink port / bits by the bit map; face-port sources by lane)."""
    bm = rep["bitmap"]
    n = 0
    for m in r8["members"]:
        snk = m["sink"]
        if snk.startswith("u_rsv_") and m["sink_port"] in GROUP_OF:
            newp, nb = None, []
            for a, b in m["sink_bits"]:
                for i in range(a, b + 1):
                    p, k = bm[f"{snk}.{m['sink_port']}[{i}]"]
                    assert newp in (None, p), (m["id"], newp, p)
                    newp = p
                    nb.append(k)
            rng = []
            for k in sorted(nb):
                if rng and rng[-1][1] + 1 == k:
                    rng[-1][1] = k
                else:
                    rng.append([k, k])
            old = f"{snk}.{m['sink_port']}"
            m["sink_port"], m["sink_bits"] = newp, rng
            m["id"] = m["id"].replace(f"{old}[", f"{snk}.{newp}[", 1)
            n += 1
        src = m["source"]
        sp = src.split(".")[-1] if "." in src else ""
        if src.startswith("u_rsv_") and sp in GROUP_OF:
            # face of the source (r8_source_faces): the lane net the sink face reads (w_<lane>_lnd) <- w_<lane>_src
            nsrc = m["_src_face"]
            m["id"] = m["id"].replace(f"<-{src}@", f"<-{nsrc}@")
            m["source"] = nsrc
            n += 1
    return n


def r8_source_faces(r8, rep, die_text):
    """Resolve face-port sources with >1 candidate face by the lane net: sink bit -> w_<lane>_lnd -> w_<lane>_src."""
    nets = {}
    for line in die_text.split("\n"):
        m = INST.match(line)
        if not m:
            continue
        for p, e in conns(m.group(6)):
            if p in GROUP_OF:
                nets[f"{m.group(4)}.{p}"] = expand(e)
    for m in r8["members"]:
        src = m["source"]
        sp = src.split(".")[-1] if "." in src else ""
        if not (src.startswith("u_rsv_") and sp in GROUP_OF and m["sink"].startswith("u_rsv_")):
            continue
        b = nets[f"{m['sink']}.{m['sink_port']}"][m["sink_bits"][0][0]]
        assert b[0] == "net" and b[1].endswith("_lnd"), (m["id"], b)
        m["_src_face"] = rep["src_faces"][f"{b[1][:-4]}[{b[2]}]"]
        assert m["_src_face"].split(".")[0] == src.split(".")[0], (m["id"], m["_src_face"])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("die_in")
    ap.add_argument("die_out")
    ap.add_argument("--report")
    ap.add_argument("--r8", nargs=2, metavar=("IN", "OUT"))
    a = ap.parse_args()
    t = open(a.die_in).read()
    out, rep = rewrite(t)
    open(a.die_out, "w").write(out)
    if a.r8:
        r8 = json.load(open(a.r8[0]))
        r8_source_faces(r8, rep, t)
        n = r8_translate(r8, rep)
        for m in r8["members"]:
            m.pop("_src_face", None)
        r8["note"] = r8.get("note", "") + " | S81-P9-FACE: svc face pins renamed to the role port variants (svc_rs_face_bind.py)"
        json.dump(r8, open(a.r8[1], "w"), indent=1)
        rep["r8_members_renamed"] = n
    s = {k: v for k, v in rep.items() if k not in ("bitmap", "src_faces")}
    if a.report:
        json.dump(s, open(a.report, "w"), indent=1)
    print(json.dumps(dict(instances=len(rep["instances"]), dropped_in_bits=rep["dropped_in_bits"],
                          dropped_out_bits=rep["dropped_out_bits"], nc_decls_removed=rep["nc_decls_removed"],
                          r8_members_renamed=rep.get("r8_members_renamed"))))


if __name__ == "__main__":
    main()
