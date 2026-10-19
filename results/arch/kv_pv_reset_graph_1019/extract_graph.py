#!/usr/bin/env python3
"""Read-only source inventory; no RTL simulation or native reset certification."""
import json,re,hashlib,pathlib,collections
P=pathlib.Path(__file__).resolve().parent
text=(P/'die.v').read_text()
instances={}
for m in re.finditer(r'^\s+(\w+) (\w+) \((.*)\);$',text,re.M):
    instances[m[2]]={'master':m[1],'pins':dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3]))}
drivers={v:n for n,x in instances.items() for k,v in x['pins'].items() if k=='b' and x['master'].startswith(('qkd_rly','qkd_rst_region'))}
rows=[]
for name in ['pvw_0','pvw_1']:
    cell=instances[name]; net=cell['pins']['rst_n']; path=[]
    while net in drivers:
        n=drivers[net]; x=instances[n]; path.append({'instance':n,**x});net=x['pins']['a']
    clocks={k:v for k,v in cell['pins'].items() if k.startswith('ck_c')}
    region=path[0];assert region['master']=='qkd_rst_region'
    dlynet=region['pins']['dly']
    dly=sum(int(b)<<int(i) for i,b in re.findall(r'assign '+re.escape(dlynet)+r"\[(\d+)\] = 1'b([01]);",text))
    assert len(clocks)==33 and set(clocks.values())=={'n_clk_core_c'}
    assert net=='n_rst_die_t0'
    rows.append({'instance':name,'master':cell['master'],'target_clocks':clocks,'external_reset':cell['pins']['rst_n'],'region_clock':region['pins']['ck'],'dly':dly,'source_root':{'instance':'host','master':instances['host']['master'],'port':'die_rst_n','net':net},'backward_path':path,'relay_cells_including_region':len(path),'plain_relays_before_region':len(path)-1})
manifest={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((P/'source').rglob('*')) if p.is_file()}
manifest.update({n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['die.v','kv_flags.env','selected_source.tgz']})
result={'schema':'opentallas.kv_pv_reset_graph.v2','source_commit':'5f2ce19bc','generated_run':'/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-5f2ce19bc-gen8v3mub','generated_stage':'pre-expansion source snapshot; live PREP preserved','pv':rows,'source_hashes':manifest,'native_qualified':False,'receipt_issued':False,'production_changed':False,'conditions':{'logical_pll_model':'all five core outputs assigned to one free-running core oscillator while package por_n=1','startup':'POR asserted to each region; stable dly; continuous target clocks; IGNORE=255 region edges before input accepted','warm':'region b transitions 1->0 after recognized a_q=0; HOLD=128 region cycles before next release','actual_required':'At least six valid target leaf clock edges sample rst_n LOW; the original proof already includes the RESET_PIN shell. Do not subtract a shell edge or re-run with modified pulses.','sufficient_physical':'Clock continuously qualified, max target edge gap Ttarget_max, and stable LOW interval after setup/hold aperture removal strictly exceeds 6*Ttarget_max. Region pulse width and clock continuity must be measured/bounded at actual PV pins.','unproved':['package POR pin connectivity and valid assertion width in native integration','regional-to-centre phase, period, pulse propagation and recovery/removal','all 33 actual leaf clocks qualified during external reset LOW','no-stop/PLL-loss restart protocol at target pins','warm-reset admission quietness and actual full-plane reset completion']}}
(P/'graph.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'die_sha256':manifest['die.v'],'pv':[{k:r[k] for k in ['instance','region_clock','dly','plain_relays_before_region']}for r in rows]},indent=2))
