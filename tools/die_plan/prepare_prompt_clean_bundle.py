#!/usr/bin/env python3
"""Prepare the explicit +1 program-edge prompt source for the existing HR face flow.

Usage: prepare_prompt_clean_bundle.py --core-json INPUT --out OUT
Then hr_face_ports.sh OUT/core.json FACE_OUT, and GEN with --hr-face-ports
FACE_OUT --prompt-clean-bundle. The default source and input core JSON are unchanged.
"""
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core-json",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[2])
    a=ap.parse_args();a.repo=a.repo.resolve();a.out=a.out.resolve()
    data=json.loads(a.core_json.read_text())
    if data.get("module")!="qkd_hr_core_prompt":
        raise SystemExit("only the prompt HR core accepts this opt-in")
    base=a.repo/"rtl/qwen_sys/host_integrated_20261014/qkd_host_program_rx_target.sv"
    opt=base.with_name("qkd_host_program_rx_target_cp.sv")
    matches=[i for i,p in enumerate(data["files"]) if Path(p).name==base.name]
    if len(matches)!=1:raise SystemExit("expected exactly one native program receiver source")
    old=Path(data["files"][matches[0]])
    if not old.is_absolute():old=a.repo/old
    if old.read_bytes()!=base.read_bytes():
        raise SystemExit("input receiver differs from the proven base; fresh retiming proof required")
    text=opt.read_text()
    needle="module qkd_host_program_rx_target_cp #"
    if text.count(needle)!=1:raise SystemExit("unexpected opt-in receiver module identity")
    native=a.out/"native"/base.name;native.parent.mkdir(parents=True,exist_ok=True)
    native.write_text(text.replace(needle,"module qkd_host_program_rx_target #"))
    data["files"][matches[0]]=str(native)
    data["prompt_program_delta"]={"added_program_cycles":1,"invalid_program_fault_cycles":1,"normal_frame_cycles":0,"credit_return_cycles":0,"overflow_fault_cycles":0,"default_off":True,"proof":"results/kv_prompt_clean_pipe_1106","parent_requirement":"opt into this same source and price one additional program service/fault edge"}
    (a.out/"core.json").write_text(json.dumps(data,indent=1)+"\n")
    print(json.dumps({"core":str(a.out/"core.json"),"native":str(native),"added_program_cycles":1}))

if __name__=="__main__":main()
