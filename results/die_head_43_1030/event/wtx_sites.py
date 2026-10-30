"""DIE-HEAD-43: hd_spn_wshim_tx link (3 stations, unlanded) explicit per-bit sites: stage1 at x~350 (mid), stage2 at the
E (out) face column, each bit on the row of its own pin (pins W/E at equal y, lsb_high). Output: plan JSON fragment +
ft_bit_sites.tcl text.  usage: wtx_sites.py geom.tsv out_prefix"""
import sys, json, re, math
tsv, out = sys.argv[1], sys.argv[2]
X0, Y0, SW, RH = 4.32, 4.32, 0.054, 0.27
CELL = (1.404, 0.27)
def gx(x): return round(X0 + math.floor((x - X0) / SW + 1e-9) * SW, 3)
pins = {}
for ln in open(tsv):
    f = ln.rstrip("\n").split("\t")
    if f[0] == "P":
        m = re.fullmatch(r"link_o\[(\d+)\]", f[2])
        if m: pins[int(m.group(1))] = float(f[7])
W = len(pins) - 1   # payload width; bit W = epoch
assert sorted(pins) == list(range(W + 1)), "pin bits not contiguous"
cols = {1: [gx(349.92), gx(349.92) + 1.404], 2: [gx(678.3), gx(678.3) + 1.404]}
sites = []
for j in (1, 2):
    used = set(); st = []
    for b in range(W + 1):
        y = pins[b]; n0 = round((y - RH / 2 - Y0) / RH)
        for dn in (0, 1, -1, 2, -2, 3, -3):
            for ci, x in enumerate(cols[j]):
                if (n0 + dn, ci) not in used:
                    used.add((n0 + dn, ci)); st.append([round(x, 3), round(Y0 + (n0 + dn) * RH, 3)]); break
            else: continue
            break
        else: raise SystemExit(f"no site bit {b}")
    sites.append(st)
dmax = max(abs(s[1] + RH / 2 - pins[b]) for st in sites for b, s in enumerate(st))
print("width", W, "stage x", cols, "max |dy| site-centre vs pin", round(dmax, 3))
json.dump({"bit_sites_um": sites, "bit_site_cell_um": list(CELL)}, open(out + ".json", "w"))
sys.path.insert(0, "/home/ubuntu/.claude/jobs/b7f906df/tmp/tools_main")
import ft_bit_sites
open(out + ".tcl", "w").write(ft_bit_sites.table([{"name": "link", "width": W, "stations": 3, "bit_sites_um": sites, "bit_site_cell_um": list(CELL)}]))
