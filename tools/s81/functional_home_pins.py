#!/usr/bin/env python3
"""Allocate S81 missing functional homes against the measured v19c instance plan.
New slots are native RTL reservations, never bound shell cells. Production enable
requires actual child views and static memory/link calendar proofs.
"""
import json
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_functional';out.mkdir(exist_ok=True)
 ports={};x=200.064
 # VM is south of the MIX home; stream all row payloads at its S face.
 for p,n in [('rs_d',2560),('rs_v',5),('rq_v',5),('rq_row',70),('wq_d',512),('wq_mask',16),('wq_row',14),('wq_v',1)]:
  ports[p]=[['S','M5',round(x+.096*i,3),.192] for i in range(n)];x+=.096*n+.96
 y=100.032
 for p,n in [('c_cmd',85),('c_done',9),('c_st',2),('f_inp',1),('ck',25),('rst',1)]:
  ports[p]=[['E','M4',round(y+.096*i,3),.192] for i in range(n)];y+=.096*n+.96
 V.write(out,'dsfd_engram_mix_c',[1152.,864.],ports,'ck','VM-facing S payloads, sequencer-facing E command/root; staged routes required from actual source pins','v20_functional_home',{'clock_entries':{'stream':[f'ck[{i}]' for i in range(25)]},'adoption':'25 real child clock/reset entries; compiled static VM calendar required'})
 mix={'name':'sp_engram_mix','master':'dsfd_engram_mix_c','at_um':[13942.8,22770.0],'outline':{'w':1152.,'h':864.},'clock':'stream_1p2','geometry':'xsp7_screen plan.json.gz actual entire instance set:0overlaps','memory_calendar':{'read_rows_per_cycle':5,'read_port_shape_reserved':5,'write_rows_per_cycle':1,'format':'H/out packedBF16;K/W/V FP32','runtime_backpressure':False,'qualification':'OPEN: fixed source/flight/bank cycles must be compiled'},'pin_file':'physical/s81_die_pins/v20_functional/dsfd_engram_mix_c.tcl','qualification':'RESERVED_REAL_RTL_NOT_ROUTED'}
 hc=[]
 for band,y in [('south',1857.6),('middle',12238.56),('north',22350.24)]:
  for c in range(2):
   hc.append({'name':f'sp_hcx_{band}{c}','master':'ot_s81_hcx_projection_leaf','at_um':[17334.+907.2*c,y],'outline':{'w':864.,'h':1296.},'clock':'serial_0p9','geometry':('169 existing station/relay collisions in full middle band: relocation+reach check REQUIRED before submission' if band=='middle' else 'xsp7_screen actual instance set:0overlaps'), 'ROM':{'macro':'ot_rom_4096x72_m8','count':128,'used_rows_per_macro':160,'used_payload_bits_per_word':64,'phase_rows':'80attn+80ffn','physical_area_mm2':128*38.016*62.910/1e6,'weight_payload_bits':20480*32*2},'MAC':{'count':256,'cell_area_estimate_mm2':256*1168.791/1e6,'logic_utilization_target':.55},'X_stage':{'macro':'ot_sram_1r1w_128x256_m1_r2c2','count':16},'qualification':'RESERVATION: synthesis/clock/pins/staticcalendar/nativegate owed; middle relocation required'})
 data={'schema':'opentallas.s81.functional_homes.v1','scope':'one TP4 layer die owns6of24coefficients, both attn/ffn resident. All6 projection leaves required. Geometry source v19c xsp7 full instance plan. No synthetic ETM/stub permitted.','engine_ports':{'engram_lookup_mix':10,'hc_projection':11},'engram_mix':mix,'hc_projection':hc,'HC_memory_calendar':{'native_prefetch':'8VMrows/cycle80cycles perleaf,4096bit/cycle packedBF16 stagedbroadcast6ways','steady_compute':'80dot tasks perbank, canonical8bank csum, 6outputsparallel','runtime_credit_backpressure':False,'qualification':'OPEN fullactualcompiledphase/link/SRAMpipeline latency and bandwidth proof'},'native_clock_rule':'independent hardened roots phi-R_i; <=15k or measured<=300ps/80ps; no parent hidden state'}
 (out/'homes.json').write_text(json.dumps(data,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';d=json.loads(p.read_text());d['v20_functional_home_reservation']='physical/s81_die_pins/v20_functional/homes.json'
 # Keep north HCP clear of the accepted serial capture expansion (10.8um/cth).
 for slab in d['slots']:
  if slab.get('name')=='sp_hc_s':slab['outline']['h']=8633.52
  if slab.get('name')=='sp_hc_t':slab['outline']['h']=9020.16
 d['slots']=[s for s in d['slots'] if s.get('name') not in {mix['name'],*[s['name'] for s in hc]}]+[mix]+hc
 d.setdefault('changelog',[]).append('Codex S-DIE: reserve real Engram MIX and six HCP homes in measured voids; middle relay collisions OPEN; no production adoption without static calendar/native checks.')
 p.write_text(json.dumps(d,indent=1)+'\n');print('FUNCTIONAL_HOMES 1 MIX+6 HCP;4 HCP+MIX clean,2 HCP need middle relay relocation')
if __name__=='__main__':main()
