"""HEAD-REMAP-1 rp21z20 delta = rp21z19 + (a) + (b) + (c): the three plan items rp21z19 left out because each renumbers
generated names (landing_remap.py re-maps them at prepare time).
 (a) hd_mesh: right member of every 256x64 SRAM pair +17.28 um east (pair 2: +7.92; seam pins never abut) -> reset tree
     renumbers (coll_ib START rst_rl_60).
 (b) hd_lep0N: taps in the stack band to y 604.8, tx rows back to back mid corridor (y 529.2 / 558.36, pitch 187.2 from
     x 22.5), rx column +7.2 east -> density taps renumber (forwarded source clk_t218), relays renumber.
 (c) hd_host_e: no tap change (STA what-if: no u_epc shift closes -395 ps); the PG cut is a GEN ENVIRONMENT switch, not a plan key (schema rejects
     it): OT_PG_FACE_CUT=1 for hd_host_e (PG-AWARE-1 @240cf2612f: parent PG stripes stop 1.5 um before the macro pin
     faces of u_epc, no core re-sign).
Translations / one tap row only, no reshape.  usage: head_z20_delta.py RP21Z19.json RP21Z20.json [TOOLS_ROOT]"""
import json
import os
import sys

a, b = sys.argv[1:3]
ROOT = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("ROOT", ".")
d = json.load(open(a))
T = d["partition_types"]


def rect(h):
    w, hh = h["outline_um"]
    if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, hh = hh, w
    x, y = h["origin_um"]
    return (x, y, x + w, y + hh)


def overlap(r, s):
    return r[0] < s[2] - 0.05 and s[0] < r[2] - 0.05 and r[1] < s[3] - 0.05 and s[1] < r[3] - 0.05


def check(t):
    hc = T[t]["hard_cores"]
    o = T[t]["outline_um"]
    for i, h in enumerate(hc):
        r = rect(h)
        assert r[0] >= -1e-6 and r[1] >= -1e-6 and r[2] <= o[0] + 1e-6 and r[3] <= o[1] + 1e-6, (t, h["inst"], r)
        for g in hc[i + 1:]:
            assert not overlap(r, rect(g)), (t, h["inst"], g["inst"])


# (a)
m = T["hd_mesh"]
n = 0
for h in m["hard_cores"]:
    if h["module"] == "ot_sram_1r1w2c_256x64_m1" and any(abs(h["origin_um"][0] - x) < 1e-3 for x in (103.68, 224.64, 345.6)):
        h["origin_um"][0] = round(h["origin_um"][0] + (7.92 if abs(h["origin_um"][0] - 224.64) < 1e-3 else 17.28), 4)
        n += 1
assert n == 36, n
m["note"] += " | HEAD-REMAP-1 rp21z20 (a): right member of each 256x64 SRAM pair +17.28 um east (pair 2: +7.92, reset/clk tap x 276.48 keeps its 8.64 halo), no pin face abuts; reset relay names re-mapped by landing_remap.py."
check("hd_mesh")
print("hd_mesh moved", n)

# (b)
NUDGE = {(1149.12, 8.64): (1166.4, 8.64)}
MV = [[428.192, 547.584], [1365.6, 552.736], [1340.28, 552.96], [1885.272, 570.24]]
nmv = [0]


def _mv(o):
    it = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
    for k, v in list(it):
        if isinstance(v, list) and len(v) == 2 and all(isinstance(q, (int, float)) for q in v) and any(
                abs(v[0] - q[0]) < 1e-3 and abs(v[1] - q[1]) < 1e-3 for q in MV):
            o[k] = [v[0], 604.8]
            nmv[0] += 1
        else:
            _mv(v)


l = T["hd_lep0N"]
_mv(l)
lt = l["reset"]["local_taps_um"]
for i, v in enumerate(lt):
    if (v[0], v[1]) in NUDGE:
        lt[i] = list(NUDGE[(v[0], v[1])])
XS = [round(22.5 + 186.368 * i, 3) for i in range(10)]
k = {}
for h in l["hard_cores"]:
    if "g_tx[" in h["inst"] and "ot_sram_1r1w_512x128" in h["module"]:
        tx = int(h["inst"].split("g_tx[")[1][0])
        bk = int(h["inst"].split("g_bank[")[1][0])
        idx = bk if tx in (1, 2) else 5 + bk
        h["origin_um"] = [XS[idx], 529.2 if tx in (2, 3) else 558.36]
        k[tx] = k.get(tx, 0) + 1
    elif ".g_rx[" in h["inst"] and "32x128" in h["module"]:
        h["origin_um"][0] = round(h["origin_um"][0] + 7.2, 4)
l["note"] += " | HEAD-REMAP-1 rp21z20 (b) = rp21z19 delta item 3: tx SRAM rows back to back mid corridor (y 529.2/558.36), pitch 187.2, rx column +7.2; taps/names re-mapped by landing_remap.py."
check("hd_lep0N")
print("hd_lep0N taps moved", nmv[0], "tx rows", k)

# (c) hd_host_e: NO u_epc core tap.  The STA what-if on the routed ws database (HEAD-REMAP-1 11-14) showed that no u_epc
# clock-pin shift closes -395 ps: input setup needs +395, input hold allows <= +282, output setup (-8.4 ps) allows ~0.
# The fix is inside the core (new lane).  The PG cut is a GEN ENVIRONMENT switch (OT_PG_FACE_CUT=1 for hd_host_e,
# PG-AWARE-1 @240cf2612f, on main); no plan key (schema rejects it).

# (d) hd_serdes raw_0 (pin x 1439.3 y 17.2): NO tap added.  Checked on the re-solved tree (prepared z20, gen --trial): the
# taps at x 1439 ('clk' and an explicit clk_t22 at (1439.3, 31.2)) are leaf taps ('gated tap ... depth 7') hanging off the
# depth-6 relay at tap 4 (x 1691.6, 252 um away, within the 405 um reset reach); the tree builder gives no relay of its
# own to a leaf tap, so an extra tap does not create one.  landing_remap keeps the pin site and renames the row to u_rrl_103.

d["note"] = d["note"].replace("rp21z19 HEAD FINAL", "rp21z20 HEAD FINAL")
json.dump(d, open(b, "w"), indent=1, ensure_ascii=False)
