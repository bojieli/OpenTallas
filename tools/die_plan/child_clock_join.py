#!/usr/bin/env python3
"""Qualify retained native child clock identities without asserting parent expansion.

A complete internal pair graph is not an interface graph. This helper leaves
parent clock coverage UNEXPANDED even when the native graph identity passes.
"""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

import die_sta as D
import signoff as SO


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def child_path(root, name):
    p = (root / name).resolve()
    require(p.is_relative_to(root.resolve()), 'child witness path escapes view')
    return p


def rows(path):
    with Path(path).open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def source_identity(receipt, lec, native, lec_path):
    """Consume an input identity established while proving or by AIG replay.

    A bound official run records its complete unchanged input inventory.
    Legacy LEC path strings alone do not establish the contents proved. A
    deterministic frontend replay can join current inputs to retained proof
    AIGs without rerunning or relabelling the SAT proof.
    """
    require(receipt is not None, 'LEC has no exact retained input identity; frontend replay required')
    r = load(receipt)
    require(r.get('schema') in ('opentallas.lec_frontend_replay.v1', 'opentallas.lec_input_identity.v1'), 'unsupported LEC source identity')
    require(r.get('lec_sha256') == sha(lec_path), 'LEC receipt identity mismatch')
    require(r.get('netlist_sha256') == native['6_final.v'], 'LEC native source mismatch')
    if r['schema'] == 'opentallas.lec_input_identity.v1':
        require(r.get('exit_code') == 0 and r.get('before') == r.get('after') and r.get('before'), 'official proof inputs changed or proof failed')
        require(re.fullmatch(r'sha256:[0-9a-f]{64}', r.get('image_id', '')), 'official proof image identity absent')
        for path, value in r['before'].items():
            require(sha(path) == value, 'official proof input changed: ' + path)
        require(r.get('netlist') in r['before'] and r['before'][r['netlist']] == native['6_final.v'], 'official proof does not bind native netlist')
        command = r.get('command', [])
        require(len(command) > 2 and command[1] in r['before'], 'official proof driver identity absent')
        require('--image' in command and command[command.index('--image')+1] == r['image_id'], 'official proof image was not explicit')
        require('--netlist' in command and command[command.index('--netlist')+1] == r['netlist'], 'official proof gate input not explicit')
        return dict(status='PASS', basis=r['schema'], receipt_sha256=sha(receipt))
    for side in ('gold', 'gate'):
        s = r.get(side, {})
        require(Path(s['retained_aig']).resolve() != Path(s['replayed_aig']).resolve(), side + ' replay aliases retained AIG')
        require(sha(s['retained_script']) == s['script_sha256'] == sha(s['replayed_script']), side + ' frontend script changed')
        require(s.get('retained_aig_sha256') == sha(s['retained_aig']), side + ' retained proof AIG changed')
        require(s.get('replayed_aig_sha256') == sha(s['replayed_aig']), side + ' replay AIG changed')
        require(s['retained_aig_sha256'] == s['replayed_aig_sha256'], side + ' proof frontend mismatch')
        require(s.get('inputs'), side + ' frontend source identities absent')
        for item in s['inputs']:
            require(sha(item['path']) == item['sha256'], side + ' proof source changed: ' + item['path'])
    require(any(x['sha256'] == native['6_final.v'] for x in r['gate']['inputs']), 'gate replay does not bind native netlist')
    return dict(status='PASS', basis=r['schema'], receipt_sha256=sha(receipt))


def qualify(view, native_base, signoff_path, lec_path, libraries, master, clock_pin,
            replay=None):
    view, native_base = Path(view), Path(native_base)
    result = dict(schema='opentallas.child_clock_join.v1',
                  source_qualification=dict(status='NOT RUN'),
                  graph_identity=dict(status='NOT RUN'),
                  parent_coverage=dict(status='UNEXPANDED_CHILD_ETM', verdict='NOT RUN'),
                  required_interface_maps=['input_bit -> every reachable first native capture/data pin',
                                           'output_bit -> every reachable native launch/output pin',
                                           'combinational input_bit -> output_bit feedthroughs',
                                           'per-mapped-endpoint actual clock/root/edge and path sense'],
                  reasons=[])
    try:
        witness_path = view / 'child_clock_witness.json'
        witness, provenance = load(witness_path), load(view / 'provenance.json')
        require(witness.get('schema') == 'opentallas.child_clock_witness.v1', 'unsupported child graph schema')
        require(provenance['child_clock_witness']['sha256'] == sha(witness_path), 'graph provenance mismatch')
        require(witness.get('source_identity_kind') == 'routed_native_netlist_sha256', 'graph has no native netlist identity')
        native = witness['native']
        for name in ('6_final.v', '6_final.odb', '6_final.spef'):
            require(sha(native_base / name) == native[name], 'native source mismatch: ' + name)
        require(D.module_of(native_base / '6_final.v') == master, 'native child master mismatch')
        nl = D.read_verilog(native_base / '6_final.v')[master]
        insts = {inst: (cell, dict(conns)) for cell, inst, conns in nl.insts}
        require(any(name == clock_pin and direction == 'input' for direction, name, _, _ in nl.ports), 'native clock root port mismatch')
        so, lec = load(signoff_path), load(lec_path)
        require(so.get('verdict') == 'SIGNED', 'child not SIGNED')
        require(provenance['export']['signoff_sha256'] == sha(signoff_path), 'SIGNED receipt identity mismatch')
        require(lec.get('verdict') == 'EQUIVALENT' and lec.get('top') == master, 'child routed EQ mismatch')
        counts = lec.get('counts', {})
        require(counts.get('compare_points', 0) > 0 and counts.get('proved') == counts['compare_points']
                and counts.get('differs') == 0 and counts.get('undecided') == 0, 'child EQ incomplete')
        corner_stats = {}
        for corner in ('tt', 'ff'):
            require(sha(libraries[corner]) == provenance['child_clock_witness']['view_lib_sha256'][corner],
                    corner + ' selected child Liberty mismatch')
            library = Path(libraries[corner])
            libtext = gzip.open(library, 'rt').read() if library.suffix == '.gz' else library.read_text()
            cells = [body for name, body in SO._lib_groups(libtext, 'cell') if name == master]
            require(len(cells) == 1, corner + ' selected Liberty master missing/ambiguous')
            clock_pins = [body for name, body in SO._lib_groups(cells[0], 'pin') if name == clock_pin]
            require(len(clock_pins) == 1 and re.search(r'\bclock\s*:\s*true\s*;', clock_pins[0]), corner + ' selected Liberty clock pin mismatch')
            c = witness['corners'][corner]
            for name, digest in c['files'].items():
                require(sha(child_path(view, name)) == digest, 'native graph artifact mismatch: ' + name)
            def table(suffix):
                names = [n for n in c['files'] if n.endswith('_' + suffix + '.tsv')]
                require(len(names) == 1, 'ambiguous graph table: ' + suffix)
                return rows(child_path(view, names[0]))
            endpoints, masters, pairs = table('endpoints'), table('masters'), table('pairs')
            refs = {e['reference']: e for e in endpoints}
            require(len(refs) == len(endpoints) == c['counts']['refs'], 'endpoint coverage/count mismatch')
            require(len(pairs) == c['counts']['pairs'] and c['counts']['missing'] == 0
                    and c['counts']['inter_clock_pairs_skipped'] == 0, 'native pair graph incomplete')
            require(len(masters) == len(refs) and {m['reference'] for m in masters} == set(refs), 'native master coverage missing')
            for row in masters:
                ref = row['reference']
                require(ref in refs and ref in insts, 'native endpoint absent from actual netlist: ' + ref)
                require(insts[ref][0] == row['master'] and row['clock_pin'] == refs[ref]['clock_pin'], 'native master/clock identity mismatch')
            root_rows = table('roots')
            require(len(root_rows) == 1 and root_rows[0]['clock_edge'] == clock_pin, 'native graph clock root mismatch')
            clocks = table('clocks')
            require(any(x['clock'] == clock_pin and x['source_kind'] == 'port' and x['source'] == clock_pin for x in clocks), 'native clock source mismatch')
            for ref, e in refs.items():
                require(e['clock'] == clock_pin and e['clock_pin'] == ref + '/CLK'
                        and 'CLK' in insts[ref][1] and e['edge'] in ('rise', 'fall'), 'native endpoint clock pin/edge mismatch')
                require(all(math.isfinite(float(e[k])) for k in ('late_ps', 'early_ps')), 'nonfinite native clock arrival')
            seen = set()
            for p in pairs:
                require(all(p[k] in refs for k in ('launch', 'capture_setup', 'capture_hold')), 'pair references unknown native endpoint')
                cap = p['capture_setup']
                require(p['data_pin'].startswith(cap + '/') and p['data_pin'][len(cap)+1:] in insts[cap][1], 'native pair data pin absent')
                key = tuple(p[k] for k in ('launch', 'capture_setup', 'data_pin', 'capture_hold'))
                require(key not in seen, 'duplicate native pair identity'); seen.add(key)
                require(all(math.isfinite(float(p[k])) for k in ('raw_setup_ps', 'raw_hold_ps')), 'nonfinite native pair')
            corner_stats[corner] = dict(endpoints=len(refs), internal_pairs=len(pairs),
                                        selected_liberty_sha256=sha(libraries[corner]))
        result['graph_identity'] = dict(status='PASS', native=native, corners=corner_stats,
                                       master=master, clock_pin=clock_pin)
        try:
            result['source_qualification'] = source_identity(replay, lec, native, lec_path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            result['reasons'].append(str(error))
        result['status'] = 'QUALIFIED_NATIVE_GRAPH' if result['source_qualification']['status'] == 'PASS' else 'UNQUALIFIED_SOURCE_IDENTITY'
    except (OSError, ValueError, KeyError, TypeError, SystemExit) as error:
        result['status'] = 'UNQUALIFIED'
        result['reasons'].append(str(error))
    return result


def buffer_models(library, expected_sha256):
    """Read exact A/Y buffer functions from an actual hashed native library."""
    require(sha(library)==expected_sha256,'native buffer Liberty mismatch')
    library=Path(library)
    text=gzip.open(library,'rt').read() if library.suffix=='.gz' else library.read_text()
    models={}
    for master,body in SO._lib_groups(text,'cell'):
        pins={name:b for name,b in SO._lib_groups(body,'pin')}
        if set(pins)!={'A','Y'}: continue
        if not re.search(r'\bdirection\s*:\s*input\s*;',pins['A']): continue
        if not re.search(r'\bdirection\s*:\s*output\s*;',pins['Y']): continue
        f=re.search(r'\bfunction\s*:\s*"([^"\n]+)"',pins['Y'])
        if not f: continue
        function=re.sub(r'\s','',f[1])
        if function not in ('A','!A',"A'"): continue
        models[master]=dict(inverted=function!='A',liberty_sha256=expected_sha256,function=function)
    return models


def boundary_maps(native_base, master, endpoint_rows, controls, models=None):
    """Exact direct/BUF/INV boundary maps; arbitrary logic is left unexpanded.

    These maps do not create data timing arcs, infer false paths or grant CPPR.
    The supported ASAP7 BUF/INV pin contract is A->Y. Native state clock pins
    and D data pins must already occur in the source-qualified endpoint graph.
    """
    nl = D.read_verilog(Path(native_base) / '6_final.v')[master]
    parent = {}
    def find(n):
        parent.setdefault(n, n)
        if parent[n] != n: parent[n] = find(parent[n])
        return parent[n]
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b: parent[b]=a
    for a,b in nl.assigns: union(a,b)
    endpoints = {e['reference']:e for e in endpoint_rows}
    cells = {i:(m,dict(c)) for m,i,c in nl.insts}
    outputs = {'Y','Q','QN','H','L','CON','SN','Z','ZN','O'}
    loads,drivers=defaultdict(list),defaultdict(list)
    for inst,(typ,pins) in cells.items():
        for pin,bits in pins.items():
            for net in bits:
                (drivers if pin in outputs else loads)[find(net)].append((inst,pin))
    def buffer(inst):
        typ,pins=cells[inst]
        return (typ in models if models is not None else bool(re.fullmatch(r'(?:BUF|INV)x[0-9p]+(?:DC)?_ASAP7_75t_(?:R|L|SL)',typ))) and set(pins)=={'A','Y'}
    missing=[]
    def walk(net,forward,stack):
        net=find(net)
        if net in stack: raise ValueError('boundary combinational cycle')
        hits=[]; edges=loads[net] if forward else drivers[net]
        if not edges: raise ValueError('boundary has no native endpoint')
        if not forward and len(edges)!=1: raise ValueError('boundary has multiple drivers')
        for inst,pin in edges:
            if inst in endpoints:
                require(pin=='D' if forward else pin in ('Q','QN'), 'boundary reaches non-data state pin')
                hits.append(dict(reference=inst,data_pin=inst+'/'+pin,clock_pin=endpoints[inst]['clock_pin'],
                                 clock=endpoints[inst]['clock'],edge=endpoints[inst]['edge'],buffer_chain=[],inversions=0))
            elif buffer(inst) and pin==('A' if forward else 'Y'):
                nxt=cells[inst][1]['Y' if forward else 'A']
                require(len(nxt)==1,'boundary buffer bus unsupported')
                for row in walk(nxt[0],forward,stack|{net}):
                    row=dict(row)
                    row['buffer_chain']=[dict(instance=inst, master=cells[inst][0], contract=(models or {}).get(cells[inst][0], 'ASAP7 typed BUF/INV'))]+row['buffer_chain']
                    row['inversions']+=int(models[cells[inst][0]]['inverted'] if models is not None else cells[inst][0].startswith('INV'))
                    hits.append(row)
            else: raise ValueError('boundary logic requires full interface map: '+inst+'/'+pin)
        return hits
    maps={'inputs':{},'outputs':{}}
    for direction,name,bit in nl.port_bits():
        if name in controls: continue
        if direction not in ('input','output'):
            missing.append(dict(port=bit,reason='unsupported interface direction'));continue
        try:
            found=walk(bit,direction=='input',set())
            # Preserve every distinct native endpoint, including fanout branches.
            unique={json.dumps(row,sort_keys=True):row for row in found}
            maps['inputs' if direction=='input' else 'outputs'][bit]=list(unique.values())
        except ValueError as error: missing.append(dict(port=bit,reason=str(error)))
    refs={row['reference'] for group in maps.values() for values in group.values() for row in values}
    return dict(schema='opentallas.child_boundary_clock_map.v1',
                status='COMPLETE_DIRECT_BUFFER_MAPS' if not missing else 'INCOMPLETE',
                basis='actual mapped native Verilog; direct state pins and exact A/Y buffer contracts; buffer chains and polarity retained',
                native_netlist_sha256=sha(Path(native_base)/'6_final.v'),controls=sorted(controls),
                maps=maps,missing=missing,boundary_registers=len(refs),
                parent_coverage='UNEXPANDED_CHILD_ETM',
                limitation='No parent STA paths, data arc conditions, timing checks or CPPR have been expanded')


def join_parent(qualification, parent_netlist, parent_top, instance, parent_clock_net,
                libraries, native_base):
    """Join one actual instance to a qualified graph; never infer data coverage.

    This structural join proves selected file identity, not that a future STA
    process consumed those files. The STA library-loader receipt must still be
    joined by the eventual parent coverage consumer.
    """
    result = dict(status='NOT RUN', parent_coverage='UNEXPANDED_CHILD_ETM',
                  parent_consumption='SELECTED_INPUTS_ONLY_NOT_STA', instance=instance)
    try:
        graph = qualification['graph_identity']
        require(graph.get('status') == 'PASS', 'child graph identity not qualified')
        for c in ('tt', 'ff'):
            require(sha(libraries[c]) == graph['corners'][c]['selected_liberty_sha256'],
                    c + ' parent selected Liberty mismatch')
        nl = D.read_verilog(parent_netlist)[parent_top]
        matching = [(cell, dict(conns)) for cell, inst, conns in nl.insts if inst == instance]
        require(len(matching) == 1 and matching[0][0] == graph['master'], 'actual parent child instance/master mismatch')
        pin = graph['clock_pin']
        require(matching[0][1].get(pin) == [parent_clock_net], 'actual parent child clock/root connection mismatch')
        native_nl = D.read_verilog(Path(native_base) / '6_final.v')[graph['master']]
        dirs = {name: (direction, msb, lsb) for direction, name, msb, lsb in native_nl.ports}
        expected = {}
        for name, (direction, msb, lsb) in dirs.items():
            expected[name] = abs(msb-lsb)+1 if msb is not None else 1
        actual = matching[0][1]
        require(set(actual) == set(expected), 'actual parent child interface port set mismatch')
        require(all(len(actual[p]) == width for p, width in expected.items()), 'actual parent child interface width mismatch')
        result.update(status='PASS', parent_netlist_sha256=sha(parent_netlist),
                      parent_top=parent_top, master=graph['master'],
                      clock_pin=pin, parent_clock_net=parent_clock_net,
                      interface_bits=sum(expected.values()),
                      input_bits=sum(expected[n] for n, d in dirs.items() if d[0] == 'input'),
                      output_bits=sum(expected[n] for n, d in dirs.items() if d[0] == 'output'),
                      source_qualification=qualification['source_qualification']['status'],
                      missing='actual parent STA consumption, native interface map linkage and related parent path composition')
        maps=qualification.get('boundary_maps',{})
        if maps.get('status')=='COMPLETE_DIRECT_BUFFER_MAPS' and maps.get('native_netlist_sha256')==graph.get('native',{}).get('6_final.v'):
            result['boundary_map_artifact_sha256']=maps.get('artifact_sha256')
            result['missing']='actual parent STA consumption and related parent path composition'
    except (OSError, ValueError, KeyError, TypeError, SystemExit) as error:
        result['reason'] = str(error)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('view', 'native-base', 'signoff', 'lec', 'library-tt', 'library-ff', 'master', 'clock-pin', 'out'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--source-identity', '--frontend-replay', dest='source_identity', help='exact bound official proof inputs or retained frontend replay receipt')
    p.add_argument('--native-buffer-lib', help='actual native library snapshot for exact A/Y boundary buffer functions')
    for name in ('parent-netlist', 'parent-top', 'instance', 'parent-clock-net'):
        p.add_argument('--' + name)
    a = p.parse_args()
    r = qualify(a.view, a.native_base, a.signoff, a.lec,
                dict(tt=a.library_tt, ff=a.library_ff), a.master, a.clock_pin, a.source_identity)
    if a.native_buffer_lib and r['graph_identity']['status']=='PASS':
        try:
            view=Path(a.view); witness=load(view/'child_clock_witness.json'); provenance=load(view/'provenance.json')
            c=witness['corners']['tt']
            names=[n for n in c['files'] if n.endswith('_inputs.tsv')]
            require(len(names)==1,'native input table ambiguous')
            records=[line.split('\t') for line in child_path(view,names[0]).read_text().splitlines()]
            hashes=[row[2] for row in records if row[0]=='liberty' and Path(row[1]).name==Path(a.native_buffer_lib).name]
            require(len(hashes)==1,'native buffer library absent/ambiguous in actual graph inputs')
            ep=[n for n in c['files'] if n.endswith('_endpoints.tsv')]
            require(len(ep)==1,'native endpoint table ambiguous')
            maps=boundary_maps(a.native_base,a.master,rows(child_path(view,ep[0])),
                               provenance['kit']['clocks']+provenance['kit']['resets'],
                               buffer_models(a.native_buffer_lib,hashes[0]))
            mp=Path(a.out).with_suffix('.boundary_maps.json'); mp.write_text(json.dumps(maps,indent=2)+'\n')
            r['boundary_maps']={k:v for k,v in maps.items() if k!='maps'}
            r['boundary_maps'].update(artifact=str(mp),artifact_sha256=sha(mp))
        except (OSError,ValueError,KeyError,TypeError) as error:
            r['boundary_maps']=dict(status='NOT RUN',reason=str(error))
    parent_args = (a.parent_netlist, a.parent_top, a.instance, a.parent_clock_net)
    if any(parent_args):
        if not all(parent_args):
            p.error('all four parent identity arguments are required together')
        r['parent_join'] = join_parent(r, *parent_args, dict(tt=a.library_tt, ff=a.library_ff), a.native_base)
    Path(a.out).write_text(json.dumps(r, indent=2) + '\n')
    return 0 if (r['status'] == 'QUALIFIED_NATIVE_GRAPH'
                 and r.get('parent_join', {'status': 'PASS'})['status'] == 'PASS'
                 and (not a.native_buffer_lib or r.get('boundary_maps',{}).get('status') == 'COMPLETE_DIRECT_BUFFER_MAPS')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
