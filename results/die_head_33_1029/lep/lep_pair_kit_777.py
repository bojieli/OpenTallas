#!/usr/bin/env python3
"""DIE-HEAD-33 (2026-10-29): lep_pair hard-core kit at the COORD-admitted 777.6 x 492.48 outline (HEAD-013, COORD 07:52 +
17:30 ruling 3).  Die-local driver around main tools/s81_head/head_lep_pair_kit.py (no shared-code edit):

  * plan copy = src25m (a7435da4) with ONLY the 4 hd_lep0N ot_s81hd_lep_pair hard cores set to 777.6 x 492.48 and
    pins_file -> lep_pair_pins_777.json (the kit reads the core outline + pin view from the plan; the parent placement
    of the 4 pairs is the separate lep0N plan event, see README);
  * pin view = lep_pair_pins_777.json (Codex LEP V5 head_lep_child_resize.py: same rule as tools/s81_head/
    head_lep_pair_pins.py -- W coll_i M4 / coll_o M6, S K-side in M5 / out M7, centre M5 rst_n; 2141 pins);
  * SRAM sites = lep_pair_child_v5.json child_type.contents (the 55 sites of Codex LEP V5 at 777.6 x 492.48) instead of
    head_lep_pair_kit.sram_sites (hard-coded for 388.8 x 432).

    python3 lep_pair_kit_777.py SRC_PLAN OUT_PLAN_DIR KITROOT [-- extra gen_core_kit_hbm args]
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools/s81_head"))
import head_lep_pair_kit as K  # noqa: E402

W_UM, H_UM = 777.6, 492.48
CHILD = HERE / "lep_pair_child_v5.json"
PINS = HERE / "lep_pair_pins_777.json"


def plan_copy(src, out_dir):
    p = json.loads(Path(src).read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cores").mkdir(exist_ok=True)
    shutil.copyfile(PINS, out_dir / "cores/lep_pair_pins_777.json")
    n = 0
    for hc in p["partition_types"]["hd_lep0N"]["hard_cores"]:
        if hc["module"] == K.MODULE:
            hc["outline_um"] = [W_UM, H_UM]
            hc["pins_file"] = "cores/lep_pair_pins_777.json"
            n += 1
    assert n == 4, n
    f = out_dir / "plan_lep_pair_kitview.json"
    f.write_text(json.dumps(p, indent=1) + "\n")
    return f


def main():
    src, out_plan, kit = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    rest = sys.argv[4:]
    if rest and rest[0] == "--":
        rest = rest[1:]
    plan = plan_copy(src, out_plan)
    K.DELTA = str(CHILD)          # Path(ROOT / abs) == abs
    sites = {c["inst"]: list(c["origin_um"]) for c in json.loads(CHILD.read_text())["child_type"]["contents"]
             if c.get("kind") == "sram"}
    if len(sites) != 55:
        raise SystemExit(f"expected 55 V5 SRAM sites, got {len(sites)}")

    def sram_sites(srams, w, h):
        if [float(w), float(h)] != [W_UM, H_UM]:
            raise SystemExit("outline mismatch")
        return {c["inst"]: sites[c["inst"]] for c in srams}
    K.sram_sites = sram_sites
    # main d379a4b741c reformatted the core face_guard call (straps/dead kwargs), so the exact-string hook in
    # head_lep_pair_kit.main no longer matches.  Show the hook the old one-line form, let it append the same land=
    # declaration, and write the file back with the current straps/dead kwargs kept.
    new = ('r = FG.guard(Path(net).read_text(), fz["design"], skip_re=skip, pins=pins,\n'
           '                 straps=FG.kit_strap_list(kd), dead=FG.kit_dead_list(kd))')
    old = 'r = FG.guard(Path(net).read_text(), fz["design"], skip_re=skip, pins=pins)'
    land = ', land=FG.kit_land(kd / "land_slots.json"))'
    rt, wt = Path.read_text, Path.write_text

    def read_text(self, *a, **k):
        t = rt(self, *a, **k)
        return t.replace(new, old) if self.name == "face_guard_core.py" else t

    def write_text(self, data, *a, **k):
        if self.name == "face_guard_core.py":
            data = data.replace(old[:-1] + land, new[:-1] + land)
            if "land=FG.kit_land" not in data or "dead=FG.kit_dead_list" not in data:
                raise SystemExit("face_guard_core land hook not applied")
        return wt(self, data, *a, **k)
    Path.read_text, Path.write_text = read_text, write_text
    sys.argv = ["head_lep_pair_kit.py", "--out", kit, "--plan", str(plan)] + (["--"] + rest if rest else [])
    K.main()


if __name__ == "__main__":
    main()
