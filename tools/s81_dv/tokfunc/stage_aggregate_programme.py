#!/usr/bin/env python3
"""Stage actual aggregate MAT/config/native CTL assets; never create a producer.

Run from a frozen compiler tree whose RTL matches the shipping inventory. The
checkpoint norm vector is used only by the return legaliser/scoreboard. It is
never written as gather/VM data, a replay input, or a runtime preload.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/s81_dv'), str(ROOT/'tools/s81_dv/layer_prog')]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--tree', type=Path)
    p.add_argument('--die-v', type=Path, help='Actual current materializeddie; explicit componentphase only')
    p.add_argument('--plan', type=Path, help='Exact actualcurrentplan for frame membership; no route model')
    p.add_argument('--fixtures', type=Path, required=True)
    p.add_argument('--frame-schedule', type=Path, required=True)
    p.add_argument('--functional-kit', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rank-rows', help='Explicit NEW component phase range START:END, exactly24realrows; preserves oldA/B assets')
    p.add_argument('--tensor', choices=['wq_a','wkv'])
    p.add_argument('--producer-receipt',type=Path,help='Actual80context VN/VQ producer, mandatory for explicitphase')
    p.add_argument('--configured-receipt', type=Path)
    p.add_argument('--configured-source-root', type=Path)
    p.add_argument('--actual-source-audit', type=Path, help='Immutable actualG9 die/table/source audit for explicitphase')
    p.add_argument('--actual-port-bind',type=Path)
    p.add_argument('--actual-tap-consumer',type=Path)
    p.add_argument('--actual-source-readset','--actual-address-readset',dest='actual_address_readset',type=Path,help='Fullactualmanifest/PB289/orderedhashes;3ABIproxyisrejected')
    a = p.parse_args()
    import dv_layer_compile as C
    import lower_xs as L
    from layer_prog.aproj_native import phase_material, programme
    from selected_cap_phase import configured_profile, explicit_capture, local_programme, produced_fixture, ComponentDie, require_selected_profile
    profile = None
    if a.configured_receipt:
        assert a.configured_source_root
        profile = configured_profile(a.configured_receipt,a.configured_source_root)
    if a.rank_rows:
        assert profile and a.tensor, 'explicitphase needs actual191sourceprofile and declaredtensor'
        lo,hi=map(int,a.rank_rows.split(':')); selected_rows=list(range(lo,hi))
    else:
        assert not a.tensor
    inventory = json.loads(a.inventory.read_text())
    for rel, receipt in inventory['sources'].items():
        source_root = ROOT
        if profile:
            assert rel in profile['files_sha256'], ('source absent from configuredprofile',rel)
            if profile['files_sha256'][rel]!=receipt['sha256']:
                profile.setdefault('explicit_inventory_binding_changes',{})[rel]=dict(previous=receipt['sha256'],selected=profile['files_sha256'][rel],reason='owner-selected configured source; oldshipping inventory not relabeled')
            continue # all192source/top bytes checked against immutable actualreceipt
        if receipt.get('source_root_kind') == 'functional_kit_src':
            assert a.functional_kit, 'selected emitted source requires exact functional kit'
            source_root = a.functional_kit/'src'
        assert digest(source_root/rel) == receipt['sha256'], ('shipping source mismatch', rel)
    for schedule in a.frame_schedule.glob('*_schedule.json'):
        model = json.loads(schedule.read_text())
        source_root = ROOT
        if model.get('source_root_kind') == 'functional_kit_src':
            assert a.functional_kit, 'emitted frame model requires exact functional kit'
            if not profile:
                assert digest(a.functional_kit/'kit.json') == model['functional_kit_sha256']
            source_root = a.configured_source_root if profile else a.functional_kit/'src'
        for rel, expected in model['source_sha256'].items():
            assert digest(source_root/rel) == expected, ('LP source schedule mismatch', rel)
    os.environ.update(OT_XS_APROJ_TOPO='1', OT_XS_APROJ_RANK_TAGS='1', OT_XS_APROJ_ALIGN4='1',
                      OT_XS_DENSE_SPLIT2_ROWS=inventory['placement_environment']['OT_XS_DENSE_SPLIT2_ROWS'],
                      OT_XS_APROJ_CAP_PLAN='1', OT_XS_FRAME_SCHEDULE_DIR=str(a.frame_schedule.resolve()))
    if a.die_v:
        assert a.rank_rows and a.plan, 'directdie parser onlyfor explicitselectedphase withactualplan'
        die=ComponentDie(a.die_v,a.plan,C)
    else:
        assert a.tree
        die = C.Die(a.tree)
    sl = inventory['selected_slice']
    actual_audit=None
    if a.rank_rows:
        assert a.actual_source_audit, 'explicitnewphase must bind actualcurrentdie audit'
        assert digest(a.actual_source_audit)=='5e2de380659740383ab311382803d92b34b8cf49359a3167d6f9aa3c56e6d7ee'
        actual_audit=json.loads(a.actual_source_audit.read_text())
        assert die.die_sha==actual_audit['die_sha256'], 'actualdie identity mismatch; no oldG8capture adoption'
        top_binding=actual_audit['instances'][sl[2:]]
        rel=top_binding['selected_source'].split('/src/',1)[1]
        assert profile['files_sha256'][rel]==top_binding['source_sha256']
        assert top_binding['param_sets']=={'{}':1}
        profile['actual_G9_audit_reference']=dict(sha256=digest(a.actual_source_audit),die_sha256=actual_audit['die_sha256'],table_sha256=actual_audit['table_sha256'],defines=actual_audit['defines'])
        assert a.actual_port_bind and a.actual_tap_consumer, 'prospectiveactualsevenprofile needs exactreadset/TAPconsumer'
        assert digest(a.actual_port_bind)=='309c101e3be0f1062ad35fd964db4aa6b7f348dd0704691e2a2d1f82e9700398'
        assert digest(a.actual_tap_consumer)=='d5c8c903a66a636a5ce9d1cc6ddd3b9c3fd9c93927b4d2d625326466e5d4e5d8'
        pb=json.loads(a.actual_port_bind.read_text());assert len(pb['rtl_files'])==289
        assert set(pb['defines'])==set(actual_audit['defines'])
        profile['prospective_target']=dict(source_audit_sha256=digest(a.actual_source_audit),port_bind_sha256=digest(a.actual_port_bind),defines=actual_audit['defines'],final_ordered_rtl_files=pb['rtl_files'],rtl_roots=pb['rtl_roots'],tap_consumer_sha256=digest(a.actual_tap_consumer),TAP_macro='OT_S81ENG_TAP_N32R2',executed=False)
        profile['configuration_gap']='ProspectiveactualG9sevenprofile selected; historical191sixdefine is independent. Fullactualselectedmodule/clockcone readset preflight required before build; no alias or sevenprofile execution claimed.'
        assert a.actual_address_readset, 'fullactualselectedreadset is required before MATgeneration'
        full_readset=json.loads(a.actual_address_readset.read_text())
        try:
            selected_files=require_selected_profile(profile,actual_audit,full_readset)
        except ValueError as error:
            a.out.mkdir(parents=True,exist_ok=False)
            hold=dict(status='SOURCE_SELECTION_HOLD_BEFORE_MAT_GENERATION',reason=str(error),actual_source_audit_sha256=digest(a.actual_source_audit),actual_port_bind_sha256=digest(a.actual_port_bind),source_readset_sha256=digest(a.actual_address_readset),compiler_run=False,simulation_performed=False,source_assets_emitted=False)
            (a.out/'receipt.json').write_text(json.dumps(hold,indent=1)+'\n')
            raise SystemExit(str(error))
        profile['prospective_target']['selected_files_sha256']=selected_files
    else:
        assert die.die_sha == inventory['die_sha256']
    if profile:
        selected = profile['bindings']
    else:
        from layer_prog.slice_source import resolve
        selected = resolve(die, sl)
    producer_binding=None
    if a.rank_rows:
        assert a.producer_receipt, 'no checkpointnorm oracle for explicitphase'
        fx,producer_binding=produced_fixture(a.fixtures,a.producer_receipt)
    else:
        fx = L.load_fixture(a.fixtures)
    assert digest(a.fixtures/'meta.json') == inventory['fixture_meta_sha256']
    a.out.mkdir(parents=True, exist_ok=False)
    halves=('EXPLICIT_'+a.tensor,) if a.rank_rows else ('A','B')
    for half in halves:
        os.environ['OT_XS_DENSE_SPLIT2'] = 'B' if a.rank_rows else half
        out = a.out/half
        images = out/'rom'
        images.mkdir(parents=True)
        _, placement = L.placement(die, sl, fx)
        if a.rank_rows:
            assert [(f['frame'],f['master'],f['lk']) for f in placement]==[(f['frame'],f['master'],f['lk']) for f in inventory['selected_ownership']['B']], 'actualphysicalframe/strap census changed'
            capture=explicit_capture(inventory,fx,L,selected_rows,a.tensor)
            capture['die_sha']=die.die_sha
            capture['actual_source_audit_sha256']=digest(a.actual_source_audit)
            actual_frames=die.frames_of(sl)
            assert actual_frames==[f['frame'] for f in capture['frames']], 'actualcurrentframe placement changed'
            assert all(die.strap(f['frame'],'lk')==f['lk'] and die.inst[f['frame']]['master']==f['master'] for f in capture['frames'])
            placement=capture['frames']
        else:
            assert placement == inventory['selected_ownership'][half]
            capture = L.aproj_capture_contract(die, sl, fx, 1)
        frames, shared, expected_returns = [], None, {}
        for member in placement:
            assert member['rows'], ('unexpected idle selected member', member)
            mats, indices = L.frame_mats(fx, member['rows'])
            frame_source=None
            if a.rank_rows:
                selected_frame=profile['bindings']['col_h9_l4_lp']
                frame_source=dict(path=str(a.configured_source_root/selected_frame['source']),sha256=selected_frame['sha256'])
            field, phase, plan, qa, q, bf = L.frame_programme(member['master'], member['lk'], mats,
                fx['x'], rank_rows=member['rows'], cap_cfg=capture['cfg'],frame_source=frame_source)
            assert plan['faults'] == 0
            material = phase_material(field)
            assert shared is None or shared == material, 'one real XS requires identical shared P/S words'
            shared = material
            L.field_images(field, qa, q, bf, member['frame'], images, rank_rows=member['rows'])
            mapped = L.rank_plan(plan, member['rows'])
            expected_returns[member['frame']] = mapped['ret']
            frames.append(dict(member, phase={k:v for k,v in phase.items() if k != 'matrices'},
                pairs=qa, out_index=indices, faults=plan['faults'], ret=mapped['ret'],
                emission=plan['emission'], source_schedule=str(L.source_frame_schedule(member['master']))))
        # Zero is an explicitly RELATIVE programme origin, never a global epoch
        # or fabricated HOST/KS descriptor. Parent must bind immutable dates.
        if a.rank_rows:
            native=local_programme(die.slices()[sl]['sid'],sl,shared,capture,profile)
            assert a.actual_address_readset, 'realaddressABI source readset needed for unsealedfeedassembly'
            address=full_readset
            from layer_prog.kv_operand_feed import assemble
            feed=assemble(die,[dict(rank=fx['meta']['rank'],programme=native['manifest'])],a.actual_source_audit.read_bytes(),address)
            (out/'kv_operand_feed.json').write_text(json.dumps(feed,indent=1)+'\n')
        else:
            native = programme(die, dict(id='L0_'+half+'_aproj_'+sl, end=0),
                               dict(slice=sl, t_issue=0), shared, frames, capture)
        for name, content in native['files'].items():
            path = out/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        # Plans contain checkpoint-dependent values for comparison only. They
        # are deliberately outside all replay/ROM producer inputs.
        score = out/'SCOREBOARD_ONLY'
        score.mkdir()
        (score/'frame_return_plan.json').write_text(json.dumps(expected_returns, indent=1)+'\n')
        (out/'native_ctl_relative.json').write_text(json.dumps(dict(rows=native.get('rows',[]),
            templates=native.get('templates',[]), events=native.get('events',[]),
            command_descriptors=native.get('manifest',{}).get('command_descriptors'),
            epoch='RELATIVE_ONLY_NOT_HOST_ADOPTED', physical_phase_qualified=False), indent=1)+'\n')
    files = {str(f.relative_to(a.out)):digest(f) for f in sorted(a.out.rglob('*')) if f.is_file()}
    receipt = dict(schema='opentallas.s81.aggregate_source_assets.v1', status='STAGED_HELD_FOR_REAL_PRODUCER',
        selected_source=selected, producer_binding=producer_binding, configured_profile=profile, explicit_component_rank_rows=selected_rows if a.rank_rows else None, selected_slice=sl, die_sha256=die.die_sha,
        actual_die_sha256=die.die_sha, actual_plan_sha256=getattr(die,'plan_sha256',None), actual_source_audit_sha256=digest(a.actual_source_audit) if actual_audit else None,
        inventory_sha256=digest(a.inventory), fixture_meta_sha256=digest(a.fixtures/'meta.json'),
        compiler_sha256={str(f.relative_to(ROOT)):digest(f) for f in [Path(__file__), Path(L.__file__)]},
        files=files, actual_gather_data_emitted=False, synthetic_frame_returns_emitted=False,
        simulation_launched=False, global_epoch_bound=False, aggregate_FIN_qualified=False,
        pending=['real 16-slice NORMR/XFIN VQ producer trace', 'exact grown clock/reset/return cone',
                 'all-frame aggregate CAP collision/FIN qualification', 'native HOST adoption'])
    (a.out/'assets.json').write_text(json.dumps(receipt, indent=1)+'\n')
    print(json.dumps(dict(status=receipt['status'], files=len(files), slice=sl)))


if __name__ == '__main__':
    main()
