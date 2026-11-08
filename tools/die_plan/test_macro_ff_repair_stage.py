"""A requested macro FF repair must consume its actual FF timing views only."""
from pathlib import Path
import json
import os
import subprocess
import pytest
import gen_phys as G


def kit(tmp_path):
    (tmp_path / "macros").mkdir()
    (tmp_path / "macros" / "leaf_ff.lib").write_text('library(leaf_fast) { cell(leaf) {} }')
    return [("u_leaf", "leaf", "leaf.lef", "leaf_tt.lib", 0, 0, "R0")], ["/work/macros/leaf_tt.lib"]


def test_separate_ff_config_selects_only_ff_macro_views(tmp_path):
    macros, libs = kit(tmp_path)
    assert G.macro_ff_repair_stage(tmp_path, macros, libs) == {"leaf": "leaf_fast/leaf"}
    # Expand the generated stage with a representative original TT config.
    (tmp_path / "config.mk").write_text(
        "export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl\n"
        "export CORNER = TC\nexport ADDITIONAL_LIBS = /work/macros/leaf_tt.lib\n"
        "export BC_LIB_FILES = /platform/ff.lib /work/macros/leaf_ff.lib\n")
    stage = (tmp_path / "macro_ff_repair.mk").read_text().replace("include /work/config.mk", f"include {tmp_path}/config.mk")
    (tmp_path / "stage.mk").write_text(stage + '\nprobe:\n\t@echo $(CORNER) $(CORNERS) $(LIB_FILES) $(ADDITIONAL_LIBS) $(OT_MACRO_FF_BASE_PRE_GRT)\n')
    p = subprocess.run(["make", "-s", "-f", str(tmp_path / "stage.mk"), "probe"], check=True, capture_output=True, text=True)
    assert p.stdout.strip() == "BC bc /platform/ff.lib /work/macros/leaf_ff.lib /work/macros/leaf_ff.lib /work/hold_repair_pre.tcl"
    assert "leaf_fast/leaf" in (tmp_path / "macro_ff_pre_grt.tcl").read_text()
    assert "leaf_tt.lib" in (tmp_path / "config.mk").read_text()


def test_missing_ff_view_refuses_stage(tmp_path):
    macros, libs = kit(tmp_path)
    (tmp_path / "macros" / "leaf_ff.lib").unlink()
    with pytest.raises(ValueError, match="no ff view"):
        G.macro_ff_repair_stage(tmp_path, macros, libs)


def test_wrong_ff_master_refuses_stage(tmp_path):
    macros, libs = kit(tmp_path)
    (tmp_path / "macros" / "leaf_ff.lib").write_text('library(fast) { cell(other) {} }')
    with pytest.raises(ValueError, match="missing actual FF macro cells"):
        G.macro_ff_repair_stage(tmp_path, macros, libs)


def test_runner_shell_remains_valid(tmp_path):
    path = tmp_path / "run.sh"
    path.write_text(G.RUN_KIT)
    subprocess.run(["bash", "-n", str(path)], check=True)
    assert "DESIGN_CONFIG=/work/macro_ff_repair.mk" in G.RUN_KIT


@pytest.mark.parametrize("macro_ff", [False, True])
def test_exported_runner_expands_inner_stage_commands(tmp_path, macro_ff):
    """Execute the exported shell with explicit fake CAD commands, never Docker/CAD."""
    kitdir = tmp_path / "kit"
    bindir = tmp_path / "bin"
    kitdir.mkdir(); bindir.mkdir()
    flow = tmp_path / "fake_flow"
    flow.mkdir(); (flow / "env.sh").write_text("")
    # config.mk before the results: a newer config.mk is the RESYNTH-GUARD refusal case (KW-FIX-32)
    (kitdir / "config.mk").write_text("export OT_HOLD_FF_MARGIN = 10\n")
    result = kitdir / "run/results/asap7/fixture/base"
    result.mkdir(parents=True)
    for f in ("1_synth.odb", "1_2_yosys.v", "4_cts.odb", "4_cts.sdc", "5_1_grt.odb", "6_final.odb"):
        (result / f).write_text("")
    if macro_ff:
        (kitdir / "macro_ff_repair.mk").write_text("# fake stage marker, no CAD\n")
    def executable(name, body):
        p = bindir / name; p.write_text(body); p.chmod(0o755)
    executable("python3", "#!/bin/sh\nexit 0\n")
    executable("openroad", '#!/bin/sh\necho "OT_POSTCTS_GATE TEST_ONLY PASS"\n')
    executable("chown", "#!/bin/sh\nexit 0\n")
    executable("make", '''#!/usr/bin/python3
import os,sys,json
with open(os.environ['MAKE_CAPTURE'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
if 'print-OT_HOLD_FF_MARGIN' in sys.argv: print('OT_HOLD_FF_MARGIN: 10')
''')
    executable("docker", '''#!/usr/bin/python3
import os,sys,json,subprocess
a=sys.argv[1:]
if 'bash' not in a:sys.exit(0)
i=a.index('bash');assert a[i+1]=='-lc'
cmd=a[i+2]
with open(os.environ['COMMAND_CAPTURE'],'w') as f:f.write(cmd)
env=os.environ.copy()
for j,x in enumerate(a[:-1]):
 if x=='-e' and '=' in a[j+1]:
  k,v=a[j+1].split('=',1);env[k]=v
cmd=cmd.replace('/OpenROAD-flow-scripts',os.environ['FAKE_FLOW']).replace('/work',os.environ['FAKE_KIT'])
sys.exit(subprocess.run(['bash','-c',cmd],env=env).returncode)
''')
    runner = tmp_path / "run_kit.sh"
    runner.write_text(G.RUN_KIT)
    env = dict(os.environ, PATH=str(bindir) + ":" + os.environ["PATH"], OT_LEC_ASYNC="0",
               MAKE_CAPTURE=str(tmp_path / "make.jsonl"), COMMAND_CAPTURE=str(tmp_path / "inner.sh"),
               FAKE_FLOW=str(flow), FAKE_KIT=str(kitdir))
    p = subprocess.run(["bash", str(runner), str(kitdir), "route", "16", "8"], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr + (kitdir / "run_route.log").read_text()
    calls = [json.loads(x) for x in (tmp_path / "make.jsonl").read_text().splitlines()]
    assert any("synth" in x for x in calls)
    assert any("cts" in x for x in calls)
    grt = next(x for x in calls if "grt" in x)
    assert grt[-4:] == ["grt", "CORNER=BC", "CORNERS=bc", "HOLD_SLACK_MARGIN=10"]
    assert (f"DESIGN_CONFIG={kitdir}/macro_ff_repair.mk" in grt) == macro_ff
    assert any("route" in x for x in calls)
