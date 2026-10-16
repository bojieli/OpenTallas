#!/usr/bin/env python3
"""Prepare candidate capture leaf specs from source census and assigned pin files.

Generation fails until the die lead supplies each literal pin Tcl. No existing
physical view is inherited; all actual multi-domain data paths remain timed.
"""
import argparse,json
from pathlib import Path
from capture_split_census import census,ROOT

def specs(pins_dir):
    graph=census();request=json.loads((ROOT/'results/arch/s81_hub_parents_1016/capture_split_slot_request.json').read_text());rows={}
    requested=dict(request['masters'])
    for m,r in request['additional_requested_rebuilds'].items():
        requested[m]=dict(r,clocks=['ckv'] if m=='dsfd_capt_cd' else ['ck'])
    for master,row in requested.items():
        if not row.get('requested_outline_um'):continue
        samples=[c for c in graph['children'].values() if c['master']==master]
        if not samples:raise ValueError('unused requested master '+master)
        dirs=samples[0]['port_directions'];clocks=[p+'[0]' if p in graph['single_bit_bus_ports'][master] else p for p in row['clocks']];dual=row['clocks']==['ck','ckv']
        spec=dict(name=master.lower()+'_split1016',top=master,kind='tile',sources=[
          'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv',
          'rtl/common/ot_ratio_cdc_fifo.sv','rtl/dsrom_sys/s81_glue/ot_s81_rly.sv','rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_cd.sv'],params={},
          clock_port=clocks[0],reset_ports=[p for p in dirs if p in ('rst','rsv','rs')],outline=dict(zip(('w','h'),row['requested_outline_um'])),
          macros=[],pins={'ANY':list(dirs)},route=dict(pd=.45,threads=8,peak_ram_gb=16,pin_v='M3 M5',hold_margin_ns=.03),
          recipe=2,pin_regs=dict(enable=False,reason='Source-exact capture cones retain every used data/status/fault sampling edge. Native registered boundary capture/launch checks and recipe2 dedicated outputflops still apply; blanket recipe3 registers would insert unpriced semantic stages into this exact comparison.'),clock='cts',io_tcl=str(pins_dir/(master+'.tcl')),
          structural_change='Source-exact capture split: only source-proven unused status/padding removed, both actual half faults captured at original g2 hoq edge, all used status/data/control epochs unchanged.',
          job=dict(owner='codex:S81 hub parents',branch='codex/s81-hub-parents-0811',tag='split1',purpose='Source-exact candidate; no parent adoption or inherited native view.',extra_paths=['tools/s81_ph','rtl/dsrom_sys/s81_ph','rtl/common','rtl/dsrom_sys/s81_glue',str(pins_dir)],benches=[
           dict(name='capture_split_exact',cmd="bash tools/s81_ph/capc_split_bench.sh {RUN}/bench eq 'mix mix11 mix12 mix13 trace err over range rreq'",expect='pass',pass_regex='^CAPC_BENCH PASS cases=9$',threads=8,peak_ram_gb=16),
           dict(name='capture_split_mutant',cmd="bash tools/s81_ph/capc_split_bench.sh {RUN}/mut mut 'mix' S81PH_CAPS_MUT_STATUS",expect='fail',fail_regex='CAPC_EQ mismatches=[1-9][0-9]*.*EQ_FAIL',threads=8,peak_ram_gb=16)]))
        if row['requested_outline_um'][0]<17.28:
            spec['route']['m5_pg_pitch']=2.7
        if dual:
            inp='f_w' if master.startswith('dsfd_capt_x8_data_') else 'f_sn';out='t_vm' if inp=='f_w' else 't_st'
            spec.update(clock='multiple_cts_roots',clock_ports=clocks,clock_data_paths='related_pll_ratio',clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[4,3],phase_ps=0),clock_entry_domains={
              'core':dict(ratio=[1,1],ports=[clocks[0]],inputs=['rst',inp],outputs=['t_ho'] if inp=='f_w' else []),
              'serial':dict(ratio=[4,3],ports=[clocks[1]],inputs=['rsv'],outputs=[out])})
        if master in ('dsfd_capt_ctl','dsfd_capt_cd'):
            spec['reroute_reason']=dict(kind='slot_change',change='Die lead granted independent compactctl324x86.4 or CD15.12 native-reset rekit; no old view inheritance. Assigned pin contract required.')
        rows[master]=spec
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pins-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--require-assigned',action='store_true');a=p.parse_args()
    rows=specs(a.pins_dir)
    if a.require_assigned:
        for s in rows.values():
            if not (ROOT/s['io_tcl']).is_file():raise ValueError('missing actual assigned pin file '+s['io_tcl'])
    a.out.mkdir(parents=True,exist_ok=True)
    for m,s in rows.items():(a.out/(m+'.json')).write_text(json.dumps(s,indent=2)+'\n')
    print('CAPTURE_SPLIT_SPECS',len(rows),'ASSIGNED' if a.require_assigned else 'DRAFT ONLY')
