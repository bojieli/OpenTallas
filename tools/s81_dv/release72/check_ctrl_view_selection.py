#!/usr/bin/env python3
"""Require rvcase's actual first-ref view selection to match the CLOSED CTRL packet."""
import argparse,ast,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--view-ref',action='append',required=True);ap.add_argument('--table',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    packet=json.loads((ROOT/'results/arch/s81_die72_1021/g9_assembly/ctrl_first_closed/binding.json').read_text());table=json.loads(a.table.read_text())
    assert set(packet['defines'])<=set(table['defines']),'configured native CTRL defines missing'
    rows=[v for v in table['masters'].values()if v.get('module')==packet['module']and v.get('view')]
    assert len(rows)==1 and rows[0]['view']==packet['view'] and rows[0].get('params',{})=={},'wrong configured CTRL master/view'
    assert rows[0].get('ref')==packet['source_ref'],'wrong configured CTRL source pin'
    for path,h in packet['source_sha256'].items():
        assert path in table.get('rtl_refs',{}).get(packet['source_ref'],[]) and packet['source_ref']+'/'+path in table.get('prefer',[]),'missing exact source preference'
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',packet['source_ref']+':'+path]);assert hashlib.sha256(raw).hexdigest()==h,'CLOSED source bytes mismatch'
    # Evaluate the exact existing production selector function, not a parallel resolver.
    path=ROOT/'tools/s81_dv/dv_rvcase.py';src=path.read_text();node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)and n.name=='closed_views');scope={'subprocess':subprocess,'re':re,'GITDIR':str(ROOT)};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
    chosen=scope['closed_views'](a.view_ref).get(packet['module']);assert chosen and chosen[1]==packet['view'],'actual first-ref selection does not choose exact CTRL kit'
    hashes={}
    for f,h in packet['view_sha256'].items():
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',chosen[0]+':'+chosen[1]+'/'+f]);hashes[f]=hashlib.sha256(raw).hexdigest();assert hashes[f]==h,'actual selected CTRL view bytes differ from CLOSED receipt'
    result={'status':'PASS','master':packet['module'],'view_refs':a.view_ref,'selected':chosen,'actual_selector_sha256':hashlib.sha256(ast.get_source_segment(src,node).encode()).hexdigest(),'selected_view_sha256':hashes,'source_contract':'Packet8RTL hashes and3configureddefines; apply_ctrl_g9 must precede this check','scope':'Exact existing GEN view-selection guard only, no physical/STA/timing claim'};a.out.write_text(json.dumps(result,indent=1)+'\n');print('G9_CTRL_ACTUAL_VIEW_SELECTION PASS',chosen)
if __name__=='__main__':main()
