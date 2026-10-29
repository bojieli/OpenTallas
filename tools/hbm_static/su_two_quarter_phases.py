"""Finite actual NW/NE operator phases; never invent between-phase VM writes.

Each phase is a freshly compiled two-quarter programme for a contiguous set
of independent rows. The combined job remains non-installable until a caller
provides its real input publication/output drain and programme reload events.
"""
import argparse,contextlib,io,json,sys
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'toksim_su/suvop'))
import prod_compile as C

def plan(record,out,mlat=4,alat=4,wcopy=0,rr=25,wr=22):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    spec=C.RECS[record];original_rows=spec[2];phases=[];row=0
    C.MLAT,C.ALAT,C.WCOPY=mlat,alat,wcopy
    while row<original_rows:
        choices=[];failed=[]
        for nrows in range(original_rows-row,0,-1):
            name=f'{record}__phase{row}_rows{nrows}'
            shape=list(spec);shape[2]=nrows;C.RECS[name]=tuple(shape)
            for qpr in ([1,2] if spec[5] else [1]):
                target=out/f'row{row}_rows{nrows}_qpr{qpr}'
                a=SimpleNamespace(out=str(target),rec=name,quarters=2,pin_reg=1,full_side=True,
                    rr=rr,wr=wr,fill_slack=1,drain_slack=2,side_ii=0,rfd_slack=1,pretree=True,qpr=qpr)
                try:
                    with contextlib.redirect_stdout(io.StringIO()):C.compile_rec(a)
                    m=json.loads((target/'programme.json').read_text())
                    choices.append(dict(first_row=row,rows=nrows,qpr=qpr,path=str(target),
                        cycles=m['cycles_stream_833ps'],dispatch_service_edges=m['cycles_serial'],edges=m['edges'],writes=m['expected_vm_writes'],
                        golden=m['reduction'].get('model_check')))
                except (ValueError,AssertionError,IndexError) as e:
                    failed.append(dict(rows=nrows,qpr=qpr,reason=str(e)))
            if choices:break
        if not choices:raise ValueError(f'no finite row phase for {record}: {failed}')
        chosen=min(choices,key=lambda c:c['cycles']);chosen['rejected_larger_shapes']=failed
        phases.append(chosen);row+=chosen['rows']
    r=dict(schema='opentallas.native_su_two_quarter_phases.v1',record=record,rows=original_rows,
        actual_qids=[2,3],lane_profile=dict(mlat=mlat,alat=alat,wcopy=wcopy,pin_reg=1),
        clock_ps=833,phases=phases,component_service_edges=sum(p['cycles'] for p in phases),
        retained_component_edges=sum(p['edges'] for p in phases),
        interphase_inputs='Actual row-specific VM publication/copy, prior output drain and programme reload required; same-address concatenation is forbidden',
        added_publication_or_reload_edges=None,installable=False,whole_programme_qualified=False)
    (out/'phase_plan.json').write_text(json.dumps(r,indent=2)+'\n');return r

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('record');p.add_argument('out');p.add_argument('--mlat',type=int,default=4)
    p.add_argument('--alat',type=int,default=4);p.add_argument('--wcopy',type=int,default=0);p.add_argument('--rr',type=int,default=25);p.add_argument('--wr',type=int,default=22)
    a=p.parse_args();r=plan(a.record,a.out,a.mlat,a.alat,a.wcopy,a.rr,a.wr)
    print(json.dumps({k:r[k] for k in ['record','rows','component_service_edges','added_publication_or_reload_edges','installable']}))
if __name__=='__main__':main()
