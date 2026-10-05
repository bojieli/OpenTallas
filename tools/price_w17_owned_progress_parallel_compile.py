"""Source-identical sixteen-worker compile price from retained per-child RSS."""
import copy,hashlib,json,math,re
from pathlib import Path
BASE='results/rtl/w17_owned_progress_native_build_handoff_20261002'
METADATA='results/rtl/w17_connected_observation_fulltoken_preparation_20261002/retained_build_metadata.json'
OUT='results/rtl/w17_owned_progress_parallel_compile_20261002'

def price(root,workers=16):
    logs=json.loads((root/METADATA).read_text())['logs']
    builds=[x for x in logs if 'build_die' in x['path']]
    peaks=[int(re.search(r'Maximum resident set size \(kbytes\): (\d+)', '\n'.join(x['metrics_and_command'])).group(1)) for x in builds]
    cpu=sum(float(re.search(r'User time \(seconds\): ([0-9.]+)', '\n'.join(x['metrics_and_command'])).group(1)) for x in builds)
    rss=max(peaks)/(1<<20);request=math.ceil(workers*rss*1.25+8)
    if type(workers) is not int or workers<1 or workers>48 or request>94:raise ValueError('RSS margin exceeds per-request fleet budget')
    inherited=json.loads((root/BASE/'native_commands.json').read_text());phases=copy.deepcopy(inherited['phases'])
    for phase in phases:
        if phase['kind']=='CXX_archive':
            if phase['argv'].count('-j2')!=1:raise ValueError('original make job binding')
            phase['argv']=[f'-j{workers}' if x=='-j2' else x for x in phase['argv']]
            phase.update(CPU=workers,aggregate_memory_GiB=request,wall_seconds=3600)
    return dict(status='SOURCE_IDENTICAL_PARALLEL_COMPILE_PRICE',source_commit=inherited['source_commit'],inherited_manifest_sha256=hashlib.sha256((root/BASE/'native_commands.json').read_bytes()).hexdigest(),metadata_sha256=hashlib.sha256((root/METADATA).read_bytes()).hexdigest(),workers=workers,largest_measured_child_RSS_KiB=max(peaks),measured_RSS_scope='Retained original per-child maximum, not fresh aggregate or successor measurement',RSS_margin_multiplier=1.25,other_process_overhead_GiB=8,CXX_aggregate_cap_GiB=request,one_group_user_CPU_seconds=cpu,two_mode_user_CPU_seconds=2*cpu,two_mode_CPU_only_projection_seconds=2*cpu/workers,projection_is_service_or_wall_bound=False,phases=phases,compile_cap_sum_seconds=sum(p['wall_seconds'] for p in phases),link_cap_seconds=240,disk_with_traces_and_reserve_GiB=56,minimum_live_reserve_GiB=24,fresh_free_RAM_required_GiB=request+24,container_image=inherited['container_image'],enforcement=dict(CPU='Docker --cpus16 and --cpuset-cpus16 selected host CPUs; make-j16',memory='Docker --memory88g --memory-swap88g: entire compiler tree aggregate cgroup cap; cap hit terminal failure',threads='One CXX phase at a time; coordination limits all VM jobs to48aggregate job threads; no automatic metadata enforcement',frontend='Serial original --cc phases with64GiB cgroup and64GiBAS,2CPUs,600s',logs='16MiB shared gate cap; stop first failure, no retry or warning waiver',supervisor='Must inspect exact container digest and fresh headroom before each phase; timeout must stop named owned container/process tree; not merely make client'),source_arguments_changed=['CXX make concurrency -j2 to -j16 only'],functional_RTL_changes=0,default_off_observer_preserved=True,target_mapping_requirements=['persistent layer0..39 plus final norm/head programme and rank/physical mapping','RTL-produced stage handoffs rather than golden reloads','exact FAST1 PP1 CUT379 LAT8 field and attention artifact identity','actual ownership/provider retirement, causal finite deadline and cancellation joined interface','complete host link against actual generated Vdie/attention classes','exact final output comparison'],native_helper_transfer_credit=False,execution_authorized=False)

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    with (root/OUT/'parallel_compile_plan.json').open('x') as f:f.write(json.dumps(price(root),indent=2)+'\n')
