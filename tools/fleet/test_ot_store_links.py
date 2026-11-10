"""KW-FIX-44 COORD 19:3x: ot_store keeps relative in-tree links and absolute links resolving inside the tree (stored
relative); a link that leaves the tree (absolute or relative) is refused."""
import json
import os
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

S = SourceFileLoader("ot_store", str(Path(__file__).with_name("ot_store.py"))).load_module()


def tree(store, sha):
    return S.read_tree(str(store), sha)


def test_absolute_inside_link_is_kept_as_relative(tmp_path):
    root, store = tmp_path / "W", tmp_path / "store"
    (root / "prov" / "plan").mkdir(parents=True)
    (root / "plandir").mkdir()
    (root / "prov" / "plan" / "README").write_text("r")
    (root / "plandir" / "README.md").symlink_to(root / "prov" / "plan" / "README")      # absolute, inside
    (root / "plandir" / "rel").symlink_to("../prov/plan/README")                         # relative, inside
    store.mkdir()
    t = tree(store, S.put_tree(str(store), str(root)))
    assert t["links"]["plandir/README.md"] == "../prov/plan/README"
    assert t["links"]["plandir/rel"] == "../prov/plan/README"


@pytest.mark.parametrize("target", ["/etc/hostname", "../../outside"])
def test_link_leaving_the_tree_is_refused(tmp_path, target):
    root, store = tmp_path / "W", tmp_path / "store"
    (root / "a").mkdir(parents=True)
    store.mkdir()
    (root / "a" / "x").symlink_to(target)
    with pytest.raises(S.StoreError, match="leaves the tree"):
        S.put_tree(str(store), str(root))


def test_absolute_link_to_sibling_with_common_prefix_is_refused(tmp_path):
    root, store = tmp_path / "W", tmp_path / "store"
    (root).mkdir()
    (tmp_path / "W2").mkdir()
    store.mkdir()
    (root / "x").symlink_to(tmp_path / "W2" / "f")
    with pytest.raises(S.StoreError, match="leaves the tree"):
        S.put_tree(str(store), str(root))
