#!/usr/bin/env python3
"""S81 plan view event 2026-11-11 (DS85-VIEWS, DIE-S81-85; POROUS-ALL-1 17:50 ASK, owner-assigned 11-10 to DIE-S81-85).

Points the plan rows of four signed hard cores at views exported from their SIGNED routed DBs.  Before this event
the col_h9 / col_h10 parents were assembled against older views that the signed DBs do not match:

  dsfd_node_LLd / LLfd / LLfu (9 / 60 / 62 insts): plan view physical/ref_tile/s81net_node_ll*/views (CORE-KS 10-23
      ref_tile export).  Its PG is 15 VDD + 15 VSS M5 straps at 2.7 um pitch (x 2.46 .. 40.45); every signed DB has 8 + 8
      at 4.32 um (x 6.38 .. 36.82).  A parent whose M6 PG drops vias on the plan straps lands on no metal in the DB:
      a real PG open on every LL instance.  Signal pins and outline are identical (asserted below).
  dsfd_bf_front_roots (28 insts): plan view physical/s81_die_views/bf_roots_1016_fg (a 10-16 closure-loop run that no
      longer exists).  cfg[47] carries an M3 stub to y 1.723 that the counted DB (record 3ad323860e44,
      kl_dsfd_bf_front_roots_s52a) does not have (DB: M3 0..0.038 only); PG is 21 + 21 M5 straps at 5.4 um vs the DB's
      25 + 25 at 4.32 um.  The other 3,271 signal pins and the outline are identical (asserted below).

New views: physical/die_plan/s81/cores/views/<master>_signed_1111/ = tools/autopilot/export_view.py of the signed run
(LEF = the run's write_abstract_lef of 6_final.odb, <m>_tt.lib / <m>_ff.lib = the run's ORFS finish ETMs _tc / _BC),
view_lef.bind receipt <m>.view.json, signoff.json, odb.sha (and PROVENANCE.json, the re-sign record, for front_roots).

Per row: lib -> the view TT ETM, lef -> the view LEF (view_lef.attach), note added.  Nothing else in the plan moves:
the output with those three keys restored is json-equal to the input (asserted).  Asserted per master, fail-closed:
  * base plan sha256 is a known base (FEED-BAL 66466e86ebcd, plan of record ebea5f5b8ade or combined
    FEED-BAL-2/SVCRS-3 v5 99f40d35071d); input serialisation is
    json.dumps(indent=1)+"\\n" or json.dumps()+"\\n" (kept for the output);
  * old plan LEF sha256 and old lef/lib paths as below; view LEF/lib sha256 = this script's pins and = the bind receipt;
    view provenance views_status 'signoff', gates view_complete, signoff.json verdict SIGNED, odb.sha as below;
  * SIZE equal to the plan LEF and to every row's outline_um; lib cell = macro; lib signal bits = LEF signal bits;
  * signal pins: same names, DIRECTION and per-layer RECT set as the plan LEF, except the listed exception
    (front_roots cfg[47]: old/new RECT sets as listed, the new set a subset of the old);
  * every plan pins_file pin (name, layer, centre; canonical face-pin size where known) lies inside a PORT RECT of that
    pin on that layer in the NEW LEF, so the parent's route target exists in the signed DB;
  * PG pin names unchanged (VDD, VSS); only PG / OBS geometry differs (recorded in the report).

    python3 physical/die_plan/s81/delta_signed_views_1111.py PLAN_IN PLAN_OUT REPORT.json [--check]   (cwd = repo root)
--check: verify everything, write only the report (PLAN_OUT not written).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import view_lef as VL  # noqa: E402

TAG = "DS85-VIEWS-1111"
BASES = {
    "66466e86ebcd7450a7db52c3b8ae807926721845a2e64583dadc4c41da5b2a7f": "FEED-BAL plan (feed1111/out/plan.json)",
    "ebea5f5b8ade7a2311458f2aa9b7ea5647c4acd7d8cb6030f39bd114208d7e31": "S81 plan of record (pgr1/out_s81_meas_1111_0332)",
    "99f40d35071d66bf2edd2b81f4d7046598f297bbf0b1b3884006252e85172eb9":
        "combined S81 plan: FEED-BAL-2 on SVCRS-3 v5 ca10ae6afbab (feed1111/out2/plan.json)",
}
VIEW = lambda m: f"physical/die_plan/s81/cores/views/{m}_signed_1111"  # noqa: E731
MASTERS = {
    "dsfd_node_LLd": dict(
        old_lef="physical/ref_tile/s81net_node_lld/views/dsfd_node_LLd/dsfd_node_LLd.lef",
        old_lib="physical/ref_tile/s81net_node_lld/views/dsfd_node_LLd/dsfd_node_LLd_tt.lib",
        old_lef_sha256="7515e8aedaff164377c59b4b9c352ef2ff1e438b61a86e08da26e7f0be3641e8",
        lef_sha256="d4db37c56f4b8343e3bd7baed36b58e47a180ff1010d37d8f4c5e190d8e1efd1",
        lib_sha256="114b9675caf8ffe3d65f432987c2d01b1cc8ba3b6ba282c1de99ceb62008e702",
        odb_sha256="218b0171982b48ecc955b2eeb8f700f98dda23a5218d54df629acb5ac32004e9",
        insts=9, exceptions={}),
    "dsfd_node_LLfd": dict(
        old_lef="physical/ref_tile/s81net_node_llfd/views/dsfd_node_LLfd/dsfd_node_LLfd.lef",
        old_lib="physical/ref_tile/s81net_node_llfd/views/dsfd_node_LLfd/dsfd_node_LLfd_tt.lib",
        old_lef_sha256="6dd0ecaebebfc88aa62753c7e54a46cda8306e69227d54c7fb351cbcc43a1dca",
        lef_sha256="b6405c298205070be484d57bb1c4e25b92d375f31edfcf061646e854132153d1",
        lib_sha256="82418ff20a076e7c838e25d145c06776f79e1c0467a8b2eaf5538db89530cb67",
        odb_sha256="6e611fdfc18b0b2d85410e845e27e1811b00451ae4d9a00584526eeba0966777",
        insts=60, exceptions={}),
    "dsfd_node_LLfu": dict(
        old_lef="physical/ref_tile/s81net_node_llfu/views/dsfd_node_LLfu/dsfd_node_LLfu.lef",
        old_lib="physical/ref_tile/s81net_node_llfu/views/dsfd_node_LLfu/dsfd_node_LLfu_tt.lib",
        old_lef_sha256="7c874fd7cae5d56089b626938d9a06d1e43c9d67dac4160454d397f065847d2f",
        lef_sha256="b84636b8bab94cd98341c52d1edd0fe1e96e5957f717376256507897a8e637bf",
        lib_sha256="dea19331277a3661bcaa10f9b46fb0753ac9c62ece1909f641b42f735e24e715",
        odb_sha256="8484e2f66fe786054fde7c97eeaaee035812da3709fa167e9a8d35f2227482f6",
        insts=62, exceptions={}),
    "dsfd_bf_front_roots": dict(
        old_lef="physical/s81_die_views/bf_roots_1016_fg/dsfd_bf_front_roots/dsfd_bf_front_roots.lef",
        old_lib="physical/s81_die_views/bf_roots_1016_fg/dsfd_bf_front_roots/dsfd_bf_front_roots_tt.lib",
        old_lef_sha256="231d5c7708f81245134ce4cd798bf3ae2ca8d2bc176ac40c4c97b318eeb1bf3b",
        lef_sha256="70aaf97be0cebc8b1a78acfe94ac364e2791a00212612f44d9190d955412667a",
        lib_sha256="564d652636832fe657a58bd5e86be0fc7e8fd148597fb16dcc1333a61afd4dc7",
        odb_sha256="cf4bae456ed11e9a60a72bbad99d574fb435b4e4b84af1ccfc641ca4417ba568",
        insts=28,
        # the stale view's M3 stub (abstract_pin_stub of the 10-16 run's wire) is not in the counted DB
        exceptions={"cfg[47]": dict(old={"M3": [[16.128, 0.0, 16.146, 0.144], [16.128, 0.108, 16.146, 1.723]]},
                                    new={"M3": [[16.128, 0.0, 16.146, 0.038]]})}),
}
SHAPE = {"M3": (0.018, 0.038), "M4": (0.084, 0.024), "M5": (0.024, 0.084)}   # == gen_core_kit_legacy.RECT
EPS = 1e-6
FORMATS = {"indent1_nl": lambda d: json.dumps(d, indent=1) + "\n",   # the base plans' own byte forms (kept)
           "compact_nl": lambda d: json.dumps(d) + "\n"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def repo_bytes(path):
    p = Path(path)
    if p.exists():
        return p.read_bytes()
    return subprocess.run(["git", "show", f"HEAD:{path}"], check=True, capture_output=True).stdout


def parse_lef(text, macro):
    m = re.search(r"^MACRO\s+%s\s*$(.*?)^END\s+%s\s*$" % (re.escape(macro), re.escape(macro)), text, re.S | re.M)
    assert m, f"LEF has no MACRO {macro}"
    body = m.group(1)
    s = re.search(r"^\s*SIZE\s+(\S+)\s+BY\s+(\S+)\s*;", body, re.M)
    pins = {}
    for pm in re.finditer(r"^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+\1\s*$", body, re.S | re.M):
        d, cur = dict(dir=None, use="SIGNAL", rects=defaultdict(set)), None
        for ln in pm.group(2).splitlines():
            t = ln.split()
            if not t:
                continue
            if t[0] == "DIRECTION":
                d["dir"] = t[1].rstrip(";")
            elif t[0] == "USE":
                d["use"] = t[1].rstrip(";").upper()
            elif t[0] == "LAYER":
                cur = t[1]
            elif t[0] == "RECT":
                d["rects"][cur].add(tuple(round(float(v), 4) for v in t[1:5]))
            elif t[0] == "POLYGON":
                raise AssertionError(f"{macro} PIN {pm.group(1)}: POLYGON not handled")
        pins[pm.group(1).replace("\\", "")] = d
    obs, cur = defaultdict(list), None
    om = re.search(r"^\s*OBS\s*$(.*?)^\s*END\s*$", body, re.S | re.M)
    for ln in (om.group(1).splitlines() if om else []):
        t = ln.split()
        if t and t[0] == "LAYER":
            cur = t[1]
        elif t and t[0] == "RECT":
            obs[cur].append(tuple(round(float(v), 4) for v in t[1:5]))
    return dict(size=[round(float(s.group(1)), 4), round(float(s.group(2)), 4)], pins=pins, obs=obs)


def pg_summary(pin):
    out = {}
    for layer, rs in sorted(pin["rects"].items()):
        xs = sorted({round((r[0] + r[2]) / 2, 4) for r in rs})
        out[layer] = dict(rects=len(rs), x_centres=[xs[0], xs[-1]] if xs else [],
                          pitch_um=sorted({round(b - a, 4) for a, b in zip(xs, xs[1:])}),
                          width_um=sorted({round(min(r[2] - r[0], r[3] - r[1]), 4) for r in rs}),
                          y_span=[min(r[1] for r in rs), max(r[3] for r in rs)])
    return out


def rects_json(d):
    return {k: sorted([list(r) for r in v]) for k, v in sorted(d.items())}


def check_master(m, spec, rows):
    vd = VIEW(m)
    lef_p, lib_p = f"{vd}/{m}.lef", f"{vd}/{m}_tt.lib"
    old_b = repo_bytes(spec["old_lef"])
    assert sha(old_b) == spec["old_lef_sha256"], (m, "old plan LEF differs from the event base")
    new_b = Path(lef_p).read_bytes()
    assert sha(new_b) == spec["lef_sha256"], (m, "view LEF sha")
    assert sha(Path(lib_p).read_bytes()) == spec["lib_sha256"], (m, "view TT lib sha")
    assert Path(f"{vd}/{m}_ff.lib").is_file(), (m, "view FF lib missing")
    rec = json.loads(Path(VL.receipt_path(lib_p)).read_text())
    assert rec["lef_sha256"] == spec["lef_sha256"] and rec["lib_sha256"] == spec["lib_sha256"], (m, "bind receipt")
    prov = json.loads(Path(f"{vd}/provenance.json").read_text())
    gates = json.loads(Path(f"{vd}/gates.json").read_text())
    so = json.loads(Path(f"{vd}/signoff.json").read_text())
    assert prov.get("views_status") == "signoff" and gates.get("view_complete") is True, (m, "view not complete")
    assert so.get("verdict") == "SIGNED", (m, so.get("verdict"))
    assert gates.get("routed_lec") == "EQUIVALENT", (m, gates.get("routed_lec"))
    assert Path(f"{vd}/odb.sha").read_text().split()[0] == spec["odb_sha256"], (m, "odb sha")
    row = VL.compare(new_b.decode(), lib_p)
    assert row["cell"] == m and not (row.get("unread") or row["lef_only"] or row["lib_only"]), (m, row)

    A, B = parse_lef(old_b.decode(), m), parse_lef(new_b.decode(), m)
    assert A["size"] == B["size"], (m, "SIZE", A["size"], B["size"])
    sig = lambda L: {k: v for k, v in L["pins"].items() if v["use"] not in ("POWER", "GROUND")}  # noqa: E731
    pg = lambda L: {k: v for k, v in L["pins"].items() if v["use"] in ("POWER", "GROUND")}  # noqa: E731
    sa, sb = sig(A), sig(B)
    assert set(sa) == set(sb), (m, "signal pin names", sorted(set(sa) ^ set(sb))[:8])
    assert set(pg(A)) == set(pg(B)) == {"VDD", "VSS"}, (m, "PG pin names", sorted(pg(A)), sorted(pg(B)))
    changed = []
    for n in sorted(sa):
        assert sa[n]["dir"] == sb[n]["dir"], (m, n, "DIRECTION", sa[n]["dir"], sb[n]["dir"])
        ra, rb = rects_json(sa[n]["rects"]), rects_json(sb[n]["rects"])
        if ra == rb:
            continue
        ex = spec["exceptions"].get(n)
        assert ex and ra == ex["old"] and rb == ex["new"], (m, n, "signal pin shape differs", ra, rb)
        assert all(any(q[0] <= r[0] + EPS and q[1] <= r[1] + EPS and q[2] >= r[2] - EPS and q[3] >= r[3] - EPS
                       for q in ra.get(k, [])) for k in rb for r in rb[k]), (m, n, "new shape not within the old one")
        changed.append(dict(pin=n, old=ra, new=rb))
    assert len(changed) == len(spec["exceptions"]), (m, "listed exception did not occur", changed)

    # every plan pin centre lands on metal of that pin in the NEW (signed) LEF, for every pins_file the rows use
    pin_tables = {}
    for _, c in rows:
        pf = c["pins_file"]
        if pf in pin_tables:
            continue
        raw = repo_bytes(f"physical/die_plan/s81/{pf}")
        pins = json.loads(raw)["pins"]
        assert {p["name"] for p in pins} == set(sb), (m, pf, "pins_file names differ from the LEF signal pins")
        for p in pins:
            w, h = SHAPE.get(p["layer"], (0.0, 0.0))
            s = [p["x"] - w / 2, p["y"] - h / 2, p["x"] + w / 2, p["y"] + h / 2]
            assert any(r[0] <= s[0] + EPS and r[1] <= s[1] + EPS and r[2] >= s[2] - EPS and r[3] >= s[3] - EPS
                       for r in sb[p["name"]]["rects"].get(p["layer"], ())), (m, pf, p, "plan pin not on signed metal")
        pin_tables[pf] = dict(sha256=sha(raw), pins=len(pins), on_signed_metal=len(pins))
    return dict(view=vd, lef=lef_p, lib=lib_p, size_um=B["size"], signal_pins=len(sb),
                signal_pins_identical=len(sb) - len(changed), signal_pin_changes=changed,
                pg_old={n: pg_summary(v) for n, v in sorted(pg(A).items())},
                pg_new={n: pg_summary(v) for n, v in sorted(pg(B).items())},
                obs_rects_old={k: len(v) for k, v in sorted(A["obs"].items())},
                obs_rects_new={k: len(v) for k, v in sorted(B["obs"].items())},
                obs_new={k: [list(r) for r in v] for k, v in sorted(B["obs"].items())},
                pins_files=pin_tables, signoff=dict(tt_wns_ps=gates.get("tt_wns_ps"), ff_wns_ps=gates.get("ff_wns_ps"),
                                                    routed_lec=gates.get("routed_lec"),
                                                    lec_record=gates.get("routed_lec_record"),
                                                    odb_sha256=spec["odb_sha256"], record=rec["record"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("report")
    ap.add_argument("--check", action="store_true", help="verify only; write the report, not the plan")
    a = ap.parse_args()
    raw = Path(a.plan_in).read_bytes()
    base = sha(raw)
    assert base in BASES, f"base plan {base[:12]} is not a known event base {[b[:12] for b in BASES]}"
    P = json.loads(raw)
    fmt = next((k for k, f in FORMATS.items() if f(P).encode() == raw), None)
    assert fmt, "input serialisation is not one of " + ", ".join(FORMATS)
    rows = defaultdict(list)
    for tn, t in P["partition_types"].items():
        for k in ("hard_cores", "contents"):
            for c in t.get(k) or []:
                if (c.get("physical_master") or c.get("module")) in MASTERS:
                    assert k == "hard_cores", (tn, c["inst"], k)
                    rows[c["module"]].append((tn, c))
    report = dict(schema="opentallas.s81.plan_view_event.v1", event=TAG, base_plan_sha256=base, base=BASES[base],
                  serialisation=fmt,
                  masters={}, types={})
    for m, spec in MASTERS.items():
        rs = rows[m]
        assert len(rs) == spec["insts"], (m, len(rs), spec["insts"])
        info = check_master(m, spec, rs)
        for tn, c in rs:
            assert c["lef"] == spec["old_lef"] and c["lib"] == spec["old_lib"], (tn, c["inst"], c["lef"], c["lib"])
            assert [round(v, 4) for v in c["outline_um"]] == info["size_um"], (tn, c["inst"], c["outline_um"])
            assert "note" not in c, (tn, c["inst"], "row already has a note")
            VL.attach(c, info["lib"])
            assert c["lef"] == info["lef"], (tn, c["inst"])
            c["note"] = (f"signed view {info['view']} ({TAG}: plan view aligned to the signed routed DB, odb "
                         f"{spec['odb_sha256'][:12]}; record PROVENANCE/provenance.json there)")
            report["types"].setdefault(tn, []).append(dict(inst=c["inst"], module=m))
        info.pop("obs_new")
        report["masters"][m] = dict(info, insts=len(rs), types=len({tn for tn, _ in rs}), old_lef=spec["old_lef"],
                                    old_lib=spec["old_lib"])
    # preservation: with lef / lib / note of the touched rows removed, the output is json-equal to the input
    def strip(plan):
        for t in plan["partition_types"].values():
            for c in t.get("hard_cores") or []:
                if c.get("module") in MASTERS:
                    for k in ("lef", "lib", "note"):
                        c.pop(k, None)
        return plan
    assert strip(json.loads(json.dumps(P))) == strip(json.loads(raw)), "the event moved more than lef/lib/note"
    out = FORMATS[fmt](P).encode()
    report.update(plan_out_sha256=sha(out), relaunch_types=sorted(report["types"]),
                  relaunch_type_count=len(report["types"]),
                  insts=sum(len(v) for v in report["types"].values()))
    if not a.check:
        Path(a.plan_out).write_bytes(out)
    Path(a.report).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(dict(base=base[:12], out=sha(out)[:12], types=len(report["types"]), insts=report["insts"],
                          masters={m: dict(insts=v["insts"], signal_pin_changes=[x["pin"] for x in v["signal_pin_changes"]])
                                   for m, v in report["masters"].items()}, written=not a.check)))


if __name__ == "__main__":
    main()
