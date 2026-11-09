#!/usr/bin/env python3
"""S81 plan event T51-SPLIT-1109 (DIE-S81-85, COORD GO 11-09; rom_q split model 3a92e86c4c8, view format b5ec9b39080):
the soft station type slice_station__t51 (module s81p_slice_station__t51, 1442.88 x 1226.88, 1 instance s_7N_x13 MY)
takes its native split form: a soft parent (15198 cells, 0 FF) with two hard children

  W = s81p_slice_station__t51_ot_s81_station_t51_native_w  origin [8.64, 8.64]   outline 613.44 x 1209.6
  E = s81p_slice_station__t51_ot_s81_station_t51_native_e  origin [639.36, 8.64] outline 794.88 x 1209.6

(boxes = station_split_1106/controls_pose.json children; outlines = each kit's DIE_AREA = LEF SIZE).  The parent and
children are the S81-T51-RECUT native split of the mapped t51 netlist: station_split_1106/native_conservation_controls.json
(188969 cells, 53074 FFs before = after, 0 added cycles), registered-face copies station_face_copies.py (0 added cycles,
no new port), lockstep.json (latency_delta_cycles 0).  PIN CYCLES: 0 on every face of the type; the type's own ports
and ft_slots are unchanged (the parent netlist keeps the s81p_slice_station__t51 port list).

Per child (hard_cores row, inst = the instance name in the split parent netlist = the module name):
  pins_file  inputs/core_pins/<module>.json = that child's kit pins.json (names, layer, x, y exact; 1-bit ports);
  E view     cores/views/<E>_signed_1109/: LEF + TT/FF ETMs of the signed vE DB (routed DB 379f773899bb3c8b, build
             aec3135c52, RE-SIGN flow-20261109-fh-s81, LEC EQUIVALENT; PROVENANCE.json there), view_lef receipt;
  W view     PENDING: lef = the unsigned rc51a abstract (cores/legacy/lef/t51w_rc51a_1106/, epyc2 11-06 NOT SIGNED:
             setup_tt -45.78, hold_ff -7.40, drv), no lib -- the plan's pending-view form (as gunit l1c / l1f rows);
  obs_max M7 (native M7 clock root pins, honest OBS7; the parent routes M8/M9), orient R0, track_offset
             [0.108, 0.012] = the plan's hard-core convention: it puts every M2-M6 child pin on the plan tracks; the 89
             native M7 clock root pins keep the source M7 grid (exact original metal), so they are 0.108 um off the
             plan M7 track (no single offset serves both: M5 needs dx = 0.012 mod 0.048, M7 dx = 0 mod 0.064).
Clock: one early core tap per child clock root port (46 W + 43 E = 89; clk_t2 / clk_t19 / clk_t62 feed both),
  name <inst>.<port>, xy = origin + track_offset + the kit pin centre (asserted = native_root_pins.json child rect + origin);
  insertion E = the signed core_latency.measured mean, W = the plan bound 250 / 202.5 ("measured view pending").
Reset: unchanged.  Every child reset-role port is an internal parent net (relay chain through the parent, kit
  reset_ports contract); no child port is a type reset input, so no collector_tree.core_resets leaf is added.
Bind: unchanged.  The die bind carves s81p_slice_station__t51 as before; the split is below the type boundary on the
  mapped netlist (identity = conservation receipt + per-child kit LEC).  The type kit that builds the parent uses the
  split parent netlist station_split_1106/t51_parent_split.v.gz (yosys write_verilog of split_fc.json, recovered
  11-07; port bindings of both children asserted against the kit pins here).
The plan text is edited in place (only the t51 hard_cores insert and the t51 taps tail), asserted json-equal to the
object edit.
    python3 delta_t51_split_1109.py PLAN REPORT        (cwd = repo root)
"""
import copy
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
from delta_romq_split_1106 import render_like, spans  # noqa: E402

D = Path("physical/die_plan/s81")
TN = "slice_station__t51"
TM = "s81p_slice_station__t51"
TOFF = [0.108, 0.012]
EV = "T51-SPLIT-1109 DIE-S81-85 (COORD GO 11-09)"
SPLIT = D / "station_split_1106"
PARENT_V = SPLIT / "t51_parent_split.v.gz"
PARENT_V_SHA = "1ab8a4717eb33279788cef6bc8a5f2d8cdf171a3ba77214a7c297fbf97d907a8"
W_LEF_DIR = "physical/die_plan/s81/cores/legacy/lef/t51w_rc51a_1106"
CH = {
    "w": dict(module=TM + "_ot_s81_station_t51_native_w", key="ot_s81_station_t51_native_w",
              origin=[8.64, 8.64], outline=[613.44, 1209.6],
              lef=f"{W_LEF_DIR}/{TM}_ot_s81_station_t51_native_w.lef", lib=None,
              kit_pins=f"{W_LEF_DIR}/pins.json", core=f"{W_LEF_DIR}/core.json",
              ins=(250.0, 202.5), ins_src="plan bound 250 / 202.5, measured view pending (native_w not signed)"),
    "e": dict(module=TM + "_ot_s81_station_t51_native_e", key="ot_s81_station_t51_native_e",
              origin=[639.36, 8.64], outline=[794.88, 1209.6]),
}
E_VIEW = f"physical/die_plan/s81/cores/views/{CH['e']['module']}_signed_1109"
CH["e"].update(lef=f"{E_VIEW}/{CH['e']['module']}.lef", lib=f"{E_VIEW}/{CH['e']['module']}_tt.lib",
               kit_pins=f"{E_VIEW}/pins.json", core=f"{E_VIEW}/{CH['e']['module']}.core.json")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def kit_rows(p):
    out = []
    for q in json.loads(Path(p).read_text()):
        n = q["bus"] if q.get("bit") is None else f"{q['bus']}[{q['bit']}]"
        out.append(dict(name=n, layer=q["layer"], x=q["x"], y=q["y"]))
    return out


def parent_conns():
    """{child: {port: parent net}} of the split parent netlist; the parent module keeps the type's port list"""
    t = gzip.open(PARENT_V, "rt").read()
    assert hashlib.sha256(t.encode()).hexdigest() == PARENT_V_SHA, "parent netlist content"
    assert t.count("\nmodule ") + t.startswith("module ") == 1 and f"module {TM}(" in t
    top = set(re.findall(r"^\s*(?:input|output)\s+(?:\[\d+:\d+\]\s+)?(\S+)\s*;", t, re.M))
    out = {}
    for c, d in CH.items():
        m = d["module"]
        i = t.index(f"  {m} {m} (")
        body = t[i:t.index(");", i)]
        out[c] = {p: n.strip() for p, n in re.findall(r"\.(\w+)\(([^()]*)\)", body)}
    return out, top


def main():
    plan_p, rep_p = map(Path, sys.argv[1:3])
    text = plan_p.read_text()
    P = json.loads(text)
    t = P["partition_types"][TN]
    assert t["module"] == TM and t["outline_um"] == [1442.88, 1226.88] and not t["hard"] and not t.get("hard_cores")
    assert [p["name"] for p in P["partitions"] if p["type"] == TN] == ["s_7N_x13"]
    pose = json.loads((SPLIT / "controls_pose.json").read_text())
    cons = json.loads((SPLIT / "native_conservation_controls.json").read_text())
    roots = json.loads((SPLIT / "native_root_pins.json").read_text())
    assert cons["verdict"] == "PASS" and cons["cycles_added"] == 0 and cons["state_bits_before"] == cons["state_bits_after"]
    conns, top = parent_conns()
    report = dict(event=EV, type=TN, children={}, parent_netlist=dict(path=str(PARENT_V), content_sha256=PARENT_V_SHA,
                  top_ports=len(top)), cycles_added=0)
    rows, taps = [], []
    for c, d in CH.items():
        m = d["module"]
        x0, y0, x1, y1 = pose["children"][c]
        assert [x0, y0] == d["origin"] and [round(x1 - x0, 4), round(y1 - y0, 4)] == d["outline"], (c, pose["children"][c])
        assert cons["children"][d["key"]]["module"] == m
        kr = kit_rows(d["kit_pins"])
        names = [q["name"] for q in kr]
        assert len(names) == len(set(names)) == cons["children"][d["key"]]["ports"], (c, len(names))
        assert set(names) == set(conns[c]), (c, "kit pins != parent instance ports")
        core = json.loads(Path(d["core"]).read_text())
        assert core["module"] == m
        role = core["boundary_role"]
        lef = Path(d["lef"]).read_text()
        size = re.search(r"^\s*SIZE\s+(\S+)\s+BY\s+(\S+)\s*;", lef[lef.index(f"MACRO {m}"):], re.M)
        assert [float(size[1]), float(size[2])] == d["outline"], (c, size.groups())
        if d["lib"]:
            import view_lef as VL
            row = VL.compare(lef, d["lib"])
            assert row["cell"] == m and not (row.get("unread") or row["lef_only"] or row["lib_only"]), (c, row)
            rec = json.loads(Path(VL.receipt_path(d["lib"])).read_text())
            assert rec["lib_sha256"] == sha(d["lib"]) and rec["lef_sha256"] == sha(d["lef"]), c
            ins = json.loads(Path(E_VIEW, "insertion.json").read_text())
            d["ins"] = (ins["tt"]["boundary"]["mean"], ins["ff"]["boundary"]["mean"])
            d["ins_src"] = f"signed core_latency.measured mean {E_VIEW}/insertion.json"
            prov = json.loads(Path(E_VIEW, "PROVENANCE.json").read_text())
            assert prov["verdict"] == "SIGNED" and prov["lec_verdict"] == "EQUIVALENT"
            assert prov["routed_db_sha256"].startswith("379f773899bb3c8b") and prov["build_commit"].startswith("aec3135c52")
        pf = f"inputs/core_pins/{m}.json"
        pins_doc = dict(module=m, lef=d["lef"],
                        source=(f"{EV}: kit pins.json of the native split child ({d['kit_pins']}, sha256 "
                                f"{sha(d['kit_pins'])}); names / layer / xy exact, 1-bit ports (station_face_copies a391a4ddd21)"),
                        pinhash=hashlib.sha256(json.dumps(sorted((q["name"], q["layer"], q["x"], q["y"]) for q in kr)).encode()).hexdigest()[:12],
                        pins=kr)
        (D / pf).write_text(json.dumps(pins_doc, indent=0) + "\n")
        hc = dict(inst=m, module=m, lef=d["lef"])
        if d["lib"]:
            hc["lib"] = d["lib"]
        hc.update(origin_um=d["origin"], outline_um=d["outline"], orient="R0", track_offset_um=list(TOFF), pins_file=pf,
                  obs_max="M7",
                  note=(f"{EV}: native split child {c.upper()} of {TM} (controls_pose box {pose['children'][c]}); "
                        + ("signed view " + E_VIEW + " (PROVENANCE.json there)" if d["lib"] else
                           "VIEW PENDING: unsigned rc51a abstract, no lib (epyc2 11-06 NOT SIGNED; sealed build pending)")))
        rows.append(hc)
        # early core taps: one per child clock root port
        rp = roots[d["key"]]["ports"]
        moves = {r["root"]: r for r in roots[d["key"] + "_review"]["root_pin_moves"]}
        ck = sorted(k for k, v in role.items() if v == "clk")
        assert set(rp) <= set(ck) and all(conns[c][k] == k and k in top for k in ck), (c, "clock root ports")
        byname = {q["name"]: q for q in kr}
        crow = []
        for k in ck:
            q = byname[k]
            tx, ty = round(d["origin"][0] + TOFF[0] + q["x"], 4), round(d["origin"][1] + TOFF[1] + q["y"], 4)
            if k in rp:
                r = rp[k]["rect_um"]
                assert r[0] - 1e-6 <= q["x"] <= r[2] + 1e-6 and r[1] - 1e-6 <= q["y"] <= r[3] + 1e-6, (c, k, q, r)
            mv = moves.get(k)
            taps.append(dict(name=f"{m}.{k}", kind="core", xy=[tx, ty], insertion_ps=d["ins"][0], insertion_ff_ps=d["ins"][1],
                             budget_owner=f"{EV} PLAN UNCHECKED: {d['ins_src']}",
                             note=(f"{EV}: early core tap of native {c.upper()} root {k} (source root "
                                   f"{(mv or {}).get('source_root', k)}, translation {(mv or {}).get('translation_um', 'n/a')} um)")))
            crow.append(k)
        report["children"][c] = dict(module=m, origin=d["origin"], outline=d["outline"], pins=len(kr), pins_file=pf,
                                     pins_kit_sha256=sha(d["kit_pins"]), lef=d["lef"], lib=d["lib"],
                                     view="signed" if d["lib"] else "PENDING", clock_roots=len(crow),
                                     reset_ports=sorted(k for k, v in role.items() if v == "reset"),
                                     reset_ports_internal=all(conns[c][k] not in top for k, v in role.items() if v == "reset"),
                                     insertion=list(d["ins"]))
        assert report["children"][c]["reset_ports_internal"], c
    assert len(taps) == 89, len(taps)
    assert not (set(tp["name"] for tp in taps) & set(tp["name"] for tp in t["clock"]["taps"]))
    # text edits: insert hard_cores after contents; append the core taps to clock.taps
    sp = spans(text)
    edits = []
    a, b = sp[("partition_types", TN, "contents")]
    line0 = text.rfind("\n", 0, a) + 1
    ind = re.match(r" *", text[line0:a]).group(0)
    body = render_like("{\n}", rows, ind + " ")
    edits.append((b, b, ",\n" + ind + '"hard_cores": [\n' + ind + " " + body + "\n" + ind + "]"))
    nt = len(t["clock"]["taps"])
    a, b = sp[("partition_types", TN, "clock", "taps", nt - 1)]
    line0 = text.rfind("\n", 0, a) + 1
    edits.append((b, b, "," + "\n" + text[line0:a] + render_like(text[a:b], taps, text[line0:a])))
    out = text
    for a, b, s in sorted(edits, reverse=True):
        out = out[:a] + s + out[b:]
    Q = json.loads(out)
    want = copy.deepcopy(P)
    wt = want["partition_types"][TN]
    wt["hard_cores"] = rows
    wt["clock"]["taps"] = wt["clock"]["taps"] + taps
    assert Q == want, "text edit != object edit"
    plan_p.write_text(out)
    report["core_taps"] = [tp["name"] for tp in taps]
    report["plan_sha256_before"] = hashlib.sha256(text.encode()).hexdigest()
    report["plan_sha256_after"] = hashlib.sha256(out.encode()).hexdigest()
    rep_p.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(dict(hard_cores=len(rows), core_taps=len(taps), before=report["plan_sha256_before"][:16],
                          after=report["plan_sha256_after"][:16])))


if __name__ == "__main__":
    main()
