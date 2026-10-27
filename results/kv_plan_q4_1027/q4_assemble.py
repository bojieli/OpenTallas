"""CLOCK-KV hm_r26q4 = hm_r26q3 256600e2 + (a) FT re-site (ft_corridor per-slot lanes, census-chosen variant per type)
+ (d) D-KV-STRAP-FORM-2 (q4_straps.py) + (e) D-KV-AHUB-ENTRY (q4_ahub.py) + R8 landing table regen (r8cal).
Asserts: per type only ft_slots regs_um/bit_sites_um/bit_site_cell_um change (name/faces/width/stations equal); hard_cores
differ only in pins_file (the listed repoints); outlines, latency, lanes, ports byte-identical to q3."""
import json, sys, hashlib
Q = "/srv/opentallas-scratch2/claude/kv-plan-q4-1027"
PD = f"{Q}/pd"
CHOICE = {  # type: (variant file, lane-pack, lane um/bit)
    "kv3_hub_Ei": ("f_kv3_hub_Ei_0.08.json", "walk", 0.08),
    "kv3_hgi_v5": ("d_kv3_hgi_v5_0.08.json", "bin", 0.08),
    "kv3_hgi_v7": ("d_kv3_hgi_v7_0.06.json", "bin", 0.06),
    "kv3_hgi_v8": ("d_kv3_hgi_v8_0.07.json", "bin", 0.07),
    "kv3_hub_Eo": ("d_kv3_hub_Eo_0.08.json", "bin", 0.08),
}
q3 = json.load(open(f"{PD}/hm_r26q3.json"))
P = json.load(open(f"{PD}/hm_r26q4_s.json"))          # q3 + straps
SITE = ("regs_um", "bit_sites_um", "bit_site_cell_um")
for tn, (f, _, _) in CHOICE.items():
    src = json.load(open(f"{Q}/{f}"))["partition_types"][tn]["ft_slots"]
    dst = P["partition_types"][tn]["ft_slots"]
    assert len(src) == len(dst)
    for a, b in zip(dst, src):
        assert {k: v for k, v in a.items() if k not in SITE} == {k: v for k, v in b.items() if k not in SITE}, (tn, a["name"])
        assert all(k in b for k in SITE) or int(b["stations"]) <= 1, (tn, b["name"])
    P["partition_types"][tn]["ft_slots"] = src
n = 0
for t in P["partition_types"].values():
    for hc in t.get("hard_cores", []):
        if hc.get("pins_file") == "cores/qkd_ahub_pins.json":
            hc["pins_file"] = "cores/qkd_ahub_pins_r26q4.json"; n += 1
assert n == 1
# assertions vs q3
for tn, t in P["partition_types"].items():
    t3 = q3["partition_types"][tn]
    assert t["outline_um"] == t3["outline_um"]
    hc, hc3 = t.get("hard_cores", []), t3.get("hard_cores", [])
    assert [{k: v for k, v in c.items() if k != "pins_file"} for c in hc] == [{k: v for k, v in c.items() if k != "pins_file"} for c in hc3], tn
    for k in set(t) | set(t3):
        if k not in ("ft_slots", "hard_cores"):
            assert t.get(k) == t3.get(k), (tn, k)
    if tn not in CHOICE:
        assert t["ft_slots"] == t3["ft_slots"], tn
for k in ("latency", "lanes", "ports", "clock", "reset"):
    if k in q3:
        assert P[k] == q3[k], k
P["note"] = P.get("note", "") + (" | hm_r26q4 (CLOCK-KV 10-27): FT re-site per-slot lanes "
             + ", ".join(f"{tn} {p}/{l}" for tn, (_, p, l) in CHOICE.items())
             + "; D-KV-AHUB-ENTRY ck/rst_n entry y 241.92; R8 landing regen for +210")
open(f"{PD}/hm_r26q4.json", "w").write(json.dumps(P, indent=1) + "\n")
print("hm_r26q4", hashlib.sha256(open(f"{PD}/hm_r26q4.json", "rb").read()).hexdigest())
