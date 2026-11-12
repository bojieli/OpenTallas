"""GRTM-RUNNERS-1 11-11 (COORD class bug VISLAYOUT2): the legacy core-kit runner honours OT_GRT_TRANSITION_MODE
(contract = hbm_arch_cores/run_kit_hbm.sh KW-FIX-45).  python3 -I -m pytest -q physical/die_plan/s81/cores/legacy/test_gen_core_kit_legacy_grtm.py"""
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools/die_plan"))

def load():
    spec = importlib.util.spec_from_file_location("gen_core_kit_legacy_grtm", HERE / "gen_core_kit_legacy.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


G = load()
TEXTS = {"modern": lambda: G.run_kit(True)}


def test_gen_writes_mode_file(tmp_path):
    m = load()
    assert m.write_grt_transition_mode(tmp_path, {"OT_GRT_TRANSITION_MODE": "edge_outline"}) == "edge_outline"
    assert (tmp_path / "grt_transition_mode").read_text() == "edge_outline\n"


def test_gen_unset_writes_nothing(tmp_path):
    m = load()
    assert m.write_grt_transition_mode(tmp_path, {}) is None
    assert not (tmp_path / "grt_transition_mode").exists()


def test_gen_rejects_bad_mode(tmp_path):
    m = load()
    with pytest.raises(ValueError):
        m.write_grt_transition_mode(tmp_path, {"OT_GRT_TRANSITION_MODE": "full"})


def test_generator_calls_the_writer():
    src = (HERE / "gen_core_kit_legacy.py").read_text()
    assert src.count("write_grt_transition_mode(kd)") == 1
    assert src.index("write_grt_transition_mode(kd)") > src.index("def main(")


@pytest.mark.parametrize("name", list(TEXTS))
def test_runner_selects_patched_image_for_the_main_run_only(name):
    s = TEXTS[name]()
    assert "GRTM=${OT_GRT_TRANSITION_MODE:-$(head -1 \"$K/grt_transition_mode\"" in s
    assert 'GIMAGE=${OT_GRT_IMAGE:-opentallas/orfs:asap7lock-grtoff}' in s
    main = [l for l in s.splitlines() if "-w /OpenROAD-flow-scripts/flow" in l and "bash -lc" in l]
    assert len(main) == 1 and '"${GRTD[@]}"' in main[0] and '"$GIMAGE" bash -lc' in main[0]
    for l in s.splitlines():           # LEC / chown / sign-off keep the stock image
        if "chown -R $(id -u)" in l or "--image" in l or "lec_async.sh\" start" in l:
            assert "$GIMAGE" not in l and "$IMAGE" in l
    assert "FAIL_GRT_MODE" in s and "GRT-9103" in s


def _blk(name, tag):
    return "\n".join(l for l in TEXTS[name]().splitlines() if l.rstrip().endswith("# GRTM"))


@pytest.mark.parametrize("name", list(TEXTS))
def test_runner_bash_syntax(name, tmp_path):
    p = tmp_path / "r.sh"
    p.write_text(TEXTS[name]())
    assert subprocess.run(["bash", "-n", str(p)]).returncode == 0


@pytest.mark.parametrize("name", list(TEXTS))
def test_runner_mode_selection(name, tmp_path):
    blk = _blk(name, "")
    # unset mode: stock image, empty docker args, no marker files
    out = subprocess.run(["bash", "-c", 'unset OT_GRT_TRANSITION_MODE; K=%s; IMAGE=stock; GOAL=route\n%s\necho "[$GIMAGE][${#GRTD[@]}]"' % (tmp_path, blk)],
                         capture_output=True, text=True)
    assert out.stdout.strip() == "[stock][0]" and not (tmp_path / "grt_transition.json").exists()
    # bad mode: refused before any docker call
    bad = subprocess.run(["bash", "-c", 'K=%s; IMAGE=stock; GOAL=route; OT_GRT_TRANSITION_MODE=full\n%s' % (tmp_path, blk)],
                         capture_output=True, text=True)
    assert bad.returncode == 10 and (tmp_path / "FAIL_PREFLOOR").exists()
    # missing image
    nodock = tmp_path / "nodocker"
    nodock.write_text("#!/bin/bash\nexit 1\n"); nodock.chmod(0o755)
    (tmp_path / "FAIL_PREFLOOR").unlink()
    miss = subprocess.run(["bash", "-c", 'K=%s; IMAGE=stock; GOAL=route; OT_GRT_TRANSITION_MODE=edge; OT_DOCKER=%s\n%s' % (tmp_path, nodock, blk)],
                          capture_output=True, text=True)
    assert miss.returncode == 10 and "missing" in (tmp_path / "FAIL_PREFLOOR").read_text()
    # file mode with a fake docker that knows the image
    fake = tmp_path / "fakedocker"
    fake.write_text("#!/bin/bash\necho sha256:abc\n"); fake.chmod(0o755)
    (tmp_path / "grt_transition_mode").write_text("edge_outline\n")
    ok = subprocess.run(["bash", "-c", 'unset OT_GRT_TRANSITION_MODE; K=%s; IMAGE=stock; GOAL=route; OT_DOCKER=%s\n%s\necho "[$GIMAGE][${GRTD[*]}]"' % (tmp_path, fake, blk)],
                        capture_output=True, text=True)
    assert "[opentallas/orfs:asap7lock-grtoff][-e OT_GRT_TRANSITION_MODE=edge_outline]" in ok.stdout
    assert re.search(r'"mode": "edge_outline"', (tmp_path / "grt_transition.json").read_text())


@pytest.mark.parametrize("name", list(TEXTS))
def test_runner_grt9103_check(name, tmp_path):
    chk = [l for l in TEXTS[name]().splitlines() if l.rstrip().endswith("# GRTM")]
    i = next(j for j, l in enumerate(chk) if l.startswith('if [ -n "$GRTM" ] && [ $rc = 0 ]'))
    chk = "\n".join(chk[i:])
    log = tmp_path / "run/logs/asap7/x/base/5_1_grt.log"
    log.parent.mkdir(parents=True)
    def run(text, mode="edge_outline"):
        log.write_text(text)
        return subprocess.run(["bash", "-c", 'K=%s; GRTM=%s; GOAL=route; rc=0\n%s\necho rc=$rc' % (tmp_path, mode, chk)],
                              capture_output=True, text=True).stdout
    assert "rc=1" in run("nothing\n") and (tmp_path / "FAIL_GRT_MODE").exists()
    (tmp_path / "FAIL_GRT_MODE").unlink()
    assert "rc=0" in run("[INFO GRT-9103] OT transition-layer mode edge_outline layers x\n")
    assert "rc=0" in run("nothing\n", mode="")           # unset: never checked


def test_legacy_flow_runner_has_no_transition_mode():
    leg = G.run_kit(False)
    assert "GRTM" not in leg and "GRTD" not in leg and "GIMAGE" not in leg
    assert '-w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc' in leg

