#!/usr/bin/env python3
"""Real F20 target -> mapped W187 programme calendar; all endpointcontrol bit mappings and mutants."""
import json,pathlib,subprocess,tempfile
R=pathlib.Path(__file__).resolve().parents[2]
s=json.loads((R/'tools/hbm_die_v15/v16_specs/host_completion.json').read_text())
links=dict(SW=('S0','S1','S2'),SE=('S3','S4'),NW=('N0','N1'),NE=('N2','N3'))
fields=[('rx_arm_v',1),('rx_arm_bank',1),('rx_block_words',7),('rx_release_v',1),
        ('rx_release_bank',1),('rx_slot_v',1),('rx_slot_bank',1),('rx_slot_index',6)]
for q,es in links.items():
    for j,ep in enumerate(es):
        lo=j*19
        for port,w in fields:
            es_=[e for e in s['edges'] if e['dst'][:2]==['ep_'+ep,port]]
            universal_fields={f['name']:f for f in json.loads((R/'results/arch/hbm_vm_calendar_1015/universal_layout.json').read_text())['fields']}
            bit_map={}
            for e in es_:
                assert e['src'][0]=='epcal_'+q
                f=universal_fields[e['src'][1]]
                for k in range(e['bits']):
                    di=e['dst'][2]+k
                    assert di not in bit_map
                    bit_map[di]=f['lo']+e['src'][2]+k
            assert bit_map=={k:lo+k for k in range(w)}
            lo+=w
print('EP_CALENDAR_MAPPING PASS171 bits/9 endpoints')
sources=['rtl/hbm_accel/host_static_20261015/tb_hbm_ep_calendar_host.sv',
         'rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv',
         'rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv',
         'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv',
         'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
with tempfile.TemporaryDirectory(prefix='hbm-epcal-') as td:
    for m in (0,1,2):
        subprocess.run(['iverilog','-g2012','-s','tb_hbm_ep_calendar_host','-Ptb_hbm_ep_calendar_host.MUT='+str(m),
                        '-o',td+'/sim']+[str(R/p) for p in sources],check=True)
        r=subprocess.run(['vvp',td+'/sim'],capture_output=True,text=True)
        print(f'MUT{m} rc={r.returncode}: {r.stdout.strip()}')
        assert (r.returncode==0 and 'EP_CALENDAR_HOST PASS' in r.stdout) if m==0 else (r.returncode!=0 and 'FATAL:' in r.stdout)
print('EP_CALENDAR_HOST_GATE PASS')
