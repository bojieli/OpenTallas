"""VISLAYOUT2-QC 11-11: coll_n hand arrangement (positions only, EQ by construction).
Dataflow: N serdes rx/tx (597 b each, PHY above) <-> u_rx/u_tx mems <-> codec banks 0..3 <-> S rec_rx/rec_tx (548 b, coll_ftn
below).  Old: 6 macros in the NW at y 432-700, columns 20 um apart (1000+ W/E edge pins in one 20-um channel), S half
empty, clock taps 170 um E of the block (inside b1 after any move), clk_serdes launch insertion 594 ps vs clk 256 ps.
New: macros in dataflow rows top->bottom (rx/tx | codec b2/b3 | codec b0/b1), two columns x 34.56 / 285.12 with a 72-um
middle channel, block centred between N and S faces; all type taps (tap_um, glue, clk_coll, clk_serdes, reset) in the
middle channel at the block centre.  usage: make_colln.py BASE.json OUT.json DELTA.json"""
import hashlib, json, sys
src, dst, dpath = sys.argv[1:4]
G = 8.64
raw = open(src, "rb").read()
p = json.loads(raw)
assert json.dumps(p, indent=1).encode() == raw
t = p["partition_types"]["coll_n"]
XL, XR = 34.56, 285.12
POS = {"u_bound.u_core.u_rx.u_mem": (XL, 535.68), "u_bound.u_core.u_tx.u_mem": (XR, 535.68),
       "u_bound.u_core.g_codec.u_codec.g_bank[2].u_store.u_sram": (XL, 440.64),
       "u_bound.u_core.g_codec.u_codec.g_bank[3].u_store.u_sram": (XR, 440.64),
       "u_bound.u_core.g_codec.u_codec.g_bank[0].u_store.u_sram": (XL, 345.6),
       "u_bound.u_core.g_codec.u_codec.g_bank[1].u_store.u_sram": (XR, 345.6)}
BASE = (241.92, 466.56)
VAR = sys.argv[4] if len(sys.argv) > 4 else "b"
if VAR == "c":
    # one W column, pin edges W -> W channel (112 um) and E -> the open E area; rows in dataflow order, pitch 95.04
    XC = float(sys.argv[7]) if len(sys.argv) > 7 else 112.32
    PITCH = float(sys.argv[5]) if len(sys.argv) > 5 else 95.04
    Y0 = float(sys.argv[6]) if len(sys.argv) > 6 else 112.32
    order = ["u_bound.u_core.g_codec.u_codec.g_bank[1].u_store.u_sram", "u_bound.u_core.g_codec.u_codec.g_bank[0].u_store.u_sram",
             "u_bound.u_core.g_codec.u_codec.g_bank[3].u_store.u_sram", "u_bound.u_core.g_codec.u_codec.g_bank[2].u_store.u_sram",
             "u_bound.u_core.u_tx.u_mem", "u_bound.u_core.u_rx.u_mem"]
    POS = {n: (XC, round(Y0 + i * PITCH, 4)) for i, n in enumerate(order)}
    BASE = (float(sys.argv[8]), 397.44) if len(sys.argv) > 8 else (328.32, 397.44)
TAPS = {"tap_um": BASE, "glue": (BASE[0] + 8.64, BASE[1]), "clk_coll": (BASE[0] + 17.28, BASE[1] + 8.64),
        "clk_serdes": (BASE[0] + 34.56, BASE[1] + 8.64)}
if VAR == "c":
    TAPS["clk_serdes"] = (BASE[0], 561.6)      # rx/tx + N-face serdes flops
for v in [c for xy in list(POS.values()) + list(TAPS.values()) for c in xy]:
    assert abs(v / G - round(v / G)) < 1e-6, v
edits = []
CORE_TX = (float(sys.argv[8]) if len(sys.argv) > 8 else 328.32) if VAR == "c" else 241.92
boxes = []
for h in t["hard_cores"]:
    x, y = POS[h["inst"]]
    edits.append(dict(kind="core", inst=h["inst"], was=h["origin_um"], now=[x, y]))
    h["origin_um"] = [x, y]
    w, hh = h["outline_um"]
    boxes.append((h["inst"], x - 4.32, y - 4.32, x + w + 4.32, y + hh + 4.32))
ck = t["clock"]
edits.append(dict(kind="clock.tap_um", was=ck["tap_um"], now=list(TAPS["tap_um"]))); ck["tap_um"] = list(TAPS["tap_um"])
edits.append(dict(kind="reset.tap_um", was=t["reset"]["tap_um"], now=list(TAPS["tap_um"]))); t["reset"]["tap_um"] = list(TAPS["tap_um"])
for tp in ck["taps"]:
    if tp["name"] == "glue":
        edits.append(dict(kind="tap glue", was=tp["xy"], now=list(TAPS["glue"]))); tp["xy"] = list(TAPS["glue"])
    if tp["name"] == "u_coll_face_s0.ck":
        edits.append(dict(kind="tap u_coll_face_s0.ck", was=tp["xy"], now=[CORE_TX, tp["xy"][1]])); tp["xy"] = [CORE_TX, tp["xy"][1]]
OLD = (388.8, 397.44); D = (TAPS["tap_um"][0] - OLD[0], TAPS["tap_um"][1] - OLD[1])
for cs in t.get("count_straps") or []:
    was = [list(s_) for s_ in cs["sites_um"]]
    cs["sites_um"] = [[round(a + D[0], 4), round(b + D[1], 4)] for a, b in cs["sites_um"]]
    edits.append(dict(kind="count_strap " + cs["name"], was=was, now=cs["sites_um"]))
for r in ck["landing_contract"]["collector_tree"]["relays"]:
    if r["xy"] == [196.56, 380.16] and VAR == "c" and abs(Y0 - 112.32) < 1e-6:
        edits.append(dict(path="clock.landing_contract.collector_tree.relays", was=list(r["xy"]), now=[196.56, 388.8], why="b3/b2 row gap"))
        r["xy"] = [196.56, 388.8]
    elif r["xy"] == [196.56, 380.16] and VAR != "c":
        edits.append(dict(kind="collector relay", was=r["xy"], now=[196.56, 336.96])); r["xy"] = [196.56, 336.96]
for e in ck["edge_clocks"]:
    if e["port"] in TAPS:
        edits.append(dict(kind="edge " + e["port"], was=e["tap_um"], now=list(TAPS[e["port"]]))); e["tap_um"] = list(TAPS[e["port"]])
def xys(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from xys(v, path + "." + k)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(a, (int, float)) for a in o):
            yield path, o
        else:
            for i, v in enumerate(o):
                yield from xys(v, path + "[%d]" % i)
warn = []
for path, (a, b) in list(xys(t["clock"], "clock")) + list(xys(t["reset"], "reset")) + list(xys(t.get("count_straps") or [], "count_straps")):
    for nm, x0, y0, x1, y1 in boxes:
        if x0 < a < x1 and y0 < b < y1:
            warn.append((path, (a, b), nm.rsplit(".", 2)[-2]))
p["note"] = p["note"] + " | vl2qc_colln (VISLAYOUT2-QC 11-11): coll_n macros in dataflow rows, 72-um middle channel, taps at the block centre"
out = json.dumps(p, indent=1)
open(dst, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, edits=edits, inside_box_xy=warn), open(dpath, "w"), indent=1)
print("coll_n edits", len(edits), "sha256", sha[:12])
for w in warn:
    print("XY-IN-MACRO", *w)
