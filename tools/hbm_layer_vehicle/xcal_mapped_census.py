#!/usr/bin/env python3
"""Fleet-only standalone TT/RVT mapped census, not a physical gate or STA."""
import argparse,collections,gzip,hashlib,json,pathlib,re,subprocess,sys
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('output');ap.add_argument('--spec',action='append',default=[]);args=ap.parse_args()
root=pathlib.Path.cwd();out=pathlib.Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
libroot=pathlib.Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=[];areas={}
for group in ['AO','OA','SIMPLE','INVBUF','SEQ']:
    src=sorted(libroot.glob('asap7sc7p5t_'+group+'_RVT_TT_nldm*'))[0]
    txt=gzip.open(src,'rt').read() if src.suffix=='.gz' else src.read_text()
    dst=out/(group+'.lib');dst.write_text(txt);libs.append(dst)
    for m in re.finditer(r'cell\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{',txt):
        a=re.search(r'\barea\s*:\s*([0-9.eE+-]+)',txt[m.end():])
        if a:areas[m[1]]=float(a[1])
base='rtl/hbm_accel/loader/service_native/'
common=[base+n for n in ['ot_hbm_xcal_desc_host_native.sv','ot_hbm_xcal_desc_native.sv','ot_hbm_xcal_prog_native.sv','ot_hbm_xcal_calendar_native.sv','ot_hbm_xcal_target_native.sv','ot_hbm_xcal_kept_bits.sv']]
bbs=['physical/asap7_memory_macros/'+n+'/'+n+'_bb.v' for n in ['ot_sram_1r1w_128x256_m1_r2c2','ot_sram_1r1w_1024x256_m2_r2c2']]
yosys='/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys'
jobs=[json.loads(pathlib.Path(p).read_text()) for p in args.spec] if args.spec else [dict(top='ot_hbm_xcal_desc_host_native',params={'PAW':11,'PREL':1,'DD':256,'DAW':8}),dict(top='ot_hbm_xcal_prog_native',params={'PAW':11,'PREL':1})]
for job in jobs:
    top=job['top'];params=job.get('params',{});sources=job.get('sources',common+bbs)
    tag=job.get('name',top+('_'+hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()[:8] if sum(j['top']==top for j in jobs)>1 else ''))
    dst=out/tag;dst.mkdir(exist_ok=True)
    la=''.join(' -liberty '+str(p) for p in libs)
    script=['read_liberty -lib '+str(p) for p in libs]
    script+=['read_verilog -sv '+p for p in sources]
    script+=['hierarchy -check -top '+top+''.join(' -chparam '+k+' '+str(v) for k,v in params.items()),'synth -top '+top+' -flatten','dfflibmap -liberty '+str(libs[-1]),'abc'+la+' -D 833.333','setundef -zero','setattr -mod -unset keep_hierarchy','setattr -unset keep_hierarchy','flatten','opt_clean -purge','tee -o '+str(dst/'stat.txt')+' stat'+la,'write_json '+str(dst/'mapped.json'),'write_verilog '+str(dst/'mapped.v')]
    (dst/'synth.ys').write_text('\n'.join(script)+'\n')
    with (dst/'yosys.log').open('w') as log:subprocess.run([yosys,'-s',str(dst/'synth.ys')],stdout=log,stderr=subprocess.STDOUT,check=True)
    design=json.loads((dst/'mapped.json').read_text());mod=design['modules'][top]
    aliases=collections.defaultdict(list)
    for name,net in mod['netnames'].items():
        for bit in net['bits']:
            if isinstance(bit,int):aliases[bit].append(name)
    loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
    for name,c in mod['cells'].items():
        for port,bits in c['connections'].items():
            dest=drivers if c['port_directions'].get(port)=='output' else loads
            for bit in bits:
                if isinstance(bit,int):dest[bit].append([name,c['type'],port])
    nets=[]
    for bit,sinks in loads.items():
        names=aliases[bit];reset=any('rst' in n or 'reset_landing' in n or 'reset_' in n for n in names)
        clock_names=set(job.get('clock_ports',[]))|{job.get('clock_port','clk'),'clk_desc'}
        clock=any(n in clock_names for n in names) or all(c[2].upper() in ['CLK','CK','C','CLOCK'] for c in sinks)
        nets.append(dict(bit=bit,fanout=len(sinks),names=names,drivers=drivers[bit],reset=reset,clock=clock,sinks=sinks))
    nets.sort(key=lambda x:x['fanout'],reverse=True)
    counts=collections.Counter(c['type'] for c in mod['cells'].values());unknown={k:v for k,v in counts.items() if k not in areas and not k.startswith('ot_sram_')}
    report=dict(top=top,tool='ORFS docker Yosys + ABC, RVT TT,833.333ps target',physical_claim=False,std_area_um2=sum(areas.get(k,0)*v for k,v in counts.items()),source_sha256={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in sources},macro_counts={k:v for k,v in counts.items() if k.startswith('ot_sram_')},unmapped_or_unknown=unknown,cell_counts=counts,over32_data_control=[n for n in nets if n['fanout']>32 and not n['reset'] and not n['clock']],clock_networks=[n for n in nets if n['clock']],reset_networks=[n for n in nets if n['reset']],top50=nets[:50])
    (dst/'census.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['top50','over32_data_control','cell_counts','clock_networks','reset_networks']},indent=2),flush=True)
    print('OVER32',[(n['names'],n['fanout']) for n in report['over32_data_control']],flush=True)
