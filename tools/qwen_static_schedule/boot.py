"""Compile earliest fixed traffic edges from source-bound physical reset paths.

The die owner supplies every physical instance, reset relay, pin arrival delay,
and compensated clock profile. Missing graph/phase evidence is an error. Runtime
ready never alters a descriptor; release and first traffic are compiler times.
"""
import hashlib,json
from pathlib import Path
from .calendar import ScheduleError


def _pins(root, bindings):
    if not bindings:
        raise ScheduleError('boot path requires actual source/physical receipt hashes')
    for name, digest in bindings.items():
        path = Path(root) / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ScheduleError('boot source/physical receipt differs: '+name)


def _advance(time_fs, stage, clocks):
    try:
        clock = clocks[stage['clock']]
        period, phase = clock['period_fs'], clock['phase_fs']
        edges = stage['edges']
        delay, setup, cq = stage['net_delay_fs'], stage['setup_fs'], stage['cq_fs']
    except KeyError as error:
        raise ScheduleError('missing physical boot clock/relay field: '+str(error)) from error
    if period <= 0 or edges <= 0 or min(delay, setup, cq) < 0:
        raise ScheduleError('invalid measured boot clock/relay timing')
    # Release at a source edge cannot be consumed at that same edge. Include
    # the actual wire and setup before counting complete receiving clock edges.
    sample = phase + ((time_fs + delay + setup - phase)//period + 1)*period
    return sample + (edges-1)*period + cq


def compile_boot(local, graph, root):
    if not graph.get('complete') or graph.get('missing'):
        raise ScheduleError('complete actual die reset graph/phase profile is required')
    _pins(root, graph.get('source_sha256'))
    clocks = graph['clocks']
    for name, clock in clocks.items():
        if clock.get('phase_kind') != 'compensated_phi_minus_R':
            raise ScheduleError('boot clock must use actual compensated child phase')
        _pins(root, clock.get('source_sha256'))
        profile = clock.get('profile_path')
        if not profile or profile not in clock['source_sha256']:
            raise ScheduleError('actual compensated clock receipt path is required')
        receipt = json.loads((Path(root)/profile).read_text())['clocks'][name]
        if any(clock.get(key) != receipt.get(key) for key in ('period_fs','phase_fs','phase_kind')):
            raise ScheduleError('boot phase differs from actual compensated receipt')
    instances = graph['instances']
    inventory_path = graph.get('instance_inventory_path')
    if not inventory_path or inventory_path not in graph['source_sha256']:
        raise ScheduleError('source-pinned complete physical instance inventory is required')
    inventory = json.loads((Path(root)/inventory_path).read_text())['instances']
    actual = {x['instance']:(x['master'],x['parameters']) for x in inventory}
    supplied = {x['instance']:(x['master'],x['parameters']) for x in instances}
    if actual != supplied or len(actual) != len(inventory):
        raise ScheduleError('reset graph does not cover every actual physical instance')
    if not instances or len({x['instance'] for x in instances}) != len(instances):
        raise ScheduleError('boot requires unique actual physical instance inventory')
    result = {}
    pending = list(instances)
    while pending:
        changed = False
        for item in pending[:]:
            parent = item.get('reset_from_instance')
            if parent is not None and parent not in result:
                continue
            if item['master'] not in local['masters']:
                raise ScheduleError('actual master has no local reset source contract: '+item['master'])
            spec = local['masters'][item['master']]
            _pins(root, spec['source_sha256'])
            if item['parameters'] != spec['parameters']:
                raise ScheduleError('actual reset master parameters differ')
            stages = item['reset_path']
            if not stages or stages[-1]['edges'] != spec['reset_deassert_edges_after_pin']:
                raise ScheduleError('actual local reset pipeline is missing from path')
            time = result[parent]['reset_release_fs'] if parent is not None else item['root_release_fs']
            for stage in stages:
                time = _advance(time, stage, clocks)
            dependencies = item['child_instances']
            expected = sorted(spec['child_reset_dependencies'])
            actual = sorted(next(x['master'] for x in instances if x['instance'] == child) for child in dependencies)
            if actual != expected:
                raise ScheduleError('actual child reset dependencies differ')
            traffic = item['first_traffic_fs']
            if traffic <= time:
                raise ScheduleError('compiled traffic precedes actual reset release: '+item['instance'])
            result[item['instance']] = dict(reset_release_fs=time,first_traffic_fs=traffic,
                source_master=item['master'],data_successor_delta_edges=spec['data_successor_delta_edges'],
                fault_successor_delta_edges=spec['fault_vs_legacy_delta_edges'])
            pending.remove(item);changed=True
        if not changed:
            raise ScheduleError('cyclic or missing actual reset producer')
    # A parent that launches traffic into a child must account for that child's
    # complete local reset, even when the child uses another compensated phase.
    for item in instances:
        if any(item['first_traffic_fs'] <= result[child]['reset_release_fs'] for child in item['child_instances']):
            raise ScheduleError('parent traffic precedes child reset: '+item['instance'])
    return dict(schema='opentallas.qwen.boot-calendar.v1',instances=result,
                fixed_first_traffic_fs=min(r['first_traffic_fs'] for r in result.values()))


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local',required=True,type=Path)
    parser.add_argument('--graph',required=True,type=Path)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    try:
        result=compile_boot(json.loads(args.local.read_text()),json.loads(args.graph.read_text()),args.root)
    except (ScheduleError,KeyError,FileNotFoundError)as error:
        parser.exit(1,'BOOT CALENDAR REFUSED: '+str(error)+'\n')
    args.out.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
