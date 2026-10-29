"""Actual source hierarchy qualification; no arithmetic or physical PASS implied.

Run via ot-run: qualify_fullside.py OUT. The negative control restores the old
QID predicate in the new source and must fail the same hierarchy obligations.
"""
from pathlib import Path
import hashlib,json,re,subprocess,sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/die_plan'))
import bind_elab as E
sys.path.insert(0,str(root/'tools/hbm_b2'))
from su_fullside_profile import apply_profile

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
src=root/'rtl/hbm_accel/generic/adapters/static_su/top'
pg=src/'ot_hbm_su_static_pgslice_s.sv';lg=src/'ot_hbm_su_static_pgslice_lg_s.sv'
# Under the default FULL_SIDE=(QID==0), the only replacements are identities.
original=subprocess.check_output(['git','-C',str(root),'show','e126d4b1d:'+str(pg.relative_to(root))],text=True)
normalized=pg.read_text().replace(' // FULL_SIDE decouples arithmetic capability from the unchanged VM address QID.\n // The default reproduces the original selection; explicit enablement needs a new bind/model/kit.\n parameter integer FULL_SIDE=(QID==0),\n','').replace('FULL_SIDE!=0&&L==0','QID==0&&L==0').replace('FULL_SIDE!=0&&G==0','QID==0&&G==0')
assert normalized==original,'unrelated arithmetic/body change'
oldlg=subprocess.check_output(['git','-C',str(root),'show','e126d4b1d:'+str(lg.relative_to(root))],text=True)
assert lg.read_text().replace(' parameter integer FULL_SIDE=(QID==0),\n','').replace('.FULL_SIDE(FULL_SIDE),','')==oldlg
source='module hbm_current_native_top;\n'+''.join('  ot_hbm_su_static_pgslice_lg_s #(.QID(%d),.G(%d),.MLAT(4),.ALAT(4),.LEAF(1)) su_%s%d ();\n'%(qid,g,role,g) for role,qid in [('NW',2),('NE',3)] for g in range(4))+'endmodule\n'
assert apply_profile(source,[])[0]==source
candidate,selection=apply_profile(source,['su_NW0','su_NE0'])
assert candidate.count('.FULL_SIDE(1)')==2
rejected=0
for names in [['su_NW1'],['su_SW0'],['su_NW0','su_NW0']]:
    try:apply_profile(source,names)
    except ValueError:rejected+=1
assert rejected==3
top=out/'top.sv';top.write_text(candidate)
records=[]
for label,mutant in [('candidate',False),('old_qid_mutant',True)]:
    d=out/label;d.mkdir(exist_ok=True)
    override=pg
    if mutant:
        override=d/pg.name
        override.write_text(pg.read_text().replace('FULL_SIDE!=0&&L==0','QID==0&&L==0').replace('FULL_SIDE!=0&&G==0','QID==0&&G==0'))
    ab=dict(top='hbm_current_native_top',netlist=[str(top)],rtl_roots=['rtl/hbm_accel'],
            files=[str(override),str(lg)],prefer=[str(override),str(lg)],
            dissolve=['ot_hbm_su_static_pgslice_lg_s','ot_hbm_su_static_pgslice_s'])
    E.elab(ab,str(root),d,mem_gb=12)
    flat=E.flatten(json.loads((d/'asbuilt.json').read_text()),ab['top'])
    cells={c.path:c for c in flat.cells};violations=[];slices=[]
    for role in ('NW','NE'):
        for g in range(4):
            base=f'su_{role}{g}.u_slice'
            lane=cells[base+'.g_lane[0].g_pr.u_lane']
            got=int(lane.params['KIND']);expected=2 if g==0 else 1 if g==1 else 0
            side=base+'.g_side_pipe.u_side' in cells
            if got!=expected or side!=(g==0):violations.append(base)
            slices.append(dict(instance=f'su_{role}{g}',lane0_kind=got,side_present=side))
    assert bool(violations)==mutant,(label,violations)
    records.append(dict(label=label,caught=bool(violations),slices=slices,violations=violations))
receipt=dict(schema='opentallas.hbm.fullside_source_qualification.v1',
             default_source_equivalence=True,default_selector_identity=True,negative_inputs_rejected=rejected,
             actual_hierarchy=records,selection_example_only=selection,
             added_data_cycles=0,source_sha256=hashlib.sha256(pg.read_bytes()).hexdigest(),
             arithmetic_qualification='NOT_RUN_UNCHANGED_ORIGINAL_KIND2_AND_SIDE_MASTERS',
             physical_qualification='NOT_RUN',adoption=False)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('FULLSIDE_SOURCE PASS default byte-normalized identity; actual hierarchy; old-QID control CAUGHT',flush=True)
