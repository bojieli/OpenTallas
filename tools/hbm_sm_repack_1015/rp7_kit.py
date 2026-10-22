#!/usr/bin/env python3
"""Build r7 half kits without changing the qualified hard children or outline."""
import copy
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/landed_parent'))
import lp
import rp6_kit as K

REC='results/arch/hbm_smh_r7_1021'
RTL='rtl/hbm_accel/sm/repack/h2a7'
FENCE='physical/hbm_smh_r7'

def spec(h,v):
    base=json.loads((ROOT/f'physical/ref_tile/smh_rp6{h}_{v}/spec.json').read_text())
    s=copy.deepcopy(base)
    lps=lp.load(str(ROOT/f'{REC}/lp_spec_{h}_{v}.json'))
    p=lp.Parent(lps); plan=p.plan()
    recpath=f'{REC}/{lps["top_lp"]}_record.json'
    rec=json.loads((ROOT/recpath).read_text())
    kit=f'smh_rp7{h}_{v}'
    names=[r['name'] for r in lps['regions']]
    height=1512.0 if h=='n' else 1252.8
    boxes={r:list(b) for r,b in K.G.BANDS[(h,v)].items()}
    boxes.update(tpw=[0,1123.2,86.4,height],tpe=[604.8,1123.2,691.2,height],
                 cpw=[0,302.4,86.4,712.8],cpe=[604.8,302.4,691.2,712.8],
                 upn=[0,height-86.4,432,height],upne=[561.6,height-86.4,691.2,height],
                 mpse=[561.6,0,691.2,86.4],xs=[129.6,712.8,604.8,1123.2],
                 cw=[0,302.4,345.6,518.4],ce=[345.6,302.4,691.2,518.4])
    # Boxes may overlap: each cell belongs to exactly one group, and fixed
    # qualified children retain their original positions.  There is no
    # artificial area contraction of the body or a change to the macro pitch.
    K.G.BANDS[(h,v)]={r:boxes[r] for r in names}
    clkpos={r:K.CKPIN[(h,v)].get(r,('W',560.0)) for r in names}
    clkpos.update(tpw=('N',43.2),tpe=('N',648.0),cpw=('W',500.0),cpe=('E',500.0),
                  upn=('N',430.0),upne=('N',675.0),mpse=('S',680.0),
                  xs=('W',918.0),u=('W',990.0),cw=('W',485.0),ce=('E',485.0))
    pins={f:[n for n in ns if not n.startswith('ck_')] for f,ns in base['pins'].items()}
    ranges={n:x for n,x in base['pin_ranges'].items() if not n.startswith('ck_')}
    for r in names:
        face,at=clkpos[r]
        pins.setdefault(face,[]).append('ck_'+r)
        ranges['ck_'+r]=[round(at-.54,2),round(at+.54,2)]
    domains={}
    for r in names:
        domains[r if r!=names[0] else 'core']=dict(ratio=[1,1],ports=['ck_'+r],
            inputs=[x['name'] for x in p.mod['ports'] if x['dir']=='in' and x['name']!='clk' and plan['nreg'].get('port:'+x['name'])==r],
            outputs=[x['name'] for x in p.mod['ports'] if x['dir']=='out' and plan['nreg'].get('port:'+x['name'])==r])
    oldsrc=f'rtl/hbm_accel/sm/repack/h2a6/lp_{h}_{v}/ot_hbm_smh_rp6{h}_{v}.sv'
    newsrc=f'{RTL}/lp_{h}_{v}/{lps["top_lp"]}.sv'
    sources=[newsrc if f==oldsrc else f for f in base['sources']]
    sources.append(f'{RTL}/ot_rp7_delay_ring.sv')
    imap=K.inst_regions((ROOT/newsrc).read_text(),names)
    assert all(ch['inst'].split('.')[0] in imap for ch in base['children'])
    fpath=f'{FENCE}/fence_{kit}.tcl'
    (ROOT/FENCE).mkdir(parents=True,exist_ok=True)
    fence=K.fence_tcl(h,v,kit,imap,names[0]).replace('R6_','R7_')
    (ROOT/fpath).write_text(fence)
    (ROOT/FENCE/'fence_dissolve.tcl').write_text((ROOT/'physical/hbm_smh_r6/fence_dissolve.tcl').read_text())
    offsets=lps['r7']['output_offsets']
    checklist={
      '1_pins':'Existing registered faces kept; face stages now use their own landed root. Original hard-child pin registers unchanged.',
      '2_reach':'Face/body and x-store/body paths all enter fixed-latency D4/E2 rings; regional placement boxes retained. Actual placed reach remains a gate obligation.',
      '3_fanout':'Kept W24 landing reset field copies and same-edge per-consumer reset copies. Native census must pass before layout; no waiver.',
      '4_depth':'No arithmetic logic added; all schedule compensation is registered. Original hard children unchanged.',
      '5_storage':'Landings are D4 rings. Additional delay compensation is a fixed-throughput chain of three-slot rings in kept eight-bit chunks; no indexed wide flop store or long shift pipeline. Same 3/6/9/12 data-edge ages; phase reset copies are bounded.',
      '6_floorplan':f'Unchanged {691.2}x{height} pin-bound outline; original hard children and 43.2 lattice retained. Face groups never shrink the qualified macros.',
      '7_clock':f'{len(names)} landed regional roots; face pins separated from hard-child insertion, x-store on own root; child centring taps; TT/FF within-region spread <=80 remains required. Hold margins 0.03.',
      '8_schedule':f'Static retiming against r6, interface output offsets {offsets}; regional reset depth {rec["reset"]["depth"]}. Edge equality recorded for every source/read pair; exact miter and priced composition required.'}
    s.update(name=kit,top=lps['top_lp'],sources=sources,pins=pins,pin_ranges=ranges,
        clock_port='ck_'+names[0],clock_ports=['ck_'+r for r in names],clock_entry_domains=domains,
        pin_hook_before_flops=[fpath],pre_dpl_extra=[FENCE+'/fence_dissolve.tcl'],
        safe_design_checklist=checklist,landed_record=recpath,
        landed=dict(record=recpath,landings=len(plan['lands']),landing_flops=rec['flops']['landing'],
                    reset_depth=rec['reset']['depth'],lp_spec=f'{REC}/lp_spec_{h}_{v}.json'),
        child_centre_tap=dict(children=[x['inst'] for x in base['children']],
                              why='Hard-child roots centred independently of external pin roots; actual gate decides.'),
        structural_change='r7 landed external face roots plus separate x-store clock; deterministic compensation preserves r6 fan-in ages')
    job=copy.deepcopy(base['job'])
    job.update(owner='CODEX-HBM-SVGSMH-2000',branch='codex/hbm-svgsmh-2000-1021',tag=kit,
               purpose='r7 structural landed face clocks and source-pinned exact retiming',
               extra_paths=list(dict.fromkeys(job.get('extra_paths',[])+[RTL,REC,FENCE])))
    sh=f'{RTL}/lp_{h}_{v}/retime.sh'
    job['benches']=[dict(name='retime',cmd=f'bash {sh} {{RUN}}/retime0 0',expect='pass',
                        pass_regex='R7_RETIME PASS',pass_witness=f'{REC}/bench/{h}_{v}_m0.log',threads=8,peak_ram_gb=64),
                    dict(name='mut_land',cmd=f'bash {sh} {{RUN}}/retime1 1',expect='fail',
                        fail_regex='R7_RETIME FAIL',fail_witness=f'{REC}/bench/{h}_{v}_m1.log',threads=8,peak_ram_gb=64)]
    s['job']=job
    return s

if __name__=='__main__':
    out=ROOT/'physical/ref_tile_specs/smh';out.mkdir(parents=True,exist_ok=True)
    for h in 'ns':
        for v in 'mf':
            path=out/f'smh_rp7{h}_{v}.json'
            path.write_text(json.dumps(spec(h,v),indent=1)+'\n')
            print(path.relative_to(ROOT))
