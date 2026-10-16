"""Actual S81F03 W->E source snapshots and S81F14 same-face negative controls."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closed_stands as CS
import custom_io_faces as IO

CASES = json.loads((HERE / "testdata/custom_io_faces/s81_f03_f14.json").read_text())["cases"]


class Store:
    def __init__(self, case):
        self.snapshots = copy.deepcopy(case["snapshots"])
        self.objects = {s["commit"]: s for s in self.snapshots.values()}

    def show(self, commit, path):
        return self.objects[commit]["files"].get(path)

    def blob(self, commit, path):
        if path == "":
            return "fixture-tree-" + commit
        return self.objects[commit]["blobs"].get(path)

    def check(self):
        old = self.snapshots["old"]
        new = self.snapshots["new"]
        job = dict(name=old["job"]["name"], status="CLOSED", spec=old["job"], commit_full=old["commit"],
                   publish={"branch_commit": "fixture-source-published"}, finished_at="2026-10-16T00:00:00-07:00")
        return CS.check(new["job"], new["job"]["name"], [job], self.show, self.blob)


class ActualSourceGate(unittest.TestCase):
    def test_actual_f03_west_to_east_is_a_real_face_change(self):
        for case in CASES[:3]:
            with self.subTest(master=case["master"]):
                result = Store(case).check()
                self.assertEqual(result["verdict"], "PASS", result)
                evidence = next(iter(result["facts"]["custom_io_face_comparisons"].values()))
                self.assertEqual(evidence["status"], "changed")
                self.assertEqual(evidence["changed_pins"], 126)
                self.assertEqual(set(map(tuple, evidence["examples"].values())), {("W", "E")})
                self.assertIn("sha256", evidence["new"])
                self.assertEqual(result["facts"]["rtl"], "same")

    def test_actual_f14_centering_keeps_closed_view_standing(self):
        for case in CASES[3:]:
            with self.subTest(master=case["master"]):
                result = Store(case).check()
                self.assertEqual(result["verdict"], "REFUSE", result)
                self.assertIn("outline and pin faces", result["message"])

    def test_coordinate_layer_order_and_path_changes_are_not_faces(self):
        store = Store(CASES[0])
        old, new = store.snapshots["old"], store.snapshots["new"]
        new_kit = next(p for p in new["files"] if p.endswith("kit.env"))
        old_kit = next(p for p in old["files"] if p.endswith("kit.env"))
        old_io = IO.read(old["files"][old_kit], old["commit"], store.show)
        new_io = IO.read(new["files"][new_kit], new["commit"], store.show)
        # Keep the candidate's distinct source path, change only literal position,
        # layer and statement order on the original faces.
        text = old["files"][old_io["source"]].replace("35.388000", "35.400000").replace("-layer M4", "-layer M2")
        new["files"][new_io["source"]] = "\n".join(reversed(text.splitlines())) + "\n"
        result = store.check()
        self.assertEqual(result["verdict"], "REFUSE", result)
        evidence = next(iter(result["facts"]["custom_io_face_comparisons"].values()))
        self.assertEqual(evidence["status"], "same")

    def test_missing_current_or_historical_source_fails_closed(self):
        for side in ("new", "old"):
            for remove in ("tcl", "kit.env"):
                with self.subTest(side=side, remove=remove):
                    store = Store(CASES[0])
                    files = store.snapshots[side]["files"]
                    del files[next(p for p in files if p.endswith(remove))]
                    result = store.check()
                    self.assertEqual(result["verdict"], "REFUSE", result)
                    self.assertRegex(result["message"], "unverified|unreadable|readable source-pinned")

    def test_partial_or_renamed_pin_maps_cannot_prove_changed_faces(self):
        for mutate in (lambda text: text.replace("{a[0]}", "{not_the_same_pin}"),
                       lambda text: "\n".join(line for line in text.splitlines() if "{a[0]}" not in line)):
            store = Store(CASES[0])
            new = store.snapshots["new"]
            path = next(p for p in new["files"] if p.endswith(".tcl"))
            new["files"][path] = mutate(new["files"][path])
            self.assertEqual(store.check()["verdict"], "REFUSE")

    def test_dynamic_or_ambiguous_statements_are_not_evaluated(self):
        additions = ["source other.tcl", "set x [exec false]", "place_pin -pin_name {a[0]} -layer M4 -location {$x 4} -force_to_die_boundary",
                     "place_pin -pin_name {new} -layer M4 -location {0 0} -force_to_die_boundary",
                     "place_pin -pin_name {a[0]} -layer M4 -location {43.056 4} -force_to_die_boundary",
                     "# comment continuation \\"]
        for extra in additions:
            with self.subTest(extra=extra):
                store = Store(CASES[0])
                new = store.snapshots["new"]
                path = next(p for p in new["files"] if p.endswith(".tcl"))
                new["files"][path] += extra + "\n"
                self.assertEqual(store.check()["verdict"], "REFUSE")

    def test_nonliteral_region_rules_cannot_establish_a_face_change(self):
        for pins in ("(--pin-region '^.*=left')", "(--pin-region '^(a)(\\[|$)=$FACE')",
                     "(--pin-region '^(a)(\\[|$)=left' --pin-region '^(a)(\\[|$)=right')"):
            with self.subTest(pins=pins):
                store = Store(CASES[3])
                new = store.snapshots["new"]
                path = next(p for p in new["files"] if p.endswith("kit.env"))
                new["files"][path] = re.sub(r"^PINS=.*$", lambda _: "PINS=" + pins, new["files"][path], flags=re.M)
                result = store.check()
                self.assertEqual(result["verdict"], "REFUSE", result)
                self.assertIn("pin regions are unverified", result["message"])

    def test_dynamic_custom_source_path_is_not_a_git_object(self):
        store = Store(CASES[0])
        new = store.snapshots["new"]
        path = next(p for p in new["files"] if p.endswith("kit.env"))
        new["files"][path] = new["files"][path].replace("IO_CONSTRAINTS=/src/", "IO_CONSTRAINTS=$ROOT/")
        self.assertEqual(store.check()["verdict"], "REFUSE")

    def test_conflicting_custom_and_generic_geometry_is_ambiguous(self):
        store = Store(CASES[0])
        new = store.snapshots["new"]
        path = next(p for p in new["files"] if p.endswith("kit.env"))
        new["files"][path] = new["files"][path].replace("PINS=()", "PINS=(--pin-region '^(a)(\\[|$)=left')")
        self.assertEqual(store.check()["verdict"], "REFUSE")

    def test_dropping_a_generic_region_does_not_prove_a_new_face(self):
        store = Store(CASES[3])
        new = store.snapshots["new"]
        path = next(p for p in new["files"] if p.endswith("kit.env"))
        new["files"][path] = re.sub(r"^PINS=.*$", lambda _: "PINS=(--pin-region '^(i|o)(\\[|$)=right')",
                                  new["files"][path], flags=re.M)
        self.assertEqual(store.check()["verdict"], "REFUSE")

    def test_literal_custom_io_outline_changes_remain_supported(self):
        store = Store(CASES[0])
        old, new = store.snapshots["old"], store.snapshots["new"]
        path = next(p for p in new["files"] if p.endswith("kit.env"))
        old_path = next(p for p in old["files"] if p.endswith("kit.env"))
        # Preserve the OLD faces, grow the real outline, and move its E-face
        # pins onto the new boundary. The outline itself is a supported change.
        old_io = IO.read(old["files"][old_path], old["commit"], store.show)
        new_io = IO.read(new["files"][path], new["commit"], store.show)
        new["files"][path] = new["files"][path].replace("FW=43.2\n", "FW=45.36\n")
        new["files"][new_io["source"]] = old["files"][old_io["source"]].replace("43.056000", "45.216000")
        result = store.check()
        self.assertEqual(result["verdict"], "PASS", result)

    def test_actual_kit_layer_and_exclusion_only_changes_do_not_justify_reroute(self):
        for key, value in (("PIN_H", "'M2'"), ("PIN_V", "'M3'"), ("PINEX", "0")):
            with self.subTest(key=key):
                store = Store(CASES[3])
                old, new = store.snapshots["old"], store.snapshots["new"]
                old_path = next(p for p in old["files"] if p.endswith("kit.env"))
                new_path = next(p for p in new["files"] if p.endswith("kit.env"))
                text, count = re.subn(r"^" + key + r"=.*$", lambda _: key + "=" + value,
                                      old["files"][old_path], flags=re.M)
                self.assertEqual(count, 1)
                self.assertNotEqual(text, old["files"][old_path])
                new["files"][new_path] = text
                result = store.check()
                self.assertEqual(result["verdict"], "REFUSE", result)
                self.assertIn("outline and pin faces equal", result["message"])

    def test_missing_closed_outline_fields_fail_closed_for_ref_tile(self):
        store = Store(CASES[3])
        old = store.snapshots["old"]
        path = next(p for p in old["files"] if p.endswith("kit.env"))
        old["files"][path] = re.sub(r"^FW=.*$", "", old["files"][path], flags=re.M)
        result = store.check()
        self.assertEqual(result["verdict"], "REFUSE", result)
        self.assertIn("outline geometry", result["message"])

    def test_outline_numeric_formatting_is_not_a_physical_change(self):
        store = Store(CASES[3])
        old, new = store.snapshots["old"], store.snapshots["new"]
        old_path = next(p for p in old["files"] if p.endswith("kit.env"))
        new_path = next(p for p in new["files"] if p.endswith("kit.env"))
        new["files"][new_path] = old["files"][old_path].replace("FW=15.12\n", "FW=15.12000\n")
        self.assertEqual(store.check()["verdict"], "REFUSE")

    def test_non_ref_tile_legacy_behavior_is_outside_this_repair(self):
        store = Store(CASES[3])
        new = store.snapshots["new"]
        new["job"]["ref_tile"] = False
        del new["files"][next(p for p in new["files"] if p.endswith("kit.env"))]
        result = store.check()
        self.assertEqual(result["verdict"], "PASS", result)
        self.assertIn("not verifiable", result["message"])


if __name__ == "__main__":
    unittest.main()


def test_place_pin_with_pin_size_is_literal():
    # S-NET+FILL 2026-10-16: tools/ref_tile/spread_face_pins.py writes -pin_size before -force_to_die_boundary
    import custom_io_faces as C
    line = "place_pin -pin_name {do0[0]} -layer M3 -location {4.365 25.920} -pin_size {0.018 0.144} -force_to_die_boundary"
    m = C.PLACE.fullmatch(line)
    assert m and m.group('pin') == 'do0[0]' and m.group('layer') == 'M3'
    assert C.PLACE.fullmatch(line.replace('-pin_size {0.018 0.144}', '-pin_size {0.018}')) is None
