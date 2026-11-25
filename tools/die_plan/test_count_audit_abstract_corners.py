"""COUNT-AUDIT-1700: a macro kit's generate_abstract must write both corner libs (the signed view needs <mod>_ff.lib); preflight reports a kit with no bc corner."""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eco_loop
import kit_preflight as KP


def _abstract_cmd(tmp_path, config):
    d = tmp_path / "kit"
    d.mkdir()
    (d / "config.mk").write_text(config)
    out = tmp_path / "args.txt"
    dk = tmp_path / "fakedocker"
    dk.write_text('#!/bin/bash\necho "$@" >> %s\nexit 0\n' % out)
    dk.chmod(0o755)
    subprocess.run(["bash", "-c", eco_loop.ABSTRACT_SH, "eco_abstract", str(d), "4", "8", "img", str(dk), "0"], check=False, capture_output=True)
    return [ln for ln in out.read_text().splitlines() if "do-generate_abstract" in ln][0]


def test_eco_abstract_corners_follow_bc_libs(tmp_path):
    a = tmp_path / "a"; a.mkdir()
    b = tmp_path / "b"; b.mkdir()
    assert "CORNERS=tc bc" in _abstract_cmd(a, "export CORNER = TC\nexport BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /work/macros/a_ff.lib\n")
    assert "CORNERS" not in _abstract_cmd(b, "export CORNER = TC\n")


def test_gen_phys_run_script_abstract_both_corners_for_bc_lib_kits():
    src = (HERE / "gen_phys.py").read_text()
    m = re.search(r"if grep -q '\^export BC_LIB_FILES' /work/config.mk; then \\\$M do-generate_abstract \\\"CORNERS=tc bc\\\"; else \\\$M do-generate_abstract; fi", src)
    assert m, "the route/finish abstract step must pass CORNERS=tc bc when config.mk lists BC_LIB_FILES"


def test_preflight_reports_kit_without_bc_corner(tmp_path):
    (tmp_path / "config.mk").write_text("export CORNER = TC\nexport BC_LIB_FILES = x\n")
    assert KP.no_bc_corner(tmp_path) and "_ff.lib" in KP.no_bc_corner(tmp_path)[0]


def test_preflight_quiet_with_bc_corner_or_abstract_step(tmp_path):
    (tmp_path / "config.mk").write_text("export CORNERS = tc bc\n")
    assert KP.no_bc_corner(tmp_path) == []
    (tmp_path / "config.mk").write_text("export CORNER = TC\n")
    (tmp_path / "run_kit.sh").write_text('x; \\$M do-generate_abstract \\"CORNERS=tc bc\\"; y\n')
    assert KP.no_bc_corner(tmp_path) == []
    assert KP.no_bc_corner(tmp_path / "missing") == []
