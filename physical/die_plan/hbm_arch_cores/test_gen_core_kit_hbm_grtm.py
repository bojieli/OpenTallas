"""KW-FIX-45 11-11 (COORD class bug VISLAYOUT2-HBM): HBM core kits honour OT_GRT_TRANSITION_MODE (edge_outline default)."""
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("gck_grtm", HERE / "gen_core_kit_hbm.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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


def test_generator_calls_the_writer_before_copying_run_kit():
    src = (HERE / "gen_core_kit_hbm.py").read_text()
    assert src.index("write_grt_transition_mode(kd)") < src.index('"run_kit_hbm.sh", "face_guard_core.py"')


def test_run_kit_selects_patched_image_for_the_main_run_only():
    s = (HERE / "run_kit_hbm.sh").read_text()
    assert "GRTM=${OT_GRT_TRANSITION_MODE:-$(head -1 \"$K/grt_transition_mode\"" in s
    assert 'GIMAGE=${OT_GRT_IMAGE:-opentallas/orfs:asap7lock-grtoff}' in s
    main = [l for l in s.splitlines() if "-w /OpenROAD-flow-scripts/flow" in l and "bash -lc" in l]
    assert len(main) == 1 and '"${GRTD[@]}"' in main[0] and '"$GIMAGE" bash -lc' in main[0]
    assert '"$IMAGE" chown' in s and 'lec_async.sh" start "$K" "$NAME" "$IMAGE"' in s     # LEC / chown stay stock
    assert "FAIL_GRT_MODE" in s and "GRT-9103" in s


def test_run_kit_bash_syntax_and_mode_validation(tmp_path):
    assert subprocess.run(["bash", "-n", str(HERE / "run_kit_hbm.sh")]).returncode == 0
    blk = "\n".join(l for l in (HERE / "run_kit_hbm.sh").read_text().splitlines() if l.rstrip().endswith("# GRTM"))
    # unset mode: stock image, empty docker args
    out = subprocess.run(["bash", "-c", 'K=%s; IMAGE=stock; GOAL=route\n%s\necho "[$GIMAGE][${#GRTD[@]}]"' % (tmp_path, blk)],
                         capture_output=True, text=True)
    assert out.stdout.strip() == "[stock][0]"
    # bad mode: refused before any docker call
    bad = subprocess.run(["bash", "-c", 'K=%s; IMAGE=stock; GOAL=route; OT_GRT_TRANSITION_MODE=full\n%s' % (tmp_path, blk)],
                         capture_output=True, text=True)
    assert bad.returncode == 10 and (tmp_path / "FAIL_PREFLOOR").exists()
    # file mode with a fake docker that knows the image
    fake = tmp_path / "fakedocker"
    fake.write_text("#!/bin/bash\necho sha256:abc\n"); fake.chmod(0o755)
    (tmp_path / "grt_transition_mode").write_text("edge_outline\n")
    ok = subprocess.run(["bash", "-c", 'K=%s; IMAGE=stock; GOAL=route; OT_DOCKER=%s\n%s\necho "[$GIMAGE][${GRTD[*]}]"' % (tmp_path, fake, blk)],
                        capture_output=True, text=True)
    assert "[opentallas/orfs:asap7lock-grtoff][-e OT_GRT_TRANSITION_MODE=edge_outline]" in ok.stdout
    assert re.search(r'"mode": "edge_outline"', (tmp_path / "grt_transition.json").read_text())
