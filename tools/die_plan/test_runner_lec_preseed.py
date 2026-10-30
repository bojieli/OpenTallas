"""The existing untrusted-hints opt-in must reach the real generated runner's container argv."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_phys as GP


@pytest.mark.parametrize("value,early,expected,expected_early", [
    (None,None,"0","0"),("0","0","0","0"),("1",None,"1","0"),(None,"1","0","1")])
def test_generated_runner_forwards_preseed_without_changing_default(tmp_path,value,early,expected,expected_early):
    kit=tmp_path/"kit";kit.mkdir()
    (kit/"kit_preflight.py").write_text("raise SystemExit(0)\n")
    runner=kit/"run_kit.sh";runner.write_text(GP.RUN_KIT)
    bin=tmp_path/"bin";bin.mkdir()
    docker=bin/"docker"
    docker.write_text("#!/usr/bin/env python3\nimport json,os,sys\nwith open(os.environ['TRACE'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\n")
    docker.chmod(0o755)
    trace=tmp_path/"args.jsonl"
    env=dict(os.environ,PATH=str(bin)+os.pathsep+os.environ["PATH"],TRACE=str(trace))
    env.pop("OT_LEC_HINTS_PRESEED",None)
    env.pop("OT_LEC_EARLY_COMPARE",None)
    if value is not None:env["OT_LEC_HINTS_PRESEED"]=value
    if early is not None:env["OT_LEC_EARLY_COMPARE"]=early
    subprocess.run(["bash",str(runner),str(kit),"place","1","1"],env=env,check=True,capture_output=True,text=True)
    args=json.loads(trace.read_text().splitlines()[0])
    i=args.index("OT_LEC_HINTS_PRESEED="+expected)
    assert args[i-1]=="-e"
    assert args[args.index("OT_LEC_EARLY_COMPARE="+expected_early)-1]=="-e"
    # The container still runs the ordinary generated pre-floorplan LEC command.
    assert any("/work/lec.py" in arg for arg in args)
