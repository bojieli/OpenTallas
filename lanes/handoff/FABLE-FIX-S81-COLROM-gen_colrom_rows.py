#!/usr/bin/env python3
"""FABLE-FIX-S81-COLROM 11-21 (FABLE-CLOSURE-0600 lever 1): S81 col ROM stage rows per type, from the type's AS-BUILT names.

One self-contained generator for the three row classes of the col ROM read path (no donor file):
  rom_in  +1 posedge stage on every data/control input of each ROM element half (ot_v41_rom_elem_*: cfg_a cfg_d cfg_v go
          go_tag xs_b xs_e0 xs_e1 xs_p xs_pos xs_q0 xs_q1 xs_v), seat 5.59 um outside the pin face at the port's pin centroid
  rom_pval +1 posedge stage on the element outputs into the q bank (bn<k>.e_r0 <- u_w pval, e_r1 <- u_e pval, e_st <- u_w busy),
          seat 5.32 um outside the element's output face (only where the base plan does not already hold the row)
  cfg7_q  +1 posedge stage on each cfg ROM rd_out -> sequencer q<M> bus (ot_s81_cfg7_seq only; ot_s81_cfg7_seq_bfp has no
          RD_EXTRA and is skipped), seat off the ROM rd_out face, pulled toward the sequencer until the hop is <= --hop-max
plus the repoint of every ot_s81_cfg7_seq hard core to the signed RD_EXTRA=1 view, and (--sidecars) RD_EXTRA=1 in every
portable hard-params sidecar that lists ot_s81_cfg7_seq, so the die parameter equals the view (192 HARD_CORE_PARAM errors).
Row inst names are the bound leaf names: the hard-core inst with '.' -> '_' when the bound type RTL holds u_<name>, else the
same name without its region prefix u_r<N>_ (types whose partition root is the region).  A row is emitted only when the bound
leaf has that port.  Rows already in the plan are kept and not repeated; the delta is row-level adds (no whole-key replace).
The tree also needs: define OT_S81_CFG7_RDX in asbuilt_run.json, the signed view + RTL, the hard_core_built_params registry
entry and the dead-input re-proof (epyc10 s81-j6/j7/j7_post.sh does these four).
usage: gen_colrom_rows.py PLAN BOUND_RTL_DIR OUT_DELTA [--type-re RE] [--out-plan P] [--hop-max 400]
                          [--sidecars DIR --sidecars-out DIR] [--no-pval] [--report R.json]"""
import argparse, collections, json, os, re
RDX_LIB = "physical/die_plan/s81/cores/views/ot_s81_cfg7_seq_rdx_1121/ot_s81_cfg7_seq_tt.lib"
IN = ["cfg_a", "cfg_d", "cfg_v", "go", "go_tag", "xs_b", "xs_e0", "xs_e1", "xs_p", "xs_pos", "xs_q0", "xs_q1", "xs_v"]
N_IN = ("FABLE-FIX-S81-COLROM lever 1: ROM input stage; the falling-edge ROM element captures on a half cycle, +1 posedge "
        "stage at the ROM input pins (+1 cycle, declared internal pipe)")
N_OUT = ("ROM-PVAL: falling-edge ROM face -> qbank pin register is a half cycle; +1 posedge stage at the ROM pins "
         "(+1 cycle, declared internal pipe)")
N_Q = ("FABLE-FIX-S81-COLROM RD_EXTRA: +1 posedge stage on the cfg ROM rd_out -> sequencer q bus (needs define "
       "OT_S81_CFG7_RDX = seq RD_EXTRA 1; +1 cycle)")
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("rtl"); ap.add_argument("delta")
ap.add_argument("--type-re", default=r"^col_"); ap.add_argument("--out-plan"); ap.add_argument("--hop-max", type=float, default=400.0)
ap.add_argument("--sidecars"); ap.add_argument("--sidecars-out"); ap.add_argument("--no-pval", action="store_true"); ap.add_argument("--report")
A = ap.parse_args()
pdir = os.path.dirname(os.path.abspath(A.plan)); plan = json.load(open(A.plan)); tre = re.compile(A.type_re)
inst_re = re.compile(r"^    (\w+)(?: #\([^\n]*\))? (u_\w+) \(\n(.*?)\n    \);", re.M | re.S)
pins_cache = {}
def pins(h):
    pf = h["pins_file"]
    if pf not in pins_cache:
        g = collections.defaultdict(list)
        for p in json.load(open(os.path.join(pdir, pf)))["pins"]: g[p["name"].split("[")[0]].append((p["x"], p["y"]))
        pins_cache[pf] = g
    return pins_cache[pf]
def absolute(h, pts):
    o = h.get("orient", "R0"); w, hh = h["outline_um"]; ox, oy = h["origin_um"]
    if o not in ("R0", "MX", "MY", "R180"): return None
    f = {"MY": lambda x, y: (w - x, y), "MX": lambda x, y: (x, hh - y), "R180": lambda x, y: (w - x, hh - y)}.get(o, lambda x, y: (x, y))
    return [(ox + f(x, y)[0], oy + f(x, y)[1]) for x, y in pts]
def face_seat(h, pts, off):
    """seat outside the face of h nearest to the pin centroid"""
    ox, oy = h["origin_um"]; w, hh = h["outline_um"]
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    e = min({"W": cx - ox, "E": ox + w - cx, "S": cy - oy, "N": oy + hh - cy}.items(), key=lambda kv: kv[1])[0]
    return {"W": (ox - off, cy), "E": (ox + w + off, cy), "S": (cx, oy - off), "N": (cx, oy + hh + off)}[e]
def in_core(t, x, y):
    return any(c["origin_um"][0] < x < c["origin_um"][0] + c["outline_um"][0] and c["origin_um"][1] < y < c["origin_um"][1] + c["outline_um"][1]
               for c in t["hard_cores"])
ops, st, warn, fam = [], collections.Counter(), [], collections.defaultdict(collections.Counter)
for T, t in sorted(plan["partition_types"].items()):
    if not tre.search(T): continue
    f = os.path.join(A.rtl, T + ".sv")
    if not os.path.exists(f): warn.append(f"{T}: no bound RTL"); st["type_no_rtl"] += 1; continue
    cells = {m.group(2): set(re.findall(r"^\s*\.(\w+)\(", m.group(3), re.M)) for m in inst_re.finditer(open(f).read())}
    cores = {h["inst"]: (i, h) for i, h in enumerate(t.get("hard_cores", []))}
    def leaf(inst):
        s = inst.replace(".", "_")
        if "u_" + s in cells: return s
        s2 = re.sub(r"^u_r\d+_", "", s)
        return s2 if s2 != s and "u_" + s2 in cells else None
    have = {(r["inst"], r.get("port"), r.get("side")) for r in t.get("relay_depth") or []}
    sites = t.get("relay_sites") or {}
    rows, newsites = [], {}
    def add(cls, li, port, note, seat):
        if li is None: st["no_leaf:" + cls] += 1; return
        if port not in cells["u_" + li]: st["no_port:" + cls] += 1; return
        if (li, port, "sink") in have: st["exists:" + cls] += 1; return
        k = f"u_y_xd_{li}_{port}_0_0"
        if k in sites or k in newsites or len(k) >= 100: warn.append(f"{T}: site key {k}"); st["bad_site_key"] += 1; return
        seat = [round(seat[0], 3), round(seat[1], 3)]
        if in_core(t, *seat): warn.append(f"{T}: seat of {li}.{port} inside a hard core {seat}"); st["seat_in_core"] += 1
        rows.append({"inst": li, "port": port, "side": "sink", "D": 1, "note": note}); newsites[k] = seat
        have.add((li, port, "sink")); st[cls] += 1; fam[T.split("__")[0]][cls] += 1
    for inst, (i, h) in cores.items():
        mod = h.get("module", "")
        m = re.match(r"^(?:(.+)\.)?u_e(\d+)\.u_([we])$", inst)
        if mod.startswith("ot_v41_rom_elem") and m:                       # ---- ROM element half
            g = pins(h); li = leaf(inst)
            for port in IN:
                if port in g:
                    pts = absolute(h, g[port])
                    if pts is None: st["rotated"] += 1; continue
                    add("rom_in", li, port, N_IN, face_seat(h, pts, 5.59))
            if not A.no_pval:
                bn = cores.get((m.group(1) + "." if m.group(1) else "") + f"u_bn{m.group(2)}")
                if bn is not None:
                    for qp, rp in ([("e_r0", "pval"), ("e_st", "busy")] if m.group(3) == "w" else [("e_r1", "pval")]):
                        pts = absolute(h, g[rp])
                        if pts is not None: add("rom_pval", leaf(bn[1]["inst"]), qp, N_OUT, face_seat(h, pts, 5.32))
        m = re.match(r"^(?:(.+)\.)?u_c(\d+)_(\d+)$", inst)
        if mod == "ot_rom_4096x72_m8" and m:                              # ---- cfg ROM -> sequencer q bus
            sq = cores.get((m.group(1) + "." if m.group(1) else "") + f"u_s{m.group(2)}")
            if sq is None: st["cfg_rom_without_seq"] += 1; continue
            if sq[1]["module"] != "ot_s81_cfg7_seq": st["skip_q:" + sq[1]["module"]] += 1; continue
            pts = absolute(h, pins(h)["rd_out"]); port = f"q{m.group(3)}"
            spts = absolute(sq[1], pins(sq[1]).get(port, []))
            if pts is None or not spts: st["rotated"] += 1; continue
            sx, sy = face_seat(h, pts, 5.32)
            hop = max(abs(sx - x) + abs(sy - y) for x, y in spts)
            if hop > A.hop_max:                                           # pull the seat toward the sequencer pins
                cx = sum(p[0] for p in spts) / len(spts); cy = sum(p[1] for p in spts) / len(spts)
                need = hop - A.hop_max; d = abs(cx - sx) + abs(cy - sy); k = min(1.0, need / d)
                for kk in [k + 0.02 * j for j in range(0, 40)]:
                    nx, ny = sx + (cx - sx) * kk, sy + (cy - sy) * kk
                    if not in_core(t, nx, ny) and max(abs(nx - x) + abs(ny - y) for x, y in spts) <= A.hop_max: break
                rom_leg = abs(nx - sx) + abs(ny - sy); sx, sy = nx, ny; st["cfg7_q_seat_pulled"] += 1
                warn.append(f"{T}: {inst} -> {sq[1]['inst']}.{port} hop {hop:.0f} um, seat pulled {rom_leg:.0f} um toward the sequencer")
            add("cfg7_q", leaf(sq[1]["inst"]), port, N_Q, (sx, sy))
    rep = 0
    for inst, (i, h) in cores.items():
        if h.get("module") == "ot_s81_cfg7_seq" and h.get("lib") != RDX_LIB:
            ops.append({"op": "replace", "path": f"/partition_types/{T}/hard_cores/{i}/lib", "value": RDX_LIB}); rep += 1
            if A.out_plan: h["lib"] = RDX_LIB
    st["seq_repoint"] += rep
    if rows and "relay_depth" not in t:
        ops.append({"op": "add", "path": f"/partition_types/{T}/relay_depth", "value": []})
    if rows and "relay_sites" not in t:
        ops.append({"op": "add", "path": f"/partition_types/{T}/relay_sites", "value": {}})
    for r in rows: ops.append({"op": "add", "path": f"/partition_types/{T}/relay_depth/-", "value": r})
    for k, v in newsites.items():
        ops.append({"op": "add", "path": f"/partition_types/{T}/relay_sites/{k.replace('~', '~0').replace('/', '~1')}", "value": v})
    if A.out_plan and rows:
        t.setdefault("relay_depth", []).extend(rows); t.setdefault("relay_sites", {}).update(newsites)
    if rows or rep: st["types"] += 1
side = {}
if A.sidecars:
    os.makedirs(A.sidecars_out, exist_ok=True)
    for n in sorted(os.listdir(A.sidecars)):
        if not n.endswith(".hard_params.json"): continue
        s = json.load(open(os.path.join(A.sidecars, n))); m = (s.get("masters") or {}).get("ot_s81_cfg7_seq")
        if m is None: continue
        side[n] = m.get("RD_EXTRA", "(unset)")
        if m.get("RD_EXTRA") != "1":
            m["RD_EXTRA"] = "1"; s["note"] = s.get("note", "") + (" | FABLE-FIX-S81-COLROM 11-21: RD_EXTRA=1 on ot_s81_cfg7_seq (every "
                "cfg7_seq core of the die uses the signed RD_EXTRA=1 view ot_s81_cfg7_seq_rdx_1121; the vg netlist passes no RD_EXTRA)")
            p = os.path.join(A.sidecars_out, n); json.dump(s, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
left = sum(1 for T, t in plan["partition_types"].items() for h in t.get("hard_cores", [])
           if h.get("module") == "ot_s81_cfg7_seq" and h.get("lib") != RDX_LIB) if A.out_plan else None
delta = {"schema": "opentallas.s81.j6_donor_delta.v1", "types_changed": sorted({o["path"].split("/")[2] for o in ops}),
         "manifest_ops": [], "ops": ops, "lane": "FABLE-FIX-S81-COLROM",
         "note": "S81 col ROM stage rows (rom_in, rom_pval where missing, cfg7_q) per type from as-built names + cfg7 RD_EXTRA=1 "
                 "view repoint; row-level adds; apply after ROM-PVAL; tree needs define OT_S81_CFG7_RDX, RD_EXTRA=1 sidecars, "
                 "registry entry and the dead-input re-proof",
         "stats": dict(st), "warnings": warn}
json.dump(delta, open(A.delta + ".tmp", "w"), separators=(",", ":")); os.replace(A.delta + ".tmp", A.delta)
if A.out_plan:
    json.dump(plan, open(A.out_plan + ".tmp", "w"), separators=(",", ":")); os.replace(A.out_plan + ".tmp", A.out_plan)
rep = {"stats": dict(st), "per_family": {k: dict(v) for k, v in sorted(fam.items())}, "sidecars_rd_extra_before": side,
       "cfg7_seq_cores_not_on_rdx_view_die_wide": left, "warnings": warn}
if A.report: json.dump(rep, open(A.report, "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "warnings"}, indent=1)); print("warnings", len(warn)); [print(" ", w) for w in warn[:14]]
