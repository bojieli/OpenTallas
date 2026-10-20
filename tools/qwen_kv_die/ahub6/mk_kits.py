#!/usr/bin/env python3
"""AHUB6 kit preparation only. A new native PASS must precede a layout gate."""
import copy
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
INPUT=Path(__file__).with_name('inputs')
OUT=ROOT/'results/arch/kv_ahub6_1020'
RECORD='results/arch/kv_ahub6_1020/qkd_ahub_static_dw_g6_lp_record.json'


def number(expr):
    assert re.fullmatch(r'[0-9()+*/ -]+',expr),expr
    return eval(expr.replace('/','//'),{'__builtins__':{}})


def record():
    d=json.loads((INPUT/'qkd_ahub_static_dw_g3_lp_record.json').read_text())
    d.update(lane='KV-AHUB6',generator='tools/qwen_kv_die/ahub6/mk_source.py',top='qkd_ahub_static_dw_g6_lp')
    d['landing_implementation']['chunk_bits']=2
    total=0
    for l in d['landings']:
        # Existing source/destination/bank timing is unchanged.
        width=l.get('width')
        if isinstance(width,int):total+=(width+1)//2
    ff=d['reset']['same_depth_forest']
    leaves=branches=0
    for name,r in ff['regions'].items():
        r['terms']=[s.replace('+8-1)/8','+2-1)/2') for s in r['terms']]
        r['leaves']=sum(number(s) for s in r['terms'])
        r['branches']=(r['leaves']+31)//32
        r['FFs']=r['leaves']+r['branches']
        leaves+=r['leaves'];branches+=r['branches']
        for b in r['bindings']:
            for k in ('first_expr','chunks_expr'):b[k]=b[k].replace('+8-1)/8','+2-1)/2')
            b['first_leaf']=number(b['first_expr']);b['chunks']=number(b['chunks_expr'])
    ff['root_D_loads']=7
    ff['regional_root_copies']=7
    d['reset']['note']='Seven same-edge root copies; per-region branches <=32; child/reset and D4/K2 ages unchanged.'
    # Fifteen vectors total1805 data bits; two-bit chunks total903. Each kept
    # local writer/reader has33 metadata flops including the kept epoch ports.
    d['flops'].update(landing=5*1805+33*903,reset=leaves+branches+7+52)
    d['flops']['model_scope']='Outer LP implementation; private core/io copies counted separately in mapped native census.'
    d['flops']['kept_epoch_ports_included']=True
    d['regions']['c']['children'].append('g_lpr_root')
    d['warnings']=['Native admission and current physical review required; no old gate/closure is inherited.']
    OUT.mkdir(parents=True,exist_ok=True)
    (ROOT/RECORD).write_text(json.dumps(d,indent=1)+'\n')


def main():
    record()
    base=json.loads((INPUT/'qkd_ahub_g4a_spec.json').read_text())
    for suffix in ('a','b'):
        old='qkd_ahub_g4'+suffix;name='qkd_ahub_g6'+suffix
        s=copy.deepcopy(base if suffix=='a' else json.loads((INPUT/'qkd_ahub_g4b_spec.json').read_text()))
        s.update(name=name,top='qkd_ahub_static_dw_g6_lp',landed_record=RECORD)
        s['sources']=[p for p in s['sources'] if not p.endswith('qkd_ahub_static_dw_safe.sv')]
        s['sources']=[p.replace('qkd_ahub_static_dw_g3_lp.sv','qkd_ahub_static_dw_g6_lp.sv') for p in s['sources']]
        s['sources'].insert(1,'rtl/hdc/nearhbm/qkd_ahub6_controls.sv')
        s['pin_hook_before_flops']=[f'physical/ref_tile/{name}/lp_fences.tcl']
        s['pre_dpl_extra']=[f'physical/ref_tile/{name}/lp_fences_release.tcl']
        j=s['job'];j.update(owner='Codex:KV-AHUB6',branch='codex/kv-ahub6-1020',tag='g6',purpose='AHUB6 native-safe local control/state and complete regional ownership; no added cycles vs g3.')
        j['benches']=[]
        for m in (0,1,19):
            b=dict(name=f'ahub_g6_m{m}',cmd=f'bash tools/qwen_kv_die/ahub6/bench.sh {{RUN}}/bench/m{m} {m}',expect='pass' if m==0 else 'fail',threads=4,peak_ram_gb=12,needs=['verilator'],pass_regex='^AHUB_DW PASS')
            if m==0:b['pass_witness']='results/rtl/qwen_kv_ahub6_1020/m0.log'
            else:b.update(fail_regex=f'^AHUB_DW FAIL mut={m} errors=',fail_witness=f'results/rtl/qwen_kv_ahub6_1020/m{m}.log')
            j['benches'].append(b)
        j['extra_paths']=['tools/qwen_kv_die/ahub6','rtl/hdc','rtl/lib','rtl/common/landed_parent','rtl/qwen_sys/split_20261014','rtl/test/qwen_kv_die/tb_qkd_ahub_static_dw_g6.sv','physical/ref_tile/ot_nhb_zh_m5','physical/ref_tile/qkh_recip_ref','results/arch/kv_ahub6_1020','results/rtl/qwen_kv_ahub6_1020']
        s['cycle_cost']='0 vs g3/g4; HUB_RECIP/HUB_PUB +6 and AM+3 inherited; reset age unchanged, no new stage.'
        s['structural_change']='AHUB6: CHUNK2 with recomputed reset trees; local kept same-edge command/metadata/decoder/max/capture copies; all mapped dynamic drivers <=32 required before gate; u_rx/u_ry and root copies explicitly included in c fence.'
        s['floorplan_note']='AHUB6 uses reviewed g4'+suffix+' geometry, core under own N pins, one Z strip per root. Source/state distribution is redesigned, region membership includes actual late-tail relays.'
        d=ROOT/'physical/ref_tile'/name;d.mkdir(parents=True,exist_ok=True)
        (d/'spec.json').write_text(json.dumps(s,indent=1)+'\n')
        fence=(INPUT/'lp_fences.tcl').read_text().replace('qkd_ahub_g4a',name).replace('tools/qwen_kv_die/ahub5/mk_kits.py','tools/qwen_kv_die/ahub6/mk_kits.py')
        if suffix=='b':
            for a,b in [('43.2 194.4 194.4 237.6','43.2 2.16 194.4 43.2'),('518.4 194.4 669.6 237.6','518.4 2.16 669.6 43.2'),('43.2 302.4 194.4 345.6','43.2 496.8 194.4 537.84'),('518.4 302.4 669.6 345.6','518.4 496.8 669.6 537.84')]:fence=fence.replace(a,b)
        fence=fence.replace('{u_io u_core u_eq u_lpr_root ', '{u_io u_core u_eq u_rx u_ry g_lpr_root u_lpr_root ')
        (d/'lp_fences.tcl').write_text(fence)
        (d/'lp_fences_release.tcl').write_text((INPUT/'lp_fences_release.tcl').read_text().replace('qkd_ahub_g4a',name))
        (d/'README.md').write_text(f'''# {name}: AHUB6 structural successor

Do not inherit g4's gate. Native mapped admission must PASS with exact loaded
Liberties before this first layout gate. Exactness witnesses must match g6.

SAFE review before gate:
1. Pins: registered as in g3;32 same-edge start copies; reset source pin7 D loads.
2. Reach: existing landed D4/K2 region crossings; u_rx/u_ry now inside c beside
   core and reciprocal child, existing single-cycle segments below405um.
3. Fanout: mandatory actual-Liberty full dynamic/reset BUF/INV census required;
   attach the exact actual-top/source receipt. No waiver is permitted.
4. Depth: exact FP-max comparison duplicated in8-bit output cones, semantic
   decoder partitions; stage boundaries unchanged; gate must measure <=600ps.
5. Storage: two-bit local rings, four slots; core LM512bits/seen512bits, no new
   runtime-indexed storage above2kb. Extra metadata flops are priced explicitly.
6. Floorplan: g4{suffix} macro lattice/whole faces retained; core box324x149um,
   Z strips151x43.2um; source SYNTHESIS area and current fill still need receipt.
7. Clock: seven existing regional roots; u_rx/u_ry fence omission fixed;
   io_hold_margin0.03; actual TT+FF child-inclusive spread must be <=80ps.
8. Schedule: static; no added edge vs g3/g4. Inherited HUB+6, AM+3, reset+10.

This README is a preparation checklist, not a gate verdict or closure approval.
''')
        print(d)


if __name__=='__main__':main()
