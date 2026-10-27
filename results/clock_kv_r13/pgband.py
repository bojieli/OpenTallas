"""CLOCK-KV-R13 item 3: WN hgi M7 ft band (die_share 0.5) vs the hgi partition M7 PG grid (kit abstracts)."""
import re, json, sys, math
new, old = sys.argv[1], sys.argv[2]
PITCH, W, SP = 0.064, 0.032, 0.032        # asap7_tech_1x_201209.lef M7 PITCH / WIDTH / SPACING; kit tracks.tcl M7 pitch 0.064
def pg(f):
    s = open(f).read()
    size = tuple(map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", s).groups()))
    out = {}
    for net in ("VDD", "VSS"):
        m = re.search(r"PIN %s\b(.*?)END %s" % (net, net), s, re.S)
        rr = []
        for lay, rs in re.findall(r"LAYER (\w+) ;\s*((?:RECT [^;]+;\s*)+)", m.group(1)):
            if lay == "M7":
                rr += [tuple(map(float, r.split()[1:5])) for r in re.findall(r"RECT[^;]+", rs)]
        out[net] = sorted(rr)
    return size, out
res = {}
for t in ("kv3_hgi_v6_part", "kv3_hgi_v7_part", "kv3_hgi_v8_part"):
    (w, h), n = pg(f"{new}/{t}.lef")
    _, o = pg(f"{old}/{t}.lef")
    rects = n["VDD"] + n["VSS"]
    ntr = int(round(w / PITCH))
    blocked = set()
    for x0, y0, x1, y1 in rects:
        # a track (centre c, wire c+-W/2) is unusable when its wire comes within SP of the strap
        k0 = math.floor((x0 - SP - W / 2 - PITCH / 2) / PITCH); k1 = math.ceil((x1 + SP + W / 2 - PITCH / 2) / PITCH)
        for k in range(k0, k1 + 1):
            c = PITCH / 2 + k * PITCH
            if c + W / 2 > x0 - SP + 1e-9 and c - W / 2 < x1 + SP - 1e-9:
                blocked.add(k)
    pg_share = len(blocked) / ntr
    res[t] = dict(width_um=w, m7_tracks=ntr, pg_straps_M7=dict(VDD=len(n["VDD"]), VSS=len(n["VSS"])),
                  pg_straps_identical_to_d5_kit=(n == o), strap_width_um=sorted({round(r[2] - r[0], 3) for r in rects}),
                  strap_pitch_um=round(n["VDD"][1][0] - n["VDD"][0][0], 3), pg_blocked_tracks=len(blocked),
                  pg_track_share=round(pg_share, 4), band_die_share=0.5,
                  partition_left_share=round(1 - 0.5 - pg_share, 4))
json.dump(res, open(sys.argv[3], "w"), indent=1)
for k, v in res.items(): print(k, v)
