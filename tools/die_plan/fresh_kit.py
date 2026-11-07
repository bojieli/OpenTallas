#!/usr/bin/env python3
"""Fresh preparation through existing factories, without routing or legacy tool overlays.

Run heavy preparation through ot-run. A partition specification names an existing
read-only bind/profile; s81-coll names the canonical core recipe. Overrides are
explicit JSON, never shell snippets. The output must not exist. A review image is
produced, but a person still reviews it before route. Existing signoff is unchanged.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text())


def keys(value, allowed, label):
    unknown = set(value) - set(allowed)
    if unknown:
        raise ValueError(f'{label}: unsupported fields {sorted(unknown)}; encode a reviewed factory recipe instead')


def render_core(kit, output):
    """Render the generated kit's exact macro placements/pins; no placed/routed claim."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    f = read(kit / 'freeze.json')
    w, h = f['outline_um']
    fig, ax = plt.subplots(figsize=(7, 8))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False))
    for master, sites in f.get('macros', {}).items():
        lef = (kit / 'macros' / (master + '.lef')).read_text()
        m = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef)
        if not m:
            raise ValueError(f'cannot render macro size: {master}')
        mw, mh = map(float, m.groups())
        for x, y, orientation in sites:
            rw, rh = (mh, mw) if orientation in ('E', 'W', 'FE', 'FW', 'R90', 'R270') else (mw, mh)
            ax.add_patch(Rectangle((x, y), rw, rh, facecolor='0.8', edgecolor='0.4', linewidth=.4))
    pins = read(kit / 'pins.json')
    ax.scatter([p['x'] for p in pins], [p['y'] for p in pins], s=2, color='teal')
    ax.set(xlim=(-5, w+5), ylim=(-5, h+5), aspect='equal', xlabel='um', ylabel='um',
           title=f"{f['module']}: generated macro/pin plan (not routed)")
    fig.tight_layout(); fig.savefig(output, dpi=130); plt.close(fig)


def prepare(source, profile, plan, output, *, type_name=None, core_spec=None, overrides=None,
            history_pack=None, image='openroad/orfs:asap7lock', mem=16, cpus=2, run=subprocess.run):
    source, plan, output = map(lambda p: Path(p).resolve(), (source, plan, output))
    overrides = dict(overrides or {})
    if mem <= 0 or cpus <= 0:
        raise ValueError('memory and CPU budgets must be positive')
    if profile == 'partition':
        keys(overrides, ('bind_out', 'asbuilt', 'instance', 'reset_mode', 'assembly_contracts',
                         'util', 'skip_kit_ir', 'reset_context_plan', 'reset_expected', 'bind_context_plan', 'component_proof', 'library_profile'), 'partition overrides')
        keys(overrides.get('reset_expected', {}), ('entry', 'depth', 'release_clocks'), 'reset expected contract')
        if not type_name or core_spec or not overrides.get('bind_out'):
            raise ValueError('partition needs --type and overrides.bind_out; no core spec')
        if overrides.get('reset_mode') == 'native' and read(plan).get('reset') and not overrides.get('reset_context_plan'):
            raise ValueError('native reset needs reset_context_plan; an isolated plan can invent a different root/tree')
        if overrides.get('reset_mode') not in ('native', 'canonical'):
            raise ValueError('choose reset_mode native (full original context) or canonical (kit_rsync)')
        if read(plan)['partition_types'][type_name].get('hard') and (overrides['reset_mode']!='native' or overrides.get('reset_expected')):
            raise ValueError('hard bound partitions preserve their delivered native reset; no generated canonical reset tree/expected tree')
    elif profile == 's81-coll':
        keys(overrides, ('clock_pin',), 'compact COLL overrides')
        if type_name or not core_spec or not overrides.get('clock_pin'):
            raise ValueError('s81-coll needs --core-spec and overrides.clock_pin; no partition type')
        core_spec = read(core_spec) if not isinstance(core_spec, dict) else dict(core_spec)
        keys(core_spec, ('module', 'recipes'), 'core specification')
        if core_spec.get('module') not in ('dsfd_coll_lane_e_safe8_ntf', 'dsfd_coll_lane_w_safe8_ntf'):
            raise ValueError('s81-coll supports the two explicit compact COLL modules only')
        if not core_spec.get('recipes'):
            raise ValueError('core specification needs recipes')
        recipe = read(core_spec['recipes'])[core_spec['module']]
        if recipe.get('plan') and Path(recipe['plan']).resolve() != plan:
            raise ValueError('explicit plan differs from selected core recipe plan')
    else:
        raise ValueError(f'unsupported profile {profile!r}')
    if output.exists():
        raise ValueError(f'output already exists: {output}; original kits/runs are never updated')
    dp = source / 'tools/die_plan'
    identity = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    output.mkdir(parents=True)
    record = dict(schema='opentallas.fresh_kit.v1', profile=profile, source=str(source),
                  tool_commit=identity, plan=str(plan), overrides=overrides, stages=[], review='NOT REVIEWED')

    def save():
        (output / 'fresh_kit.json').write_text(json.dumps(record, indent=2) + '\n')

    def step(name, script, *args):
        command = script if isinstance(script, list) else [sys.executable, '-I', str(script), *map(str, args)]
        result = run(command, cwd=source, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = output / (name + '.log'); log.write_text(result.stdout or '')
        record['stages'].append(dict(name=name, command=command, rc=result.returncode, log=str(log)))
        save()
        if result.returncode:
            raise RuntimeError(f'{name} failed rc {result.returncode}; see {log}')

    try:
        if history_pack:
            step('history', source / 'tools/autopilot/source_history.py', 'install', '--repo', source,
                 '--pack', Path(history_pack).resolve())
        if profile == 'partition':
            sys.path.insert(0,str(dp))
            import kit_topology as KT
            rtl = output / 'rtl'
            bind_out=Path(overrides['bind_out']).resolve()
            context=Path(overrides.get('bind_context_plan',overrides.get('reset_context_plan',plan))).resolve()
            context_raw=read(context)
            selected_raw=read(plan)
            component_report=None
            if overrides.get('component_proof'):
                component_report=KT.verify_component_source(Path(overrides['component_proof']).resolve(),
                    context_plan=context,prepared_plan=plan,bind_out=bind_out,type_name=type_name,
                    instance=overrides.get('instance'),asbuilt=overrides.get('asbuilt'))
                record.update(source_scope='LOCAL_COMPONENT',source_preparation_only=True,
                              component_report=component_report,global_bind=component_report['global_bind'])
            if component_report is None and (type_name not in context_raw['partition_types'] or KT.native_contract(dict(selected_raw,asbuilt=context_raw.get('asbuilt',{})) if not overrides.get('asbuilt') else selected_raw,overrides.get('asbuilt'),context)['types'][type_name]!=KT.native_contract(context_raw,overrides.get('asbuilt'),context)['types'][type_name]):
                raise ValueError('selected stage/reset topology differs from bind_context_plan; update the full native context before regeneration')
            if KT.has_topology(selected_raw,type_name,overrides.get('asbuilt')) and component_report is None and not KT.bind_matches(context_raw,type_name,bind_out,overrides.get('asbuilt'),context):
                # A stage/reset change must be emitted by the native factory.
                # Never repair a cached bound body with a private source patch.
                if not overrides.get('asbuilt'):
                    raise ValueError('native topology is unrecorded or changed: supply explicit asbuilt and bind_context_plan to regenerate native bind')
                regenerated=output/'native_bind';regenerated.mkdir()
                cached=bind_out/'asbuilt.json'
                old_receipt=bind_out/'native_topology.json'
                cfg_sha=hashlib.sha256(Path(overrides['asbuilt']).read_bytes()).hexdigest()
                reusable=old_receipt.is_file() and read(old_receipt).get('asbuilt_sha256')==cfg_sha
                if cached.is_file() and reusable:
                    (regenerated/'asbuilt.json').symlink_to(cached)
                else:
                    step('native_elab',dp/'bind.py','elab',context,'--out',regenerated,
                         '--asbuilt',overrides['asbuilt'],'--mem',mem)
                step('native_bind',dp/'bind.py','bind',context,'--out',regenerated,
                     '--asbuilt',overrides['asbuilt'],'--strict','--all-gaps','--mem',mem)
                if not KT.bind_matches(context_raw,type_name,regenerated,overrides.get('asbuilt'),context):
                    raise ValueError('native bind did not record the selected stage/reset topology')
                bind_out=regenerated
            record['native_bind']=str(bind_out)
            args = [plan, '--out', bind_out, '--type', type_name, '--kit', rtl]
            for key in ('asbuilt', 'instance'):
                if overrides.get(key):
                    args += ['--' + key, overrides[key]]
            if overrides.get('component_proof'):
                args += ['--component-proof',str(Path(overrides['component_proof']).resolve())]
            if overrides.get('library_profile'):
                args += ['--library-profile',str(Path(overrides['library_profile']).resolve())]
            step('kit_rtl', dp / 'bind.py', 'kit-rtl', *args)
            if overrides.get('library_profile') and not read(rtl / 'kit_rtl.json').get('library_profile_selected'):
                raise ValueError('kit-rtl did not record the selected library profile replacements')
            receipt = output / 'kit_assembly.json'
            if overrides.get('assembly_contracts'):
                step('hard_views', dp / 'kit_hard_views.py', '--plan', plan, '--type', type_name,
                     '--rtl-dir', rtl, '--contracts', Path(overrides['assembly_contracts']).resolve())
                step('assembly', dp / 'kit_assembly.py', 'assemble', '--rtl-dir', rtl, '--contracts',
                     Path(overrides['assembly_contracts']).resolve(), '--receipt', receipt)
            if (overrides['reset_mode'] == 'canonical' or overrides.get('reset_context_plan')) and not selected_raw['partition_types'][type_name].get('hard'):
                reset_plan = Path(overrides.get('reset_context_plan', plan)).resolve()
                step('reset', dp / 'kit_rsync.py', reset_plan, type_name, rtl)
                # Native profiles use the full original context: an isolated
                # extraction can change relay entry into a root synchronizer.
                manifest = read(rtl / 'kit_rtl.json')
                expected = overrides.get('reset_expected', {})
                if 'kit_rsync' not in manifest and (rtl / 'bound_reset.json').is_file():
                    # S81-RCK-3 11-06: kit_rsync preserved the verified bound native reset (a376b4bddb): it generates
                    # no canonical tree, so there is nothing to compare; an expected tree cannot be honoured.
                    if expected:
                        raise ValueError('bound native reset preserved: no generated canonical reset tree for reset_expected')
                    record['reset_context'] = dict(plan=str(reset_plan), actual='preserved_bound_native_reset')
                    expected = {}
                    actual = {}
                else:
                    actual = manifest['kit_rsync']['reset_tree']
                    record['reset_context'] = dict(plan=str(reset_plan), actual=actual)
                mismatch = {k: dict(expected=v, actual=actual.get(k)) for k, v in expected.items() if actual.get(k) != v}
                if mismatch:
                    raise ValueError(f'canonical reset differs from selected native contract: {mismatch}')
            # Never omit this because generation/frontend happened to succeed.
            station_args=['prepare-stations',plan,type_name,rtl]
            if component_report is not None:
                station_args += ['--native-plan',context]
            step('istations', dp / 'kit_topology.py', *station_args)
            census=read(rtl/'kit_topology.json')
            shutil.copyfile(rtl/'kit_topology.json',output/'kit_topology.json')
            if census['problems']:
                raise ValueError('emitted native topology differs from plan: '+'; '.join(census['problems']))
            args = ['phys', plan, '--out', output / 'gen', '--rtl-root', source, '--types', type_name,
                    '--kit-rtl', f'{type_name}={rtl / "kit_rtl.f"}', '--trial',
                    '--util', overrides.get('util', .4)]
            if selected_raw['partition_types'][type_name].get('hard'):
                args += ['--hard-wrappers',type_name]
            if (rtl / 'bound_reset.json').is_file():
                args += ['--bound-native-reset', type_name]
            if overrides.get('skip_kit_ir', True):
                args += ['--skip-kit-ir']
            step('generate', dp / 'gen.py', *args)
            kit = output / 'gen' / type_name
            if receipt.exists():
                # Carry the existing assembly helper/manifest into the generated
                # kit; rtl_lint supplies inventory using its one native frontend.
                for name in ('kit_assembly.json', 'kit_assembly.py'):
                    shutil.copyfile(output / name, kit / name)
            KT.install_inventory(census,kit/'kit_assembly.json',read(plan)['partition_types'][type_name]['module'])
            shutil.copyfile(output/'kit_topology.json',kit/'kit_topology.json')
        else:
            step('generate', source / 'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py',
                 '--module', core_spec['module'], '--recipes', Path(core_spec['recipes']).resolve(),
                 '--plan', plan, '--out', output / 'gen', '--trial')
            kits = list((output / 'gen').glob('*/freeze.json'))
            if len(kits) != 1:
                raise ValueError('core factory did not produce exactly one fresh kit')
            kit = kits[0].parent
            step('compact_form', HERE / 'compact_coll_form.py', source, kit, Path(overrides['clock_pin']).resolve())
            # Zero signed-child substitutions, but retain the explicit parent
            # profile so the existing frontend writes its actual native inventory.
            contracts = output / 'core_inventory_profile.json'
            contracts.write_text(json.dumps(dict(children=[], parameter_contracts=[],
                parent_profile=dict(top=core_spec['module'], parameters=recipe.get('params', {}))), indent=2)+'\n')
            step('core_inventory_profile', dp / 'kit_assembly.py', 'assemble', '--rtl-dir', kit / 'rtl',
                 '--contracts', contracts, '--receipt', kit / 'kit_assembly.json')
        record['kit'] = str(kit); save()
        # Factory configs deliberately use /work paths, including macro Liberty.
        # Run their one existing frontend in the same image/mount as run_kit.
        try:
            dk = ['docker'] if subprocess.call(['docker', 'ps'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0 else ['sudo', 'docker']
        except OSError:
            dk = ['docker']  # the stage reports the missing runtime normally
        step('rtl_lint', dk + ['run', '--rm', '--cpus', str(cpus), '--memory', f'{mem}g',
             '--memory-swap', f'{mem}g', '-v', f'{kit}:/work', '-w', '/OpenROAD-flow-scripts/flow',
             image, 'bash', '-lc', 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/rtl_lint.py /work'])
        if (kit/'kit_assembly.json').exists() and not (kit/'kit_hierarchy.json').is_file():
            raise ValueError('existing frontend did not produce the selected parent/station inventory')
        if (kit / 'kit_hierarchy.json').is_file():
            record['inventory'] = str(kit / 'kit_hierarchy.json')
            record['frontend_json'] = str(kit / 'kit_assembly_elaborated.json')
            actual_inventory=read(kit/'kit_hierarchy.json')
            if actual_inventory.get('status')=='NOT RUN' or actual_inventory.get('problems'):
                raise ValueError('actual frontend hierarchy differs from selected child/station topology')
        review = output / 'review'; review.mkdir()
        if profile == 'partition':
            step('render', source / 'tools/geom_review/plan_review.py', plan, review, '--tools', dp)
            image = review / 'die_cores.png'
        else:
            image = review / 'kit_plan.png'; render_core(kit, image)
        record.update(verdict='PREPARED', review_image=str(image), review_record=str(review / 'fresh_review.json'))
        (review / 'fresh_review.json').write_text(json.dumps(dict(verdict='NOT REVIEWED', image=str(image),
            kit=str(kit), basis='generated geometry; review before route; physical signoff NOT RUN'), indent=2)+'\n')
        save(); return record
    except Exception as error:
        record.update(verdict='FAILED', error=str(error)); save(); raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True); p.add_argument('--profile', required=True, choices=('partition', 's81-coll'))
    p.add_argument('--plan', required=True); p.add_argument('--out', required=True)
    p.add_argument('--type', dest='type_name'); p.add_argument('--core-spec'); p.add_argument('--overrides', required=True)
    p.add_argument('--history-pack')
    p.add_argument('--image', default=os.environ.get('OT_ORFS_IMAGE', 'openroad/orfs:asap7lock'))
    p.add_argument('--mem', type=int, default=16); p.add_argument('--cpus', type=int, default=2)
    a = p.parse_args()
    try:
        print(json.dumps(prepare(a.source, a.profile, a.plan, a.out, type_name=a.type_name, core_spec=a.core_spec,
                                 overrides=read(a.overrides), history_pack=a.history_pack,
                                 image=a.image, mem=a.mem, cpus=a.cpus)))
    except (ValueError, RuntimeError, OSError, ImportError, subprocess.SubprocessError) as error:
        p.exit(1, f'fresh_kit: {error}\n')


if __name__ == '__main__':
    main()
