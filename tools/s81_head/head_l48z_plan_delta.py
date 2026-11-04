#!/usr/bin/env python3
"""DIE-HEAD-53 helper l48z (COORD 11-01 09:2x): HEAD plan event l48z = l48x + one-block geometry fixes for the l48x
kit-wave AUTO-GEOM classes, inside four types only (HEAD plan frozen, OWNER 12.20: no slot/outline/die change).

hd_st_n3_turn (r2r 1183 x143, pin_reg_max 223 tstart, relay_collapse 1): the DIE-HEAD-38 R1/R2/W1 landing keys the
  other HEAD station types already carry (reader START depth 2 per input ring from the origin at the tstart pin,
  writer START depth 2 per output ring, status input relays on the long legs, agg anchors, 4 same-cycle local reset
  copies).  Count straps: K_d1_i/K_u1_i -2 on nst3_turn, +2 at the receivers of d1_o/u1_o (boot cycles only).
hd_st_n3_transit (r2r 501 x4 = ring d2_i -> u_cland_sin_*_d2_i_0): one more status input relay on both d2_i legs.
hd_mesh_e (pin_reg 281 m_rx_ft_o, r2r 814 face status -> agg_1): m_rx_ft per-bit station sites (s1 ~407, s2 ~810 um,
  each bit on its pin row; was L*j/3 = 279/559), reader/writer START depth 1, status relay on the m_tx_ft_i leg,
  agg anchors W->E, 2 local reset copies.  Count straps: K_m_tx_ft_i -1 on mesh_e, +1 at receivers of m_rx_ft_o.
hd_spn_eshim_tx (pin_reg_max 163.5 cland_tstart_in): local reset copy 'o' moved next to the tstart pin.
All other types byte-identical.  The die top count-strap literals follow Landings.strap_expected() (old vs new).

usage: head_l48z_plan_delta.py REPO SRC_DIR(head_source_l48x) MESH_E_GEOM_TSV OUT_DIR
"""
import json, math, re, shutil, sys
from pathlib import Path

repo, src, geom, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, str(repo / "tools/die_plan"))
import clock_landings as CL  # noqa: E402

raw = json.loads((src / "source_plan.json").read_text())
side = json.loads((src / "source_sidecar.json").read_text())
old_k = CL.Landings(json.loads(json.dumps(raw)), side).strap_expected()
T = raw["partition_types"]
rep = {}


def st(x, y, r=None):
    return dict(xy_um=[x, y], **({"raw_reset": r} if r else {}))


# ---- hd_st_n3_turn (1304.64 x 604.8; tstart (722.976, 67.488)) ----
c = T["hd_st_n3_turn"]["clock"]
for k in ("landing_reader_start", "landing_writer_start", "landing_status_input_stages", "landing_status_anchors",
          "landing_local_resets"):
    assert k not in c, k
c["landing_reader_start"] = dict(depth=2, origin_rect_um=[651.36, 111.36, 668.64, 128.64], branches={
    "d1_i": {"stages": [st(920, 220, "rst_rl_7"), st(1180, 320, "rst_rl_3")]},
    "u1_i": {"stages": [st(455, 285, "rst_rl_16"), st(250, 450, "rst_rl_31")]}})
c["landing_writer_start"] = dict(depth=2, branches={
    "d1_o": {"stages": [st(559, 280, "rst_rl_43"), st(457, 440, "rst_rl_16")]},
    "u1_o": {"stages": [st(873, 123, "rst_rl_69"), st(1086, 127, "rst_rl_24")]}})
c["landing_status_input_stages"] = {
    "agg": {"u1_i": [st(322, 473), st(511, 362)], "d1_i": [st(990, 300)]},
    "d1_o": {"d1_i": [st(1050, 412), st(815, 473), st(580, 535)]}}
c["landing_status_anchors"] = {"u_cland_agg_%d" % (i + 1): [700 + 120 * i, 250 - 25 * i] for i in range(5)}
c["landing_local_resets"] = [
    dict(name="c", raw="rst_rl_69", xy_um=[670, 135], consumers=["u_cland_origin"]),
    dict(name="w", raw="rst_rl_31", xy_um=[420, 480], consumers=[
        "u_cland_sin_agg_u1_i_0", "u_cland_sin_agg_u1_i_1", "u_cland_sin_d1_o_d1_i_2", "u_cland_up_d1_o",
        "u_cland_fstart_d1_o"]),
    dict(name="m", raw="rst_rl_14", xy_um=[820, 380], consumers=[
        "u_cland_agg_1", "u_cland_agg_2", "u_cland_sin_agg_d1_i_0", "u_cland_sin_d1_o_d1_i_0",
        "u_cland_sin_d1_o_d1_i_1"]),
    dict(name="e", raw="rst_rl_24", xy_um=[1150, 170], consumers=[
        "u_cland_agg_3", "u_cland_agg_4", "u_cland_agg_5", "u_cland_up_u1_o", "u_cland_fstart_u1_o"])]
rep["hd_st_n3_turn"] = "reader START d2 + writer START d2 + status relays agg.u1_i x2, agg.d1_i x1, d1_o.d1_i x3 + 5 agg anchors + 4 local reset copies"

# ---- hd_st_n3_transit ----
c = T["hd_st_n3_transit"]["clock"]
c["landing_status_input_stages"]["agg"]["d2_i"] = [st(1200, 320), st(960, 270)]
c["landing_status_input_stages"]["d2_o"]["d2_i"] = [st(1210, 340), st(970, 300)]
lr = {r["name"]: r for r in c["landing_local_resets"]}
lr["c"]["consumers"] += ["u_cland_sin_agg_d2_i_1", "u_cland_sin_d2_o_d2_i_1"]
rep["hd_st_n3_transit"] = "status relays agg.d2_i and d2_o.d2_i 1 -> 2 (new _1 on local reset c)"

# ---- hd_mesh_e (838.08 x 86.4; tstart (287.968, 34.08)) ----
t = T["hd_mesh_e"]; c = t["clock"]
c["landing_reader_start"] = dict(depth=1, origin_rect_um=[279.36, 25.44, 296.64, 42.72],
                                 branches={"m_tx_ft_i": {"stages": [st(560, 30, "rst_rl_5")]}})
c["landing_writer_start"] = dict(depth=1, branches={"m_rx_ft_o": {"stages": [st(560, 60, "rst_rl_5")]}})
c["landing_status_input_stages"] = {"agg": {"m_tx_ft_i": [st(600, 40)]}}
c["landing_status_anchors"] = {"u_cland_agg_1": [300, 60], "u_cland_agg_2": [480, 62], "u_cland_agg_3": [660, 64]}
c["landing_local_resets"] = [
    dict(name="w", raw="rst_rl_5", xy_um=[300, 40], consumers=["u_cland_origin", "u_cland_agg_1"]),
    dict(name="m", raw="rst_rl_5", xy_um=[560, 50], consumers=["u_cland_agg_2", "u_cland_sin_agg_m_tx_ft_i_0"])]
# m_rx_ft per-bit sites (wtx_sites.py form: ASAP7 site grid X0=Y0=4.32, SW 0.054, RH 0.27; DFF footprint 1.404x0.27)
X0 = Y0 = 4.32; SW, RH, CELL = 0.054, 0.27, [1.404, 0.27]
pins = {}
for ln in geom.read_text().splitlines():
    f = ln.split("\t")
    if f[0] == "P":
        m = re.fullmatch(r"m_rx_ft_o\[(\d+)\]", f[2])
        if m: pins[int(m.group(1))] = float(f[7])
slot = {s["name"]: s for s in t["ft_slots"]}["m_rx_ft"]
assert sorted(pins) == list(range(slot["width"] + 1)), "m_rx_ft_o pins not 0..width"
gx = lambda x: round(X0 + math.floor((x - X0) / SW + 1e-9) * SW, 3)
sites = []
for xc in (407.6, 809.6):           # cell centres: s0 face flop ~5.6 -> 402 -> 402 -> E pin 838 (~28.4)
    x = gx(xc - CELL[0] / 2); used = set(); col = []
    for b in range(slot["width"] + 1):
        n0 = round((pins[b] - RH / 2 - Y0) / RH)
        n = next(n0 + d for d in (0, 1, -1, 2, -2) if n0 + d not in used); used.add(n)
        col.append([x, round(Y0 + n * RH, 3)])
    sites.append(col)
slot["bit_sites_um"] = sites; slot["bit_site_cell_um"] = CELL
slot["note"] = ("l48z (DIE-HEAD-53): per-bit station sites s1 x~%.1f, s2 x~%.1f, each bit on its pin row "
                "(L*j/3 put s2 279 um from the E pins)" % (sites[0][0][0] + 0.702, sites[1][0][0] + 0.702))
rep["hd_mesh_e"] = "m_rx_ft bit sites + reader START d1 + writer START d1 + status relay agg.m_tx_ft_i + 3 agg anchors + 2 local resets"

# ---- hd_spn_eshim_tx ----
lr = {r["name"]: r for r in T["hd_spn_eshim_tx"]["clock"]["landing_local_resets"]}
lr["o"]["xy_um"] = [40.0, 850.0]
rep["hd_spn_eshim_tx"] = "local reset copy o (60,700) -> (40,850) next to cland_tstart_in"

# ---- die top count straps ----
new_k = CL.Landings(json.loads(json.dumps(raw)), side).strap_expected()
if out.exists(): shutil.rmtree(out)
shutil.copytree(src, out)
top = (out / "s81_head_top.sv").read_text(); ch = []
for part in sorted(set(old_k) | set(new_k)):
    for sp in sorted(set(old_k.get(part, {})) | set(new_k.get(part, {}))):
        o, n = old_k.get(part, {}).get(sp), new_k.get(part, {}).get(sp)
        if o == n: continue
        w, v = n; inst = CL.ident(part)
        m = re.search(r"\n    (\w+)(?:\s*#\(.*?\))?\s+" + re.escape(inst) + r"\s*\((.*?)\n    \);", top, re.S)
        assert m, inst
        body = m.group(2); pm = re.search(r"\." + re.escape(sp) + r"\((\d+)'b([01]+)\)", body)
        assert pm and int(pm.group(2), 2) == o[1], (inst, sp, o, pm and pm.group(0))
        nb = body[:pm.start()] + ".%s(%d'b%s)" % (sp, w, format(v, "0%db" % w)) + body[pm.end():]
        top = top[:m.start(2)] + nb + top[m.end(2):]
        ch.append([inst, sp, o[1], v])
(out / "s81_head_top.sv").write_text(top)
(out / "source_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
(out / "l48z_report.json").write_text(json.dumps(dict(event="l48z", base="l48x", types=rep, strap_changes=ch), indent=1) + "\n")
print("types", sorted(rep), "strap changes", len(ch))
for r in ch: print("  ", r)
