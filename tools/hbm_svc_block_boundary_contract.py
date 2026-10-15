#!/usr/bin/env python3
"""Source-exact corrected two-clock HBM boundary; physical/price gaps fail closed."""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_die_views as views

ROOT=Path(__file__).resolve().parents[1]
BASE=Path('rtl/hbm_accel/loader/service_native')
TOPS=('ot_hbm_svc_wb_block_cdc','ot_hbm_svc_prefetch_block_cdc','ot_hbm_svc_phy_mux','ot_hbm_svc_static_sm_rows')

def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def build():
    modules={}
    for top in TOPS:
        path=BASE/(top+'.sv')
        ports=views.L.parse_module(str(ROOT/path),top)['ports']
        rows={}
        for name,(direction,bits) in ports.items():
            domain=('hbm1024' if name.startswith(('hbm_','k_','kr_','rd_','wb_')) and top=='ot_hbm_svc_phy_mux'
                    else 'hbm1024' if name.startswith(('hbm_','k_','kr_'))
                    else 'stream833')
            rows[name]=dict(direction=direction,bits=bits,domain=domain)
        modules[top]=dict(source=str(path),sha256=sha(path),ports=rows)
    dependencies=[Path('rtl/chip/ot_chip_v41x_hbm3e_phy.sv'),Path('rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'),
                  Path('rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv'),Path('rtl/hbm_accel/service/ot_hbm_kport_map.sv'),
                  Path('rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv'),Path('rtl/lib/ot_async_fifo.sv'),Path('rtl/lib/ot_reset_sync.sv')]
    if '.CLK_PS(CLK_PS)' not in (ROOT/dependencies[0]).read_text().split('u_k (')[0]:
        raise ValueError('actual K-port PHY clock parameter is not forwarded')
    assert modules['ot_hbm_svc_wb_block_cdc']['ports']['done_sectors']['bits']==12
    assert modules['ot_hbm_svc_wb_block_cdc']['ports']['wd']['bits']==8*289
    assert modules['ot_hbm_svc_prefetch_block_cdc']['ports']['out_data']['bits']==8*256
    for top in TOPS[:2]:
        for clock in ('stream_clk','hbm_clk','stream_rst_n','hbm_rst_n'):
            assert modules[top]['ports'][clock]['bits']==1
    return dict(schema='opentallas.hbm-svc-block-boundary.v1',modules=modules,
        dependency_sha256={str(p):sha(p) for p in dependencies},
        clocks=dict(stream_period_ps=2500/3,hbm_period_ps=1024,relationship='asynchronous; actual FIFOs and synchronized block identity'),
        address=dict(global_wd='stack2,local_sector30',k_addr='full local sector30',pc='s[6:2]^s[11:7]^s[16:12]'),
        writeback=dict(admission='one reserve_ready check per buffer block',payload='8x{v,global_sector32,data256}',
                       fixed_fill_cycles='ceil(total/8), total1..2048',posted_count='done_v ? done_sectors12 : 0',
                       completion='only matching actual k_wr_done for every sector, returned through ACK CDC with bank/epoch'),
        prefetch=dict(admission='whole block ready before compiled start',fixed_delivery_cycles='ceil(total/8)',
                      issue_policy='serialized source-correct successor only; NOT throughput-qualified',
                      response_identity='full epoch16/bank and physical owner ordinal; arbitrary response waits remain inside boundary'),
        physical_inventory=dict(wb_sram_macros=32,prefetch_sram_macros=32,sm_row_macros_per_sm=5,
                                wb_payload_fifos=8,prefetch_payload_fifos=8,
                                old_34_pc_wrappers='historical address/clock assumptions rejected; not corrected block physical wrappers'),
        fail_closed_requirements=[
            'Corrected block hardware is not yet physically partitioned into all34 accepted service bands',
            'Actual 900GB/s/stack service price and production prefetch overlap not met by serialized issue',
            'Actual compiler83bit SM program, real scale/weight allocation and rowcache fill calendar not bound',
            'Actual loader programme/native block command issuer not bound',
            'Real macro placements, source-derived clock sink census, CTS and die timing not qualified',
            '2334 shared PHY W/clock/status bits require explicit active-source or protocol-idle binding',
            'Mapped PHY, root clock/reset and every physical boundary require source-exact station graph and timing evidence'],
        qualified=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'physical/hbm_accel_die_views/svc/v15/block_boundary_contract.json');ap.add_argument('--require-qualified',action='store_true');a=ap.parse_args()
    d=build();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n')
    print('BLOCK_BOUNDARY source headers exact; qualified=False; outstanding='+str(len(d['fail_closed_requirements'])))
    if a.require_qualified:raise SystemExit(2)
