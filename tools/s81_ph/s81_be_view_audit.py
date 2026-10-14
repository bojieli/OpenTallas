#!/usr/bin/env python3
"""Record BE legacy source/view provenance and conservative window validation."""
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint as C
BASE=ROOT/'results/arch/s81_be_view_audit_1014'
ORIGINAL=ROOT/'results/arch/s81_be_native_mc_placement_1014/inputs/be_sl_c15e2bf6a.lef'
CANDIDATE=BASE/'be_sl_c15e2bf6a_selective_window_closed_candidate.lef'
VIEW=ROOT/'physical/s81_ph_views/vm_master/routes/s81vm-besl4-c15e2bf6a-tc-rd-pd45/dsfd_vm_be_sl'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metal(p):
    m=C.parse_lef(p.read_text());d=collections.defaultdict(list)
    for r in m['obs']:d[r[0]].append(box(*r[1:]))
    for pin in m['pins'].values():
        for r in pin['rects']:d[r[0]].append(box(*r[1:]))
    return {k:unary_union(v) for k,v in d.items()}
def record():
    a,z=metal(ORIGINAL),metal(CANDIDATE)
    unions={k:dict(original_area_um2=a[k].area,candidate_area_um2=z[k].area,erased_area_um2=a[k].difference(z[k]).area,added_area_um2=z[k].difference(a[k]).area) for k in a}
    assert all(v['erased_area_um2']<1e-9 for v in unions.values())
    old=subprocess.check_output(['git','show','c15e2bf6a:rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv'],cwd=ROOT,text=True)
    new=(ROOT/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv').read_text()
    def extract(t,n):return re.search(r'\bmodule '+n+r'\b.*?\bendmodule',t,re.S)[0]
    modules={}
    for top in ['dsfd_vm_be_sl','dsfd_vm_be_rcdc','dsfd_vm_be_kreg']:
        o,n=extract(old,top),extract(new,top)
        modules[top]=dict(route_source_sha256=hashlib.sha256(o.encode()).hexdigest(),current_source_sha256=hashlib.sha256(n.encode()).hexdigest(),byte_identical=o==n)
    assert all(v['byte_identical'] for v in modules.values())
    provenance=json.loads((VIEW/'abstract.json').read_text())
    pins=C.parse_lef(CANDIDATE.read_text())['pins']
    assert set(pins)==set(C.parse_lef(ORIGINAL.read_text())['pins'])
    original_sha=sha(ORIGINAL)
    assert original_sha==provenance['files']['dsfd_vm_be_sl.lef']
    m7=json.loads((BASE/'selective_window_m7_lint.json').read_text())
    m6=json.loads((BASE/'selective_window_m6_lint.json').read_text())
    assert m7['verdict']=='PASS' and m6['verdict']=='FAIL'
    actual_AP=json.loads((BASE/'ap_selective_window_m7/record.json').read_text())
    assert not actual_AP['pass_']
    libs={f'dsfd_vm_be_sl_{c}.lib':sha(VIEW/f'dsfd_vm_be_sl_{c}.lib') for c in ['tt','ss','ff']}
    assert all(v==provenance['files'][k] for k,v in libs.items())
    rec=dict(schema='opentallas.be_legacy_view_audit.v1',status='REEXPORT_CANDIDATE_REJECTED_ACTUAL_PIN_ACCESS',
        source_epoch='c15e2bf6a',source_modules=modules,source_closed_child_status='preserved; TT21.72ps/FF18.68ps recorded by legacyverdict; no newSS/parentclosureclaim',
        route_actual_cap='M7',route_arguments=(VIEW/'args').read_text(),abstract_sha256=sha(VIEW/'abstract.json'),original_LEF_sha256=original_sha,candidate_LEF_sha256=sha(CANDIDATE),unchanged_Liberty_sha256=libs,
        metal_union=unions,original_metal_retained=True,pin_identities_preserved=True,pin_window_strategy='onlyblockedpins;largestclearouterfraction .75/.5/.25',access_window_min_depth_um=.048,
        original_export_defects=dict(own_stub_pins=14,open_M7_pockets=2127,full_depth_above_OBS_overlaps=1509),candidate_m7_child_lint='PASS',candidate_m6_child_lint='FAIL',actual_M2_M7_pin_access='FAIL',actual_AP_record=actual_AP,admissible=False,
        disposition=dict(export='standardstub/pocket postprocess fixesstub/pockets; selectiveconservativewindowsexport passesgeometrylint but failsactualM2-M7PA; do notadopt',
            metadata='actualM7 cap may behonestlyrecordedaslegacyviewcap; changinglabeltoM6wouldhideactualM7signals/PG',
            physical='physicalabove-layerpin-depth/halo keepoutrepair/reroute orrawroute-backedalternateexport withactualPAproof needed. M6/M5cap requiresactualreroute; metadata/export cannotremoveabove-caproutedmetal',
            adoption=['actualparenttechnology/AP/DRCprobe MUST PASS; currentselectivewindowFAIL','die accepts truthfullegacyM7viewcap/strapM8 and recomposesavailablelayers','realperclockroutedR, actualglobalclock/resetsourcepins, SS/FFperpairbudgets','allparenttrafficcuts']),
        fail_records_preserved=True,globally_clock_bound=False,globally_reset_bound=False,pass_=False)
    (BASE/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(dict(source_modules_identical=True,pins_preserved=True,metal_retained=True,m7_lint=m7['verdict'],m6_lint=m6['verdict'],actual_pin_access='FAIL',candidate_admissible=False,parent_qualified=False)))
if __name__=='__main__':record()
