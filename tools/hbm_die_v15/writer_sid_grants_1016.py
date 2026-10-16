#!/usr/bin/env python3
"""Four literal-SID future grants preserving all5098 measured v6 pin positions."""
import copy,hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));import hbm_die_views as V
def main():
    get=lambda ref,path:subprocess.check_output(['git','-C',str(ROOT),'show',ref+':'+path])
    request_path='results/rtl/hbm_writer_v7_sid_0430/typed_root_request.json';request_raw=get('12f696ea2',request_path);req=json.loads(request_raw);raw=get('27f1f83ba',req['new_source']);assert hashlib.sha256(raw).hexdigest()==req['new_source_sha256']
    base=json.loads(get('863313e0a','results/arch/hbm_die_v15/writer_roots_v6_wmid_1016/grant.json'));slot0=base['slots'][0];slots=[]
    pin_raw=get('863313e0a','results/arch/hbm_die_v15/writer_roots_v6_wmid_1016/assigned_pins.tcl').decode();pin_lines=[line for line in pin_raw.splitlines() if not line.startswith('ot_assigned_pin_exact {sid[')]
    exact={n:(l,f,float(v)) for n,l,f,v in re.findall(r'ot_assigned_pin_exact\s+\{([^}]+)\}\s+(M\d)\s+([NSEW])\s+([\d.]+)','\n'.join(pin_lines))};assert len(exact)==5098
    for sid,q in enumerate(['SW','SE','NW','NE']):
        master=req['new_masters'][sid]
        with tempfile.NamedTemporaryFile(suffix='.sv') as f:
            f.write(raw);f.flush();ports=V.L.parse_module(f.name,master,dict(MUT=0))['ports']
        expected={n if bits==1 else f'{n}[{k}]' for n,(direction,bits) in ports.items() for k in range(bits)};assert len(ports)==39 and expected==set(exact)
        s=copy.deepcopy(slot0);s.update(name=master+'_future',cell=master,source=req['new_source'],source_sha256=hashlib.sha256(raw).hexdigest(),source_prerequisite='27f1f83ba',physical_view=None,instances=[f'hb_coll_{q}.u_q.u_q.u_writer'],instance_scope='future substitution only; current source still instantiates original generic writer',configured_sid=sid)
        s['pins']=[p for p in s['pins'] if p['name'].split('[')[0]!='sid'];s['clock_entry_domains']['meta']['inputs'].remove('sid')
        s['face_capacity']['N']['bits']-=2;s['face_capacity']['N']['utilization']=round(s['face_capacity']['N']['bits']*.096/103.68,6)
        covered=[p for domain in s['clock_entry_domains'].values() for p in domain['inputs']+domain['outputs']+domain['ports']];assert set(covered)==set(ports) and len(covered)==len(set(covered))
        slots.append(s)
    out=dict(schema='opentallas.hier_contract.v1',qualification=False,canonical_die_contract_mutated=False,production_binding_adopted=False,source_ref='27f1f83ba',request_ref='12f696ea2',request_path=request_path,request_sha256=hashlib.sha256(request_raw).hexdigest(),slots=slots,normal_cycles_added=0,changed_pin_geometry_count=0,removed_pin_bits=['sid[0]','sid[1]'],proof=req['bench'],open=['new source-specific kit and exact source proof binding','actual per-root insertion/spread and phi-R','actual ODB5098pin readback/PG','TTsetup/FFhold/DRC0/native220/190/80','actual parent source dispatch/constant binding and die adoption'])
    d=ROOT/'results/arch/hbm_die_v15/writer_sid_v7_1016';d.mkdir(exist_ok=True);(d/'grants.json').write_text(json.dumps(out,indent=1)+'\n');(d/'assigned_pins.tcl').write_text('\n'.join(pin_lines)+'\n');print('four masters;5098 identical retained pins;39ports;16 exact roots;0 normal cycle delta')
if __name__=='__main__':main()
