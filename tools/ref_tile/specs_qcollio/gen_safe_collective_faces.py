#!/usr/bin/env python3
"""Source-bound SAFE faces for the dv2f18dh2 production calendar."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'tools/ref_tile/specs_qcollio/qfd_coll_face_s1.json'
CAL=ROOT/'results/rtl/qwen_coll_safe_1019/dv2f18dh2_coll_lane_latency.json'
OUT=ROOT/'rtl/physical/qwen_coll_safe_1019'

def main():
    calendar=json.loads(CAL.read_text())['calendar']
    assert calendar['LS']==378 and calendar['LU']==53
    profiles={
        'p':dict(FW=546,PHY=20,L=53,R=5,PEER_R=5),
        'r':dict(FW=514,PHY=20,L=53,R=5,PEER_R=5),
        's0':dict(FW=546,PHY=350,L=378,R=0,PEER_R=5),
        's1':dict(FW=546,PHY=339,L=378,R=0,PEER_R=0),
        's2':dict(FW=546,PHY=349,L=378,R=5,PEER_R=0),
    }
    OUT.mkdir(parents=True,exist_ok=True)
    original=(ROOT/'rtl/physical/ot_qfd_coll_static_face.sv').read_text()
    first=original.index(' input wire cal_ck')
    ports=original[first:original.index('\n);',first)]
    all_ports=['cal_ck','cal_lck','tx_wck','tx_rck','rx_wck','rx_rck','rst_n','tx_slot','peer_slot',
               'tx_valid','tx_data','rx_valid','rx_data','phy_up','phy_rx_valid','phy_rx',
               'phy_tx_valid','phy_tx','phy_tx_slot','phy_rx_slot','cdc_fault','epoch_abort','fault_cause']
    for label,profile in profiles.items():
        name='qfd_coll_face_'+label+'_safe'
        header=ports.replace('input wire [4:0] codec_ck,','input wire codec0,codec1,codec2,codec3,codec4,')
        header=header.replace('FW-1',str(profile['FW']-1)).replace('PW-1',str(profile['FW']+50))
        param=','.join(f'.{k}({v})' for k,v in profile.items())
        con=','.join(f'.{p}({p})' for p in all_ports)
        rtl=(f'`timescale 1ns/1ps\n// Generated from {CAL.relative_to(ROOT)}; fixed production profile.\n'
             f'module {name}(\n{header}\n);\n'
             f' qfd_coll_static_face #({param},.TOK_REG(1),.SAFE(1))u_body(\n'
             f' .codec_ck({{codec4,codec3,codec2,codec1,codec0}}),{con});\nendmodule\n')
        wrapper=OUT/(name+'.sv');wrapper.write_text(rtl)
        spec=copy.deepcopy(json.loads(BASE.read_text()))
        spec.update(name=name,top=name,params={},outline=dict(w=950.4,h=561.6))
        spec['sources'].insert(0,str(wrapper.relative_to(ROOT)))
        spec['clock_ports']=[p for p in spec['clock_ports'] if not p.startswith('codec_ck')]+['codec'+str(i) for i in range(5)]
        spec['clock_cts_roots']=['cal_ck','cal_lck','codec0']
        for i in range(5):spec['clock_entry_domains']['codec'+str(i)]['ports']=['codec'+str(i)]
        spec['clock_entry_domains']['core']['inputs']+=['tx_slot','tx_valid','tx_data']
        spec['clock_entry_domains']['txw']['inputs']=[]
        spec['pins']={
            'W':['tx_slot','peer_slot','tx_valid','tx_data','rx_valid','rx_data','cdc_fault','cal_ck','tx_wck','rx_rck','tx_rck','rx_wck'],
            'E':['phy_up','phy_tx_valid','phy_tx','phy_rx_valid','phy_rx','phy_tx_slot','phy_rx_slot','epoch_abort','fault_cause','codec0'],
            'N':['cal_lck','rst_n'], 'S':['codec1','codec2','codec3','codec4']}
        spec['pin_ranges']={
            'tx_data':[16,230],'rx_data':[310,530], 'tx_slot':[234,236],'peer_slot':[239,241],
            'tx_valid':[244,246],'rx_valid':[296,298],'cdc_fault':[286,292],
            'cal_ck':[260,262],'tx_wck':[136,138],'rx_rck':[392,394],'tx_rck':[194,196],'rx_wck':[454,456],
            'phy_tx':[16,230],'phy_rx':[310,530],'phy_up':[249,251],'epoch_abort':[254,256],
            'fault_cause':[259,264],'codec0':[269,271],'phy_tx_slot':[275,277],'phy_rx_slot':[281,283],
            'phy_tx_valid':[235,237],'phy_rx_valid':[302,304],
            'cal_lck':[619,621],'rst_n':[300,302],
            'codec1':[492,494],'codec2':[500,502],'codec3':[752,754],'codec4':[760,762]}
        spec['children'][0]['at']=[129.6,43.2]
        spec['children'][1].update(at=[129.6,302.4],orient='MY')
        for k,c in enumerate(spec['children'][2:]):
            c.update(at=[388.8 if k<2 else 648,43.2 if k%2==0 else 259.2],orient='R0')
        spec['route'].update(pd=.5,threads=8,peak_ram_gb=48,hold_margin_ns=.03,io_hold_margin_ns=.03)
        spec['defines']=['OT_QFD_FACE_HARD']
        spec['reset_landing']=dict(enable=True,stages=2,clock='cal_ck')
        spec['io_flop_at_pins']=dict(cols=6,allow_none=True)
        spec['structural_change']=(
            'SAFE=1/TOK_REG=1: stationary <=16-token banks replace delay chains; exact four-slot E2 core/link token landings; '
            'kept same-depth reset copies; reset-free codec metadata; captured PHY-up with +1 fault observation edge. '
            'RX CDC mirrored so its write face is adjacent to codec; fault/abort pins beside PHY-up on E; scalar bank-clock '
            'pins on S avoid long undriven/raw clock reach. Five hard children on43.2 lattice; RX MY child uses owner-approved +0.024um X track legalization (proof JSON); continuous full-width '
            'std-cell band y475.2..561.6. Local CTS entries beside core/codec masses. Normal calendar unchanged. Boundary reset landing adds2 startup edges before the unchanged same-depth local copies.')
        spec['slot_change_request']='SAFE face 950.4x561.6; production parent/die must use source-bound new outline, pins and measured clock references.'
        spec['pin_regs']['reason']='SAFE/TOK_REG registered owning roots; exact calendar neutral. PHY-up captured; no extra automatic data stages.'
        spec['job'].update(owner='Codex:SAFE-QW-COLL',branch='codex/safe-qw-coll-1019',tag='safe1',
            purpose='Safe source-bound dv2f18dh2 face; critical review packet only, no automatic submit',
            views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}')
        for bench in spec['job']['benches']:
            bench['cmd']=bench['cmd'].replace('HARD=1 bash','FACE_L=378 SAFE=1 SIM=verilator HARD=1 bash')
            bench.update(threads=8,peak_ram_gb=48,needs=['verilator'])
            for key in ['pass_witness','fail_witness']:
                if key in bench:bench[key]='results/rtl/qwen_coll_safe_1019/r3/'+('m0.log' if key=='pass_witness' else 'm'+str(spec['job']['benches'].index(bench))+'.log')
        if label!='s1':
            spec['job']['benches']=[]
            spec['job']['no_bench_reason']='DRAFT PROFILE: full production RTL passes all five profiles; dedicated fixed-wrapper witness required before gate/submit.'
        spec['job']['extra_paths']+=['rtl/physical/qwen_coll_safe_1019','results/rtl/qwen_coll_safe_1019']
        path=ROOT/'tools/ref_tile/specs_qcollio'/(name+'.json')
        path.write_text(json.dumps(spec,indent=1)+'\n')
        print(path.relative_to(ROOT))

if __name__=='__main__':main()
