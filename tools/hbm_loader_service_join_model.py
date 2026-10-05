#!/usr/bin/env python3
"""Finite current ND1 loader -> existing four-stack provider join, before RTL."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from hbm_accel_shared_join_model import build as shared_model
SOURCE='728217150'
ROOT=Path(__file__).resolve().parents[1]
def build():
    pins={}
    for p in ['rtl/hbm_accel/loader/ot_hbm_accel_loader_host_addr.sv','rtl/hbm_accel/loader/ot_hbm_accel_loader_addr_to_service.sv','rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv']:
        b=subprocess.check_output(['git','show',f'{SOURCE}:{p}'],cwd=ROOT);pins[p]=hashlib.sha256(b).hexdigest()
    return dict(source=SOURCE,source_pins=pins,default_enabled=False,adopted=False,
      selected='one bridge per physical die, existing four providers shared, no duplicate PC/controller/tag-owner macros',
      instance_counts=dict(DS=96,Qwen=4),per_die_ND=1,actual_parent_module='ot_hbm_accel_die_host_join',parent_instances_per_die=dict(loader_host_addr=1,loader_service_join=1,formatter=1,new_service_controllers=0),system_host_DMA='existing ot_hbm_host_dma_shared64 ND96/ND4 takes real burst master outputs',loader_address_bits=37,request_bits=341,reply_bits=273,
      formatter=dict(module='ot_hbm_accel_loader_addr_to_service',ENABLE=1,ADDR_W=37,STACK_W=2,SECTOR_W=34,STACK_BYTES=22500000000),
      address='stack=byte[36:35], localbyte=byte[34:0], checked localbyte+32<=22500000000; sector34=zeroextend(localbyte>>5)',
      provider_request=dict(bits=455,LEN=1,caller='all16 actual loader tag bits including STOREclass15',
        identity='actual hardware owner supplies192bit identity; stack/sector/caller must equal current formatter/tag, localdie1 preserved',
        producer='hardware lease/producer, never generated Python payload or synthetic oracle',global_rank='7bits retained outside contained per-die id.die1 namespace'),
      provider_owned=dict(bits=465,physical_tag_bits=12,beat_bits=5,return_flags='owned_we actual write visibility, owned_credit actual positive reverse grant'),
      service_ports=dict(requests=4,one_selected_per_transaction=True,owned_returns=4,one_held_response=True,
        other_clients='actual owned client6 demux; non-loader data/reversegrants pass unchanged, reverse credit per-stack held2:1 arbitration',reverse_mux_cell_um2_estimate=4*(192+12+5+1)*4,client_compare_cell_um2_estimate=4*6*4,reverse_id_bits=192,reverse_tag_bits=12,reverse_beat_bits=5,request_cut_bits=4*455,owned_cut_bits=4*465),
      flow='request -> exact owned DATA/physical write visibility -> actual loader rsp handshake -> retained full reverse tuple -> actual credit acceptance -> matching owned_credit grant -> next request',
      refusal=['missing hardware identity holds without fabricated identity','foreign id/caller/we/beat refuses ACK and retains state','partial strobes on writes refused rather than discarded','service fault holds transaction','reverse credit grant is not a second loader reply'],
      finite=dict(max_outstanding=1,raw_stored_bits=192+465+7+1+3+1+8,coded_storage_reservation_bits=800,
        coded_DFF_body_um2=800*.2916,identity_compare_cell_um2_estimate=(2*192+12+5)*4,
        payload_mux_cell_um2_estimate=3*465*4,stack_decode_cell_um2_estimate=4*2*4,
        four_stack_request_gate_um2_estimate=4*455*2),
      latency=dict(minimum_bridge_reverse_edges_after_rsp=2,service_tag_restore_core_edges=12,
        one_outstanding_effect='cold per-die payload throughput <=32B/(actual request->owned reply+reverse-grant interval); not MAXOUT/VOUT parallel throughput',
        host_ceiling_GBps=shared_model()['host']['shared_DMA']['peak_payload_GBps_at_1p2GHz'],
        no_free_overlap='source preload and STORE readback charged separately; actual service arbitration/row waits/reverse grant expose stalls',
        no_time_cap=True),
      physical='existing model constants and positive mux/compare/storage estimate; placement/loadedSSFF of bridge required, original loader/provider closure not transferred',
      next_parent_hooks=['bind actual hardware owner issuer identity, not constant dummy values','bind existing shared stack provider req/owned/credit ports','Erdos binds actual resident/window storage allocator and provider destinations; no wstream-count payload credit'])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();p=Path(a.out);p.mkdir(parents=True,exist_ok=True);(p/'model.json').write_text(json.dumps(build(),indent=2)+'\n');print('priced ND1 four-stack actual request/reply/reverse movement')
if __name__=='__main__':main()
