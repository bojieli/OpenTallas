#!/usr/bin/env python3
"""Build physical candidates for the four independently rooted landing lanes, after the analytical model."""
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_vm'))
from landing_lane_model import model
P=ROOT/'physical/s81_vm_landing_lanes_1417'; P.mkdir(parents=True,exist_ok=True)
widths=dict(ck=1,rst_n=1,larm_v=1,larm_g=4,larm_base=14,i_v=1,i_d=512,o_v=1,o_row=14,o_d=512,fault=3)
for lane in range(4):
    m=model()['lanes'][lane]; side=m['outline_um'][0]
    if lane<2: faces=dict(W=['ck','rst_n','larm_v','larm_g','larm_base','i_v'],N=['i_d'],S=['o_d','o_v','o_row'],E=['fault'])
    else: faces=dict(N=['ck','rst_n','larm_v','larm_g','larm_base','i_v'],E=['i_d'],W=['o_d','o_v','o_row'],S=['fault'])
    tcl=[]
    for face,ports in faces.items():
        layer='M5' if face in 'NS' else 'M4'
        sites=[]
        for k in range(int(side/.048)):
            x=round(.012+.048*k,3)
            if x<4.32 or x>side-4.32 or (layer=='M5' and .18<=x%5.4<=.74):continue
            if not sites or x-sites[-1]>=.144-1e-6:sites.append(x)
        bits=[(p,i) for p in ports for i in range(widths[p])]
        assert len(sites)>=len(bits),(face,len(bits),len(sites))
        for j,(p,i) in enumerate(bits):
            v=sites[int((j+.5)*len(sites)/len(bits))]
            x,y=(v,side if face=='N' else 0) if face in 'NS' else (side if face=='E' else 0,v)
            p=p if widths[p]==1 else f'{p}[{i}]'
            size='.024 .192' if layer=='M5' else '.192 .024'
            tcl.append(f'place_pin -pin_name {{{p}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{size}}} -force_to_die_boundary')
    pin=P/f'lane{lane}.tcl';pin.write_text('\n'.join(tcl)+'\n')
    benches=[]
    for mode in ['base','stride','rowskew']:
        b=dict(name='landing_lane_'+mode,cmd=f'bash tools/s81_vm/landing_lane_gate.sh {{RUN}}/bench/lane_{mode} {mode}',
               expect='pass' if mode=='base' else 'fail',threads=1,peak_ram_gb=1,needs=['iverilog'])
        b['pass_regex' if mode=='base' else 'fail_regex']='LANDING_LANE '+('PASS' if mode=='base' else 'FAIL')
        benches.append(b)
    spec=dict(name=f'dsfd_vm_static_landing_lane{lane}_native_1417',top='dsfd_vm_static_landing_lane',kind='tile',
        sources=['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_landing_lane.sv'],params=dict(LANE=lane),
        clock_port='ck',reset_ports=['rst_n'],outline=dict(w=side,h=side,exact=True),pins=faces,io_tcl=str(pin.relative_to(ROOT)),
        macros=[],route=dict(pd=.4,threads=8,peak_ram_gb=16,period_ps=770,hold_margin_ns=.03,
            cts_sink=dict(size=16,diameter_um=20,extra='-distance_between_buffers 15')),
        recipe=2,io_flop_at_pins=dict(cols=4,allow_none=True),inhold=True,outhold=True,
        keep_pin_regs=True,pin_reg_split=True,hold_pad=dict(cell='HB2xp67_ASAP7_75t_R',out_cell='HB1xp67_ASAP7_75t_R'),
        io_budget=dict(**{'in':.55,'out':.55}),
        structural_change='r5 monolithic landing repeatedly failed FF with57ps input-to-local clock difference. Replace with four independently hardened512b lane leaves, one local reset/arm/counter/root per lane, opposing local payload pin faces. No shared payload/control clock tree; no added age or throughput cost. Model tools/s81_vm/landing_lane_model.json; startup and age2 exact against r4 reference; all four lane data retained.',
        slot_change_request=dict(contract='S81 VM landing four-root candidate',version='1417',
            why='4x95.04um lane leaves per slice instead181.44um monolith; +12 clock pins across4slices; +.0128397mm2 across4slices; parent14mm2 fit pending'),
        job=dict(owner='codex:S81 VM landing1417',branch='codex/s81-vm-landing-1417',tag='split1',cycles_added=0,
            extra_paths=['tools/s81_vm','rtl/dsrom_sys/s81_ph/vm','physical/s81_vm_landing_lanes_1417'],
            purpose='Independent lane root structural replacement; exact full4lane age2/startup equivalence and two observed failing DUT mutants.',benches=benches))
    path=P/f'lane{lane}.json';path.write_text(json.dumps(spec,indent=1)+'\n')
    subprocess.run([sys.executable,str(ROOT/'tools/ref_tile/ref_tile.py'),'gen',str(path)],check=True,cwd=ROOT)
