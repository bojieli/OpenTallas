#!/usr/bin/env python3
"""Finite conservative Q construction power envelope; no physical qualification."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import re

NUM=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
def blocks(text, pattern):
    for m in re.finditer(pattern,text):
        start=text.index('{',m.start());i=start+1;depth=1
        while depth:
            depth+=(text[i]=='{')-(text[i]=='}');i+=1
        yield text[m.start():i]
def scalar(text,key,default=None):
    m=re.search(r'\b'+key+r'\s*:\s*('+NUM+')',text)
    if m:return D(m[1])
    if default is not None:return default
    raise ValueError('missing '+key)
def coefficients(text,name,leakage_unit):
    cells=list(blocks(text,r'cell\s*\('+re.escape(name)+r'\)'))
    if len(cells)!=1:raise ValueError('missing/duplicate '+name)
    c=cells[0]; pins={}
    for pin in blocks(c,r'\bpin\s*\([^)]*\)'):
        n=re.search(r'pin\s*\(([^)]*)\)',pin)[1]
        direction=re.search(r'direction\s*:\s*(\w+)',pin)[1]
        pins[n]={'direction':direction,'cap_fF':scalar(pin,'capacitance',D(0)),
                 'max_cap_fF':scalar(pin,'max_capacitance',D(0))}
    for bus in blocks(c,r'\bbus\s*\([^)]*\)'):
        n=re.search(r'bus\s*\(([^)]*)\)',bus)[1]
        typ=re.search(r'bus_type\s*:\s*(\w+)',bus)[1]
        tb=list(blocks(text,r'type\s*\('+re.escape(typ)+r'\)'))
        if len(tb)!=1:raise ValueError('missing bus type '+typ)
        width=int(scalar(tb[0],'bit_width'))
        direction=re.search(r'direction\s*:\s*(\w+)',bus)[1]
        for bit in range(width):
            pins[n+'['+str(bit)+']']={'direction':direction,
                'cap_fF':scalar(bus,'capacitance',D(0)),
                'max_cap_fF':scalar(bus,'max_capacitance',D(0))}
    energy=D(0);tables=0
    # Sum independent absolute maxima of every rise/fall table, including
    # mutually exclusive conditions and both rails. This overcounts deliberately.
    for table in blocks(c,r'\b(?:rise|fall)_power\s*\([^)]*\)'):
        v=re.search(r'\bvalues\s*\((.*?)\)\s*;',table,re.S)
        if not v:raise ValueError('power table lacks values')
        ns=[abs(D(n)) for n in re.findall(NUM,v[1])]
        if not ns:raise ValueError('empty table')
        energy+=max(ns);tables+=1
    if not tables:raise ValueError('no internal energy for '+name)
    leak=max(D(0),scalar(c,'cell_leakage_power',D(0)))
    # Condition-specific leakage entries are also overcounted across all states.
    leak=max(leak,sum(abs(scalar(b,'value')) for b in blocks(c,r'\bleakage_power\s*\([^)]*\)')))
    return {'pins':pins,'internal_cycle_fJ':energy,'leakage_W':leak*leakage_unit,'tables':tables}
def serial(x):
    if isinstance(x,D):return str(x)
    if isinstance(x,dict):return {k:serial(v) for k,v in x.items()}
    if isinstance(x,list):return [serial(v) for v in x]
    return x

def build(construction,inventory,libdir,macrodir):
    names={'nand':'NAND2x1_ASAP7_75t_R','storage':'DFFASRHQNx1_ASAP7_75t_R',
           'buffer':'BUFx12_ASAP7_75t_R','icg':'ICGx1_ASAP7_75t_R','macro':'ot_rom_4096x274_m8'}
    groups={'nand':'SIMPLE','storage':'SEQ','buffer':'INVBUF','icg':'SEQ'}
    counts={'nand':construction['total_nand2'],'storage':inventory['conservative_storage_clock_sinks'],
            'buffer':inventory['conditional_clock_reserve']['buffer_count'],'icg':8,'macro':4}
    all_coeff={};sources={}
    for corner in ('SS','TT','FF'):
        cs={}
        for kind,name in names.items():
            p=macrodir/f'ot_rom_4096x274_m8_{corner.lower()}.lib' if kind=='macro' else libdir/f'{groups[kind]}_{corner}.cells.lib'
            text=p.read_text();sources[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
            cs[kind]=coefficients(text,name,D('1e-9') if kind=='macro' else D('1e-12'))
        all_coeff[corner]=cs
    # Characterized-rail upper allocation: maximum of each coefficient across
    # SS/TT/FF, CV^2 evaluated at highest characterized rail. No interpolated
    # operating voltage, internal-energy V^2 scaling or baseline subtraction.
    voltage=D('.77');hz=D('1.2e9');maxima={}
    for kind in names:
        cs=[all_coeff[c][kind] for c in all_coeff]
        maxima[kind]={'internal_cycle_fJ':max(c['internal_cycle_fJ'] for c in cs),
                     'leakage_W':max(c['leakage_W'] for c in cs),
                     'input_cap_fF':max(sum(p['cap_fF'] for p in c['pins'].values() if p['direction']=='input') for c in cs),
                     'output_load_ceiling_fF':max(sum(p['max_cap_fF'] for p in c['pins'].values() if p['direction']=='output') for c in cs)}
    # External capacitance is deliberately overcounted: every cell input plus
    # every output max-load ceiling, then clock guarded wires. Output ceilings
    # include downstream pins/wires but are not subtracted from this bound.
    cap_inputs=sum(counts[k]*maxima[k]['input_cap_fF'] for k in counts)
    cap_outputs=sum(counts[k]*maxima[k]['output_load_ceiling_fF'] for k in counts)
    clock_pin_cap=sum(counts[k]*max(all_coeff[c][k]['pins'][pin]['cap_fF'] for c in all_coeff)
                      for k,pin in [('storage','CLK'),('icg','CLK'),('macro','clk')])
    buffer_cap=counts['buffer']*max(all_coeff[c]['buffer']['pins']['A']['cap_fF'] for c in all_coeff)
    wire=D(inventory['conditional_clock_reserve']['wire_guard2_cap_fF'])+D(200)*D('.145426')*2
    internal=sum(counts[k]*maxima[k]['internal_cycle_fJ'] for k in counts)*D('1e-15')*hz
    leakage=sum(counts[k]*maxima[k]['leakage_W'] for k in counts)
    switching=(cap_inputs+cap_outputs+wire)*D('1e-15')*voltage*voltage*hz
    clock_switch=(clock_pin_cap+buffer_cap+wire)*D('1e-15')*voltage*voltage*hz
    clock_internal=sum(counts[k]*maxima[k]['internal_cycle_fJ'] for k in ('storage','buffer','icg','macro'))*D('1e-15')*hz
    total=switching+internal+leakage
    replicas={str(n):{'construction_power_W':total*n,'thermal_474_56W_pass':total*n<=D('474.56')} for n in (1,512,768,1024,1536,2048,3749)}
    return serial({'schema':'w10_q_finite_power_envelope_v1','sources':sources,'counts':counts,
      'corner_coefficients':all_coeff,'conservative_coefficients':maxima,
      'voltage_envelope_V':voltage,'frequency_Hz':hz,'activity':1,'stop_credit':0,
      'cell_input_cap_fF':cap_inputs,'cell_output_load_ceiling_cap_fF':cap_outputs,
      'clock_endpoint_cap_fF':clock_pin_cap,'clock_buffer_input_cap_fF':buffer_cap,
      'guarded_clock_wire_and_ICG_wire_cap_fF':wire,
      'clock_switching_power_W':clock_switch,'clock_related_all_arc_internal_power_W':clock_internal,
      'construction_switching_power_W':switching,'construction_internal_power_W':internal,
      'construction_leakage_power_W':leakage,'construction_total_power_W':total,
      'construction_cycle_energy_J':total/hz,
      'construction_supply_average_current_A':total/voltage,
      'conservative_clock_related_power_W':clock_switch+clock_internal,
      'replica_envelopes':replicas,'thermal_limit_W':D('474.56'),'physical_admission':False,
      'qualification':'conditional analytical allocation, not measured product power or signoff',
      'envelope_conditions':['rail is a characterized SS/TT/FF point at or below 0.77V; no claim of continuous-voltage internal-energy bound',
       'slew/load stay inside characterized power-table domains; no extrapolation',
       'activity1 means at most one rise/fall pair per cycle on every modeled pin; glitch/reset activity above this requires additional bound',
       'output load does not exceed declared maximum; wire bound fixed guard2, not extracted RC',
       'no numerical credit for stop, old-clock subtraction, waveform duty or thermal averaging'],
      'excluded_composition':['hub and descriptor','PG resistive loss and repair cells','upstream package clock tree'],
      'peak_current_A_qualified':False,'IR_qualified':False})
def main():
    p=argparse.ArgumentParser()
    for name in ('construction','inventory','libdir','macrodir','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args();x=build(json.loads(Path(a.construction).read_text()),json.loads(Path(a.inventory).read_text()),Path(a.libdir),Path(a.macrodir));Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
