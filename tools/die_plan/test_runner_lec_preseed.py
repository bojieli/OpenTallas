"""The existing untrusted-hints opt-in must reach the real generated runner's container argv."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_phys as GP


@pytest.mark.parametrize("value,early,superset,configured", [
    (None,None,None,False),("0","0","0",False),("1",None,None,False),(None,"1",None,False),(None,None,"1",False),
    (None,None,None,True),(None,None,"0",True)])
def test_generated_runner_forwards_preseed_without_changing_default(tmp_path,value,early,superset,configured):
    kit=tmp_path/"kit";kit.mkdir()
    GP.write_lec_options(kit, {"lec": {"superset_vec": True}} if configured else {})
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
    env.pop("OT_LEC_SUPERSET_VEC",None)
    if value is not None:env["OT_LEC_HINTS_PRESEED"]=value
    if early is not None:env["OT_LEC_EARLY_COMPARE"]=early
    if superset is not None:env["OT_LEC_SUPERSET_VEC"]=superset
    subprocess.run(["bash",str(runner),str(kit),"place","1","1"],env=env,check=True,capture_output=True,text=True)
    args=json.loads(trace.read_text().splitlines()[0])
    i=args.index("OT_LEC_HINTS_PRESEED="+(value or "0"))
    assert args[i-1]=="-e"
    assert args[args.index("OT_LEC_EARLY_COMPARE="+(early or "0"))-1]=="-e"
    assert args[args.index("OT_LEC_SUPERSET_VEC="+(superset if superset is not None else "1" if configured else "0"))-1]=="-e"
    # The container still runs the ordinary generated pre-floorplan LEC command.
    assert any("/work/lec.py" in arg for arg in args)


def test_persisted_optin_removed_on_regeneration_and_bad_options_reject(tmp_path):
    GP.write_lec_options(tmp_path, {})
    assert not (tmp_path / "lec_options.json").exists()
    GP.write_lec_options(tmp_path, {"lec": {"superset_vec": True}})
    assert json.loads((tmp_path / "lec_options.json").read_text()) == {"superset_vec": True}
    GP.write_lec_options(tmp_path, {"lec": {"superset_vec": False}})
    assert not (tmp_path / "lec_options.json").exists()
    for options in ({"superset_vec": "1"}, {"unknown": True}, True):
        with pytest.raises(ValueError):
            GP.write_lec_options(tmp_path, {"lec": options})
