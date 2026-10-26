#!/usr/bin/env python3
"""TILE-FILL driver: per-die census -> per-master fill rows -> ranked wasted mm2 per die (closed views only for
content; unclosed slots reported with content unknown).  Usage: driver.py archive_index.json out.json"""
import json, sys, collections, re
sys.argv = [sys.argv[0], sys.argv[1]] + sys.argv[2:]
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit.py")).read())
OUT = sys.argv[2]

ALIAS = {"dsfd_bf_col": "ot_v41_bf_col", "dsfd_bf_front": "ot_s81_bf_front", "qkd_cdc_wleaf": "ot_qwen_stream4_cdc_pc"}

# ---------------- census ----------------
dies = {}

# S81: bind5 masters (top level) + hier-contract cluster slots
b5 = json.load(open(f"{WT}/results/arch/s81_canonical_bind_1015/sbind_static_1015/bind5/port_bind.json"))
hc = json.load(open(f"{WT}/results/arch/hier_contract_1011/s81_v21_gen18.json"))
slots = hc["slots"]
top_slot = {x.get("cell"): x for x in slots if x.get("parent") == "s81_layer1" and x.get("cell")}
s81 = []
for k, v in b5["masters"].items():
    n = v.get("instances") or 0
    ov = None; osrc = None
    if k in top_slot and k not in ROWS:
        o = top_slot[k]["outline"]; ov = (o["w"], o["h"]); osrc = "s81_v21_gen18 slot " + top_slot[k]["name"]
        kid_slots = [y for y in slots if y.get("parent") == top_slot[k]["name"] and y.get("cell")]
        kids = collections.Counter(y["cell"] for y in kid_slots)
        for y in kid_slots:
            if y["cell"] not in ROWS and y["cell"] not in M.m and y.get("outline"):
                M.add(y["cell"], w=y["outline"]["w"], h=y["outline"]["h"], std=None, src="s81_v21_gen18 child slot (no closed view)")
        if kids:
            M.add(k, w=o["w"], h=o["h"], children=sorted(kids.items()), src=osrc, std=None)
    if k == "dsfd_stnv_566x1":
        ov = (77.76, 36.72); osrc = "S-NET f8 footprint (el1011-s81die 18:49, slot_change_request)"
        px = ROWS["dsfd_stnh_566x1"]
        M.add(k, w=77.76, h=36.72, std=px["std_area"], pins={"N": {"M5": 567}, "S": {"M5": 567}}, children=[],
              src="in flight (s81fill_stnv_566x1-f8); content proxy = closed dsfd_stnh_566x1 std area")
    s81.append((k, n, ov, osrc))
dies["s81"] = s81

# Qwen compute: c13 bind counts + CONTRACT.md slots (sec 1-3)
QC_SLOT = {"qfd_tile_nk": (449.28, 1442.88), "qfd_tile_nl": (449.28, 1442.88), "qfd_xcst_n": (52.68, 103.66),
           "qfd_xcst_s": (52.68, 103.66), "qfd_xcol_e": (64.8, 1313.28), "qfd_xcol_w": (64.8, 1313.28),
           "qfd_sp_band_lanes": (881.28, 1131.84), "qfd_sp_res_ser": (777.6, 518.4), "qfd_sp_su64_sfu": (3240.0, 3672.0),
           "qfd_sp_vector_memory": (4708.8, 2203.2), "qfd_tt_ctlm": (777.6, 1814.4), "qfd_tt_up4": (345.6, 388.8),
           "qfd_xs_tap": (345.6, 345.6), "qfd_d2d_rom": (777.6, 518.4), "ot_qkvd_ucie_x64_phy": (777.6, 777.6)}
for p in ("0", "1", "2"):
    for s in ("", "_f1"):
        QC_SLOT[f"qfd_port_tiles_{p}{s}"] = (1036.8, 2462.4)
qb = json.load(open(f"{WT}/results/arch/qwen_split_compute_1014/c13_smoke/port_bind.json"))
qc = []
for k, v in qb["masters"].items():
    n = v.get("instances") or 0
    if k == "qfd_tile_nk":
        qc.append(("qfd_tile_nk", 720, QC_SLOT[k], "CONTRACT.md sec 1 tile slot")); qc.append(("qfd_tile_nl", 48, QC_SLOT[k], "CONTRACT.md sec 1 tile slot (block-last tiles)"))
        continue
    qc.append((k, n, QC_SLOT.get(k), "CONTRACT.md spine slot table" if k in QC_SLOT else None))
dies["qwen_compute"] = qc
# tile parents (native kits): children per kit, glue std from the bp58a NK banked gate (3,684 um2)
for t in ("qfd_tile_nk", "qfd_tile_nl"):
    kit = json.load(open(f"{WT}/tools/ref_tile/specs_q_compute_native/{t}_native.json"))
    kids = collections.Counter(c["view"].split("/")[-1] for c in kit["children"])
    M.add(t, w=kit["outline"]["w"], h=kit["outline"]["h"], children=sorted(kids.items()), std=3684.0,
          src=f"native kit tools/ref_tile/specs_q_compute_native/{t}_native.json (glue std 3,684 um2 from NK gate bp58a)")
    M.m[t]["boxes"] = [(c["view"].split("/")[-1], c["at"][0], c["at"][1], "N", c["inst"]) for c in kit["children"]]

# Qwen KV: v1.4.1 bind + contract slots
kb = json.load(open(f"{WT}/results/arch/qwen_split_1014/kvsys_v1_4_1/port_bind.json"))
kc = json.load(open(f"{WT}/results/arch/qwen_split_1014/kvsys_v1_4_1/contract.json"))["slots"]
kv = []
for k, v in kb["masters"].items():
    if v.get("cls") == "HARD_PHY":
        continue
    mod = v.get("module") or k
    n = v.get("n_instances") or 0
    s = kc.get(k) or kc.get(mod)
    ov = tuple(s["outline_um"]) if s and s.get("outline_um") else None
    name = mod if mod in ROWS else (k if k in ROWS else mod)
    kv.append((name, n, ov, "kvsys_v1_4_1/contract.json slot" if ov else None))
dies["qwen_kvsys"] = kv

# ---------------- rows ----------------
def norm(k):
    return ALIAS.get(k, k)

out = {"dies": {}, "masters": {}}
for die, lst in dies.items():
    # expand nested instance counts
    total = collections.Counter(); top = {}
    def walk(name, n, depth=0):
        total[name] += n
        if depth > 6:
            return
        for c, k in M.get(name)["children"]:
            walk(c, n * k, depth + 1)
    for k, n, ov, osrc in lst:
        k2 = norm(k)
        if RAW.match(k2):
            total[k2] += n; continue
        top[k2] = (n, ov, osrc)
        walk(k2, n)
    rows = []
    for name, n in total.items():
        if RAW.match(name) or n == 0:
            continue
        ov, osrc = (top[name][1], top[name][2]) if name in top else (None, None)
        r = analyse(name, outline=ov, src_outline=osrc)
        if not r:
            rows.append({"master": name, "instances": n, "top_level": name in top, "content_um2": None,
                         "note": "no outline: no closed view and no contract slot"}); continue
        r["instances"] = n; r["top_level"] = name in top
        A = r["outline_um2"]
        # view-vs-slot mismatch
        d = M.get(name)
        if ov and d.get("w") and d.get("src", "").startswith("closed view") and abs(d["w"] * d["h"] - ov[0] * ov[1]) > 0.02 * ov[0] * ov[1]:
            r["view_outline_um"] = [d["w"], d["h"]]
            r["note"] = "closed view outline differs from die slot: slot whitespace includes view-to-slot slack"
        A = r["outline_um2"]
        r["own_ws_mm2_die"] = round(r["own_level_whitespace_um2"] * n / 1e6, 3)
        unk = r["unknown_content_um2"] > 0.5 * A
        r["content_known"] = not unk
        r["waste_mm2_die"] = round((A - r["content_um2"]) * n / 1e6, 3) if not unk else None
        if unk:
            r["own_level_whitespace_um2"] = None; r["recoverable_keep_um2"] = r["recoverable_flat_um2"] = None
            r["fill_pct"] = r["fill_pct_known"] = None
            r["own_ws_mm2_die"] = None; r["recoverable_keep_mm2_die"] = r["recoverable_flat_mm2_die"] = None
            r["outline_mm2_die"] = round(A * n / 1e6, 3); rows.append(r); continue
        r["outline_mm2_die"] = round(A * n / 1e6, 3)
        r["own_ws_mm2_die"] = round(r["own_level_whitespace_um2"] * n / 1e6, 3)
        r["recoverable_keep_mm2_die"] = round(r["recoverable_keep_um2"] * n / 1e6, 3)
        r["recoverable_flat_mm2_die"] = round(r["recoverable_flat_um2"] * n / 1e6, 3)
        rows.append(r)
    rows.sort(key=lambda r: -(r.get("own_ws_mm2_die") or 0))
    tops = [r for r in rows if r.get("top_level")]
    out["dies"][die] = {"rows": rows,
                        "top_outline_mm2": round(sum(r.get("outline_mm2_die") or 0 for r in tops), 2),
                        "top_content_known_mm2": round(sum((r["content_um2"] or 0) * r["instances"] / 1e6 for r in tops if r.get("content_um2") is not None and not r.get("unknown_content_um2")), 2),
                        "top_unknown_outline_mm2": round(sum(r.get("outline_mm2_die") or 0 for r in tops if not r.get("content_known", True)), 2),
                        "unknown_tops": [[r["master"], r["instances"], r.get("outline_um"), r.get("outline_src")] for r in tops if not r.get("content_known", True)]}
json.dump(out, open(OUT, "w"), indent=1)
for die, d in out["dies"].items():
    print("==", die, "tops outline", d["top_outline_mm2"], "known content", d["top_content_known_mm2"], "unknown-content outline", d["top_unknown_outline_mm2"])
    for r in d["rows"][:22]:
        if not r.get("content_known", True): continue
        print("  %-38s n=%-6s %-18s fill=%-5s ownWS=%-8s waste=%-8s recK=%-8s recF=%-8s cls=%s ch=%s %s" % (
            r["master"], r["instances"], r.get("outline_um"), r.get("fill_pct_known"), r.get("own_ws_mm2_die"), r.get("waste_mm2_die"),
            r.get("recoverable_keep_mm2_die"), r.get("recoverable_flat_mm2_die"), r.get("class"),
            (r.get("channels") or {}).get("min_channel_um"), "TOP" if r.get("top_level") else ""))
