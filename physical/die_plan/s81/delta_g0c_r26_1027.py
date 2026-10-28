#!/usr/bin/env python3
"""S81 plan event 2026-10-27 (S81-CORES-R26, COORD ruling S81-CORES-R25 (1)): clear the 8 known G0C pin-to-pin errors
exposed by the R25 check (117e37566c) + the vi[5] face snap (S81-CORES-R2 packet d).  ONE batched PLAN-DELTA, 0 cycles.

1. leaf t34 / t39 / t58 (7 errors, 406-407 um): u_lf.u_vn.u_b.{n_pre,n_go,wl_d} -> u_lf.u_vp.u_b0/u_b1.  All three ports
   are the vni class of kit_istations.CORE_CLASSES: in ot_s81sl_leaf they reach vn through ONE station chain
   (u_cst_vni, CS_VNI_D; n_pre/wl_d in .d, n_go in .dv), which the plan already carries as a FIRM 1-stage station
   (the type's existing n_pre|u_bX entry).  The missing bundle pairs are recorded as entries of that SAME chain (same
   regs_um, so kit_istations' bits-weighted centroid and the class stage count are unchanged): 0 new cycles, no RTL,
   no kit change.  The vn_b <-> SRAM pairing is a co-sink relation (core_conns: the leaf's n_pre/n_go/wl_d input feeds
   u_vp directly and vn through u_cst_vni), so the real hop is station -> vn_b pin (checked per bit <= 405 um); the
   station -> SRAM leg uses the check's own lower-bound form (nearest SRAM input pin, clk / rd_out excluded), as the
   existing entries do.  from_um = the worst vn_b port pin, to_um = that nearest SRAM input pin.
2. eng__t1 (1 error, 416 um): u_eng.u_e.vi_s <- bus xtier_i0.  The partition window (svc_14 ft0_o, order lsb_high,
   exact ft bit sites) runs bit 0 at the E end; the core's vi_s pins run bit 0 at the W end, so the bundle crosses
   (bit 275: 415.8 um).  The core's 276 vi_s bits are re-assigned in reverse order onto the SAME 276 M5 sites
   (pin table + mechanical LEF PIN names).  0 cycles; eng_rr_e has no signed view and needs a new kit anyway
   (the R5 pin candidate 7f56929224 touches pci/f_ks/rco/st/cfg only, not vi_s).
3. dsdv_idx_tx_n32 vi[5]: plan centre (27.18, 545.0345) is the centre of the inset access RECT 27.168 528.517
   27.192 561.552, 16.5 um inside the N face (core_pin_sites_gate off_face).  New centre (27.18, 561.558) = centre of
   the EXISTING N-edge PORT RECT 27.168 561.516 27.192 561.6 (canonical M5 0.024 x 0.084).  LEF unchanged.
  python3 physical/die_plan/s81/delta_g0c_r26_1027.py [--check] [--json OUT]
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PLAN = HERE / "die_plan.json"
PINDIR = HERE / "inputs" / "core_pins"
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import check as C  # noqa: E402
import schema as S  # noqa: E402

REACH = 405.0
TAG = "S81-CORES-R26"
LEAF = {"ot_s81sl_leaf__t34": [("n_pre", "u_b1")],
        "ot_s81sl_leaf__t39": [("n_go", "u_b0"), ("n_pre", "u_b1"), ("wl_d", "u_b0")],
        "ot_s81sl_leaf__t58": [("n_go", "u_b1"), ("n_pre", "u_b0"), ("wl_d", "u_b1")]}
ENG = dict(type="eng__t1", inst="u_eng.u_e", pins="dsdv_eng_rr_e_e2.json", port="vi_s", width=276,
           base_pinhash="4c9446265e3c")
VI5 = dict(pins="dsdv_idx_tx_n32.json", pin="vi[5]", layer="M5", old=[27.18, 545.0345], new=[27.18, 561.558],
           edge_rect=[27.168, 561.516, 27.192, 561.6], outline=[626.4, 561.6],
           lef_zst_sha256="1a88631d85c1f8a4ade59f84aa8a23bc2247e58bcf33c0ffeef2b236b2b81b18")
FMTS = {"indent0": lambda x: json.dumps(x, indent=0), "indent0_nl": lambda x: json.dumps(x, indent=0) + "\n",
        "compact": lambda x: json.dumps(x), "compact_nl": lambda x: json.dumps(x) + "\n",
        "indent2_nl": lambda x: json.dumps(x, indent=2) + "\n"}


def pins_of(hc):
    cw, ch = hc["outline_um"]
    o = hc.get("orient", "R0")
    dx, dy = hc.get("track_offset_um", [0.0, 0.0])
    out = {}
    for nm, _ln, x, y in C.core_pins(hc, HERE):
        pn, _, b = nm.partition("[")
        tx, ty = C._orient_pt(o, cw, ch, x, y)
        out.setdefault(pn, {})[b.rstrip("]")] = (hc["origin_um"][0] + dx + tx, hc["origin_um"][1] + dy + ty)
    return out


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def leaf_entries(d):
    out, rep = {}, {}
    for tn, pairs in LEAF.items():
        t = d["partition_types"][tn]
        hcs = {h["inst"]: h for h in t["hard_cores"]}
        ex = [e for e in t["internal_stations"]
              if re.match(r"^core:u_lf\.u_vn\.u_b\.n_pre\|core:u_lf\.u_vp\.u_b[01]$", e["conn"])
              and TAG not in e.get("note", "")]
        assert len(ex) == 1 and len(ex[0]["regs_um"]) == 1, f"{tn}: expected one 1-stage vni entry, got {ex}"
        reg = ex[0]["regs_um"][0]
        vb = pins_of(hcs["u_lf.u_vn.u_b"])
        new = []
        for port, b in pairs:
            conn = f"core:u_lf.u_vn.u_b.{port}|core:u_lf.u_vp.{b}"
            if any(e["conn"] == conn for e in t["internal_stations"]):
                continue
            pp = vb[port]
            fr = max(pp.values(), key=lambda v: md(v, reg))
            sp = pins_of(hcs[f"u_lf.u_vp.{b}"])
            sin = [v for pn, dd in sp.items() if pn not in ("clk", "rd_out") for v in dd.values()]
            to = min(sin, key=lambda v: md(v, reg))
            direct = max(min(md(v, w) for w in sin) for v in pp.values())
            h1, h2 = md(fr, reg), md(reg, to)
            rep[f"{tn}:{port}->{b}"] = dict(bits=len(pp), direct_pin_to_pin_worst_um=round(direct, 3),
                                            hop1_um=round(h1, 3), hop2_um=round(h2, 3), station_um=reg)
            if max(h1, h2) > REACH:
                raise SystemExit(f"{tn} {conn}: hop {h1:.1f}/{h2:.1f} > {REACH}")
            new.append(dict(conn=conn, from_um=[round(fr[0], 3), round(fr[1], 3)],
                            to_um=[round(to[0], 3), round(to[1], 3)], regs_um=[list(reg)], bits=len(pp),
                            launch=f"core:u_lf.u_vn.u_b.{port}", capture=f"u_lf.u_vp.{b}",
                            note=(f"{TAG} 10-27 (delta_g0c_r26_1027.py): pin-to-pin > 405 um; same vni chain "
                                  f"(u_cst_vni, CS_VNI_D) and same station as the type's existing n_pre entry: "
                                  f"0 new cycles")))
        out[tn] = (ex[0]["conn"], new)
    return out, rep


def eng_reverse(pd):
    pins = pd["pins"]
    idx = {p["name"]: i for i, p in enumerate(pins)}
    w = ENG["width"]
    sites = [(pins[idx[f"vi_s[{k}]"]]["layer"], pins[idx[f"vi_s[{k}]"]]["x"], pins[idx[f"vi_s[{k}]"]]["y"])
             for k in range(w)]
    assert sites == sorted(sites, key=lambda s: s[1]), "vi_s not monotone in x (base changed)"
    for k in range(w):
        p = pins[idx[f"vi_s[{k}]"]]
        p["layer"], p["x"], p["y"] = sites[w - 1 - k]
    return pd


def lef_reverse(text, w):
    pat = re.compile(r"^(\s*(?:PIN|END)\s+)vi_s\[(\d+)\]\s*$", re.M)
    n = len(pat.findall(text))
    assert n == 2 * w, f"LEF vi_s PIN/END count {n} != {2 * w}"
    return pat.sub(lambda m: f"{m.group(1)}vi_s[{w - 1 - int(m.group(2))}]", text)


def eng_census(d, epd):
    hc = next(h for h in d["partition_types"][ENG["type"]]["hard_cores"] if h["inst"] == ENG["inst"])
    cw, ch = hc["outline_um"]
    vi = {}
    for p in epd["pins"]:
        if p["name"].startswith("vi_s["):
            tx, ty = C._orient_pt(hc.get("orient", "R0"), cw, ch, p["x"], p["y"])
            vi[p["name"][5:-1]] = (hc["origin_um"][0] + hc["track_offset_um"][0] + tx,
                                   hc["origin_um"][1] + hc["track_offset_um"][1] + ty)
    bq = C._bus_bit_targets(S.Plan(d, PLAN), ENG["type"])["xtier_i0"]
    return max(md(v, bq[k]) for k, v in vi.items())


def write_fmt(f, obj):
    raw = f.read_text()
    fmt = next((k for k, fn in FMTS.items() if fn(json.loads(raw)) == raw), None)
    if fmt is None:
        raise SystemExit(f"{f}: unknown serialisation")
    f.write_text(FMTS[fmt](obj))


def apply(check_only):
    d = json.loads(PLAN.read_text())
    rep = {}
    leaf, rep["leaf"] = leaf_entries(d)
    ef = PINDIR / ENG["pins"]
    epd = json.loads(ef.read_bytes())
    done_eng = epd["pinhash"] != ENG["base_pinhash"]
    rep["eng_vi_s_xtier_i0_max_um_before"] = round(eng_census(d, epd), 3) if not done_eng else None
    if not done_eng:
        epd = eng_reverse(epd)
    eng_max = eng_census(d, epd)
    rep["eng_vi_s_xtier_i0_max_um_after"] = round(eng_max, 3)
    if eng_max > REACH:
        raise SystemExit(f"eng vi_s still {eng_max:.1f}")
    vf = PINDIR / VI5["pins"]
    vpd = json.loads(vf.read_bytes())
    p5 = next(p for p in vpd["pins"] if p["name"] == VI5["pin"])
    done_vi5 = [p5["x"], p5["y"]] == VI5["new"]
    if not done_vi5:
        assert [p5["x"], p5["y"]] == VI5["old"] and p5["layer"] == VI5["layer"], p5
        r = VI5["edge_rect"]
        assert abs(r[3] - VI5["outline"][1]) < 1e-9 and r[0] <= VI5["new"][0] <= r[2] and r[1] <= VI5["new"][1] <= r[3]
        assert abs((r[2] - r[0]) - 0.024) < 1e-9 and abs((r[3] - r[1]) - 0.084) < 1e-9   # canonical M5 shape
    rep["vi5"] = dict(old=VI5["old"], new=VI5["new"], edge_rect=VI5["edge_rect"], lef_zst_sha256=VI5["lef_zst_sha256"])
    print(json.dumps(rep, indent=1))
    if check_only:
        return rep
    t = PLAN.read_text()
    for tn, (anchor, new) in leaf.items():
        if not new:
            continue
        ti = t.index(f'"{tn}": {{')
        a = t.index(f'"conn": "{anchor}"', ti)
        end = t.index("\n    }", a) + len("\n    }")
        blob = "".join(",\n" + "\n".join("    " + ln for ln in json.dumps(e, indent=1).splitlines()) for e in new)
        t = t[:end] + blob + t[end:]
    nd = json.loads(t)
    for tn, (_a, new) in leaf.items():
        a_ = sorted(json.dumps(e, sort_keys=True) for e in nd["partition_types"][tn]["internal_stations"])
        b_ = sorted(json.dumps(e, sort_keys=True) for e in d["partition_types"][tn]["internal_stations"] + new)
        assert a_ == b_, tn
        nd["partition_types"][tn]["internal_stations"] = d["partition_types"][tn]["internal_stations"]
    assert nd == d, "text edit touched more than the new station entries"
    PLAN.write_text(t)
    if not done_eng:
        epd["pinhash"] = hashlib.sha256(json.dumps(epd["pins"], sort_keys=True).encode()).hexdigest()[:12]
        epd["source"] += (f" | {TAG} 10-27 (delta_g0c_r26_1027.py): vi_s bits reversed on the same 276 M5 sites "
                          "(bit 0 at the core-frame E end) to match the xtier_i0 window order; LEF PIN names permuted")
        write_fmt(ef, epd)
        lf = REPO / epd["lef"]
        lf.write_text(lef_reverse(lf.read_text(), ENG["width"]))
    if not done_vi5:
        p5["y"] = VI5["new"][1]
        vpd["pinhash"] = hashlib.sha256(json.dumps(vpd["pins"], sort_keys=True).encode()).hexdigest()[:12]
        vpd["source"] += f" | {TAG} 10-27: vi[5] onto its N-edge PORT RECT (delta_g0c_r26_1027.py)"
        write_fmt(vf, vpd)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    r = apply(a.check)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1))
