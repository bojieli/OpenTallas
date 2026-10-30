#!/usr/bin/env python3
"""DIE-HEAD-34 src25p (2026-10-29): one combined fix-only HEAD event on HEAD-KITS-T src25m_kt (COORD [HEAD-KITS-T-PARK]
19:37 (1) + COORD 18:4x-b (A) hd_tile density).  Plan fields only, 0 cycles, 0 outline / die-pin changes:
  * HEAD-013 lep0N +319.68 W: the src25n-vs-src25m plan delta (lep0N type + origin, hd_st_n4 crop, reset.in_sites, note);
  * hd_mesh_e: rst_start_raw_0/1/3 x 820.8/558.72/330.404 -> 820.832/558.752/330.4 (M7 tracks) + insertion_ff_ps 342.67 (+ basis), COORD-approved;
  * hd_tile: results/die_head_34_1029/tile/tile_density_delta.py (density r200 + u_eA1 -4.32 um), run verbatim;
  * hd_turn_b + the 4 spine shims: clock tap_mode density r200 / max 1500 / target 1200 over the placed local register
    inventory (strip_sink_bins.py, HEAD-KITS-T placed dumps), so every clk sink gets a legal tap within 200 um.
The density taps change each type's clk_t<i> port count, so the source RTL is patched exactly there: the wrapper header
clk_t lines (as gen_rtl.wrapper emits them for the new plan; checked against gen_rtl on the old plan first) and the
.clk_t<i> connections of every instance (same region clock net as its .clk, as in src25m_kt).  Everything else is copied.
usage: src25p.py SRC_DIR OUT_DIR"""
import hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools/die_plan")]
import schema as S, taps, gen_rtl as G
src, out = map(Path, sys.argv[1:3])
if out.exists():
    sys.exit(f"{out} exists")
shutil.copytree(src, out)
plan = out / "source_plan.json"
old_raw = json.loads((src / "source_plan.json").read_text())
subprocess.run([sys.executable, str(ROOT / "results/die_head_34_1029/tile/tile_density_delta.py"),
                str(src / "source_plan.json"), str(plan)], check=True)
raw = json.loads(plan.read_text())
# EA1=keep (tile delta as written, -4.32: off the 8.64 lattice, 1 G0C ERROR) | drop (back to 371.52) | m864 (362.88)
import os
EA1 = os.environ.get("EA1", "m864")
for hc in raw["partition_types"]["hd_tile"]["hard_cores"]:
    if hc["inst"].endswith("u_eA1") and EA1 != "keep":
        hc["origin_um"] = {"drop": [371.52, 8.64], "m864": [362.88, 8.64]}[EA1]
# HEAD-013 lep0N +319.68 W growth (OWNER: lep_pair stays 777.6x492.48): the src25n-vs-src25m delta (DIE-HEAD-33
# src25n; RTL identical) folded here.  Every touched field must be unchanged between src25m and src25m_kt (else stop).
M = json.load(open("/srv/opentallas-scratch2/claude/die-head-32/src25m/source_plan.json"))
N = json.load(open("/srv/opentallas-scratch2/claude/die-head-33/src25n/source_plan.json"))
assert set(M) == set(N) and [p["name"] for p in M["partitions"]] == [p["name"] for p in N["partitions"]]
lep = []
for tn in sorted(set(M["partition_types"]) | set(N["partition_types"])):
    if M["partition_types"].get(tn) != N["partition_types"].get(tn):
        assert raw["partition_types"][tn] == M["partition_types"][tn], f"{tn} also changed in src25m_kt"
        raw["partition_types"][tn] = N["partition_types"][tn]; lep.append(f"type {tn}")
for i, (pm, pn) in enumerate(zip(M["partitions"], N["partitions"])):
    if pm != pn:
        assert raw["partitions"][i] == pm, pm["name"]
        raw["partitions"][i] = pn; lep.append(f"partition {pn['name']}")
for k in M:
    if k not in ("partition_types", "partitions") and M[k] != N[k]:
        if k == "reset":
            for kk in set(M[k]) | set(N[k]):
                if M[k].get(kk) != N[k].get(kk):
                    assert raw[k].get(kk) == M[k].get(kk), kk
                    raw[k][kk] = N[k][kk]; lep.append(f"reset.{kk}")
        else:
            assert raw[k] == M[k], k
            raw[k] = N[k]; lep.append(k)
shutil.copy("/srv/opentallas-scratch2/claude/die-head-33/src25n/core_pins/lep_pair_pins_777.json", out / "core_pins/")
shutil.copy("/srv/opentallas-scratch2/claude/die-head-33/src25n/src25n_moved_points.json", out)
print("src25n delta:", lep)
STRIPS = ["hd_turn_b", "hd_spn_eshim_rx", "hd_spn_eshim_tx", "hd_spn_wshim_rx", "hd_spn_wshim_tx"]
for tn in STRIPS:
    raw["partition_types"][tn]["clock"].update(tap_mode="density", tap_radius_um=200, tap_max_sinks=1500,
        tap_target_sinks=1200, control_sinks=False,
        sink_bins_file=f"results/die_head_34_1029/src25p/{tn}_sink_bins.json")
# COORD-approved hd_mesh_e local items (DIE-HEAD-34 main lane relay): rst_start_raw_1 onto its M7 track (+0.032 um, pin
# and raw-export record together) + the measured FF insertion (codex-head-measured-1859 source, 342.67 ps + basis)
me = raw["partition_types"]["hd_mesh_e"]
# 3 raw-export pins onto M7 tracks (ref intel2 die-head-34/mesh_e/source_plan_rekit_ff342_p2.json)
for pn, (ox, nx, y) in {"rst_start_raw_0": (820.8, 820.832, 21.48), "rst_start_raw_1": (558.72, 558.752, 34.104),
                        "rst_start_raw_3": (330.404, 330.4, 8.608)}.items():
    mp = [q for q in me["clock"]["landing_contract"]["pins"] if q["name"] == pn]
    mx = [q for q in me["reset_start_raw_exports"] if q["port"] == pn]
    assert len(mp) == 1 and len(mx) == 1, pn
    for q in mp + mx:
        assert abs(q["xy_um"][0] - ox) < 1e-6 and abs(q["xy_um"][1] - y) < 1e-6, (pn, q["xy_um"])
        q["xy_um"] = [nx, y]
cdx = json.load(open("/srv/opentallas-scratch2/claude/codex-head-measured-1859/source/source_plan.json"))
cm = cdx["partition_types"]["hd_mesh_e"]["clock"]
assert cm["insertion_ff_ps"] == 342.67
me["clock"]["insertion_ff_ps"] = cm["insertion_ff_ps"]
me["clock"]["insertion_basis"] = cm["insertion_basis"]
errs = S.validate(raw)
assert not errs, errs[:5]
plan.write_text(json.dumps(raw, separators=(",", ":")) + "\n")
P0, P1 = S.Plan(old_raw, src / "source_plan.json"), S.Plan(raw, plan)
rep = dict(source=str(src), out=str(out), added_cycles=0, types={}, src25n_delta=lep)
ep0, ep1 = G.bus_epochs(P0), G.bus_epochs(P1)
top = out / "s81_head_top.sv"
ttext = top.read_text()
CLKT = re.compile(r"(?m)^    input  wire clk_t\d+,[^\n]*\n")
for tn in ["hd_tile"] + STRIPS:
    t0 = taps.sink_taps(P0, tn)
    t1 = taps.sink_taps(P1, tn)
    sinks = taps.sink_sites(P1, tn, True)
    worst = max(min(abs(x - q[1]) + abs(y - q[2]) for q in t1) for x, y, _ in sinks)
    rep["types"][tn] = dict(taps_before=len(t0), taps_after=len(t1), max_load=max(q[3] for q in t1),
                            empty=sum(1 for q in t1 if q[3] == 0), sinks=round(sum(w for *_, w in sinks)),
                            worst_sink_nearest_tap_l1_um=round(worst, 2), taps=[list(q[:4]) for q in t1])
    mod = P1.types[tn]["module"]
    f = out / f"{mod}.sv"
    text = f.read_text()
    g0 = "".join(CLKT.findall(G.wrapper(P0, tn, ep0, ROOT)))
    g1 = "".join(CLKT.findall(G.wrapper(P1, tn, ep1, ROOT)))
    assert "".join(CLKT.findall(text)) == g0, f"{tn}: source clk_t header differs from gen_rtl on the base"
    text = CLKT.sub("", text)
    anchor = re.search(r"(?m)^    input  wire clk,[^\n]*\n", text)
    text = text[:anchor.end()] + g1 + text[anchor.end():]
    f.write_text(text)
    n_inst = 0
    for p in raw["partitions"]:
        if p["type"] != tn:
            continue
        pat = re.compile(r"(?m)^(    " + re.escape(mod) + r"(?: #\([^\n]*\))? " + re.escape(G.sv_id(p["name"]))
                         + r" \(\n)(.*?)(\n    \);)", re.S)
        m = pat.search(ttext)
        assert m, p["name"]
        lines = m[2].split("\n")
        ck = [re.match(r"\s*\.clk\(([^)]*)\)", l) for l in lines]
        ki = [k for k, c in enumerate(ck) if c]
        assert len(ki) == 1, p["name"]
        net = ck[ki[0]][1]
        for l in lines:
            c = re.match(r"\s*\.clk_t\d+\(([^)]*)\)", l)
            assert not c or c[1] == net, (p["name"], l, net)
        lines = [l for l in lines if not re.match(r"\s*\.clk_t\d+\(", l)]
        i = [k for k, l in enumerate(lines) if re.match(r"\s*\.clk\(", l)][0]
        assert lines[i].rstrip().endswith(","), lines[i]
        lines[i + 1:i + 1] = [f"        .clk_t{k}({net})," for k in range(1, len(t1))]
        ttext = ttext[:m.start(2)] + "\n".join(lines) + ttext[m.end(2):]
        n_inst += 1
    rep["types"][tn]["instances"] = n_inst
top.write_text(ttext)
# DIE-HEAD-31 start_d fix (as in die-head-33/bind/src): the root landing stage start_d output gets its own named wire
st = out / "start_stages.sv"
stx = st.read_text()
a = ".start(st_b0_start));"
assert stx.count(a) == 1 and "st_b0_start_d" not in stx
stx = stx.replace(a, ".start(st_b0_start), .start_d(st_b0_start_d));")
w = re.search(r"(?m)^    wire st_b0_start;\n", stx)
assert w
stx = stx[:w.start()] + "    wire st_b0_start_d;\n" + stx[w.start():]
st.write_text(stx)
rep["ea1"] = EA1
rep["sha256"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob("*.sv")) + [plan]}
(out / "src25p_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({tn: {k: v for k, v in r.items() if k != "taps"} for tn, r in rep["types"].items()}, indent=0))
print("source_plan.json sha256", rep["sha256"]["source_plan.json"])
