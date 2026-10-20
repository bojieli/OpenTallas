#!/usr/bin/env python3
"""Derive the S81 frame's external lane-clock profile from RTL and hard views.

This is an opt-in preflight/emitter, not a clock qualification receipt.  A failed
view audit never emits SDC.  Regional read phase/K/reset-epoch legality still
requires the die compiler's actual timing certificate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def groups(text, kind):
    """Balanced Liberty groups; quoted braces and comments cannot end a group."""
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    out = []
    for m in re.finditer(r'\b' + re.escape(kind) + r'\s*\(\s*("[^"\n]*"|[^)]*)\s*\)\s*\{', text):
        depth, i, quoted, escaped = 1, m.end(), False, False
        while i < len(text) and depth:
            c = text[i]
            if escaped: escaped = False
            elif c == '\\' and quoted: escaped = True
            elif c == '"': quoted = not quoted
            elif not quoted: depth += (c == '{') - (c == '}')
            i += 1
        if depth: raise ValueError(f'unclosed {kind} group')
        out.append((m[1].strip().strip('"'), text[m.end():i-1]))
    return out


def attr(text, name):
    m = re.search(r'\b' + name + r'\s*:\s*(?:"([^"]*)"|([^;\s]+))\s*;', text)
    return (m[1] if m[1] is not None else m[2]) if m else None


def pinmap(text):
    pins = groups(text, 'pin')
    if len({p for p, _ in pins}) != len(pins): raise ValueError('duplicate Liberty pin')
    return dict(pins)


def arcs(pin):
    return [dict(related=attr(t, 'related_pin'), kind=attr(t, 'timing_type') or 'combinational',
                 sense=attr(t, 'timing_sense'), body=t) for _, t in groups(pin, 'timing')]


def hard_view(text, clocks, data_ports, forward=None):
    """Checks use actual related clock pins, not only clock:true or clk->Q."""
    pins, errors, checks = pinmap(text), [], {}
    for clock, data in zip(clocks, data_ports):
        if clock not in pins or attr(pins.get(clock, ''), 'direction') != 'input':
            errors.append(f'{clock}: missing input clock pin')
        bits = [n for n in pins if re.fullmatch(re.escape(data) + r'\[\d+\]', n)]
        if set(bits) != {f'{data}[{i}]' for i in range(276)}:
            errors.append(f'{data}: expected exactly 276 actual data pins')
        covered = 0
        for bit in bits:
            kinds = {a['kind'] for a in arcs(pins[bit]) if a['related'] == clock}
            if not {'setup_rising', 'hold_rising'} <= kinds:
                errors.append(f'{bit}: missing setup/hold checks relative to {clock}')
            else: covered += 1
        launch = sum(a['related']==clock and a['kind'] in ('rising_edge','falling_edge')
                     for pin in pins.values() for a in arcs(pin))
        checks[clock] = dict(data=data, checked_bits=covered,
                            clock_flag=attr(pins.get(clock, ''), 'clock'),
                            launch_arcs=launch, writer_check_only=(covered>0 and launch==0))
    forwarding = None
    if forward:
        source, output = forward
        aa = arcs(pins.get(output, ''))
        good = [a for a in aa if a['related'] == source and a['kind'] == 'combinational'
                and a['sense'] == 'positive_unate']
        forwarding = dict(source=source, output=output,
                          arcs=[{k:v for k,v in a.items() if k != 'body'} for a in aa])
        if attr(pins.get(output, ''), 'direction') != 'output' or len(aa) != 1 or len(good) != 1:
            errors.append(f'{output}: requires one real positive_unate combinational {source}->{output} arc')
        elif any(not groups(good[0]['body'], table) for table in
                 ('cell_rise', 'cell_fall', 'rise_transition', 'fall_transition')):
            errors.append(f'{output}: forwarding edge lacks a delay/transition table')
        elif good:
            for table in ('cell_rise','cell_fall','rise_transition','fall_transition'):
                for _, body in groups(good[0]['body'],table):
                    vv=re.findall(r'\bvalues\s*\(\s*"([^"]*)"\s*\)',body)
                    try: values=[float(x) for v in vv for x in v.split(',')]
                    except ValueError: values=[]
                    if not values or any(not math.isfinite(x) or x < 0 for x in values):
                        errors.append(f'{output}: forwarding {table} values must be finite nonnegative actual delays')
    return dict(checks=checks, forwarding=forwarding, errors=errors)


def connections(text, name):
    matches = re.findall(r'\b(\w+)\s+' + re.escape(name) + r'\s*\(([^;]*)\);', text)
    if len(matches) != 1: raise ValueError(f'{name}: expected exactly one actual instance')
    master, body = matches[0]
    cc = dict(re.findall(r'\.(\w+)\s*\(([^()]*)\)', body))
    return master, {k:re.sub(r'\s+', '', v) for k,v in cc.items()}


def profile(root, top='col_h9_l4'):
    root = Path(root)
    paths = [f'rtl/dsrom_sys/s81_dv/frame_l4/{top}.sv',
             'rtl/dsrom_sys/s81_dv/frame_l4/frame_l4.json',
             'rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv',
             'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv']
    texts = {p:(root/p).read_text() for p in paths}
    rtl, manifest, cf, relay = [texts[p] for p in paths]
    errors = []
    if json.loads(manifest)['emitted'].get(top+'.sv') != hashlib.sha256(rtl.encode()).hexdigest():
        errors.append('frame RTL does not match generator manifest')
    cm, cc = connections(rtl, 'u_cf')
    if cm != 'dsfd_cfifo_crs4' or cc.get('xk') != 'xk': errors.append('u_cf actual clock/master mismatch')
    # Exact source semantics: a changed or mutant branch cannot silently reuse this profile.
    clean_cf = re.sub(r'`ifdef OT_CRS4_MUT_NBR.*?`else\s*', '', cf, flags=re.S)
    for fragment in ('wire ckl = xk[g];', '.W(276), .D(4)', '.ck_f(ckl)', '.ck(cr)', '.k(lk[3 * g +: 3])'):
        if fragment not in clean_cf: errors.append(f'cfifo source mismatch: {fragment}')
    if not all(s in relay for s in ('u_ck0 (.a(ck), .y(ckn))', 'u_ck1 (.a(ckn), .y(ck_o))', 'assign y = ~a;')):
        errors.append('relay source lacks the two-inverter noninverted clock chain')
    lanes = []
    for k in range(4):
        rm, rc = connections(rtl, f'u_xo{k}')
        expected = dict(ck=f'xk[{k}]', ck_o=f'xok[{k}]')
        if rm != 'dsfd_dvrly_276_NS' or any(rc.get(p) != v for p,v in expected.items()):
            errors.append(f'u_xo{k}: actual clock/master mismatch')
        bits = ','.join(f'x[{i}]' for i in range(276*k+275,276*k-1,-1))
        if cc.get(f'xl{k}') != '{'+bits+'}' or rc.get('i') != '{'+bits+'}':
            errors.append(f'lane{k}: FIFO/relay actual data slice mismatch')
        lanes.append(dict(root=f'xk[{k}]', clock=f'ot_frame_xk{k}', classification='external_forwarded_clock',
                          endpoints=[f'u_cf/xk[{k}]', f'u_xo{k}/ck'],
                          data=f'x[{276*k+275}:{276*k}]', output=f'xok[{k}]',
                          phase='noninverted', K=f'lk[{3*k}+:3]', read_clock='cr',
                          reader_phase_interval_certificate=None, reset_first_active_edge_certificate=None))
    lineage_errors = list(errors)
    views = {}
    for master, folder, clocks, data, forward in (
        ('dsfd_cfifo_crs4','s81coll_cfifo_crs4',[f'xk[{k}]' for k in range(4)], [f'xl{k}' for k in range(4)],None),
        ('dsfd_dvrly_276_NS','s81dv_rly_276_ns',['ck'],['i'],('ck','ck_o'))):
        view = root/'physical/ref_tile'/folder/'views'/master
        ins_path = view/'insertion.json'
        texts[str(ins_path.relative_to(root))] = ins_path.read_text()
        insertion = json.loads(texts[str(ins_path.relative_to(root))])
        for corner in ('tt','ff'):
            path = view/f'{master}_{corner}.lib'
            text = path.read_text(); texts[str(path.relative_to(root))] = text
            row = hard_view(text,clocks,data,forward)
            refs = {}
            for clock in clocks:
                measure = insertion.get('clock_measurements',{}).get(clock)
                if measure is None and insertion.get('clock') == 'core_clk' and clock == 'ck': measure=insertion
                b = (measure or {}).get(corner,{}).get('boundary',{})
                values = [b.get(n) for n in ('min','mean','max')]
                if not b.get('n') or any(type(v) not in (int,float) or not math.isfinite(v) for v in values) or not values[0]<=values[1]<=values[2]:
                    row['errors'].append(f'{clock}: missing finite per-clock routed boundary reference')
                else: refs[clock] = b
            row['boundary_ps'] = refs
            views[f'{master}/{corner}'] = row
            errors += [f'{master}/{corner}: {e}' for e in row['errors']]
    return dict(schema='opentallas.s81_frame_external_clocks.v1', top=top,
                status='REFUSED' if errors else 'PROFILE_ONLY', errors=errors,
                source_sha256={p:hashlib.sha256(t.encode()).hexdigest() for p,t in texts.items()},
                external_roots=lanes, expected_child_clock_pin_coverage=8,
                child_clock_pin_coverage=8 if not lineage_errors else 0, source_lineage_errors=lineage_errors, views=views,
                qualification='Requires actual parent TT/FF propagated clock paths, linked-child spread<=80ps, finite setup/hold and compiler K/phase/reset-first-edge certificate; not a measured receipt')


def sdc(p, period_ps):
    if p['errors']: raise ValueError('refusing SDC for invalid RTL/hard-view profile')
    if type(period_ps) not in (int,float) or not math.isfinite(period_ps) or period_ps <= 0:
        raise ValueError('period must be finite positive')
    lines=['# Opt-in external writer clocks; actual hard-view combinational arcs propagate forwarded phase.',
           '# No false paths, multicycles, core-domain assignment or generated insertion is added.']
    for lane in p['external_roots']:
        lines += [f'if {{[llength [get_ports -quiet {{{lane["root"]}}}]] != 1}} {{error "missing external lane root"}}',
                  f'create_clock -name {lane["clock"]} -period {period_ps:.9g} [get_ports {{{lane["root"]}}}]']
    return '\n'.join(lines)+'\n'



def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--root',type=Path,default=ROOT); a.add_argument('--top',choices=['col_h9_l4','col_h10_l4'],default='col_h9_l4')
    a.add_argument('--out',type=Path,required=True); a.add_argument('--sdc',type=Path); a.add_argument('--period-ps',type=float)
    args=a.parse_args(); p=profile(args.root,args.top)
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(p,indent=2)+'\n')
    if p['errors']:
        print('FRAME_CLOCK_PROFILE REFUSED: '+'; '.join(p['errors'])); return 1
    if args.sdc:
        args.sdc.write_text(sdc(p,args.period_ps))
    print('FRAME_CLOCK_PROFILE PROFILE_ONLY roots=4 child_clock_pins=8 (not measured)'); return 0

if __name__=='__main__': raise SystemExit(main())
