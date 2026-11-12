"""CPL-QC-NK-R0: RTL-traced NK link table per type, before/after: pin-centroid Manhattan length (um), bit-mm and
macro crossings (channel distance), for every NK->NK link of the bound s21 RTL (514 bits each)."""
import json, sys, subprocess
a, b, rtldir, rl = sys.argv[1:5]
A = json.load(open(a)); B = json.load(open(b))
ALIAS = {"cbf_q11": "qfd_qc_cb_f_q11", "cbf_q01": "qfd_qc_cb_f_q01__cbf_q01", "cbf_q01_s2": "qfd_qc_cb_f_q01__cbf_q01_s2"}
Y = {"n_a": 750.06, "n_b": 850.764, "n_y": 1051.98, "t_out": 951.084}   # mean pin y, core frame (a0_nk_pins.json)
def pin(h, port):
    ox, oy = h["origin_um"]; dx, dy = h["track_offset_um"]
    x = 0.096 if h["orient"] in ("R0", "MX") else 457.824
    return ox + dx + x, oy + dy + Y[port]
def chan(h):
    left = h["origin_um"][0] < 400; w = h["orient"] in ("R0", "MX")
    return (0 if w else 1) if left else (1 if w else 2)
print("type\tlink\tdepth\tlen_before_um\tlen_after_um\tcross_before\tcross_after")
tot = {}
for t in sorted(A["partition_types"]):
    TA, TB = A["partition_types"][t], B["partition_types"][t]
    ha = {h["inst"]: h for h in TA.get("hard_cores", []) if h["module"].startswith("qfd_tile_n")}
    if not any(h["module"] == "qfd_tile_nk_a0c" for h in ha.values()):
        continue
    hb = {h["inst"]: h for h in TB["hard_cores"] if h["module"].startswith("qfd_tile_n")}
    try:
        J = json.loads(subprocess.check_output(["python3", "-I", rl, f"{rtldir}/{ALIAS.get(t, t)}.sv"], stderr=subprocess.DEVNULL))
    except Exception:
        continue
    s = [0, 0, 0, 0]
    for l in J["links"]:
        if l["dst"].endswith(".tap") or "." not in l["src"] or l["src"].split(".")[0] not in ha or l["src"] == l["dst"]:
            continue
        (si, sp), (di, dp) = l["src"].split("."), l["dst"].split(".")
        L = []
        for H in (ha, hb):
            p, q = pin(H[si], sp), pin(H[di], dp)
            L.append((abs(p[0] - q[0]) + abs(p[1] - q[1]), abs(chan(H[si]) - chan(H[di]))))
        s[0] += L[0][0] * 514 / 1000; s[1] += L[1][0] * 514 / 1000; s[2] += L[0][1]; s[3] += L[1][1]
        print(f"{t}\t{l['src']}->{l['dst']}\tD{l['depth']}{l['cnt']}\t{L[0][0]:.0f}\t{L[1][0]:.0f}\t{L[0][1]}\t{L[1][1]}")
    tot[t] = s
print("\ntype\tnk_bitmm_before\tnk_bitmm_after\tcrossings_before\tcrossings_after")
for t, s in tot.items():
    print(f"{t}\t{s[0]:.0f}\t{s[1]:.0f}\t{s[2]}\t{s[3]}")
