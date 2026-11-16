import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ext_source_check as E  # noqa: E402


def test_internal_and_bind_paths_pass_external_fail(tmp_path):
    tree = tmp_path / "srv" / "tree"
    bind = tmp_path / "srv" / "bind"
    tree.mkdir(parents=True)
    bind.mkdir(parents=True)
    ok = bind / "bind.f"
    ok.write_text(f"/srv/x\n")
    assert E.main(["--allow", "/srv/x", str(bind)]) == 0
    ok.write_text("/srv/x/rtl/a.sv\n/srv/old/wt/qc-s29-tree2/rtl/b.sv\n")
    (bind / "m.json").write_text(json.dumps({"files": ["/srv/old/wt/qc-s29-tree2/rtl/c.sv"]}))
    cnt, ex, missing = E.scan(["/srv/x"], [str(bind)])
    assert sum(cnt.values()) == 2 and len(missing) == 2
    assert E.main(["--allow", "/srv/x", str(bind)]) == 1
    assert E.main(["--allow", "/srv/x", "--allow", "/srv/old/wt/qc-s29-tree2", str(bind)]) == 0


def test_prefix_is_a_path_boundary(tmp_path):
    (tmp_path / "a.f").write_text("/srv/tree2/rtl/a.sv\n")
    assert E.main(["--allow", "/srv/tree", str(tmp_path)]) == 1
