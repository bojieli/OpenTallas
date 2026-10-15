#!/usr/bin/env python3
"""Source-pinned SU child bill and physical-home requirements for native S81.

An inventory is not placement or timing closure. Missing homes, kits, independent
clock bindings and current-source views remain explicit blockers. --strict exits
nonzero until every native path has such evidence; historical slab outlines and
the old 21.151 mm2 bill cannot satisfy that gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HD='rtl/dsrom_sys/s81_suhc/hier/'

# Count expressions are from the full production dsfd_sp_su_h generate bounds:
# QN256/KV512/QB32/SW1024/SM16/LPH16/S_RD16/S_WR16. These are the actual
# fine-grain leaves, not legacy aggregate qn0/kv0/sw0/sm0 reservations.
BASE=[
 ('IO','s81su_ctl_ref',1,'one controller'),('IO','s81su_pinns_ref',4,'NPO=4'),
 ('QN','s81su_qnt_cb32_ref',2,'two data half taps'),('QN','s81su_qne_ref',32,'NQE=QN_N/8'),
 ('QN','s81su_qnh_ref',2,'NQE/16'),('QN','s81su_qnr_ref',1,'one QN reduce'),
 ('QN','s81su_qnq_ref',8,'NQQ=QN_N/32'),
 ('KV','s81su_kvt_ref',4,'four data quarter taps'),('KV','s81su_kve_ref',56,'NKE-NRP=512/8-8'),
 ('KV','s81su_kvp_ref',8,'NRP=64/8'),('KV','s81su_qnh_ref',4,'NKE/16'),
 ('KV','s81su_kvr_ref',1,'one KV reduce'),('KV','s81su_kvq_ref',16,'NKQ=KV_N/32'),
 ('QB','s81su_qbtl_ref',1,'one low half tap'),('QB','s81su_swth_ref',1,'one shared high half tap'),
 ('QB','s81su_qbe_ref',8,'NPB=S_RD/2'),
 ('SW','s81su_swtl_ref',1,'one low half tap'),('SW','s81su_swth_ref',1,'one high half tap'),
 ('SW','s81su_qbe_ref',8,'NSWQ=S_RD/2'),('SW','s81su_swe_gfix_ref',128,'SNE=32 chains*4 pass positions'),
 ('SM','s81su_smt_hb2_ref',8,'NSM=SM_H/2'),('SM','s81su_sml_u65_ref',256,'NSM*2 heads*16 lanes'),
 ('SM','s81su_smc_ref',16,'NSM*2 heads'),('SM','s81su_smr_ref',16,'NSM*2 heads'),
 ('SM','s81su_smd_u65_ref',128,'NSM*2 heads*8 pairs'),
]


def sha(data):return hashlib.sha256(data).hexdigest()


def blob(rev,path):
    p=subprocess.run(['git','show',f'{rev}:{path}'],cwd=ROOT,capture_output=True)
    if p.returncode:raise RuntimeError(f'missing source {rev}:{path}')
    return p.stdout


def source(rev,path,module=None):
    data=blob(rev,path)
    if module and not re.search(r'\bmodule\s+'+re.escape(module)+r'\b',data.decode()):
        raise RuntimeError(f'{module} absent from {rev}:{path}')
    return dict(commit=subprocess.check_output(['git','rev-parse',rev],cwd=ROOT,text=True).strip(),
                path=path,sha256=sha(data),module=module)


def base_bill():
    rows=[]
    for group,kit,count,basis in BASE:
        d=ROOT/'physical/ref_tile'/kit
        spec=json.loads((d/'spec.json').read_text())
        floor=json.loads((d/'floorplan.json').read_text())
        die=floor['die'];w,h=die[2]-die[0],die[3]-die[1]
        job=json.loads((d/'job.json').read_text())
        revision=job.get('source',{}).get('commit')
        changed=[]
        for path in spec['sources']:
            current=ROOT/path
            if not current.exists():changed.append(dict(path=path,reason='current source missing'));continue
            try: old=blob(revision,path)
            except RuntimeError:changed.append(dict(path=path,reason='view source unavailable'));continue
            if old!=current.read_bytes():changed.append(dict(path=path,reason='current source differs from view source'))
        rows.append(dict(group=group,kit=str(d.relative_to(ROOT)),master=spec['top'],count=count,count_basis=basis,
                         outline_um=[w,h],outline_area_mm2=w*h*count/1e6,
                         clock_pin=spec['clock_port'],reset_pins=spec.get('reset_ports',[]),
                         pins=spec.get('pins'),historical_view_source=revision,current_source_differences=changed,
                         source_match=not changed,placement='UNPROVEN',
                         area_basis='existing kit floorplan, not proof current RTL fits or has a matching routed view'))
    return rows


def request(module,count,clock,rev,path,home,memory=None,notes=None):
    return dict(module=module,count=count,source=source(rev,path,module),
                proposed_home=home,actual_physical_home=None,assigned_pins=None,physical_kit=None,
                clock_entries=clock,clock_binding=None,memory_ports=memory or [],
                routed_area_mm2=None,placement=None,TT_setup=None,FF_hold=None,DRC=None,
                status='OPEN',notes=notes or [])


def packing_probe(rows,width=1889.976,height=10709.256,gap=21.6):
    """Constructive R0 skyline probe, with real outlines and explicit channels.

    A failed greedy probe is not a mathematical infeasibility proof. Success
    would establish only this subset's rectangle packing, not its pin reach,
    routing capacity, new native owners, or clocks.
    """
    boxes=[]
    for row in rows:
        for k in range(row['count']):
            boxes.append((row['outline_um'][0],row['outline_um'][1],f"{row['group']}/{row['master']}_{k}"))
    boxes.sort(key=lambda b:(-b[1],-b[0],b[2]))
    skyline=[(gap,width-gap,gap)];placed=[]
    for w,h,name in boxes:
        best=None
        for x,_,_ in skyline:
            if x+w+gap>width+1e-6:continue
            y=max(v for a,b,v in skyline if a<x+w+gap-1e-6 and b>x+1e-6)
            key=(y+h+gap,y,x)
            if best is None or key<best:best=key
        if best is None:raise RuntimeError('leaf wider than slab')
        _,y,x=best;end=x+w+gap;top=y+h+gap
        next_segments=[]
        for a,b,v in skyline:
            if b<=x or a>=end:next_segments.append((a,b,v));continue
            if a<x:next_segments.append((a,x,v))
            if b>end:next_segments.append((end,b,v))
        next_segments.append((x,end,top));skyline=sorted(next_segments)
        placed.append(dict(instance=name,x=x,y=y,w=w,h=h,orient='R0',inside=y+h<=height))
    top=max(p['y']+p['h'] for p in placed)
    return dict(method='R0 skyline sorted by height, explicit 21.6um channels; incomplete existing-leaf subset',
                outline_um=[width,height],channel_um=gap,required_height_um=top,
                outside_count=sum(not p['inside'] for p in placed),instances=placed,
                verdict='SUBSET_PACKED' if top<=height else 'PROBE_OUTSIDE',
                claim='No placement feasibility/infeasibility claim for complete native SU.')


def build(cn_rev,cp_rev):
    base=base_bill();new=[]
    for mod,n,ck in [('dsfd_su_t_cn8',16,'ck_cn[15:0]'),('dsfd_su_t_cn4',4,'ck_cn[19:16]'),
                     ('dsfd_su_t_cnnw',16,'ck_cnnw[15:0]'),('dsfd_su_t_ikh',2,'ck_ikh[1:0]'),
                     ('dsfd_su_t_ikr',1,'ck_ikr')]:
        new.append(request(mod,n,ck,cn_rev,HD+'dsfd_su_t_cn_ik.sv','shared existing KV bank region',
                           notes=['39 explicit scalar child clocks; reset vectors follow the same mapping',
                                  'CN/IK norm engines reuse existing 64 KVE owners; no second norm cluster',
                                  'CN quantizer is not port/source-compatible with the closed QBE master']))
    cp='rtl/dsrom_sys/s81_suhc/ot_s81_su_cp.sv'
    new.append(request('ot_s81_su_cp_ctl',1,'ck_ctl',cp_rev,cp,'CP cache controller near two SRAMs'))
    new.append(request('ot_s81_su_cp_lane',4,'ck_lane[3:0]',cp_rev,cp,'CP cache arithmetic lanes'))
    macro='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v'
    new.append(request('ot_sram_1r1w_128x256_m1_r2c2',2,'ck_mem[1:0]',cp_rev,macro,'one CP SRAM per slot',
                       memory=[dict(read_ports=1,write_ports=1,rows=128,bits=256,read_address_bits=7,write_address_bits=7)],
                       notes=['2*128*256 = 65,536 real state bits', 'every slot stores four KV plus four score FP32 fields per row']))
    new.append(request('ot_s81_su_cp_vm',1,'bridge clk plus seven exposed CP roots',cp_rev,
                       'rtl/dsrom_sys/s81_suhc/ot_s81_su_cp_vm.sv','CP VM descriptor/capture/row-assembly owner',
                       memory=[dict(rq_v=2,rq_row=28,rs_v=2,rs_d=1024,wq_v=1,wq_row=14,wq_d=512,wq_mask=16)],
                       notes=['two 512-bit operand holds and 512-bit assembly state need this physical owner',
                              'LVM10 reads at fixed cycles 0,4,...124; response cycles10,14,...134',
                              'component compatibility wrapper clocks are not a die root assignment']))
    total=sum(x['outline_area_mm2'] for x in base)
    return dict(schema='opentallas.s81.native-physical-join.v1',
                static_cycle_rule='No credits, readiness scheduling, or dynamic stretching. Compiler consumes actual implemented cycles.',
                source=dict(cn_parent=source(cn_rev,HD+'dsfd_sp_su_h.sv','dsfd_sp_su_h'),
                            cp_parent=source(cp_rev,cp,'ot_s81_su_cp_h')),
                existing_fine_grain_bill=base,existing_fine_grain_outline_area_mm2=total,
                existing_fine_grain_count=sum(x['count'] for x in base),
                constructive_existing_subset_probe=packing_probe(base),
                slot=dict(outline_um=[1889.976,10709.256],area_mm2=1889.976*10709.256/1e6,
                          source='s_die 0b9088f0b current allocation; actual placement/pins not yet delivered'),
                new_native_owners=new,new_cn_ik_clock_entries=39,new_cp_clock_entries_min=8,
                unresolved_operations=[
                    dict(operation='SE/SO',home='existing 8 SM stops',status='current mask-pipeline source needs successor SML view and exact packing'),
                    dict(operation='idx.newkey',home=None,status='new IQ producer has 12 roots plus VM tap; final source/pin contract pending'),
                    dict(operation='cand.final',home=None,status='actual producer/physical source mapping pending')],
                excluded_from_bill=['all parent/relay/pin glue not represented by kit rows','RX RA/RB/QR new control and arithmetic leaves',
                                    'all new CN/IK/CP owners','idx.newkey IQ provider and VM tap','cand.final owned producer'],
                placement_verdict='UNPROVEN',qualification_verdict='OPEN',
                claim='Existing fine-grain kit outlines are an incomplete area bill, not a legal placement or current-source qualification.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cn-source',default='5f2fa2ea2');ap.add_argument('--cp-source',default='ee2f297d2')
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--strict',action='store_true');a=ap.parse_args()
    d=build(a.cn_source,a.cp_source);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(existing_count=d['existing_fine_grain_count'],existing_area_mm2=d['existing_fine_grain_outline_area_mm2'],
                          slot_mm2=d['slot']['area_mm2'],new_owners=sum(x['count'] for x in d['new_native_owners']),
                          qualification=d['qualification_verdict'])))
    return int(a.strict and d['qualification_verdict']!='PASS')


if __name__=='__main__':raise SystemExit(main())
