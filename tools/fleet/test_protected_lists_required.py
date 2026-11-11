"""AUTOCLEAN-12 11-10 (COORD): the 3 protected lists are REQUIRED in ot-autoclean and ot-lifecycle.
usage: python3 -I test_protected_lists_required.py OT_AUTOCLEAN.py OT_LIFECYCLE.py"""
import importlib.util, os, shutil, sys, tempfile
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
oa = load("otac", sys.argv[1])
ROOT = "/srv/opentallas-scratch3/claude/kw24-wave-1106/runs/s81/kit-wave"
LISTS = {"lanes/PROTECTED-DBS.txt": "epyc2\t/srv/opentallas-scratch2/claude/a/db\n" + "".join(f"any\t/srv/opentallas-scratch2/claude/p{i}/x\n" for i in range(300)),
         "PROTECTED-DBS.txt": "".join(f"intel1\t/srv/opentallas-scratch2/claude/q{i}/y\n" for i in range(300)),
         "lanes/prune/ARCHIVE-PROTECTED.tsv": f"# hdr\nany\t{ROOT}\tCOORD 20:0x kit_wave.json live input\nepyc7\t/srv/opentallas-scratch2/claude/wt/kw-fix-4-s81h10\tx\n"}
def coord(skip=None, empty=None, unreadable=None):
    c = tempfile.mkdtemp()
    for f, t in LISTS.items():
        os.makedirs(os.path.dirname(os.path.join(c, f)), exist_ok=True)
        if f == skip: continue
        open(os.path.join(c, f), "w").write("# only a comment\n" if f == empty else t)
        if f == unreadable: open(os.path.join(c, f), "wb").write(b"any\t/srv/x\xff\xfe\n")
    return c
n = 0
oa.REFUSE_LOG = os.path.join(tempfile.mkdtemp(), "refused.log")
# 1. all three present (optional RETIRED absent): union holds the ARCHIVE row and its children
rows = oa.build_protected_union(coord()); ps = oa.PathSet(rows)
assert ps.hit(ROOT + "/s81/e9/items/t44/attempt_5") and ps.hit("/srv/opentallas-scratch2/claude/wt/kw-fix-4-s81h10/physical")
oa.check_required_sources(rows, "t"); n += 1
# 2. each required list missing / empty / unreadable -> refuse + loud log line
for f in LISTS:
    for kw in ("skip", "empty", "unreadable"):
        try:
            oa.build_protected_union(coord(**{kw: f})); raise AssertionError(f"{kw} {f} accepted")
        except RuntimeError as e:
            assert "NOTHING DELETED" in str(e) and f in str(e), e
        n += 1
assert open(oa.REFUSE_LOG).read().count("REFUSING, NOTHING DELETED") == 9
# 3. a host snapshot union lacking one list's rows (old 2-list snapshot) -> refuse
old = [r for r in rows if r[1] != "lanes/prune/ARCHIVE-PROTECTED.tsv"]
try:
    oa.check_required_sources(old, "snapshot"); raise AssertionError("2-list snapshot accepted")
except RuntimeError as e:
    assert "ARCHIVE-PROTECTED" in str(e)
n += 1
# 4. ot-lifecycle strict_protected: all 3 read; ARCHIVE missing -> SystemExit
ol = load("otlc", sys.argv[2])
home = os.environ.get("HOME")
try:
    for case in ("ok", "skip", "empty"):
        h = tempfile.mkdtemp(); c = coord(**({} if case == "ok" else {case: "lanes/prune/ARCHIVE-PROTECTED.tsv"}))
        shutil.move(c, os.path.join(h, "coord")); os.environ["HOME"] = h
        if case == "ok":
            r = ol.strict_protected()
            assert any(x[1] == ROOT and x[2].startswith("ARCHIVE-PROTECTED.tsv:") for x in r), "ARCHIVE row not read"
        else:
            try:
                ol.strict_protected(); raise AssertionError(f"lifecycle accepted ARCHIVE {case}")
            except SystemExit as e:
                assert "NOTHING DELETED" in str(e)
        n += 1
finally:
    os.environ["HOME"] = home
print(f"PASS {n} cases")
