"""TLOAD-ROMSTAGE A plan event (DIE-QC-97 11-11): opt every stm type with the u_tload table ROMs into OT_QC_TLCAP and
give the new ROM-capture registers FIRM relay sites at their ROM pins (0 added plan cycles; the +1 loader edge is an
RTL/compiler obligation, not a lane).

  tlcap_plan.py IN_PLAN OUT_PLAN REPORT ROM_PINS_JSON

Per type (hard_cores u_bound.u_core.u_tload.u_ld.m0..m3, orient R0):
  * verilog_defines += OT_QC_TLCAP (qfd_dv_s6_stm / qfd_dv_s6_stm_se0 select CAPTURE_STAGE 1 + LOCAL_JOIN 1);
  * relay_sites u_core.u_tload.u_ld.g_capture.payload[k] (k = 266 m + b, b < 266, k < 1024) EDGE um outside the halo
    of macro m, level with rd_out[b];
  * the 4 metadata copies g_capture.meta[rg].ff/{bits_q[j] (= m3 rd_out[226 + j]), owner_q, other_q, valid_q, last_q}
    beside m3's rd_out[226..265] pins, copy rg one COPY_UM column farther out;
  * the 67 kept write enables g_wek.cp[wc].ff/q and the 6 local reset copies g_capture.rst[rg].ff/q in one column
    beside m3 (they read the metadata copies: reduction + select launch stay next to the ROM).
Keys are the kit's Yosys flop names below u_bound with the cell suffix dropped (kit_istations RELAY_TCL); existing
relay_sites keys are never overwritten.  Plan JSON style is preserved."""
import json, re, sys
from pathlib import Path
INP, OUT, REP, PINS = sys.argv[1:5]
EDGE, COPY_UM = 3.0, 1.6
raw_bytes = Path(INP).read_bytes(); raw = json.loads(raw_bytes)
pins = json.load(open(PINS))["pins"]
RD = {int(re.search(r"\[(\d+)\]", p["name"]).group(1)): (p["x"], p["y"]) for p in pins if p["name"].startswith("rd_out[")}
assert len(RD) == 266
rep = {}
P = "u_core.u_tload.u_ld."
for tn, t in sorted(raw["partition_types"].items()):
    roms = {h["inst"].rsplit(".", 1)[1]: h for h in t.get("hard_cores", [])
            if h.get("inst", "").startswith("u_bound.u_core.u_tload.u_ld.m")}
    if not roms:
        continue
    assert sorted(roms) == ["m0", "m1", "m2", "m3"], (tn, sorted(roms))
    def site(m, b, extra=0.0):
        h = roms[m]; assert h.get("orient", "R0") == "R0", (tn, m, h.get("orient"))
        (ox, oy), (w, _), halo = h["origin_um"], h["outline_um"], float(h.get("halo_um", 0.0))
        px, py = RD[b]
        x = ox - halo - EDGE - extra if px < w / 2 else ox + w + halo + EDGE + extra
        return [round(x, 3), round(oy + py, 3)]
    rs = dict(t.get("relay_sites") or {})
    new = {}
    for k in range(1024):
        new[P + f"g_capture.payload[{k}]"] = site(f"m{k // 266}", k % 266)
    for rg in range(4):
        f = P + f"g_capture.meta[{rg}].ff/"
        for j in range(40):
            new[f + f"bits_q[{j}]"] = site("m3", 226 + j, COPY_UM * (rg + 1))
        anchor = site("m3", 226, COPY_UM * (rg + 1))
        for i, nm in enumerate(["owner_q[0]", "owner_q[1]", "other_q", "valid_q", "last_q"]):
            new[f + nm] = [anchor[0], round(anchor[1] - 0.6 * (i + 1), 3)]
    h3 = roms["m3"]; (ox, oy), (w, hgt), halo = h3["origin_um"], h3["outline_um"], float(h3.get("halo_um", 0.0))
    col = round(ox + w + halo + EDGE + COPY_UM * 6, 3)
    for wc in range(67):
        new[P + f"g_wek.cp[{wc}].ff/q"] = [col, round(oy + 2.0 + (hgt - 4.0) * wc / 66, 3)]
    for rg in range(6):
        new[P + f"g_capture.rst[{rg}].ff/q"] = [round(col + COPY_UM, 3), round(oy + 4.0 + 8.0 * rg, 3)]
    clash = sorted(k for k in new if k in rs)
    assert not clash, (tn, clash[:3])
    rs.update(new)
    t2 = dict(t)
    d = list(t.get("verilog_defines") or [])
    if "OT_QC_TLCAP" not in d:
        d.append("OT_QC_TLCAP")
    t2["verilog_defines"] = d
    t2["relay_sites"] = dict(sorted(rs.items()))
    raw["partition_types"][tn] = t2
    far = max(abs(v[0] - (roms["m3"]["origin_um"][0] + w)) for k, v in new.items() if "g_wek" in k)
    rep[tn] = dict(defines=d, relay_sites_added=len(new), relay_sites_total=len(rs), wek_column_x=col, wek_dx_from_m3_um=round(far, 1))
for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
          lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
          lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
    if f(json.loads(raw_bytes)).encode() == raw_bytes:
        Path(OUT).write_text(f(raw)); break
else:
    raise SystemExit("plan JSON style not recognised")
Path(REP).write_text(json.dumps(rep, indent=1) + "\n")
print(len(rep), "types:", ", ".join(rep))
