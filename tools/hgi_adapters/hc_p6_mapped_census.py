#!/usr/bin/env python3
"""Map actual P6 arithmetic, shell and controller separately. Never qualifies physical closure.

Hard children are made blackboxes only for decomposition accounting. Their exact
source is separately mapped; no blackbox result is treated as native execution.
"""
import argparse, collections, hashlib, json, pathlib, subprocess, sys, time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import run_abi3_physical as flow

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args()
    manifest=json.loads(a.manifest.read_text());root=a.manifest.resolve().parent
    for p,h in manifest['sources_sha256'].items(): assert sha(root/p)==h,p
    a.out.mkdir(parents=True,exist_ok=False)
    libs=[pathlib.Path(p) for p in flow.VIEWS['asap7']['corners']['TT']['liberty']]
    assert all(p.is_file() for p in libs),'Missing pinned host Liberty libraries'
    cells=flow.scan_liberty(libs);seq=next(p for p in libs if '_SEQ_' in p.name)
    forbidden=flow.expand_dont_use(flow.VIEWS['asap7']['dont_use'],cells)
    libargs=' '.join('-liberty '+str(p) for p in libs)
    probes=[('slice','ot_hgi_hc_lane_sl',None),('shell','ot_hgi_hc_lane_ll','ot_hgi_hc_lane_sl'),('controller','ot_hgi_hc_ctl_ll','ot_hgi_hc_lane_ll')]
    results={}
    for name,top,child in probes:
        out=a.out/name;out.mkdir()
        script='read_verilog -sv -D SYNTHESIS '+' '.join(str(root/p) for p in manifest['sources_sha256'])+'\n'
        if child:script+='blackbox '+child+'\n'
        script+=f'hierarchy -check -top {top}\nsynth -top {top} -flatten\ndfflibmap -liberty {seq}\n'
        script+='abc '+libargs+' '+' '.join('-dont_use '+p for p in forbidden)+' -D 833.333\n'
        script+=f'opt_clean -purge\ncheck -assert\ntee -o {out}/stat.txt stat {libargs}\nwrite_json {out}/mapped.json\n'
        (out/'synth.ys').write_text(script)
        start=time.monotonic()
        with (out/'yosys.log').open('w') as log:
            cp=subprocess.run([str(flow.YOSYS),'-s',str(out/'synth.ys')],stdout=log,stderr=subprocess.STDOUT,cwd=root)
        if cp.returncode:
            (a.out/'failure.json').write_text(json.dumps({'probe':name,'exit':cp.returncode,'elapsed_s':time.monotonic()-start},indent=2)+'\n')
            return cp.returncode
        net=json.loads((out/'mapped.json').read_text());inst=net['modules'][top]['cells']
        counts=collections.Counter(c['type'] for c in inst.values()); known={k:v for k,v in counts.items() if k in cells}
        children={k:v for k,v in counts.items() if 'ot_hgi_hc_lane_sl' in k or 'ot_hgi_hc_lane_ll' in k}
        macros={k:v for k,v in counts.items() if 'ot_sram_' in k}
        unknown={k:v for k,v in counts.items() if k not in known and k not in children and k not in macros}
        result={'top':top,'elapsed_s':time.monotonic()-start,'std_cell_area_um2':sum(cells[k]['area']*v for k,v in known.items()),'std_sequential_cells':sum(v for k,v in known.items() if cells[k]['sequential']),'std_cells':sum(known.values()),'hard_child_cells':children,'mapped_memory_cells':macros,'unknown_cells':unknown,'per_cell':dict(counts),'mapped_sha256':sha(out/'mapped.json'),'yosys_log_sha256':sha(out/'yosys.log'),'stat_sha256':sha(out/'stat.txt')}
        results[name]=result
        print(json.dumps({k:v for k,v in result.items() if k!='per_cell'}),flush=True)
        if unknown:raise ValueError('Unmapped logic cells remain')
        for p,h in manifest['sources_sha256'].items(): assert sha(root/p)==h,p
    summary={'status':'MAPPED_COMPONENT_AREA_ONLY_NATIVE_PHYSICAL_OPEN','input_manifest':manifest,'liberty_sha256':{str(p):sha(p) for p in libs},'yosys_sha256':sha(flow.YOSYS),'probes':results,'composed_std_area_um2':256*results['slice']['std_cell_area_um2']+32*results['shell']['std_cell_area_um2']+results['controller']['std_cell_area_um2'],'composed_std_sequential_cells':256*results['slice']['std_sequential_cells']+32*results['shell']['std_sequential_cells']+results['controller']['std_sequential_cells'],'memory_count':32,'physical_open':['Mapped macro area/placement and density','Separate physical root pins and phi-R delivery','All incident pin/cut/hop and static calendar proof','TT setup / FF hold / DRC0 / native boundary proof']}
    (a.out/'receipt.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ('probes','input_manifest','liberty_sha256')}));return 0
if __name__=='__main__':raise SystemExit(main())
