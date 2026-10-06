#!/usr/bin/env python3
"""Before-build bounds for native station function cores, not an adoption model.
Uses actual existing W2 checked representation and existing die slot reservations.
"""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[4]
rows=[]
for function,w,ni,no in [('multicast',2063,1,3),('multicast_root',2063,1,4),('gather2',540,2,1),('gather4',1080,4,1),('gather8',2160,8,1)]:
 iw=w//ni if function.startswith('gather') else w
 # input payload + real192 identity + valid bit. Actual W2 bank adds five
 # protected repair/controller/snapshot/mask words and two held failure bits.
 n=(iw+192+1+63)//64
 input_ff=ni*((n+5)*72+2)
 controller_ff=(1+5)*72+2
 ack_ff=no*((4+5)*72+2) if ni==1 else 0
 ff=input_ff+controller_ff+ack_ff
 payload_in=ni*(iw+192+2)
 payload_out=no*(w+192+2)
 ack_in=no*(192+1) if ni==1 else 0
 rows.append(dict(function=function,payload_bits=w,input_count=ni,output_count=no,input_width=iw,
  capture_words_each=n,protected_input_FF=input_ff,protected_controller_FF=controller_ff,protected_ACK_receipt_FF=ack_ff,total_FF=ff,
  coded_payload_bits_per_capture=ni*n*72,input_bits_per_accept=payload_in,output_bits_per_accept=payload_out,reverse_ack_bits=ack_in,
  MACs_per_cycle=0,memory_ports='existing checked FF banks; one local capture/stream per edge, one controller load',
  transport_replica_cost=dict(checked_banks=ni+1+(no if ni==1 else 0),encoder64_count=ni*n+1+(4*no if ni==1 else 0),checker72_count=ni*(n+5)+6+(9*no if ni==1 else 0),owner_comparators=max(ni-1,no)),
  FF_area_um2=ff*.2916,FF_placement_um2_at55=ff*.2916/.55,legacy_raw_FF_reserved=4*w,
  clock='1.2GHz positive root for held function; actual even four-inverter forwarded root. Related receiver insertion/hold still OPEN.',
  composed_latency_edges=dict(input_capture=1,publication_arm=1,join='wait all actual input permissions',retire=('all actual branch acceptances + matching reverse ACK, never acceptance-only' if ni==1 else 'one atomic output acceptance retires all input seats')),
  routing=dict(pitch_um=.048,branch_bits_with_owner_ack=(w+192+192+4) if ni==1 else w+192+2,tracks_1layer_required=(w+192+192+4) if ni==1 else w+192+2,
   mcast_leaf_face_um=120.936,mcast_leaf_guarded_capacity_tracks=int((120.936-24)/.048),mcast_leaf_needs_growth=ni==1 and w+388>int((120.936-24)/.048)),
  default_off=True,actual_gold_required=True,physical_closed=False,model_gain_credit=False,
  parent_COMPOSITION_open=['actual per-input expected ownership/cohort map','bit order from corrected die source owner','actual reset/drain/related clock insertion','rate price in unified model after measured component latency','actual channel/pin dimensions including new owner/ACK pins']))
sources=['tools/uarch_model.py','tools/hbm_accel_die_fp.py','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv','physical/hbm_die_abstracts_20261006/memory_control/ot_hbm_die_vm_multicast_root.sv']
out=dict(schema='opentallas.hbm.links.function_prebuild.v1',source_hashes={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources},rows=rows,
 status='SIZED_COMPONENT_GLUE_ONLY_PARENT_MAP_AND_PHYSICAL_OPEN',station_master_count=1,new_208_modules=False,
 cdist=dict(legacy_bits=45,actual_forward_bits=42,actual_reverse_bits=3,groups=8,forward_total_bits=336,reverse_total_bits=24,source_owner_required=True),
 duplex=dict(TF5_each_direction=487,TF5_total=974,actual_TU_default_PWT=545,status='configured tuple/credit mapping required; cannot connect assumed487 to default545'),
 protection='Existing W2 bank repair/fail-closed implementation unchanged; no free protection; no timing closure inherited',route_launch_allowed=False)
p=root/'results/physical/hbm_die_abstracts_20261006/links/parents/function_prebuild.json';p.write_text(json.dumps(out,indent=2)+'\n')
print('SIZED before build; actual checked FF/owner/ACK costs; multicast leaf pin-face growth required; no parent closure')
