"""AUTOCLEAN-12 11-10: a protect.d wave-root line holds class a dirs, but not class b/c trims under it; other rows stay deep."""
import importlib.util, sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _run(oa_path):
    s = importlib.util.spec_from_file_location("oa", oa_path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    R = "/srv/opentallas-scratch3/claude/kw43-wave-1109/runs/s81/kit-wave"
    G = "/srv/opentallas-scratch3/claude/kw43-wave-1109/runs/s81/kit-wave/s81/e9/items/t1/attempt_3/gen/t1"
    deep = lambda q: q.count("/") > 4
    full = m.PathSet([(R, "kit_wave.txt"), (G, "kit_wave.txt")], deep=deep)
    trim = m.PathSet([(R, "kit_wave.txt"), (G, "kit_wave.txt")], deep=lambda q: deep(q) and not m.WAVE_ROOT_RE.search(q))
    kit_other = R + "/s81/e9/items/t2/attempt_5/gen/t2"
    assert full.hit(kit_other), "class a keeps everything under a wave root"
    assert not trim.hit(kit_other), "class b/c: a bare wave root does not hold a run below it"
    assert trim.hit(G + "/run") and trim.hit(G), "a specific source line still holds its subtree"
    assert trim.hit(R) and trim.hit(R.rsplit("/", 1)[0]), "the root itself and its ancestors stay held"
    print("PASS trim wave-root")


def test_trim_waveroot():
    _run(os.path.join(HERE, "ot-autoclean.py"))


if __name__ == "__main__":
    _run(sys.argv[1])
