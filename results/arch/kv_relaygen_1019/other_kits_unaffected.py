#!/usr/bin/env python3
"""KV-RELAYGEN 2026-10-19: prove that every OTHER kit is unaffected by the reset-relay-copy change.

For every kit spec on REV (physical/ref_tile/*/spec.json and tools/ref_tile/specs*/**.json): (1) none carries the new opt-in
keys (reset_relay_split, reset_landing.copies, face_land.reset_copies); (2) the new ref_tile.reset_landing_plan() equals
the BASE ref_tile's on it and reset_relay_split_vars() is empty; (3) for face_land specs, the new face_land.wrapper()
equals the BASE one on a synthetic port list.  ot_keep_regs.tcl / ot_pin_regs.tcl change only under OT_RST_SPLIT_MAX /
OT_RST_LAND_COPIES, which ref_tile emits only for (1).
usage: other_kits_unaffected.py REPO REV BASE_REV [SPEC_REV]
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

repo, rev, base = sys.argv[1:4]
spec_rev = sys.argv[4] if len(sys.argv) > 4 else rev   # the kit specs to judge (default REV)
git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout


def load(mod, rv, td):
    """the module as of REV, materialised next to the live tools/ref_tile (same imports / data files); removed after"""
    tag = rv.replace("/", "_").replace("-", "_").replace(".", "_")
    dst = Path(repo) / "tools/ref_tile" / f"_kvrg_{tag}_{mod}.py"
    dst.write_text(git("show", f"{rv}:tools/ref_tile/{mod}.py"))
    TMP.append(dst)
    sys.path[:0] = [str(Path(repo) / "tools/ref_tile"), str(Path(repo) / "tools"), str(Path(repo) / "tools/hier_contract")]
    spec = importlib.util.spec_from_file_location(dst.stem, dst)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


TMP = []
try:
  with tempfile.TemporaryDirectory() as td:
      new_rt, old_rt = load("ref_tile", rev, td), load("ref_tile", base, td)
      new_fl, old_fl = load("face_land", rev, td), load("face_land", base, td)
      files = [f for f in git("ls-tree", "-r", "--name-only", spec_rev, "--", "physical/ref_tile", "tools/ref_tile").splitlines()
               if f.endswith(".json") and (f.endswith("/spec.json") or "/specs" in f)]
      n = keyed = rl = fl = bad = 0
      for f in files:
          try:
              s = json.loads(git("show", f"{spec_rev}:{f}"))
          except Exception:
              continue
          if not isinstance(s, dict) or "top" not in s:
              continue
          n += 1
          rlr = s.get("reset_landing") if isinstance(s.get("reset_landing"), dict) else {}
          flr = s.get("face_land") if isinstance(s.get("face_land"), dict) else {}
          if "reset_relay_split" in s or "copies" in rlr or "reset_copies" in flr:
              keyed += 1
              print(f"OPT-IN {f}")
              continue
          if rlr:
              try:
                  a = old_rt.reset_landing_plan(s)
              except Exception as ex:
                  a = f"ERR {ex}"
              try:
                  b = new_rt.reset_landing_plan(s)
              except Exception as ex:
                  b = f"ERR {ex}"
              rl += 1
              if a != b or new_rt.reset_relay_split_vars(s):
                  bad += 1
                  print(f"DIFF reset_landing {f}")
          if flr:
              fl += 1
              pl = [("input", "", flr.get("clock", "ck")), *[("input", "", r) for r in flr.get("reset_ports", [])],
                    *[("input", "[7:0]", p) for p in flr.get("land", {})], ("output", "[3:0]", "q")]
              ck = flr.get("clock", "ck")
              if old_fl.wrapper(flr, pl, ck) != new_fl.wrapper(flr, pl, ck):
                  bad += 1
                  print(f"DIFF face_land {f}")
      print(f"OTHER_KITS specs={n} opt_in={keyed} reset_landing_compared={rl} face_land_compared={fl} diffs={bad}")
      print("OTHER_KITS PASS" if bad == 0 else "OTHER_KITS FAIL")
      sys.exit(1 if bad else 0)
finally:
    for f in TMP:
        f.unlink(missing_ok=True)
sys.exit(rc)
