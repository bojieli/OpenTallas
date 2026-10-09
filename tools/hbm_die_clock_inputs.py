#!/usr/bin/env python3
"""Explicit externally generated clock/reset contract for the HBM die candidate.

This replaces the historical forwarded-PLL proxy only when explicitly applied.
The external generator, package, pad and CTS costs remain qualification inputs.
"""

DOMAINS = ('stream', 'serial', 'hbm', 'link')
PERIOD_NS = dict(stream=5/6, serial=10/9, hbm=1.024, link=5/6)


def apply(m):
    if m.get('external_clock_inputs'):
        raise ValueError('external clock inputs already applied')
    ports = {}
    origin_x = m['geo']['W']/2 - 56
    for index, domain in enumerate(DOMAINS):
        for offset, prefix in ((0, 'clk'), (1, 'por')):
            name=f'{prefix}_{domain}'
            target=origin_x+(2*index+offset)*16
            x=.012+round((target-.012)/.048)*.048
            ports[name]=dict(direction='input',domain=domain,
                use='CLOCK' if prefix=='clk' else 'SIGNAL',layer='M5',
                center_um=[round(x,6),.042],size_um=[.024,.084],
                period_ns=PERIOD_NS[domain] if prefix=='clk' else None,
                reset_active_high=prefix=='por')
    buses=[]
    clocks=set()
    resets=set()
    for bid, cls, bits, eps in m['buses']:
        if cls not in ('clock_trunk','reset_tree'):
            buses.append((bid,cls,bits,eps));continue
        domain=bid.split('_',1)[1]
        if domain not in DOMAINS or bits!=1:
            raise ValueError(f'unrecognized root net {bid}')
        prefix='clk' if cls=='clock_trunk' else 'por'
        expected=('hb_coll', ('pll_' if prefix=='clk' else 'por_')+domain)
        if eps.count(expected)!=1:
            raise ValueError(f'{bid} does not have exactly one historical root')
        sinks=[p for p in eps if p!=expected]
        if domain in ('stream','link'):
            # The new full collective is a consumer of two independent clocks.
            # Its wrapper must expose these real pins, with local reset release.
            port=({'stream':'clk_stream','link':'clk_link'}[domain] if prefix=='clk' else f'por_{domain}')
            sinks.append(('hb_coll',port))
        buses.append((bid,cls,bits,[('TOP',f'{prefix}_{domain}')]+sinks))
        (clocks if prefix=='clk' else resets).add(domain)
    if clocks!=set(DOMAINS) or resets!=set(DOMAINS):
        raise ValueError('all four clock and reset domains must remain explicit')
    m['buses']=buses
    m['top_input_ports']=ports
    m['external_clock_inputs']=dict(status='unqualified-explicit-source-contract',
        selected=False,external_generation_assumed=True,
        periods_ns=PERIOD_NS,
        serial_relationship='external source phase locked: three serial edges per four stream edges; common rising edge every 10/3 ns',
        link_relationship='independent phase; only actual dual-clock FIFO crossings may receive timing exceptions',
        hbm_protocol_exception='1.024 ns (976.5625 MHz) HBM service clock remains distinct from 1.2 GHz streaming',
        reset_contract='four active-high reset assertions; domain-local synchronized release must be implemented and checked',
        input_pin_count=8,clock_pin_count=4,reset_pin_count=4,
        clock_pad_or_receiver_area_um2=None,external_generation_power_w=None,
        source_dynamic_power_w_per_input_ff={d:1e-15*.7**2/(p*1e-9) for d,p in PERIOD_NS.items()},
        power_basis='C*V^2*f at 0.7 V, per fF; actual receiver/package capacitance and clock-generator power unmeasured',
        cts_status='must rebuild from physical south-edge entries; historical hb_coll-root insertion numbers do not apply',
        remaining_gates=['actual full collective clk_stream/clk_link/por_stream/por_link pins',
            'external source jitter, 3:4 phase relationship and reset release proof',
            'package/clock receiver area, capacitance and external source energy',
            'measured south-entry CTS for every real consumer with SS/FF uncertainty',
            'CDC verification for every asynchronous edge; no blanket false paths'])
    return m


def write_sdc(m,path):
    if not m.get('external_clock_inputs'):
        raise ValueError('no external source contract')
    text='''# Candidate external clock input contract. External generation is assumed, not measured.
# Serial and stream retain the specified 3:4 rational relationship.
create_clock -name clk_stream -period 0.833333333 [get_ports clk_stream]
create_generated_clock -name clk_serial -source [get_ports clk_stream] -multiply_by 3 -divide_by 4 [get_ports clk_serial]
create_clock -name clk_hbm -period 1.024 [get_ports clk_hbm]
create_clock -name clk_link -period 0.833333333 [get_ports clk_link]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# No asynchronous clock groups or reset false paths: crossings remain visible until proved.
'''
    path.write_text(text)


def export(out, variant='r25iqg', context_only=False):
    import hashlib
    import json
    from pathlib import Path
    import hbm_accel_die_fp as H
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    m=apply(H.build(H.variant_arg(variant)))
    if not context_only:
        H.write_netlist(m,1,out/'die.v')
        H.write_def_floorplan(m,out/'floorplan.def')
    write_sdc(m,out/'clock_inputs.sdc')
    c=m['hub']['coll'];reference=[c.x+c.w/2,c.y+c.h/2]
    inputs={name:dict(pin,manhattan_to_collective_centroid_um=
              abs(pin['center_um'][0]-reference[0])+abs(pin['center_um'][1]-reference[1]))
            for name,pin in m['top_input_ports'].items()}
    report=dict(variant=variant,contract=m['external_clock_inputs'],ports=inputs,
        clock_consumers={bid:eps[1:] for bid,cls,bits,eps in m['buses'] if cls=='clock_trunk'},
        prior_reference='geometric collective centroid only, not a measured PLL location',
        collective_centroid_um=reference,
        entry_routing=dict(clock_signal_tracks=4,clock_shield_tracks=8,reset_signal_tracks=4,
            reserved_tracks=16,native_m5_pitch_um=.048,
            scope='entry demand only; complete CTS/shared corridor capacity must be measured'),
        validation=dict(top_clock_reset_sources=8,legacy_pll_root_sources=0,
            topology_scope='candidate structural wiring only; full collective views and package absent'),
        source_sha256={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(H.__file__)]})
    report['artifacts_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out/'model.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(ports=len(inputs),clock_sources=4,reset_sources=4,selected=False)))

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True)
    ap.add_argument('--variant',default='r25iqg',help='Actual selected topology; historical presets remain explicitly selectable')
    ap.add_argument('--context-only',action='store_true',help='Export consumer/source obligations without claiming a bound collective netlist')
    args=ap.parse_args()
    export(args.out,args.variant,args.context_only)
