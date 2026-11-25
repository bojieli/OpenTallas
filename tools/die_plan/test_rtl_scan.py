"""BIND-SPEED-1124 #2: the shared per-file RTL scan memo (rtl_scan.py) returns exactly what the readers computed before"""
import os
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bind_elab as E  # noqa: E402
import bind_strict_src as SS  # noqa: E402
import rtl_scan as RS  # noqa: E402
import view_define_check as V  # noqa: E402

SRC = {
    "rtl/a/top.sv": "// module fake\nmodule top #(parameter W = 4) (input x);\n`ifdef FAST\n  leaf #(.W(W)) u_l (.a(x));\n`endif\n"
                    "endmodule\n/* module also_fake */\nmodule top2; leaf u2 (); endmodule\n",
    "rtl/a/leaf.sv": "`ifndef SLOW\nmodule leaf #(parameter W = 1, parameter D = 2) (input a);\n`elsif X\n`endif\nendmodule\n",
    "rtl/b/none.v": "// nothing here\n",
    "rtl/b/x_bb.v": "module xbb; endmodule\n",
    "rtl/b/tb/tb_top.sv": "module tb_top; top u (); endmodule\n",
}


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_RTL_SCAN_CACHE", str(tmp_path / "cache"))
    RS._MEM.clear()
    for rel, text in SRC.items():
        p = tmp_path / "base" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path / "base"


def _old_module_index(roots, files, base):
    idx = {}
    paths = []
    for r in roots:
        rp = Path(base) / r
        disc = []
        for d, subs, names in os.walk(rp):
            subs[:] = [s for s in subs if s not in E.AUTO_OUTPUT_DIRS]
            disc += [Path(d) / n for n in names if Path(n).suffix in (".sv", ".v") and not E.SKIP_DIR.search(str(Path(d) / n))]
        paths += sorted(disc)
    paths += [Path(base) / f for f in files]
    for p in paths:
        t = p.read_text(errors="replace")
        if "module" not in t:
            continue
        for m in E.MOD_RE.finditer(E._strip(t)):
            idx.setdefault(m.group(1), [])
            if str(p) not in idx[m.group(1)]:
                idx[m.group(1)].append(str(p))
    return idx


def _old_rtl_index(base):
    mod, info = {}, {}
    root = Path(base) / "rtl"
    for f in sorted(list(root.rglob("*.sv")) + list(root.rglob("*.v"))):
        if f.name.endswith("_bb.v") or f.name.endswith("_bb.sv"):
            continue
        text = V.COMMENT.sub(" ", f.read_text(errors="replace"))
        top = set(V.COND.findall(V.BODY.sub(" ", text)))
        for b in V.BODY.finditer(text):
            if b.group(1) in mod:
                continue
            key = "%s::%s" % (f, b.group(1))
            mod[b.group(1)] = key
            info[key] = (set(V.COND.findall(b.group(2))) | top, set(V.WORD.findall(b.group(2))))
    return mod, info


@pytest.mark.parametrize("cache", ["disk", "off"])
def test_readers_equal_the_old_scans_cold_warm_and_from_disk(tree, monkeypatch, cache):
    if cache == "off":
        monkeypatch.setenv("OT_RTL_SCAN_CACHE", "0")
    ref_mi = _old_module_index(["rtl"], ["rtl/a/leaf.sv"], tree)
    ref_ri = _old_rtl_index(tree)
    for _ in range(2):                                  # cold, then in-process memo
        assert E.module_index(["rtl"], ["rtl/a/leaf.sv"], tree) == ref_mi
        assert V.rtl_index(tree) == ref_ri
    RS._MEM.clear()                                     # a new process: disk hits (or recompute when off)
    assert E.module_index(["rtl"], ["rtl/a/leaf.sv"], tree) == ref_mi
    assert V.rtl_index(tree) == ref_ri
    if cache == "disk":
        assert any((tree.parent / "cache").rglob("*.pkz"))
    else:
        assert not (tree.parent / "cache").exists()


def test_rewritten_file_is_rescanned(tree):
    p = tree / "rtl/a/leaf.sv"
    assert "leaf" in E.module_index(["rtl"], [], tree)
    st = p.stat()
    p.write_text(SRC["rtl/a/leaf.sv"].replace("module leaf", "module leaf2"))
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))     # same mtime (cp -p / touch -r): ctime still moves
    idx = E.module_index(["rtl"], [], tree)
    assert "leaf2" in idx and "leaf" not in idx


def test_values_are_fresh_objects(tree):
    f = tree / "rtl/a/leaf.sv"
    a = RS.scan("t.defs", f, SS.definitions)
    a["leaf"].add("MUTATED")
    assert RS.scan("t.defs", f, SS.definitions) == SS.definitions(f.read_text())


def test_strict_src_check_unchanged(tree):
    files = [str(tree / "rtl/a/leaf.sv")]
    em = [str(tree / "rtl/a/top.sv")]
    errs, _ = SS.check(files, files, [], em, [], [tree])
    assert errs == []
    (tree / "rtl/a/top.sv").write_text(SRC["rtl/a/top.sv"].replace(".W(W)", ".Q(W)"))
    errs, _ = SS.check(files, files, [], em, [], [tree])
    assert [e.split()[0] for e in errs] == ["BIND_PARAM_UNKNOWN"] and "parameter Q" in errs[0]


def test_missing_file_raises_oserror_like_read_text(tree):
    with pytest.raises(OSError):
        RS.scan("t.x", tree / "nope.sv", len)


def test_torn_cache_entry_is_a_miss(tree):
    f = tree / "rtl/a/leaf.sv"
    RS.scan("t.n", f, E._module_names)
    for c in (tree.parent / "cache").rglob("*.pkz"):
        c.write_bytes(b"torn")
    RS._MEM.clear()
    assert RS.scan("t.n", f, E._module_names) == ["leaf"]
    assert re.search(r"misses", repr(RS.STATS))
