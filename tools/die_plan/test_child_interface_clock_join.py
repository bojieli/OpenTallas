"""Pure-data contracts only. Fixtures never assert timing/source/parent coverage."""
import copy
import json
import os
from pathlib import Path

import pytest
import child_interface_clock_join as C

INSTANCE = 'u_q.u_s.u_hc.g_bank[0].u_bank'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def write_table(root, files, name, header, rows):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\t'.join(header) + '\n' + ''.join('\t'.join(str(row[k]) for k in header) + '\n' for row in rows))
    files[name] = C.digest(path)


def fixture(tmp_path):
    native, parent = tmp_path / 'native', tmp_path / 'parent'
    source = {name: digit * 64 for name, digit in [('6_final.v', 'a'), ('6_final.odb', 'b'), ('6_final.spef', 'c')]}
    qualification = dict(schema='opentallas.child_clock_join.v1', status='QUALIFIED_NATIVE_GRAPH',
        source_qualification=dict(status='PASS',basis='opentallas.lec_input_identity.v1',receipt_sha256='e'*64), graph_identity=dict(status='PASS', native=source,
        master='hist', clock_pin='clk', corners={c: dict(selected_liberty_sha256=(('1' if c == 'tt' else '2') * 64)) for c in ('tt','ff')}))
    maps = dict(schema='opentallas.child_boundary_clock_map.v1', status='COMPLETE_DIRECT_BUFFER_MAPS',
                missing=[], native_netlist_sha256=source['6_final.v'], maps=dict(inputs={}, outputs={}))
    for direction, bit, references in [('inputs','i[0]',['C0','C1']), ('outputs','o[0]',['L'])]:
        maps['maps'][direction][bit] = [dict(reference=ref, data_pin=ref+('/D' if direction == 'inputs' else '/QN'),
            clock_pin=ref+'/CLK', clock='clk', edge='rise', inversions=1 if direction=='outputs' else 0,
            buffer_chain=([dict(instance='inv', master='INV', contract=dict(liberty_sha256='9'*64, inverted=True, function='!A'))] if direction=='outputs' else [])) for ref in references]
    nw = dict(schema='opentallas.child_clock_witness.v1', source_identity_kind='routed_native_netlist_sha256', native=source, corners={})
    for corner in ('tt','ff'):
        files = {}
        write_table(native, files, corner+'/child_clock_'+corner+'_endpoints.tsv', C.ENDPOINTS,
            [dict(reference=ref, clock_pin=ref+'/CLK', clock='clk', late_ps='9', early_ps='8', edge='rise') for ref in ('L','C0','C1')])
        write_table(native, files, corner+'/child_clock_'+corner+'_masters.tsv', ['reference','clock_pin','master'],
            [dict(reference=ref, clock_pin=ref+'/CLK', master='DFF') for ref in ('L','C0','C1')])
        write_table(native, files, corner+'/child_clock_'+corner+'_roots.tsv', ['clock_edge','late_ps','early_ps'], [dict(clock_edge='clk',late_ps='0',early_ps='0')])
        write_table(native, files, corner+'/child_clock_'+corner+'_clocks.tsv', ['clock','source_kind','source'], [dict(clock='clk',source_kind='port',source='clk')])
        nw['corners'][corner] = dict(files=files)
    write_json(tmp_path/'qualification.json', qualification); write_json(tmp_path/'maps.json', maps); write_json(native/'witness.json', nw)
    qualification['boundary_maps'] = dict(artifact_sha256=C.digest(tmp_path/'maps.json'))
    write_json(tmp_path/'qualification.json', qualification)
    attachment = dict(schema='opentallas.external_child_graph_attachment.PREP.v1',
        child_qualification=dict(sha256=C.digest(tmp_path/'qualification.json')),
        boundary_maps=dict(sha256=C.digest(tmp_path/'maps.json')),
        full_native_graph=dict(sha256=C.digest(native/'witness.json'), native=source),
        parent_netlist=dict(path='actual_parent.v',sha256='d'*64), parent_top='parent', parent_structural_clock_net='ck',
        actual_selected_libraries={c:dict(path='/selected/hist_'+c+'.lib',sha256=qualification['graph_identity']['corners'][c]['selected_liberty_sha256']) for c in ('tt','ff')})
    attachment['instances']=[dict(instance=INSTANCE,status='PASS',source_qualification='PASS',master='hist',clock_pin='clk',parent_top='parent',parent_clock_net='ck',parent_netlist_sha256='d'*64,boundary_map_artifact_sha256=C.digest(tmp_path/'maps.json'))]
    write_json(tmp_path/'attachment.json',attachment)
    pw = dict(schema='opentallas.child_clock_witness.v1', native={'6_final.v':'d'*64}, corners={})
    for corner in ('tt','ff'):
        files={}; prefix=corner+'/child_clock_'+corner
        endpoints=[dict(reference=ref,clock_pin=(ref+'/clk' if ref==INSTANCE else ref+'/CLK'),clock='actual_core',late_ps='7',early_ps='6',edge='rise') for ref in (INSTANCE,'u_tx','u_rx')]
        write_table(parent,files,prefix+'_endpoints.tsv',C.ENDPOINTS,endpoints)
        write_table(parent,files,prefix+'_masters.tsv',['reference','clock_pin','master'],[dict(reference=row['reference'],clock_pin=row['clock_pin'],master='hist' if row['reference']==INSTANCE else 'DFF') for row in endpoints])
        write_table(parent,files,prefix+'_clocks.tsv',['clock','source_kind','source'],[dict(clock='actual_core',source_kind='pin',source='PLL/OUT')])
        write_table(parent,files,prefix+'_roots.tsv',['clock_edge','late_ps','early_ps'],[dict(clock_edge='actual_core',late_ps='0',early_ps='0')])
        write_table(parent,files,prefix+'_parent_targets.tsv',['instance'],[dict(instance=INSTANCE)])
        rel=[dict(launch_data_pin=INSTANCE+'/o[0]',capture_data_pin='u_rx/D',launch_clock_ref=INSTANCE,setup_capture_clock_ref='u_rx',hold_capture_clock_ref='u_rx'),
             dict(launch_data_pin='u_tx/QN',capture_data_pin=INSTANCE+'/i[0]',launch_clock_ref='u_tx',setup_capture_clock_ref=INSTANCE,hold_capture_clock_ref=INSTANCE)]
        write_table(parent,files,prefix+'_parent_relations.tsv',C.RELATIONS,rel)
        paths=[]
        for row in rel:
            for delay in ('max','min'):
                lp=next(e['clock_pin'] for e in endpoints if e['reference']==row['launch_clock_ref'])
                cp=next(e['clock_pin'] for e in endpoints if e['reference']==row['setup_capture_clock_ref'])
                path=dict(launch_data_pin=row['launch_data_pin'],capture_data_pin=row['capture_data_pin'],delay=delay,status='EXACT_STD_PATH',actual_startpoint=row['launch_data_pin'],actual_endpoint=row['capture_data_pin'],check_role='setup' if delay=='max' else 'hold',native_std_slack_ps='123.5',launch_clock_pin=lp,launch_clock='actual_core',launch_pin_edge='rise',launch_source_pin='PLL/OUT',launch_source_edge='rise',launch_source_insertion_ps='12.5',capture_clock_pin=cp,capture_clock='actual_core',capture_pin_edge='rise',capture_source_pin='PLL/OUT',capture_source_edge='rise',capture_source_insertion_ps='12.5',launch_clock_pin_arrival_ps='15.5',capture_clock_pin_arrival_ps='16.5')
                paths.append(path)
        write_table(parent,files,corner+'/parent_boundary_std_'+corner+'.tsv',C.STD,paths)
        counts=parent/corner/('parent_boundary_std_'+corner+'_counts.tsv'); counts.write_text('phase\tORIGINAL_STD_BEFORE_ZERO_UNCERTAINTY\nerrors\t0\nmissing_paths\t0\nlimited_paths\t0\nnative_engine_cppr_enabled\ttrue\n');files[str(counts.relative_to(parent))]=C.digest(counts)
        lib=dict(path='/work/macros/hist_'+corner+'.lib',sha256=attachment['actual_selected_libraries'][corner]['sha256'])
        write_json(parent/corner/'libraries.json',dict(status='LOADED',corner=corner.upper(),libraries=[lib]));files[corner+'/libraries.json']=C.digest(parent/corner/'libraries.json')
        inp=parent/(prefix+'_inputs.tsv');inp.write_text('liberty\t'+lib['path']+'\t'+lib['sha256']+'\n');files[prefix+'_inputs.tsv']=C.digest(inp)
        pw['corners'][corner]=dict(files=files,parent_boundary_relations=dict(scope='REGISTER_STARTPOINT_INTERFACE_RELATIONS_BEFORE_CLOCK_DEDUP',std_path_evidence=dict(paths=4)))
    write_json(parent/'witness.json',pw)
    return tmp_path


def run(root,parent=True,instances=None):
    return C.consume(root/'attachment.json',root/'qualification.json',root/'maps.json',root/'native/witness.json',root/'native',instances or [INSTANCE],root/'parent/witness.json' if parent else None,root/'parent' if parent else None)


def rewrite_parent(root, corner, suffix, edit):
    w=C.read_json(root/'parent/witness.json');files=w['corners'][corner]['files'];name=next(n for n in files if n.endswith(suffix));p=root/'parent'/name;p.write_text(edit(p.read_text()));files[name]=C.digest(p);write_json(root/'parent/witness.json',w)


def test_exact_DATA_fanout_root_edges_and_polarity_are_separate(tmp_path):
    r=run(fixture(tmp_path))
    assert r['status']=='NATIVE_IDENTITY_RELATIONS_EXPANDED'
    assert r['qualification']=='NOT_ASSERTED' and r['parent_coverage']==C.UNEXPANDED
    assert r['additional_clock_or_cppr_credit']=='NONE'
    rows=r['corners']['tt']['relations'];launch=rows[0]['identities']['max']['launch']
    assert launch['native_endpoints'][0]['data_inversions']==1
    assert launch['native_endpoints'][0]['native_root_edge']=='rise'
    assert launch['parent_observed']['source']['source']=='PLL/OUT'
    assert launch['parent_observed']['source']['source']!=r['selected_input_context']['parent_structural_clock_net']
    assert launch['native_endpoints'][0]['expanded_reference']==INSTANCE+'/L'
    assert len(rows[1]['identities']['min']['capture']['native_endpoints'])==2
    assert len(rows[1]['identities']['min']['endpoint_identity_pairs'])==2
    assert rows[0]['identities']['max']['original_STD_observation']['native_std_slack_ps']=='123.5'


def test_absent_parent_payload_does_not_promote_structural_net(tmp_path):
    r=run(fixture(tmp_path),False)
    assert r['status']=='UNEXPANDED' and r['qualification']=='NOT_ASSERTED'
    assert len(r['native_identity_index']['tt'])==2 and r['corners']=={}


@pytest.mark.parametrize('status',['LIMIT','NO_PATH','ERROR'])
def test_parent_nonexact_status_remains_unexpanded(tmp_path,status):
    root=fixture(tmp_path);rewrite_parent(root,'tt','parent_boundary_std_tt.tsv',lambda s:s.replace('EXACT_STD_PATH',status,1))
    assert run(root)['status']=='UNEXPANDED'


@pytest.mark.parametrize('which',['library','bit','root','source','ambiguous_source','missing_ff','parent_source'])
def test_exact_corner_source_bit_and_consumed_lib_controls(tmp_path,which):
    root=fixture(tmp_path)
    if which=='library':
        rewrite_parent(root,'tt','libraries.json',lambda s:s.replace('1'*64,'8'*64))
        rewrite_parent(root,'tt','_inputs.tsv',lambda s:s.replace('1'*64,'8'*64))
    elif which=='bit':
        rewrite_parent(root,'tt','_parent_relations.tsv',lambda s:s.replace('/i[0]','/i[99]'))
        rewrite_parent(root,'tt','parent_boundary_std_tt.tsv',lambda s:s.replace('/i[0]','/i[99]'))
    elif which=='root':rewrite_parent(root,'tt','_roots.tsv',lambda s:s.replace('actual_core','wrong_root'))
    elif which=='source':rewrite_parent(root,'tt','parent_boundary_std_tt.tsv',lambda s:s.replace('PLL/OUT','wrong_source'))
    elif which=='ambiguous_source':rewrite_parent(root,'tt','_clocks.tsv',lambda s:s+'actual_core\tpin\tPLL/OUT\n')
    elif which=='missing_ff':
        w=C.read_json(root/'parent/witness.json');w['corners']['ff'].pop('parent_boundary_relations');write_json(root/'parent/witness.json',w)
    elif which=='parent_source':
        w=C.read_json(root/'parent/witness.json');w['native']['6_final.v']='0'*64;write_json(root/'parent/witness.json',w)
    r=run(root);assert r['status']=='UNEXPANDED' and r['qualification']=='NOT_ASSERTED'


def test_selected_wrong_lib_and_partial_instance_are_rejected(tmp_path):
    root=fixture(tmp_path);a=C.read_json(root/'attachment.json');a['actual_selected_libraries']['ff']['sha256']='1'*64;write_json(root/'attachment.json',a)
    assert run(root)['status']=='UNEXPANDED'
    root=fixture(tmp_path/'other');assert run(root,instances=['u_q.u_s.u_hc'])['status']=='UNEXPANDED'


def test_ambiguous_native_bit_never_becomes_a_single_endpoint(tmp_path):
    root=fixture(tmp_path);m=C.read_json(root/'maps.json');m['maps']['inputs']['i[0]'].append(copy.deepcopy(m['maps']['inputs']['i[0]'][0]));write_json(root/'maps.json',m)
    q=C.read_json(root/'qualification.json');q['boundary_maps']['artifact_sha256']=C.digest(root/'maps.json');write_json(root/'qualification.json',q)
    a=C.read_json(root/'attachment.json');a['boundary_maps']['sha256']=C.digest(root/'maps.json');a['child_qualification']['sha256']=C.digest(root/'qualification.json');a['instances'][0]['boundary_map_artifact_sha256']=C.digest(root/'maps.json');write_json(root/'attachment.json',a)
    r=run(root);assert r['status']=='UNEXPANDED' and any('ambiguous native DATA' in s for s in r['reasons'])


def test_actual_retained_HC0_selected_identity_stays_unexpanded_without_STA():
    location=os.environ.get('OT_CHILD_CLOCK_FIXTURE')
    if not location:pytest.skip('actual immutable HC0 attachment supplied explicitly')
    root=Path(location)
    r=C.consume(root/'attachment.json',root/'qualification.json',root/'boundary_maps.json',root/'native/child_clock_witness.json',root/'native',[INSTANCE])
    assert r['status']=='UNEXPANDED' and r['parent_coverage']==C.UNEXPANDED and r['qualification']=='NOT_ASSERTED'
    assert len(r['native_identity_index']['tt'])==len(r['native_identity_index']['ff'])==433
    assert r['selected_input_context']['parent_structural_clock_net']=='ck'
    assert all(e['instance']==INSTANCE for row in r['native_identity_index']['tt'].values() for e in row['endpoints'])


def test_setup_and_hold_capture_reference_aliases_are_not_deduplicated(tmp_path):
    root=fixture(tmp_path)
    for corner in ('tt','ff'):
        alias='u_rx@ALTCLK:rise'
        rewrite_parent(root,corner,'_endpoints.tsv',lambda s:s+'u_rx@ALTCLK:rise\tu_rx/ALTCLK\tactual_core\t7\t6\trise\n')
        rewrite_parent(root,corner,'_masters.tsv',lambda s:s+'u_rx@ALTCLK:rise\tu_rx/ALTCLK\tDFF\n')
        rewrite_parent(root,corner,'_parent_relations.tsv',lambda s:s.replace(INSTANCE+'\tu_rx\tu_rx',INSTANCE+'\tu_rx\t'+alias))
        def change_hold(text):
            rows=text.splitlines();header=rows[0].split('\t');out=[rows[0]]
            for row in rows[1:]:
                values=row.split('\t')
                if values[header.index('capture_data_pin')]=='u_rx/D' and values[header.index('delay')]=='min':values[header.index('capture_clock_pin')]='u_rx/ALTCLK'
                out.append('\t'.join(values))
            return '\n'.join(out)+'\n'
        rewrite_parent(root,corner,'parent_boundary_std_'+corner+'.tsv',change_hold)
    r=run(root);assert r['status']=='NATIVE_IDENTITY_RELATIONS_EXPANDED'
    row=r['corners']['tt']['relations'][0]['identities']
    assert row['max']['capture']['parent_observed']['reference']=='u_rx'
    assert row['min']['capture']['parent_observed']['reference']=='u_rx@ALTCLK:rise'
    assert row['max']['capture']['parent_observed']['instance']==row['min']['capture']['parent_observed']['instance']=='u_rx'
    assert row['min']['endpoint_identity_pairs'][0]['parent_capture_clock_reference']=='u_rx@ALTCLK:rise'
    assert r['qualification']=='NOT_ASSERTED'
