#!/usr/bin/env python3
"""Source-pinned topology option only: no new leaf/placement/clock qualification."""
import argparse,hashlib,json,pathlib,re

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--decoder',type=pathlib.Path,required=True);ap.add_argument('--correction',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args()
 source=a.decoder.read_text();correction=a.correction.read_text()
 assert 'q_d <= ob[5419 - 512 * oc -: 512]' in source
 assert 'output reg  [511:0]  q_d' in source
 assert 'parameter integer NBM = 4' in source
 assert 'localparam integer NT = 30, SPC = 55;' in source
 assert re.search(r'reg\s+\[5439:0\]\s+bcw\s+\[0:NBM-1\]',source)
 declared={name.strip() for decl in re.findall(r'reg\s+\[5439:0\]\s+([a-z_, ]+);',source) for name in decl.split(',')}
 assert {'cw','orig','ob'}.issubset(declared)
 assert 'ncw[550+:10]=cw[550+:10]^ev[0+:10]' in correction
 owners=[((bit//10)%55)//11 for bit in range(5440)];rows=[]
 for bank in range(5):
  symbols=[s for s in range(544) if (s%55)//11==bank];qbits=[j for j in range(512) if any(owners[4908-oc*512+j]==bank for oc in range(10))];bits=10*len(symbols)
  rows.append({'candidate_group':bank,'chien_lanes':list(range(bank*11,(bank+1)*11)),'symbol_indices':symbols,'bits_per_codeword_copy':bits,'proposed_storage_copies':{'four_BM_bcw':4*bits,'Chien_cw_and_orig':2*bits,'emit_ob':bits},'total_proposed_storage_bits':7*bits,'actual_required_existing_clock_roots':['fec_clk_6','fec_clk_7','fec_clk_8','fec_clk_9','fec_clk_10','fec_clk_11'],'emit_q_output_positions':qbits,'distinct_emit_q_positions':len(qbits),'per_beat_emit_contribution_bits':[sum(owners[4908-oc*512+j]==bank for j in range(512)) for oc in range(10)],'mapped_cell_area':None,'outline':None,'face_pin_capacity':None})
 assert {4908-oc*512+j for oc in range(10) for j in range(512)}==set(range(300,5420))
 assert all(sum(r['per_beat_emit_contribution_bits'][oc] for r in rows)==512 for oc in range(10))
 result={'scope':'PROPOSED_NOT_IMPLEMENTED_LANE_LOCAL_CODEWORD_STORAGE_TOPOLOGY_MODEL','source_decoder_sha256':sha(a.decoder),'source_correction_sha256':sha(a.correction),'generator_sha256':sha(pathlib.Path(__file__)),'candidate_groups':rows,'total_existing_storage_bits_grouped':sum(r['total_proposed_storage_bits'] for r in rows),'distinct_group_to_emit_q_relations':sum(r['distinct_emit_q_positions'] for r in rows),'q_bits_with_one_group_source':sum(len({owners[4908-oc*512+j] for oc in range(10)})==1 for j in range(512)),'q_source_groups_histogram':{str(n):sum(len({owners[4908-oc*512+j] for oc in range(10)})==n for j in range(512)) for n in range(1,6)},'q_seq_registered_ob_bit_indices':list(range(5420,5428)),'emit_q_bit_index_rule':'q_d[j] = ob[4908 - 512*oc + j], oc0..9 j0..511','shared_Chien_coefficient_input_bits_per_group':470,'lane_math_owner_rule':'Each k owns Forney/correction at symbols 55*cc+k; existing coefficient-step logic stays shared outside groups','route_ready':False,'physical_qualified':False,'limits':['Proposed graph grouping; no hard-leaf RTL or placement implemented','Six independent preserved clock ports per group require actual clock-flow acceptance','470-bit coefficient broadcast and emit gather are explicit priced seams','Root coefficients, counters, capture/syndrome, emitter output/CDC and gearbox banks remain outside this grouping','Cell area, routing faces/tracks and endpoint integration remain open']}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'grouped_storage_bits':result['total_existing_storage_bits_grouped'],'emit_gather_group_to_q_relations':result['distinct_group_to_emit_q_relations'],'group_storage':[r['total_proposed_storage_bits'] for r in rows]}))
if __name__=='__main__':main()
