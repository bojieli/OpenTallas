#!/usr/bin/env python3
"""HBM plan event P-Q3VM-2 (DIE-HBM-92-Q3VM 11-08, proposed by HBM-HARD-6 04:49): q3_vm rd_il N -> E face.

Core q_hub_nw.u_hb_coll_Q_vm__q0 (ot_hfd_coll_q3_vm_core, 328.32 x 717.12).  The vmasm slice is byte-local: as_il byte b
selects among rd_il byte b.  as_il enters on the W face (M4, y 89-382) while rd_il entered on the N face (M5, y 717),
so the vmasm datapath doubled back 335-630 um inside the core beside the N M5 pin crush (rd_il 2048 + kq 2248).

Changes (nothing else):
  1. pins table: every vmasm_rd_il[i] pin moves to the E face (M4, x = 328.224), at the y of its as_il partner
     (rounded to the 0.048 M4 grid, offset 0.024; adjacent E-face M4 tracks kept free, the same rule as HBM-HARD-6
     tools/mk_q3vm_vD.py, whose table b2c55e78 this reproduces); the table's clock pin moves to the new plan entry with
     the generator's own functions (gen_core_kit_hbm plan_clock_entries + clock_entry_pin, as clock_entry_pins.py).
     Written as a NEW pins file <stem>__q3vmE.json; the old table is left in place.
  2. clock_entries.json q_hub_nw / u_hb_coll_Q_vm: core entry (164.16, 358.56) -> (164.16, 501.12) (4.32 lattice,
     ~35 um from the vmasm+writer sink centroid measured on vC placed.csv), island +-4.32.
  3. die_plan.json q_hub_nw: hard_cores[u_hb_coll_Q_vm__q0].pins_file -> the new table; clock.taps[u_hb_coll_Q_vm__q0]
     xy = origin + entry = (1218.24, 393.12) -> (1218.24, 535.68).
internal_stations, buses, contents, core_conns, outlines and every other type are untouched: PIN CYCLES 0, stations 0.

usage: delta_q3vm_e_1108.py BASE_PLAN_DIR OUT_DIR [--expect-rd-sha SHA] [--receipt F]
OUT_DIR is made by hard-linking every file of BASE_PLAN_DIR; the changed files are unlinked first and written new (a
hard-linked base file is never written through).  SHA256SUMS gets the changed / new rows."""
import argparse
import copy
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

EVENT = "P-Q3VM-2"
TYPE, INST, MOD = "q_hub_nw", "u_hb_coll_Q_vm__q0", "ot_hfd_coll_q3_vm_core"
CE_TAP = "u_hb_coll_Q_vm"
OLD_ENTRY, NEW_ENTRY = [164.16, 358.56], [164.16, 501.12]
E_X, OFF, PITCH = 328.224, 0.024, 0.048
SUFFIX = "__q3vmE"
TAG = (f"DIE-HBM-92-Q3VM {EVENT} (HBM-HARD-6 11-08 04:49): vmasm_rd_il N/M5 -> E/M4 at the as_il partner y; core "
       f"clock entry {OLD_ENTRY} -> {NEW_ENTRY}")


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def repo_root():
    return Path(__file__).resolve().parents[3]


def gen_mod():
    sys.path.insert(0, str(repo_root() / "physical/die_plan/hbm_arch_cores"))
    sys.path.insert(0, str(repo_root() / "tools/die_plan"))
    import gen_core_kit_hbm as G  # noqa: E402
    return G


def move_rd_il(pins, h):
    """vmasm_rd_il -> E face M4 at the as_il partner y (HBM-HARD-6 mk_q3vm_vD.py rule).  Returns (pins, max_dev_um)."""
    pins = copy.deepcopy(pins)
    blocked = set()
    for p in pins:
        if p["layer"] == "M4" and abs(p["x"] - E_X) < 0.01:
            k = round((p["y"] - OFF) / PITCH)
            blocked |= {k - 1, k, k + 1}
    asy = {p["name"]: p["y"] for p in pins if p["name"].startswith("vmasm_as_il[")}
    rd = [p for p in pins if p["name"].startswith("vmasm_rd_il[")]
    if not rd or len(rd) != len(asy):
        raise SystemExit(f"{EVENT}: expected equal rd_il/as_il widths, got {len(rd)}/{len(asy)}")
    partner = lambda p: asy["vmasm_as_il[" + p["name"].split("[", 1)[1]]
    rd.sort(key=partner)
    last, maxdev = -10, 0.0
    for p in rd:
        ty = partner(p)
        k = max(round((ty - OFF) / PITCH), last + 2)
        while k in blocked:
            k += 1
        y = round(OFF + k * PITCH, 4)
        if not 1.0 < y < h - 1.0:
            raise SystemExit(f"{EVENT}: rd_il pin {p['name']} y {y} off the E face")
        maxdev = max(maxdev, abs(y - ty))
        blocked |= {k - 1, k, k + 1}
        last = k
        for key in ("w", "h"):
            p.pop(key, None)
        p["layer"], p["x"], p["y"] = "M4", E_X, y
    return pins, maxdev


def move_entry(ce):
    """clock_entries.json: the module's entries -> NEW_ENTRY.  Returns (new doc, [(type, tap)])."""
    ce = copy.deepcopy(ce)
    hit = []
    for tk, blk in ce.items():
        if not isinstance(blk, dict):
            continue
        for tap, e in blk.items():
            if isinstance(e, dict) and e.get("module") == MOD:
                if [round(v, 4) for v in e["xy_um"]] != OLD_ENTRY:
                    raise SystemExit(f"{EVENT}: {tk}/{tap} entry {e['xy_um']} is not the expected {OLD_ENTRY}")
                e["xy_um"] = list(NEW_ENTRY)
                e["island_um"] = [round(NEW_ENTRY[0] - 4.32, 4), round(NEW_ENTRY[1] - 4.32, 4),
                                  round(NEW_ENTRY[0] + 4.32, 4), round(NEW_ENTRY[1] + 4.32, 4)]
                e["source"] = (e.get("source", "") + " | " + TAG)
                hit.append((tk, tap))
    if hit != [(TYPE, CE_TAP)]:
        raise SystemExit(f"{EVENT}: expected exactly one {MOD} entry at {TYPE}/{CE_TAP}, got {hit}")
    return ce, hit


def apply_plan(P, new_pf):
    """die_plan: repoint the hard_cores row and move the parent clock tap.  Returns (new plan, changed rows)."""
    Q = copy.deepcopy(P)
    t = Q["partition_types"][TYPE]
    rows = [h for h in t["hard_cores"] if h.get("inst") == INST]
    if len(rows) != 1 or rows[0].get("module") != MOD:
        raise SystemExit(f"{EVENT}: {TYPE} needs one hard_cores row {INST} of {MOD}")
    hc = rows[0]
    old_pf = hc["pins_file"]
    hc["pins_file"] = new_pf
    taps = [x for x in t["clock"]["taps"] if x.get("name") == INST]
    if len(taps) != 1:
        raise SystemExit(f"{EVENT}: {TYPE} clock.taps needs one {INST}")
    tp = taps[0]
    ox, oy = hc["origin_um"]
    old_xy = [round(ox + OLD_ENTRY[0], 4), round(oy + OLD_ENTRY[1], 4)]
    if [round(v, 4) for v in tp["xy"]] != old_xy:
        raise SystemExit(f"{EVENT}: tap xy {tp['xy']} != origin + old entry {old_xy}")
    tp["xy"] = [round(ox + NEW_ENTRY[0], 4), round(oy + NEW_ENTRY[1], 4)]
    tp["note"] = tp.get("note", "") + " | " + TAG
    Q["note"] = TAG + " <- " + Q.get("note", "")
    changed = [dict(path=f"partition_types.{TYPE}.hard_cores[inst={INST}].pins_file", old=old_pf, new=new_pf),
               dict(path=f"partition_types.{TYPE}.clock.taps[name={INST}].xy", old=old_xy, new=tp["xy"]),
               dict(path="note", old="<prev chain>", new=TAG + " <- <prev chain>")]
    return Q, changed, hc


def link_tree(src, dst):
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise SystemExit(f"{EVENT}: {dst} exists (never overwrite a plan dir)")
    for root, dirs, files in os.walk(src):
        r = Path(root)
        (dst / r.relative_to(src)).mkdir(parents=True, exist_ok=True)
        for f in files:
            s = r / f
            d = dst / r.relative_to(src) / f
            if s.is_symlink():
                os.symlink(os.readlink(s), d)
            else:
                os.link(s, d)


def write_new(path, data):
    path = Path(path)
    if path.exists() or path.is_symlink():
        path.unlink()           # never write through a hard link into the base dir
    path.write_bytes(data)


def gz(data):
    return gzip.compress(data, mtime=0)


def run(base, out, expect_rd_sha=None):
    base, out = Path(base), Path(out)
    P = json.loads((base / "die_plan.json").read_bytes())
    t = P["partition_types"][TYPE]
    hc0 = next(h for h in t["hard_cores"] if h.get("inst") == INST)
    old_pf = hc0["pins_file"]
    w, h = (float(v) for v in hc0["outline_um"])
    pins0 = json.loads((base / old_pf).read_bytes())
    pins1, maxdev = move_rd_il(pins0, h)
    rd_sha = sha_b((json.dumps(pins1)).encode())
    if expect_rd_sha and not rd_sha.startswith(expect_rd_sha):
        raise SystemExit(f"{EVENT}: rd_il table sha {rd_sha[:8]} != expected {expect_rd_sha}")
    ce1, _ = move_entry(json.loads((base / "clock_entries.json").read_bytes()))
    stem = Path(old_pf).name[: -len(".json")]
    new_pf = str(Path(old_pf).parent / f"{stem}{SUFFIX}.json")
    Q, changed, hc = apply_plan(P, new_pf)

    link_tree(base, out)
    ce_b = (json.dumps(ce1) + "\n").encode()
    write_new(out / "clock_entries.json", ce_b)
    if (base / "clock_entries.json.gz").exists():
        write_new(out / "clock_entries.json.gz", gz(ce_b))
    # clock pin -> the new entry, with the generator's functions (reads OUT_DIR/clock_entries.json)
    G = gen_mod()
    import clock_entry_pins as CEP  # noqa: E402
    m5 = CEP.m5_of(P)
    mv, rec = CEP.entry_pins(out / "clock_entries.json", MOD, pins1, w, h, m5)
    if set(mv) != {"clk"}:
        raise SystemExit(f"{EVENT}: expected the clk pin to move, got {sorted(mv)}")
    clk_old = next([p["x"], p["y"]] for p in pins1 if p["name"] == "clk")
    pins2 = [dict(p, x=mv[p["name"]][0], y=mv[p["name"]][1]) if p["name"] in mv else p for p in pins1]
    pins_b = (json.dumps(pins2) + "\n").encode()
    write_new(out / new_pf, pins_b)
    write_new(out / (new_pf + ".gz"), gz(pins_b))
    plan_b = json.dumps(Q).encode()
    write_new(out / "die_plan.json", plan_b)
    if (base / "die_plan.json.gz").exists():
        write_new(out / "die_plan.json.gz", gz(plan_b))

    old = {p["name"]: p for p in pins0}
    pin_changes = {}
    for p in pins2:
        o = old[p["name"]]
        if o != p:
            pin_changes.setdefault(p["name"].split("[")[0], 0)
            pin_changes[p["name"].split("[")[0]] += 1
    rd = [p for p in pins2 if p["name"].startswith("vmasm_rd_il[")]
    files = {}
    for f in ("die_plan.json", "die_plan.json.gz", "clock_entries.json", "clock_entries.json.gz", new_pf, new_pf + ".gz"):
        if (out / f).exists():
            files[f] = dict(sha_in=sha_b((base / f).read_bytes()) if (base / f).exists() else None,
                            sha_out=sha_b((out / f).read_bytes()))
    rc = dict(schema="opentallas.hbm_plan_event.v1", event=EVENT, lane="DIE-HBM-92-Q3VM", tag=TAG,
              base=str(base), out=str(out), type=TYPE, inst=INST, module=MOD,
              old_pins_file=old_pf, new_pins_file=new_pf,
              rd_il_only_table_sha256=rd_sha, rd_il_max_dev_um=round(maxdev, 4),
              rd_il_y=[min(p["y"] for p in rd), max(p["y"] for p in rd)], pins_changed_by_bus=pin_changes,
              clk_pin=dict(old=clk_old, new=list(mv["clk"])), clock_entry=dict(old=OLD_ENTRY, new=NEW_ENTRY),
              die_plan_rows=changed, files=files, pin_cycles_added=0, internal_stations_changed=0)
    sums = out / "SHA256SUMS"
    if sums.exists():
        keep = [ln for ln in sums.read_text().splitlines() if ln.split("  ", 1)[-1] not in files]
        add = [f"{v['sha_out']}  {k}" for k, v in files.items()]
        write_new(sums, ("\n".join(keep + add) + "\n").encode())
    write_new(out / "q3vmE_1108_event.json", (json.dumps(rc, indent=1) + "\n").encode())
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--expect-rd-sha", default=None, help="sha256 prefix of the rd_il-only table (HBM-HARD-6 b2c55e78)")
    a = ap.parse_args(argv)
    rc = run(a.base, a.out, a.expect_rd_sha)
    print(json.dumps({k: rc[k] for k in ("event", "new_pins_file", "rd_il_only_table_sha256", "pins_changed_by_bus",
                                          "clk_pin", "die_plan_rows")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
