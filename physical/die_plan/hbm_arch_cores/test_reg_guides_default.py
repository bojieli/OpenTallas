"""DIE-HBM-97 KVPIPE rev3: gen_core_kit_hbm.default_reg_guides picks up reg_guides/<module>.json (committed plan guide
boxes) and fails closed on a stale outline; the kv_line boxes pass reg_guide_boxes_spec (inside the core, disjoint,
no nesting prefixes) and sit in the north logic strip clear of the bank macros, one per bank column."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_hbm as G  # noqa: E402

KVL = "ot_hbm_sm_kv_line"
BANKS_X = [(8.64, 179.928), (188.568, 359.856), (368.496, 539.784), (548.424, 719.712)]
BANK_TOP_Y = 172.836


def test_kv_line_guides_found_and_valid():
    f = G.default_reg_guides(KVL, (734.4, 233.28))
    assert f and Path(f).name == f"{KVL}.json"
    m = G.CORE_MARGIN_UM
    rgb = G.reg_guide_boxes_spec(json.load(open(f))["boxes"], (m, m, 734.4 - m, 233.28 - m))
    assert [g["prefixes"] for g in rgb] == [[f"u_fcore.g_col[{c}]."] for c in range(4)]
    for c, g in enumerate(rgb):
        x0, y0, x1, y1 = g["box_um"]
        assert y0 > BANK_TOP_Y                                   # north strip: no macro inside the box
        bx0, bx1 = BANKS_X[c]
        assert x0 <= bx0 + 5 and x1 >= bx1 - 5                    # the box spans its own bank column


def test_no_file_is_none(tmp_path):
    assert G.default_reg_guides("ot_no_such_module", (10.0, 10.0), d=tmp_path) is None


def test_stale_outline_fails_closed():
    with pytest.raises(SystemExit):
        G.default_reg_guides(KVL, (734.4, 240.0))


def test_wrong_module_fails_closed(tmp_path):
    (tmp_path / "x.json").write_text(json.dumps(dict(schema=G.REG_GUIDES_SCHEMA, module="y", outline_um=[1, 1], boxes=[])))
    with pytest.raises(SystemExit):
        G.default_reg_guides("x", (1, 1), d=tmp_path)
