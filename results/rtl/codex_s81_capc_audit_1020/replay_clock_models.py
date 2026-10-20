"""Actual native STA for finite compensation models; no gate/constraint waiver."""
from pathlib import Path
import json,subprocess,sys,hashlib
import ck_insertion as ck
root=Path.cwd();models=root/(sys.argv[1] if len(sys.argv)>1 else 'clock_models_r2');libs=root/'clock_libs';rows={}
manifest=json.loads((models/'manifest.json').read_text())
for variant in manifest['variants']:
    name=Path(variant['odb']).stem;rows[name]={}
    for corner in ['tt','ff']:
        mlibs=[f'/audit/clock_libs/{p.name}'for p in sorted(libs.glob(f'*_{corner}.lib'))]
        text=ck.tcl(corner,models.name+'/'+variant['odb'],'4_cts.sdc',False,'core_clk',mlibs,True)
        old='puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m"'
        new='puts [join [list OT_PROFILE [expr {[dict exists $bnd $i] ? 1 : 0}] $a $ot_ck_m $cp] "\\t"]'
        assert old in text;text=text.replace(old,new)
        tp=models/f'{name}_{corner}.tcl';tp.write_text(text)
        cmd=['docker','run','--rm','-v',f'{root}:/audit:ro','-v',f'{root}:/base:ro','openroad/orfs:asap7lock','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',f'/audit/{models.name}/{tp.name}']
        r=subprocess.run(cmd,capture_output=True,text=True);(models/f'{name}_{corner}.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(f'{name}/{corner} RC{r.returncode}: '+r.stdout[-1500:]+r.stderr[-1000:])
        profiles=[]
        for line in r.stdout.splitlines():
            if not line.startswith('OT_PROFILE\t'):continue
            tag,bound,a,master,pin=line.split('\t');profiles.append({'pin':pin,'boundary':int(bound),'arrival_ps':float(a),'master':master})
        assert profiles
        intervals=[]
        for z in profiles:
            if z['master']:
                receipt=json.loads((libs/(z['master']+'_insertion.json')).read_text())[corner]['boundary']
                intervals.append({'pin':z['pin'],'min':z['arrival_ps']+receipt['min'],'max':z['arrival_ps']+receipt['max']})
            else:intervals.append({'pin':z['pin'],'min':z['arrival_ps'],'max':z['arrival_ps']})
        early=min(intervals,key=lambda z:z['min']);late=max(intervals,key=lambda z:z['max']);span=late['max']-early['min']
        rows[name][corner]={'root':'core_clk','profile_count':len(profiles),'earliest':early,'latest':late,'root_boundary_envelope_ps':span,'profiles':profiles}
        print(name,corner,'actualroot+childbound',round(span,3),flush=True)
(models/'replay.json').write_text(json.dumps({'schema':'opentallas.capc_clock_copy_model_replay.v1','manifest':manifest,'results':rows,'scope':'Placement-estimated actual native STA on owned copies, original SDC zero source latency only. Child actual boundary extrema conservatively translated. No reroute, no source gate qualification, no final signoff. No original gate ODB modified.'},indent=2)+'\n')
