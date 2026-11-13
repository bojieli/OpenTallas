"""FW-EFACE model: face_flops.tcl E/W band placement of the E-face pin registers (buses), default vs the form.
Mirrors the tcl search (column c inward, rows {0,+1,-1,+2,-2} about the pin row, optional stride comb)."""
import json, re, sys, collections
RH, W = 0.27, 1.08
def place(pins, pitch_sites, stride):
    pitch = 0.054 * pitch_sites
    occ, out = set(), []
    for py in pins:
        row = int(py // RH)
        c = 0
        while True:
            done = False
            for dr in (0, 1, -1, 2, -2):
                r = row + dr
                if r < 0 or (r, c) in occ: continue
                if stride > 1 and (r + c) % stride: continue
                occ.add((r, c)); out.append((c, c * pitch, r * RH)); done = True; break
            if done: break
            c += 1
    return out
def metrics(fl, pitch_sites):
    g = collections.Counter((int(x // 2.16), int(y // 2.16)) for c, x, y in fl)   # x = distance in from the face
    col0 = sum(1 for c, x, y in fl if x < 2.16)
    depth = max(x for c, x, y in fl) + W if fl else 0
    # flop cell area share of the face gcell column (2.16 um deep) over the busiest 10 um of face
    win = collections.Counter(int(y // 10) for c, x, y in fl if x < 2.16)
    peak10 = max(win.values()) if win else 0
    return dict(flops=len(fl), col0=col0, depth_um=round(depth, 2), max_per_gcell=max(g.values()) if g else 0,
                face_col_peak_per_10um=peak10, face_col_fill_peak=round(peak10 * W * RH / (2.16 * 10), 3))
def main():
    p = json.load(open(sys.argv[1]))
    rows = []
    for tn, t in sorted(p["partition_types"].items()):
        if not re.match(r"^(sle|slw)_(fw|st_a)_", tn): continue
        for face in ("E", "W"):
            pins = []
            for io in ("in", "out"):
                for b in t["buses"]:
                    if b["face"] == face and b["dir"] == io:
                        a, z = b["window_um"]; n = b["width"]
                        pins += [a + (i + 0.5) * (z - a) / n for i in range(n)]
            if not pins: continue
            d = metrics(place(pins, 40, 1), 40); f = metrics(place(pins, 80, 3), 80)
            rows.append((tn, face, len(pins), d, f))
            print(tn, face, "pins", len(pins), "| default", d, "| form", f)


if __name__ == "__main__":
    main()
