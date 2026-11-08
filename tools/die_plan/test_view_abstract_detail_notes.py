"""Every committed view LEF with an <name>.abstract_detail.json note matches that note (sha) and keeps its
signed pins: the note's base_sha256 view and the current LEF have the same header/PIN section, and the
replaced layers are exactly the note's layers_detailed (S81-XRT3-VIEW-1, xrt_rfj_1104 xrt1/xrt3)."""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import abstract_detail as A

REPO = HERE.parents[1]
VIEWS = REPO / "physical/die_plan/s81/cores/views/xrt_rfj_1104"


def _notes():
    return sorted(VIEWS.glob("*/*.abstract_detail.json"))


def test_xrt_rfj_notes_present():
    names = {p.parent.name for p in _notes()}
    assert {"ot_s81sl_xrt1", "ot_s81sl_xrt3"} <= names


def test_note_matches_lef_and_blanket_lower_layers_kept():
    for note in _notes():
        d = json.loads(note.read_text())
        lef = note.parent / d["out"]
        assert hashlib.sha256(lef.read_bytes()).hexdigest() == d["out_sha256"], lef
        assert d["check_ok"] and d["detail_pins_equal_base"] and not d["problems"]
        assert d["pin_clear_um"] is None and d["not_modeled"].startswith("none")
        lines = lef.read_text().splitlines(keepends=True)
        size = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", "".join(lines)).groups()
        _, body, _ = A._split(lines)
        groups = dict((l, g) for l, g in A._obs_by_layer(body))
        for layer in ("M1", "M2", "M3", "M4"):
            rects = [g for g in groups[layer] if g.strip()]
            assert len(rects) == 1 and rects[0].split()[1:5] == ["0", "0", size[0], size[1]], (lef, layer)
        for layer in d["layers_detailed"]:
            assert len(groups.get(layer, [])) == d["rects"][layer] > 1000, (lef, layer)
