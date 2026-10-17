#!/usr/bin/env python3
"""Emit propagated-clock STA for a source-bound physical clock pilot.

Requires source-exact consumed libraries for every entry by default. An explicit
partial diagnostic allows missing-load blackboxes, prominently records them and
cannot qualify either clock insertion or the die. Never assigns ideal per-sink
latencies or negative phases. Physical compensation must be implemented as cells
in a successor ODB and then remeasured.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()


def emit(candidate, dump, binding, source, out, partial=False):
    manifest=json.loads(candidate.read_text())
    table=json.loads(binding.read_text())['bound']
    master={}
    for line in dump.read_text().splitlines():
        s=line.split('\t')
        if s[0]=='T': master[s[1]]=s[2]
    entries=manifest['entries']
    used=Counter(master[e['pin']] for e in entries)
    libs, missing, hashes = {}, {}, {}
    for corner in ('tt','ff'):
        libs[corner]=set()
        for name,count in used.items():
            row=table.get(name,{})
            info=row.get('files',{}).get(corner)
            if not info:
                missing.setdefault(name,dict(entries=count,reason='not in actual consumed view binding'))
                continue
            path=source/info['path']
            if not path.exists() or sha(path)!=info['sha256']:
                raise ValueError(f'bound library missing or hash mismatch: {path}')
            text=path.read_text()
            if not re.search(r'\bcell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)',text):
                raise ValueError(f'bound Liberty has no actual master {name}: {path}')
            libs[corner].add(str(path))
            hashes[str(path)]=info['sha256']
    insertions, missing_insertion = {}, {}
    for entry in entries:
        key=entry['pin']; name=master[key]; port=key.rsplit('/',1)[1]
        row=table.get(name,{})
        path=source/row.get('export_dir','')/'insertion.json'
        if not path.is_file():
            missing_insertion[key]='no consumed per-clock insertion.json'
            continue
        raw=json.loads(path.read_text())
        measure=raw.get('clock_measurements',{}).get(port)
        if measure is None and raw.get('lib_clock_pin') == port:
            measure=raw
        if measure is None:
            missing_insertion[key]='no exact actual child clock mapping; no scalar fallback'
            continue
        values={}
        for corner in ('tt','ff'):
            c=measure.get(corner,{})
            b=c.get('boundary',{})
            if not measure.get('raw_source',raw.get('raw_source',False)) or c.get('errors') or not b.get('n'):
                missing_insertion[key]='missing raw, error-free measured boundary insertion'
                break
            values[corner]=dict(mean_ps=b['mean'],min_ps=b['min'],max_ps=b['max'],
                                spread_ps=b['max']-b['min'],n=b['n'])
        else:
            insertions[key]=dict(file=str(path),sha256=sha(path),by_corner=values)
    coverage=dict(schema='opentallas.s81.physical_clock_sta_coverage.v1',
        scope='PARTIAL_LOAD_DIAGNOSTIC_NO_NATIVE_CLOCK_QUALIFICATION' if missing or missing_insertion else 'PHYSICAL_PLACEMENT_RC_CLOCK_PILOT_NOT_ROUTED_SIGNOFF',
        selected_entries=len(entries),missing_masters=missing,
        missing_entry_loads=sum(v['entries'] for v in missing.values()),
        actual_view_libs_sha256=hashes,per_child_insertions=insertions,missing_insertions=missing_insertion,binding_sha256=sha(binding),candidate_sha256=sha(candidate),
        clock_delivery='physical ASAP7 buffers in source-bound actual ODB; no per-sink ideal latency',
        compensation='not implemented; per-child real R and positive physical delays still required',
        uncertainties_ps=dict(setup=210,hold=75),
        corner_policy='TT setup, FF hold; partial clock-network measurement has no data timing qualification')
    out.mkdir(parents=True,exist_ok=True)
    (out/'load_coverage.json').write_text(json.dumps(coverage,indent=1)+'\n')
    if (missing or missing_insertion) and not partial:
        raise ValueError(f'source-exact clock coverage FAIL: {coverage["missing_entry_loads"]} missing loads, {len(missing_insertion)} missing child insertions; see load_coverage.json')
    for corner in ('tt','ff'):
        T=[f'read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{corner.upper()}_nldm_220122.lib.gz']
        T += ['read_liberty {'+p+'}' for p in sorted(libs[corner])]
        T += ['read_db /pilot/physical_clock.odb',
              'source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl',
              'set_wire_rc -clock -layer M8',
              'proc exact_pin {name} {get_pins -quiet [string map {[ \\[ ] \\]} $name]}']
        for d,row in manifest['domains'].items():
            if d not in ('stream','serial','hbm'):
                raise ValueError('forwarded source needs an explicit native generated-clock/ratio contract; '
                                 'do not manufacture an independent ideal root: '+row['root'])
            period=dict(stream=833.333,serial=1111.111,hbm=1023.96)[d]
            T += [f'create_clock -name {d} -period {period} [exact_pin {{{row["root"]}}}]']
        T += ['set_clock_uncertainty -setup 210 [all_clocks]',
              'set_clock_uncertainty -hold 75 [all_clocks]',
              'set_propagated_clock [all_clocks]',
              'estimate_parasitics -placement',
              'sta::find_timing_paths -path_delay max -group_path_count 1',
              f'set fh [open /work/{corner}_arrivals.tsv w]']
        for entry in entries:
            pin=entry['pin']
            T += [f'set name {{{pin}}}', 'set pp [exact_pin $name]',
                  'if {[llength $pp] != 1} {error "missing or ambiguous physical clock entry $name"}',
                  'set ar [get_property $pp arrival_max_rise]',
                  'set ae [get_property $pp arrival_min_rise]',
                  'puts $fh "$name\\t$ar\\t$ae"']
        T += ['close $fh',f'puts OT_PHYSICAL_CLOCK_ARRIVALS_DONE_{corner}',
              f'report_check_types -max_slew -max_capacitance -violators > /work/{corner}_drv.rpt', 'exit']
        (out/f'propagated_{corner}.tcl').write_text('\n'.join(T)+'\n')
    return coverage


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('candidate','dump','binding','source','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--allow-partial-load-diagnostic',action='store_true')
    a=ap.parse_args()
    coverage=emit(a.candidate,a.dump,a.binding,a.source,a.out,a.allow_partial_load_diagnostic)
    print(json.dumps({k:v for k,v in coverage.items() if k not in ['actual_view_libs_sha256','missing_masters','per_child_insertions','missing_insertions']}))


if __name__=='__main__':main()
