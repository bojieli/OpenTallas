"""DIE-HBM-92-SU-IDX 11-08: hb_idx h0 split manifest = second substitute per HALF leaf + sub_core_leaf from t5_map."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
import hbm_split_idx_asbuilt as S

REPO = Path(__file__).resolve().parents[2]
LEAF = "hb_idx__s_{q}.scorer.ge[0].gc[0].leaf.core.g_col[{k}].g_half[0].u_hc"


def fixture(sides=("SW", "SE")):
    hcs = []
    for k in range(2):
        p = f"u_hb_idx__s_Q2_r0c0_k{k}h0"
        hcs += [dict(inst=p + "__ra", module=S.H0 + "_ra", physical_inst=p + ".u_fcore.u_core.u_ra"),
                dict(inst=p + "__rb", module=S.H0 + "_rb", physical_inst=p + ".u_fcore.u_core.u_rb"),
                dict(inst=f"u_hb_idx__s_Q2_r0c0_k{k}h1", module="ot_hbm_idx_score_hcol_h1")]
    plan = {"partition_types": {"q_b000": {"hard_cores": hcs}}}
    rx = lambda q, k: LEAF.format(q=q, k=k).replace(".", r"\.").replace("[", r"\[").replace("]", r"\]")
    sub = [dict(inst=rx(q, k), module=S.H0, reason="HALF") for q in ("SW", "SE") for k in range(2)]
    ab = {"files": [], "prefer": [], "substitute_inst": sub, "sub_core_leaf": {}, "sub_core_leaf_variants": {}}
    tmap = {"parts": {LEAF.format(q=q, k=k): [q[0] + "_b000", f"u_hb_idx__s_Q2_r0c0_k{k}h0"]
                      for q in sides for k in range(2)}}
    return plan, ab, tmap


def test_second_substitute_and_leaves(tmp_path):
    plan, ab, tmap = fixture()
    out = S.candidate(plan, ab, tmap, REPO, tmp_path / "st")
    assert ab["substitute_inst"] == fixture()[1]["substitute_inst"]          # base untouched
    rules = out["substitute_inst"]
    assert [r["module"] for r in rules] == [S.H0] * 4 + [S.GLUE] * 4    # HALF rules first, kept as they were
    assert sorted(r["inst"] for r in rules[4:]) == sorted(r["inst"] for r in rules[:4])
    p = "u_hb_idx__s_Q2_r0c0_k1h0"
    assert out["sub_core_leaf"][p] == LEAF.format(q="SE", k=1)
    assert out["sub_core_leaf_variants"][p] == [LEAF.format(q="SW", k=1)]
    glue = (tmp_path / "st" / (S.GLUE + ".sv")).read_text()
    assert "cs_in" not in glue.split("__split (")[1].split(");")[0]          # glue ports = as-built h0 ports
    assert f"{S.H0}_ra u_ra" in glue and f"{S.H0}_rb u_rb" in glue and "always" not in glue
    assert all(f in out["files"] and f in out["prefer"] for f in map(str, (tmp_path / "st").iterdir()))


def test_missing_mirror_leaf_fails(tmp_path):
    plan, ab, tmap = fixture(sides=("SW",))
    with pytest.raises(ValueError, match="mirrored"):
        S.candidate(plan, ab, tmap, REPO, tmp_path / "st")


def test_parent_needs_both_halves(tmp_path):
    plan, ab, tmap = fixture()
    plan["partition_types"]["q_b000"]["hard_cores"] = [h for h in plan["partition_types"]["q_b000"]["hard_cores"]
                                                       if not h["inst"].endswith("k0h0__rb")]
    with pytest.raises(ValueError, match="both ra and rb"):
        S.candidate(plan, ab, tmap, REPO, tmp_path / "st")
