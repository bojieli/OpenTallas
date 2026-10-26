#!/usr/bin/env python3
"""Pre-build actual INDEX512 -> native TKM deterministic seam model.

No SU request latency is used. Producer first-output latency is an explicit
required input once its source-pinned implementation is available.
"""
import argparse,json

def model(producer_first_launch,groups=1,k=512,nout=512):
 if groups not in (1,2,4,8,96):raise ValueError('native HGI group required')
 if not 0<nout<=k<=2048:raise ValueError('native TOPK bounds')
 n,pf,kmax=512,64,2048
 beats=(groups*pf+3)//4
 settle=3*((kmax+63)//64)+8
 ingress_end=8+beats*8
 cells=(nout+3)//4
 finish=ingress_end+2*settle+3*cells+24
 return {'scope':'typed candidate producer/qslots/TKM seam; actual producer must supply first-output contract',
 'actual_clock_entries':64,'clock_roots':{'selector':17,'staging':9,'ingest_check':1,'shared_ingress':1,'qslots':2,'TKM':34},
 'cfg_n':n,'cfg_pf':pf,'cfg_g':groups,'cfg_k':k,'cfg_nout':nout,'native_KMAX':kmax,
 'producer_first_launch':producer_first_launch,'producer_flits_per_rank':64,'beats_per_rank':16,
 'beat_spacing':8,'producer_selected_pair_inventory_per_rank':512,
 'qslots_source_sample':producer_first_launch+3,
 'qslots_first_output_launch':producer_first_launch+5,
 'TKM_first_sample':producer_first_launch+6,
 'TKM_start':producer_first_launch-3,
 'TKM_last_sample':producer_first_launch+6+8*(beats-1),
 'TKM_done':producer_first_launch-3+finish+1,
 'TKM_done_edges_from_start':finish+1,
 'native_operand_format':'545 bits: valid bit544,rank bits535:528,index bits527:512;8FP32 values bits255:0,8U32 IDs bits511:256',
 'native_index_rule':'group-relative ordinal (rank-gbase)*64+flit; no synthetic selected values',
 'new_transport_budget':{'sources':4,'sinks':4,'payload_bits':545,
 'capture_root_declared_bits':4*546+1,'output_root_declared_bits':4*545+4*545+4+8+8+2,
 'arbitration':False,'storage':'two explicit fixed capture/egress stages, no elastic queue'},
 'production_parent_note':'typed VM/IDX station adds two fixed source-capture edges; existing NS11 SW output root14824 unchanged; new local4x4 transport is separate component composition' ,
 'qualification':'unverified until source-pinned native producer and actual TKM composition execute'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--producer-first-launch',type=int,required=True);p.add_argument('--groups',type=int,default=1);a=p.parse_args();print(json.dumps(model(a.producer_first_launch,a.groups),indent=2))
