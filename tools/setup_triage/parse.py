#!/usr/bin/env python3
"""Parse a setup-triage paths.log (tools/setup_triage/paths_tcl.tcl) into per-path evidence + a first-cut class."""
import re, sys, json, collections

LINE = re.compile(r"^\s*(?:(\d+)\s+([\d.]+)\s+)?(-?[\d.]+)\s+(-?[\d.]+)\s+([\^v])\s+(\S+)\s+\((\S+)\)")
WIREBUF = re.compile(r"^(wire|max_length)\d")
FOBUF = re.compile(r"^(place|split|rebuffer|max_cap|max_slew|load_slew|fanout)\d")

def inst_of(p):
    return p.rsplit("/", 1)[0] if "/" in p else p

def parse(text):
    locs = {}
    for m in re.finditer(r"^TRI_LOC (\S+) (\S+) (\S+)", text, re.M):
        locs[m[1]] = (float(m[2]), float(m[3]))
    for m in re.finditer(r"^TRI_PORT (\S+) (\S+) (\S+)", text, re.M):
        locs.setdefault(m[1], (float(m[2]), float(m[3])))
    die = re.search(r"^TRI_DIE (\S+) (\S+)", text, re.M)
    die = (float(die[1]), float(die[2])) if die else None
    summ = []
    s = text.split("TRI_SUMMARY_BEGIN", 1)[-1].split("TRI_FULL_BEGIN", 1)[0]
    for l in s.splitlines():
        m = re.match(r"^(\S+) \((\S+)\) (\S+) \((\S+)\)\s+(-?[\d.]+)$", l.strip()) or re.match(r"^(\S+)\s+(?:\((\S+)\)\s+)?(\S+)\s+(?:\((\S+)\)\s+)?(-?[\d.]+)$", l.strip())
        if m and m[1] not in ("Startpoint", "---"):
            summ.append(dict(start=m[1], end=m[3], slack=float(m[5])))
    full = text.split("TRI_FULL_BEGIN", 1)[-1].split("TRI_LOC_BEGIN", 1)[0]
    paths = []
    for blk in re.split(r"\n(?=Startpoint: )", full):
        if not blk.startswith("Startpoint:"): continue
        p = dict(start=re.search(r"Startpoint: (\S+)", blk)[1], end=re.search(r"Endpoint: (\S+)", blk)[1])
        sc = re.search(r"Startpoint: \S+\s*\n?\s*\(([^)]*)\)", blk); ec = re.search(r"Endpoint: \S+\s*\n?\s*\(([^)]*)\)", blk)
        p["start_kind"] = sc[1] if sc else ""; p["end_kind"] = ec[1] if ec else ""
        sl = re.search(r"(-?[\d.]+)\s+slack", blk); p["slack"] = float(sl[1]) if sl else None
        p["max_delay"] = bool(re.search(r"max_delay", blk))
        parts = blk.split("data arrival time", 1)
        launch, capture = parts[0], parts[1] if len(parts) > 1 else ""
        edges = [(a, b, re.match(r"(\S+)", c)[1], d) for a, b, c, d in re.findall(r"^\s*(-?[\d.]+)\s+(-?[\d.]+)\s+clock (.*?)\((rise|fall) edge\)", blk, re.M)]
        p["launch_edge"] = float(edges[0][1]) if edges else 0.0
        p["capture_edge"] = float(edges[1][1]) if len(edges) > 1 else None
        p["launch_clock"] = edges[0][2] if edges else None
        p["capture_clock"] = edges[1][2] if len(edges) > 1 else None
        rows = []
        for l in launch.splitlines():
            m = LINE.match(l)
            if m: rows.append(dict(fo=int(m[1]) if m[1] else None, d=float(m[3]), t=float(m[4]), pin=m[6], cell=m[7]))
        sinst = p["start"]
        lc = None; di = 0
        for i, r in enumerate(rows):
            if inst_of(r["pin"]) == sinst or r["pin"] == sinst:
                lc = r["t"] - p["launch_edge"]; di = i; break
        ext = re.search(r"^\s*(-?[\d.]+)\s+(-?[\d.]+)\s+input external delay", launch, re.M)
        p["input_ext"] = float(ext[1]) if ext else None
        if ext:
            lc = float(ext[2]) - p["launch_edge"]
            di = next((i for i, r in enumerate(rows) if r["pin"] == sinst), 0)
        p["launch_clk"] = lc
        data = rows[di:]
        p["data_delay"] = round(data[-1]["t"] - data[0]["t"], 1) if data else None
        crow = []
        for l in capture.splitlines():
            m = LINE.match(l)
            if m: crow.append(dict(d=float(m[3]), t=float(m[4]), pin=m[6], cell=m[7]))
        einst = inst_of(p["end"]) if "/" in p["end"] else p["end"]
        cc = None
        for r in crow:
            if inst_of(r["pin"]) == p["end"] or r["pin"] == p["end"]:
                cc = r["t"] - (p["capture_edge"] or 0); break
        p["capture_clk"] = cc
        oext = re.search(r"^\s*(-?[\d.]+)\s+(-?[\d.]+)\s+output external delay", capture, re.M)
        p["output_ext"] = float(oext[1]) if oext else None
        stg = []
        for i in range(1, len(data)):
            r = data[i]
            stg.append(dict(d=r["d"], pin=r["pin"], cell=r["cell"], fo=data[i - 1]["fo"] if i else None))
        mac = [s for s in stg if s["cell"].startswith("ot_") or "sram" in s["cell"] or "rom" in s["cell"]]
        p["macro_delay"] = max((s["d"] for s in mac), default=0.0)
        p["macro_cell"] = mac[0]["cell"] if mac else ""
        wb = [s for s in stg if WIREBUF.match(s["pin"].split("/")[0])]
        p["wirebuf_n"] = len(wb); p["wirebuf_ps"] = round(sum(s["d"] for s in wb), 1)
        fb = [s for s in stg if FOBUF.match(s["pin"].split("/")[0])]
        p["fobuf_n"] = len(fb); p["fobuf_ps"] = round(sum(s["d"] for s in fb), 1)
        logic = [s for s in stg if not s["cell"].startswith(("BUF", "HB", "INV")) and s not in mac and not s["pin"].endswith(("/D", "/ENA"))]
        p["logic_stages"] = len(logic)
        p["logic_cells"] = collections.Counter(re.sub(r"x\d.*", "", s["cell"]) for s in logic).most_common(6)
        big = max(stg, key=lambda s: s["d"]) if stg else None
        p["max_stage"] = (big["d"], big["pin"], big["cell"]) if big else None
        fos = [(r["fo"], r["pin"]) for r in data if r["fo"]]
        p["max_fanout"] = max(fos) if fos else (0, "")
        pts = [locs.get(inst_of(r["pin"])) or locs.get(r["pin"]) for r in data]
        pts = [q for q in pts if q]
        hop = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
        p["path_len_um"] = round(sum(hop)); p["max_hop_um"] = round(max(hop, default=0))
        p["se_um"] = round(abs(pts[0][0] - pts[-1][0]) + abs(pts[0][1] - pts[-1][1])) if len(pts) > 1 else None
        p["skew"] = round(p["launch_clk"] - p["capture_clk"], 1) if (p["launch_clk"] is not None and p["capture_clk"] is not None) else None
        p["period"] = round((p["capture_edge"] or 0) - p["launch_edge"], 1) if p["capture_edge"] is not None else None
        paths.append(p)
    paths.sort(key=lambda q: q["slack"] if q["slack"] is not None else 1e9)
    summ.sort(key=lambda q: q["slack"])
    return dict(summary=summ, paths=paths, die=die, n_summary=len(summ))

def famname(n):
    return re.sub(r"\[\d+\]", "[*]", re.sub(r"_\d+_$", "_N_", n.split("/")[0]))

def families(summ, k=6):
    c = collections.OrderedDict()
    for s in summ:
        key = (famname(s["start"]), famname(s["end"]))
        if key not in c: c[key] = [s["slack"], 0]
        c[key][1] += 1
    return [(a, b, v[0], v[1]) for (a, b), v in list(c.items())[:k]]

if __name__ == "__main__":
    r = parse(open(sys.argv[1]).read())
    for p in r["paths"][:5]:
        print(json.dumps({k: p[k] for k in p if k not in ()}, default=str))
    print(families(r["summary"]))
