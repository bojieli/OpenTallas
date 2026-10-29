#!/usr/bin/env python3
"""Source-index and pin-geometry estimates only. No RTL change, STA or physical-build result."""
import json,re,math,sys
from pathlib import Path
P=Path(__file__).parent
macro_map=json.load(open(sys.argv[1]));text=Path(sys.argv[2]).read_text();pins=json.load(open(sys.argv[3]));mw,mh=172.824,41.064
mports={}
for n,b in re.findall(r'^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$',text,re.M|re.S):
 if not(n.startswith('rd_out[')or n.startswith('wd_in[')):continue
 a=re.search(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',b);mports[n]=[(float(a[1])+float(a[3]))/2,(float(a[2])+float(a[4]))/2]
rd={int(re.search(r'\[(\d+)\]',n)[1]):p for n,p in mports.items()if n.startswith('rd_out[')};wd={int(re.search(r'\[(\d+)\]',n)[1]):p for n,p in mports.items()if n.startswith('wd_in[')}
cap={int(re.search(r'\[(\d+)\]',p['name'])[1]):p for p in pins if p['name'].startswith('u_output_sr_d[')};src={int(re.search(r'\[(\d+)\]',p['name'])[1]):p for p in pins if p['name'].startswith('g_operand_2_u_group_sw_d[')}
# Source-level witness: one sector enabled, one write word masked, any bank selected, no bank conflict.
witness=[]
for bank in range(16):
 for word in range(16):
  sec,j=divmod(word,8)
  for ks in range(8):
   base=(bank-j)%16;carry=(base+j)//16;address=(((ks-carry)%8)<<4)+base;actual=address+j
   assert actual%16==bank and (actual>>4)%8==ks
   witness.append([bank,sec,j,ks,address])
write_witnesses=0
for bank in range(16):
 for word in range(64):
  sec,j=divmod(word,8)
  for ks in range(8):
   base=(bank-j)%16;carry=(base+j)//16;address=(((ks-carry)%8)<<4)+base;actual=address+j
   assert actual%16==bank and (actual>>4)%8==ks and sec<8
   write_witnesses+=1
# Macro rd_out[p] reaches sr_d[32*word+p%32] for every bank, word, ks (p%32 is lane bit).
span={b:max(cap[i]['y']for i in range(b,512,32))-min(cap[i]['y']for i in range(b,512,32))for b in range(32)}
fs={'R0':lambda x,y:(x,y),'MX':lambda x,y:(x,mh-y),'MY':lambda x,y:(mw-x,y),'R180':lambda x,y:(mw-x,mh-y),'R90':lambda x,y:(mh-y,x),'R270':lambda x,y:(y,mw-x),'MXR90':lambda x,y:(y,x),'MYR90':lambda x,y:(mh-y,mw-x)}
bounds=[]
for n,fn in fs.items():
 xx=[];lo=[];hi=[]
 for bit,(x,y)in rd.items():
  x,y=fn(x,y);ys=[cap[i]['y']for i in range(bit%32,512,32)];xx.append(405-(max(ys)-min(ys))/2+.096-x);lo.append(max(ys)-405-y);hi.append(min(ys)+405-y)
 bounds.append(dict(orient=n,origin_x_max_um=min(xx),origin_y_optimistic_min_um=max(lo),origin_y_optimistic_max_um=min(hi),feasible_ignoring_all_other_constraints=min(xx)>=0))
horz=[b for b in bounds if b['orient']in('R0','MX','MY','R180')and b['feasible_ignoring_all_other_constraints']];vert=[b for b in bounds if b['orient']not in('R0','MX','MY','R180')and b['feasible_ignoring_all_other_constraints']]
def count(bs,w,h):
 X=max(b['origin_x_max_um']for b in bs);lo=min(b['origin_y_optimistic_min_um']for b in bs);hi=max(b['origin_y_optimistic_max_um']for b in bs)
 # Two identical-orientation rectangle origins in the same w-by-h bin would overlap. Allow all bins, even mutually conflicting mixed orientations.
 return dict(x_max_um=X,y_min_um=lo,y_max_um=hi,x_origin_bins=math.floor(X/w)+1,y_origin_bins=math.floor((hi-lo)/h)+1,macro_upper_bound=(math.floor(X/w)+1)*(math.floor((hi-lo)/h)+1))
hb=count(horz,mw,mh);vb=count(vert,mh,mw)
# Input stage data:64independent word choices for each bit, shared by group0 and group1.
in_span={b:max(src[i]['y']for i in range(b,2048,32))-min(src[i]['y']for i in range(b,2048,32))for b in range(32)}
wdx_min=min(p['x']for p in src.values())-(405-min(in_span.values())/2)
vertical_write_bounds=[]
for n,fn in fs.items():
 if n in ('R0','MX','MY','R180'):continue
 local=[fn(*pt)for pt in wd.values()];xmin=wdx_min-min(p[0]for p in local);xmax=760.32-mh
 vertical_write_bounds.append(dict(orient=n,origin_x_min_um=xmin,origin_x_max_um=xmax))
write_xlo=min(z['origin_x_min_um']for z in vertical_write_bounds);write_xhi=max(z['origin_x_max_um']for z in vertical_write_bounds)
write_rot_bound=(math.floor((write_xhi-write_xlo)/mh)+1)*(math.floor((691.2-mw)/mw)+1)
# Candidate W-output window only; 2cols8rows, N/S1.08 halo rather than default4.32. Not whole-core approval.
window=86.4;newpins={i:{**cap[i],'y':302.4+round((i*window/511)/.048)*.048}for i in range(512)};positions=[];worst=(0,None)
oldout={int(re.search(r'g_bank\[(\d+)\]',m['k'])[1]):m for m in macro_map['macro_placement']if'.u_output.'in m['k']}
for bank in range(16):
 c,r=divmod(bank,8);x=[12.96,198.666][c];y=172.8+r*(mh+2.16);orient='MX'if r<4 else'R0';positions.append({**oldout[bank], 'origin_um':[round(x,3),round(y,3)],'orient':orient})
 for bit,pt in rd.items():
  px,py=fs[orient](*pt);px+=x;py+=y
  for i in range(bit%32,512,32):
   z=newpins[i];L=abs(px-z['x'])+abs(py-z['y'])
   if L>worst[0]:worst=(L,[bank,bit,i])
# Full old-capture geometry subset and source ownership; no non-output placement is proposed.
own=[]
for m in macro_map['macro_placement']:
 group=re.search(r'\.(u_output|u_group[01])\.',m['k'])[1];bank=int(re.search(r'g_bank\[(\d+)\]',m['k'])[1]);own.append(dict(macro_instance=m['k'],group=group,bank=bank,local_bank_logic=[f'{group}.g_bank[{bank}].u_b.ks',f'{group}.b_re[{bank}]',f'{group}.b_ra[{bank}]',f'{group}.b_we[{bank}]',f'{group}.b_wa[{bank}]',f'{group}.b_wd[{bank}]'],shared_read_consumers='g_rd[l] candidates {l,l^1,l>>1,(l>>1)+8}; lane0 any bank'if group!='u_output'else'g_srl[0..1].g_sr[0..7] arbitrary bank selected by sr_lo+word',write_producers='sharedgroup0_sw_d[2047:0], variable-bank selector wsel'if group!='u_output'else'output_lwd[511:0], lane write selector wsel'))
result=dict(qualification='ESTIMATE ONLY at planned pin terminals; no signoff/build claim',source_index_witnesses=len(witness),shared_write_index_witnesses=write_witnesses,source_index_witness_sample=witness[:16],required_output_banks=16,old_output_bit_capture_span_um=[min(span.values()),max(span.values())],orientation_origin_bounds=bounds,horizontal_packing_upper_bound=hb,vertical_packing_upper_bound=vb,all_orientation_optimistic_macro_upper_bound=hb['macro_upper_bound']+vb['macro_upper_bound'],packing_assumptions=['ignore all halos, all other32macros, clock/logic/PDN; coreLL>=0 only','allow all8orientations, though currentR-SRAM-entry rule usesR0','pincontact rectangular extents only~.024um cannot change3+4packing bins','405um endpoint model at planned pins; actual pin-FF offsets require their own placed review'],old_shared_swd_bit_source_span_um=[min(in_span.values()),max(in_span.values())],old_shared_swd_required_all_write_pins_x_min_um=wdx_min,old_shared_swd_macro_horizontal_width_um=mw,old_shared_swd_available_east_strip_um=760.32-wdx_min,old_shared_swd_rotated_origin_bounds=vertical_write_bounds,old_shared_swd_all_orientation_macro_upper_bound=write_rot_bound,old_shared_swd_qualification='Allwd_in256pins carry32livebits repeated8times; everybit occurs onWandE. CurrentEwindow cannot fit evenonehorizontalbank; optimisticallrotations pack<=3banks versus32stagebanks needed. This is a planned-pin-terminal estimate; nozero-cyclesharedinputtemplate repair is implemented.',output_window_candidate=dict(window_um=window,per_layer_pin_peak_per_um=6.0,centre_y_um=345.6,new_output_pins=list(newpins.values()),output_macro_positions=positions,EW_halo_um=4.32,NS_halo_um=1.08,rows8_pitch_um=mh+2.16,max_macro_pin_to_output_pin_um=worst[0],worst_bank_macrobit_portbit=worst[1],status='OUTPUT-GROUP-ONLY conditional estimate; defaultNS4.32cannotfitreach405; other32banks/sharedSWD/clockislands unresolved, no build'),next='Plan-owner event must repair all critical pin/fanout templates or split source groups/bank broadcast with priced pipeline; W-outputwindow alone is insufficient.')
(P/'estimate.json').write_text(json.dumps(result,indent=2)+'\n');(P/'macro_ownership.json').write_text(json.dumps(own,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['source_index_witnesses','old_output_bit_capture_span_um','all_orientation_optimistic_macro_upper_bound','old_shared_swd_bit_source_span_um','old_shared_swd_required_all_write_pins_x_min_um','old_shared_swd_available_east_strip_um']}));print('outputwindow',worst)
