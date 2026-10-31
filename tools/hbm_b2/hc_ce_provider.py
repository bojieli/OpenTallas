#!/usr/bin/env python3
"""Prepare, but never adopt, the full HC root CE physical provider alias.

Input and output must differ. The caller folds the candidate into its one
plan/TOK event after regenerating static calendars and native binding.
"""
from pathlib import Path
import argparse,copy,json,os,re,subprocess
REPO=Path(__file__).resolve().parents[2]
P="rtl/hbm_accel/cores_split/sk_en_q4/"
PROVIDERS=[P+n+".sv" for n in ("ot_hbm_hc_root_static_ce_phys","ot_hbm_hc_tail_unit_static_ce_phys","ot_hbm_hc_tail_rest_core_ce","ot_hdc_sinkhorn_se","ot_hdc_sinkhorn_se_phys")]
CONTRACT=dict(schema="opentallas.hbm.hc_ce_provider.v1",alias={"ot_hbm_hc_root_static":"ot_hbm_hc_root_static_ce_phys"},tail_launch_edge=0,tail_result_v_edge=507,root_tready_commit_edge=508,minimum_emit_edge=509,native_split_tail_latency_edges=503,physical_tail_latency_edges=508,increment_vs_current_split_edges=5,increment_vs_unsplit_tail_edges=12,root_ports_and_parameters="unchanged",enable_hop_stations=0,adoption="ONE plan/TOK event; calendars and native bind must be regenerated",timing="833ps, no timing exception; enable-qualified timing contract unresolved")

def root_interface_check():
    src="rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_root_static_s.sv"
    old=(REPO/src).read_text() if (REPO/src).exists() else subprocess.check_output(["git","-C",str(REPO),"show","HEAD:"+src],text=True)
    new=(REPO/PROVIDERS[0]).read_text()
    new=new.replace("ot_hbm_hc_root_static_ce_phys","ot_hbm_hc_root_static_s").replace("ot_hbm_hc_tail_unit_static_ce_phys","ot_hbm_hc_tail_unit_static_s")
    norm=lambda t:re.sub(r"\s+","",re.sub(r"//[^\n]*","",t))
    if norm(old)!=norm(new):raise ValueError("CE root changed more than its name and selected tail provider")
    return dict(verdict="PASS",scope="root parameters, ports and consumer RTL unchanged; only selected tail module differs",whole_native_bind="NOT RUN")

def candidate(asbuilt):
    d=copy.deepcopy(asbuilt)
    if d.get("alias",{}).get("ot_hbm_hc_root_static")!="ot_hbm_hc_root_static_s":
        raise ValueError("unexpected existing HC root alias; do not overwrite another plan event")
    d["alias"].update(CONTRACT["alias"])
    d["prefer"]=list(dict.fromkeys(PROVIDERS+d.get("prefer",[])))
    d["alias_note"]=d.get("alias_note","")+" | OPT-IN HC CE physical provider: tail508edges vs current503; root emit>=launch+509. No generated clock. Requires ONE plan/TOK event and fresh native bind."
    d["hc_ce_contract"]=copy.deepcopy(CONTRACT)
    return d

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asbuilt",type=Path);ap.add_argument("--out",type=Path)
    ap.add_argument("--check-interface",action="store_true")
    ap.add_argument("--contract-out",type=Path)
    a=ap.parse_args();report=root_interface_check()
    if a.check_interface:print(json.dumps(report))
    if a.contract_out:a.contract_out.write_text(json.dumps(CONTRACT,indent=2)+"\n")
    if a.asbuilt or a.out:
        if not(a.asbuilt and a.out):ap.error("both --asbuilt and --out are required")
        if a.asbuilt.resolve()==a.out.resolve():ap.error("candidate output must differ from the baseline")
        d=candidate(json.loads(a.asbuilt.read_text()))
        d["base"]=os.path.relpath(REPO,a.out.resolve().parent)
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+"\n")
        print(json.dumps(dict(candidate=str(a.out),alias=d["alias"]["ot_hbm_hc_root_static"],minimum_emit_edge=509,adopted=False)))
if __name__=="__main__":main()
