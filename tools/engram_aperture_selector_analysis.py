"""Bounded source/aperture arithmetic analysis; no checkpoint access, RTL edit, or physical admission."""
import hashlib,json,math,re,subprocess
from pathlib import Path
PIN='195fcdac57d10e9047863bf43dcacb247341d1e5'
DEMAND='b0cfaee4c9b4ab64606fc33d0d246e2ed685f559'
DP='results/quality/w16_engram_home_service_demand_20261001/demand.json'
OUT=Path('results/quality/w16_engram_aperture_selector_20261001')
def git(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def pc_of(s,npc=32):
 L=(npc-1).bit_length();return ((s>>2)^(s>>(2+L))^(s>>(2+2*L)))&(npc-1)
def main():
 assert not OUT.exists(),'immutable receipt; choose fresh output'
 dr=git(DEMAND,DP);d=json.loads(dr)
 paths=['rtl/hdc/v41/ot_hdc_engram_gather.sv','rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/kv/ot_hdc_hbm_model.sv','rtl/chip/ot_chip_v41x_hbm_karb.sv','rtl/chip/ot_chip_v41x_tile.sv']
 sources={p:git(PIN,p) for p in paths};h=sources[paths[3]].decode();assert re.search(r'parameter integer AW\s*=\s*28',h)
 gather=sources[paths[0]].decode();assert 'local_row[AW-1:0]' in gather
 rows=d['ROM_candidate']['table_rows'];cols=d['ROM_candidate']['columns'];check=[]
 for c in cols:
  n=c['rows'];off=c['global_row_offset'];macrocount=c['macros'];assert n<2**24 and off+n<=2**29
  for r in [0,1,n//2,n-1]:
   assert 0<=r<n
   for beat in [0,7]:
    globalrow=off+r;word=r*8+beat;macro,local=divmod(word,4096)
    assert globalrow-off==r and word<2**27 and macro<macrocount and macro<2**15 and local<2**12
    assert macro*4096+local==word and word//8==r and word%8==beat
   assert (r*8)//4096==((r*8+7)//4096)
  check.append(dict(layer=c['layer'],column=c['column'],table_row_range=[off,off+n],column_residue_range=[0,n],word_range=[0,n*8],macro_select_range=[0,macrocount],last_word=n*8-1,last_macro=(n*8-1)//4096,last_macro_row=(n*8-1)%4096))
 # Exact source truncation alias: selected column0 offset0, row0 and invalidrow2^24.
 valid=0;invalid=2**24;assert (valid&((1<<24)-1))==(invalid&((1<<24)-1)) and invalid>=cols[0]['rows']
 useful=d['HBM_candidate']['useful_backing_bytes'];sectors=(useful+31)//32;window=2**28;domains=(sectors+window-1)//window
 windows=[dict(id=i,global_sector_start=i*window,global_sector_end_exclusive=min((i+1)*window,sectors),local_sector_first=0,local_sector_end_exclusive=min(window,sectors-i*window),physical_stack_region=None) for i in range(domains)]
 assert domains==24 and sectors>2**32 and sectors<=2**33
 assert all(w['local_sector_end_exclusive']<=window for w in windows)
 assert sum(w['global_sector_end_exclusive']-w['global_sector_start'] for w in windows)==sectors
 for sector in [0,window-1,window,2**32,sectors-1]:
  domain,local=divmod(sector,window);assert domain*window+local==sector and domain<24
  assert pc_of(sector)==pc_of(local)
 # Find boundary-straddling compact-row request; burstmustsplit or widerbackendmapping.
 probe=window*4//33;cross=[]
 for row in range(probe-4,probe+5):
  start=row*264//32;end=(row*264+263)//32
  if start//window!=end//window:cross.append(dict(global_row=row,row_byte_offset=row*264,first_sector=start,last_sector=end,sectors=end-start+1,first_domain=start//window,last_domain=end//window,first_local_sector=start%window,first_split_length=window-start%window,second_split_length=end%window+1))
 assert cross and all(c['sectors']==9 and c['first_split_length']+c['second_split_length']==9 for c in cross)
 low_alias=dict(global_sector0=0,global_sector1=window,local28_bits_equal=0,pc32_of_both=pc_of(0),domains_required=[0,1]);assert pc_of(window)==pc_of(0)
 out=dict(schema='opentallas.engram.home-aperture-selector.source-analysis.v1',status='PASS_SOURCE_ARITHMETIC_MAPPING_REQUIREMENTS_PHYSICAL_UNBOUND',source_commit=PIN,source_sha256={p:sha(b) for p,b in sources.items()},demand_commit=DEMAND,demand_path=DP,demand_sha256=sha(dr),generator_sha256=sha(Path(__file__).read_bytes()),ROM=dict(source_global_row_bits=29,source_layer_identity='separate layer/bank index; tuple(layer,row29), notcombinedrow29 across bothtables',source_column_residue_bits=24,required_column_word_bits=27,required_macro_selector_bits=15,required_macro_row_bits=12,word_address='(validated_global_row-column_offset)*8+beat0..7',physical_home_selector='layer,column,macro_select15; bankrow12; macroselector cannotdiscard highwordbits',input_validation_required='globalrow in[offset,offset+prime); subtractonlyafterlayer/column match; rejectoutside before24bittruncation',existing_truncation_alias=dict(selected_column=0,valid_global_row=0,invalid_global_row=invalid,both_local24_address=0,RTL_execution=False,scope='source-level alias ifsender violateshashcolumncontract; no proofthatgoldenhash generatesbadrow'),column_boundaries=check,selector_implementation=None,registered_select_levels=None,route_fanout_and_capture_cost=None),
 HBM=dict(compact_backing_bytes=useful,whole_table_sectors32=sectors,required_flat_sector_bits=33,behavioral_model_default_AW=24,adopted_stack_arbiter_default_AW=28,sector_bytes=32,AW28_global_window_bytes=window*32,pseudochannels=32,pc_map='((sector>>2)^(sector>>7)^(sector>>12))&31',pc_address_semantics='PC ishashof sameAW28globalstackaddress; NOT independent28bitsperPC aperture',NPC32_does_not_expand_AW28_capacity=True,required_window_count=domains,required_home_window_bits=5,proposed_namespace='home/window5 + local_sector28, onlyIDs0..23valid; actualstack/regionbindingNULL',windows=windows,address_alias_if_high_home_bits_drop=low_alias,whole_burst_boundary_crossing_examples=cross,required_split_protocol='Splitboundary-crossing9sectorrow intohome-localrequests, retainoriginalrow/slot/column/beatcontext, reassembleall9sectors before8correct264bresponses; noearlyrelease',required_response_identity='home/window + outstandingrowlease identity cannot be lost even ifbackendusesTAG; bindtagreuse/beat/epochbeforecreditreturn',actual_global_to_stack_region_mapper=None,stack_count=None,stack_physical_capacity=None,selector_RTL=None),
 generated_L1_source=dict(complete=False,source_paths=None,product_hash=None,no_new_checkpoint_read=True),mandatory_admission_prerequisites=['source264bitpacking/imageproducer binds8scale semantics','explicitlayer/column/macro selector hierarchy withphysical bankhome/port mapping','HBMifchosen:global33bit tostack/window/local28 map andsplit-burst responseidentity','heldreturn/CDC buffers andconsumervisibility/creditlifetime priced','selector/port/area/power/SSFF closure plus composedtokenlatency beforedecoderRTL'],verification=dict(all48columnintervals_andrepresentativeinverseaddresses_exact=True,all24HBMwindowintervals_contiguous_nonoverlapping_exact=True,high_bits_truncation_counterexamples_present=True,firstHBMwindow_crossing_split_extents_exact=True),checkpoint_reads=0,RTL_changes=False,RTL_or_PnR_runs=False,hardware_or_full_home_admission=False)
 OUT.mkdir(parents=True);(OUT/'analysis.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');(OUT/'SHA256SUMS').write_text(sha((OUT/'analysis.json').read_bytes())+'  analysis.json\n')
 print(json.dumps(dict(HBM_windows=domains,sectors=sectors,burst_crossings=cross,ROM_columns=len(check))))
if __name__=='__main__':main()
