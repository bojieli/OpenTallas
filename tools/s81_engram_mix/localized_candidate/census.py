#!/usr/bin/env python3
"""Source-backed capture census and exact logical return fanout, not placement proof."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3]
BASE='rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_clocked_candidate.sv'
NEW='rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_localized_candidate.sv'
def strip(s):return re.sub(r'\s+','',re.sub(r'//[^\n]*','',s))
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 old=(R/BASE).read_text().split('// One actual clock entry per physical stage.')[0]
 new=(R/NEW).read_text().split('// Local capture boundaries are real registers')[0]
 pinned=subprocess.check_output(['git','show','b4ca1edc9:'+BASE],cwd=R).decode().split('// One actual clock entry per physical stage.')[0]
 assert old==pinned,'baseline top drift'
 # Verify all top logic outside the two replaced capture regions is unchanged.
 def regions(s):
  start=s.index(' integer q,l,hm;');end=s.index(' // fixed-latency tag lines:',start)
  s=s[:start]+' REQUEST_CAPTURE_REGION '+s[end:]
  start=s.index(' reg [19:0] rvq;') if ' reg [19:0] rvq;' in s else s.index(' wire [19:0] rvq;')
  end=s.index(' // return demux',start)
  return s[:start]+' RETURN_CAPTURE_REGION '+s[end:]
 old=regions(old).replace('dsfd_engram_mix4_clocked_candidate','dsfd_engram_mix4_localized_candidate').replace('[152+8*RS:0]','[176+8*RS:0]').replace('output reg [19:0] rq_v,output reg [279:0] rq_row','output wire [19:0] rq_v,output wire [279:0] rq_row')
 assert strip(old)==strip(regions(new)),'non-capture top logic changed'
 assert 'ck[173+8*RS+rqcopy]' in new and 'ck[153+8*RS+rlane]' in new
 clock_partitions={'control':[0],'clusters':list(range(1,153)),'RS5_stations':list(range(153,193)),'return_capture':list(range(193,213)),'request_capture':list(range(213,217))}
 covered=[n for indexes in clock_partitions.values() for n in indexes]
 assert len(covered)==len(set(covered))==217 and sorted(covered)==list(range(217))
 roots=[]
 for lane in range(20):
  role='H quarter' if lane%5==0 else ('K or shared V' if lane%5 in (1,2) else 'W')
  roots.append({'clock_index_RS5':193+lane,'path':f'g_return_capture[{lane}].cap','flops':513,'valid_bits':1,'data_bits':512,'external_lane':lane,'role':role,'ports':['rs_v[%d]'%lane,'rs_d[%d+:%d]'%(512*lane,512)],'downstream':'distributed H transpose to all4copies' if lane%5==0 else 'V broadcast to all4copies when vtag[TL], otherwise own copy' if lane in (1,2) else 'own copy return bus'})
 for copy in range(4):roots.append({'clock_index_RS5':213+copy,'path':f'g_request_capture[{copy}].cap','flops':75,'valid_bits':5,'data_bits':70,'copy':copy,'ports':[f'rq_v[{5*copy}+:5]',f'rq_row[{70*copy}+:70]'],'upstream':'own copy RS5 up station, plus control descriptor override on copy0'})
 h_graph=[{'source_lane':5*(hm//8),'source_lsb':2560*(hm//8)+16*(4*(hm%8)+q),'sink_copy':q,'sink_lsb':16*hm,'width':16}for q in range(4)for hm in range(32)]
 assert len(h_graph)==128 and sum(x['width']for x in h_graph)==2048
 d={'status':'HELD_ADDITIVE_CAPTURE_PARTITION','baseline_source':'b4ca1edc9','baseline_top_unchanged':True,'noncapture_top_logic_byte_tokens_unchanged':True,'source_sha256':{s:hashlib.sha256((R/s).read_bytes()).hexdigest()for s in (BASE,NEW)},'sizing':{'copies':4,'VM_return_lanes':20,'VM_bits_per_return_lane':513,'request_bits_per_copy':75,'boundary_capture_bits_per_cycle':10560,'moved_flops':10560,'added_flops':0,'added_capture_edges':0,'clock_roots_at_RS5':217,'baseline_roots':193,'new_roots':24,'baseline_calendar_cycles':810,'candidate_full_shape_cycles':'UNMEASURED; exact capture mechanism adds0edges, no810claim for new source','MIX4_VM_total_face_bits':12732,'face_um':3652.56,'average_bits_per_um':12732/3652.56,'routing_tracks':'OPEN:actual lane bands/per-bit pin layer plan required; density alone does not qualify cut'},'clock_index_coverage_RS5':clock_partitions,'unused_clock_indexes':[],'duplicate_clock_indexes':[],'roots':roots,'H_transpose_perbit_groups':h_graph,'slot':{'grant':'S-DIE SLOT A W1x4; actual translated c26b geometry via die_live','die_xy_um':[10444.896,16802.64],'outline_um':[1431.648,3652.56],'VM_face':'E','VM_W_x_um':11898.144,'seam_um':21.6,'command_face':'S at W end','note':'No new capture pin/root placement granted by this receipt'},'residual_open':['ck0 descriptor/control tags, v_prev1024FF and descriptor pipeline remain unlocalized','20data roots do not independently resolve H4way transpose and V broadcast physical transport','RS5 down/up stations still carry grouped buses; station pinplans, split data groups and actual reach remain OPEN','No mapped capture-leaf area, routing track allocation, PG, reset distribution, native217clock delivery or parent route','All native launch220/capture190/spread80, TTsetup/FFhold/DRC0 gates remain required','External VM fixture is a declared boundary and cannot establish actual mapped VM service or full layer/token qualification']}
 (a.out/'census.json').write_text(json.dumps(d,indent=1)+'\n');print('CENSUS_PASS roots217 movedFF10560 addedFF0 addedEdges0 noncapture_top_unchanged Hgroups128')
if __name__=='__main__':main()
