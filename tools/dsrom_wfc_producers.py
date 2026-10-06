#!/usr/bin/env python3
"""Size finite WFC producers and emit books from retained literal S81 programs."""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='results/rtl/dsrom_recovery_20261004/stage37_source_candidate/source_continuation_candidate'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def book(layer):
 import hdc_isa_v41 as isa
 base=ROOT/SOURCE;dispatch=json.loads((base/'parent_dispatch.json').read_text())
 groups=[g for g in dispatch['ownerorderedgroups'] if dispatch['offers'][g[0]]['node'].startswith(f'L{layer}.')]
 assert groups and layer in (19,20)
 images={};pins={};records=[[] for _ in range(4)];ends=[]
 for group_number,group in enumerate(groups):
  for rank,index in enumerate(group):
   offer=dispatch['offers'][index];assert offer['rank']==rank
   home=offer['stage'];p=base/f's{home}_r{rank}/prog.hex'
   assert digest(p)==dispatch['artifacts'][str(p.relative_to(base))]
   pins[str(p.relative_to(ROOT))]=digest(p)
   if (home,rank) not in images:images[home,rank]=[int(w,16) for w in p.read_text().splitlines()]
   words=images[home,rank];entry=offer['entry'];pc=entry
   while True:
    d=isa.decode(words[pc],full_shape=True);end=d['unit']==isa.UNIT_END and d['ctl']==0
    # 64bit protected-source ROM payload: home7, entry14, PC14, unit4,
    # end1, last1, group8. No ROM ECC or parity sidecar.
    value=home | entry<<7 | pc<<21 | d['unit']<<35 | int(end)<<39 | int(end and group_number==len(groups)-1)<<40 | group_number<<41
    records[rank].append(dict(home=home,entry=entry,pc=pc,unit=d['unit'],end=end,last=end and group_number==len(groups)-1,group=group_number,word=f'{value:018x}',instruction_sha256=hashlib.sha256(f'{words[pc]:0512x}'.encode()).hexdigest()))
    if end:break
    pc+=1;assert pc<len(words)
   ends.append(dict(rank=rank,home=home,entry=entry,end_pc=pc,group=group_number))
 assert all(len(r)<=4096 for r in records)
 return dict(layer=layer,groups=len(groups),records=records,ends=ends,source_sha256=pins,source_dispatch_sha256=digest(base/'parent_dispatch.json'),scope='complete emitted layer source groups; requires real restore, native retire and final visibility receipts, never END-only completion')
def model(layer):
 b=book(layer);s=ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.json';r=ROOT/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.json'
 sm=json.loads(s.read_text());rm=json.loads(r.read_text())
 # Full866 user envelope. Canonical host PMAX8; WFC WIN6 + two
 # synchronous prefetch seats requires8 tagged draft seats per user.
 # Full absolute position21/user10/block4 retained inside mutable SECDED.
 users=866;prompt=8;positions=8;slots=users*(prompt+positions);rows=math.ceil(slots/2);banks=math.ceil(rows/512)
 # Data57 = user10 + position21 + block4 + known1 + token21; SECDED64, two per128bit word.
 # Real programmed values; no generated golden token or fake control defaults.
 logic_upper=30000.;macro_area=banks*sm['area']['macro_area_um2']+4*rm['area']['macro_area_um2']
 producer_width=480.;producer_height=400.;halo=2.16
 macro_halo=banks*(sm['area']['macro_width_um']+2*halo)*(sm['area']['macro_height_um']+2*halo)+4*(rm['area']['macro_width_um']+2*halo)*(rm['area']['macro_height_um']+2*halo)
 assert logic_upper/.5+macro_halo<(producer_width-4.32)*(producer_height-4.32)
 return dict(schema='opentallas.wfc.producers.v2',before_RTL=True,layer=layer,MAXU=users,prompt_prefix_words=prompt,draft_positions_per_user=positions,absolute_position_bits=21,draft_block_tags=16,prompt_payload_bits=57,prompt_encoded_bits=64,SRAM_SECDED=True,ROM_ECC=False,prompt_slots=slots,packed_rows=rows,SRAM_banks=banks,SRAM_primitive=s.parent.name,book_words_per_rank=[len(x) for x in b['records']],book_groups=b['groups'],book_replicas=4,book_primitive=r.parent.name,MACs_per_cycle=0,memory=dict(read_payload_bytes_per_cycle=21/8,prompt_physical_bytes_per_read=16,prompt_read_ports=1,prompt_write_ports=1,book_read_ports=4,book_physical_bytes_per_cycle=36),boundary=dict(prompt_request_bits=1+10+21+4,prompt_response_bits=21+1,whole_request_bits=1+47+21+14,whole_result_bits=1+47+21+32,source_event_lanes=4,command_event_bits_per_lane=1+47+21+7+14+14+4),geometry=dict(macro_body_um2=macro_area,logic_upper_um2=logic_upper,macro_halo_reserved_um2=macro_halo,minimum_producer_envelope_um=[producer_width,producer_height],analytical_fit=True,selected_global_slot_owner='Turing',selected_global_slot_qualified=False),routing=dict(local_tracks_reserved=2048,available_tracks_for_envelope=math.floor((producer_width-4.32)/.096)*2,bank_read_mux=banks,bank_write_demux=banks,book_replicas=4,fanout_and_CTS_unqualified=True),latency=dict(prompt_reply_edges=1,prompt_validity_and_block_checked=True,boot_clear_rows=rows,run_admission_scan_words='users*prompt_len at one read/edge',new_engine_stages=0,whole_completion_wait='all literal commands, four real retirements/group, source restore and final identity-matched visibility; no fixed timer',token_rate_credit=0),clocks=dict(root='same enclosing actual clk as WFC/C8/native request and VM receipts',period_ps=1000/1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25,SRAM_timing=sm['timing'],book_timing=rm['timing'],physical_input_clocks_closed=False),source_sha256={str(s.relative_to(ROOT)):digest(s),str(r.relative_to(ROOT)):digest(r),**b['source_sha256']},source_dispatch_sha256=b['source_dispatch_sha256'],canonical_extent_sources={'prompt':'rtl/test/dsrom_sys/tb_dsrom_system.sv NPMAX8 and ot_dsrom_host_cq PMAX contract','draft':'rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv WIN6 plus pr_t0/pr_t1 two read seats; absolute tagged eight-seat cache, unknown outside resident window'},functional_adopted=False,route_ready=False,minimum_RTL_ready=True,missing_input_clocks=True)
def emit(layer,out):
 out.mkdir(parents=True,exist_ok=False);b=book(layer)
 for rank,rows in enumerate(b['records']):
  (out/f'rank{rank}.hex').write_text(''.join(x['word']+'\n' for x in rows))
  array=[0]*512
  for address,row in enumerate(rows):
   word=int(row['word'],16)
   for bit in range(72):
    if word>>bit&1:array[address//8]|=1<<(bit*8+address%8)
  (out/f'rank{rank}.viamap.hex').write_text(''.join(f'{x:0144x}\n' for x in array))
 (out/'book.json').write_text(json.dumps(b,indent=2)+'\n')
 return b
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--layer',type=int,choices=(19,20),default=19);p.add_argument('--model',type=Path);p.add_argument('--book',type=Path);a=p.parse_args()
 if a.model:a.model.parent.mkdir(parents=True,exist_ok=True);a.model.write_text(json.dumps(model(a.layer),indent=2)+'\n')
 if a.book:emit(a.layer,a.book)
