"""S81-KITS-RTLC 10-24 (COORD ruling c): re-pin ot_s81dv_xfin from the current RTL.  The core_pins table came from the
closed ref_tile LEF, which predates the ENG mode (ports mode, e_v, e_c[1:0], e_hh / e_kk / e_dd[31:0]: 100 bits).
New pins: mode on the S face beside go (the xrt x_* control group); the ENG outputs on the N face right after rb_d
(rstd / ENG results both return to xrt's collection); rst_n moved from the S-face corner (x 7.164) to mid-face
(S, x ~ 90.6).  M5, on track, the table's 0.096 spacing.  Writes core_pins/ot_s81dv_xfin.json and a kit pins.json."""
import json, sys, re
CP = "physical/die_plan/s81/inputs/core_pins/ot_s81dv_xfin.json"
d = json.load(open(CP)); P = d["pins"]
W = H = 181.44
face = lambda p: "S" if p["y"] < 1 else "N" if p["y"] > 180 else "W" if p["x"] < 1 else "E"
tr = lambda k: round(0.048 * k - 0.084, 3)                     # M5 track k (after the [0.108, 0.012] core offset)
kof = lambda x: round((x + 0.084) / 0.048)
used = {f: {kof(p["x"]) for p in P if face(p) == f} for f in "NS"}
names = {p["name"] for p in P}
assert "mode" not in names and "e_v" not in names
def take(f, k0, step=2, direction=1):
    k = k0
    while k in used[f] or k - 1 in used[f] or k + 1 in used[f]:
        k += direction
    used[f].add(k); return k
y = {"S": 0.042, "N": 181.398}
# rst_n: S corner -> mid-face
rp = [p for p in P if p["name"] == "rst_n"][0]; used["S"].discard(kof(rp["x"]))
k = take("S", kof(W / 2)); rp["x"] = tr(k)
# mode: beside go on S
kg = kof([p for p in P if p["name"] == "go"][0]["x"])
k = kg + 2
while k in used["S"] or k - 1 in used["S"] or k + 1 in used["S"]: k += 2
used["S"].add(k); P.append({"name": "mode", "layer": "M5", "x": tr(k), "y": y["S"]})
# ENG outputs: N face after rb_d
k = max(kof(p["x"]) for p in P if p["name"].startswith("rb_d")) + 2
new = ["e_v"] + [f"e_c[{i}]" for i in range(2)] + [f"{b}[{i}]" for b in ("e_hh", "e_kk", "e_dd") for i in range(32)]
for n in new:
    while k in used["N"] or k - 1 in used["N"] or k + 1 in used["N"]: k += 2
    used["N"].add(k); P.append({"name": n, "layer": "M5", "x": tr(k), "y": y["N"]}); k += 2
assert max(p["x"] for p in P if p["name"].startswith("e_")) < W - 0.5
d["source"] += "; S81-KITS-RTLC 10-24: re-pinned from current RTL (+mode, e_v, e_c, e_hh, e_kk, e_dd: ENG mode, absent from the closed LEF) and rst_n moved to S mid-face; the LEF field is the pre-ENG closed view (re-kit pending)"
json.dump(d, open(CP, "w"), indent=0)
kp = []
for p in P:
    m = re.match(r"(\w+)\[(\d+)\]$", p["name"])
    kp.append({"bus": m.group(1) if m else p["name"], "bit": int(m.group(2)) if m else None, "layer": p["layer"],
               "x": p["x"], "y": p["y"], "face": face(p)})
json.dump(kp, open(sys.argv[1], "w"))
print("pins", len(P), "rst_n", rp["x"], "mode", [p for p in P if p["name"] == "mode"][0]["x"],
      "e span", min(p["x"] for p in P if p["name"].startswith("e_")), max(p["x"] for p in P if p["name"].startswith("e_")))
