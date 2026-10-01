"""Exact eight-scale binding specification and small actual-row software oracle; no RTL edit/run."""
import ast,hashlib,json,os,subprocess
from pathlib import Path
import numpy as np
PIN='821709d3d88772edd88cba5e28039a1295dbc0fc'
CAT='25631b8754f4ec295d5d6415ca85e75f38564664'
EC='a9d1fad2835d96e4c0585a150b6a9d484b9791cc'
OUT=Path('results/quality/w16_engram_eight_scale_binding_20261001')
def read(c,p):return subprocess.check_output(['git','show',c+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def integer_decoder(code,scale):
 s=code>>7;e=(code>>3)&15;m=code&7;sig=(8|m) if e else m
 if e==15 and m==7:return (s<<15)|0x7fc0
 if sig==0:return s<<15
 E=(e-137+scale) if e else (-136+scale);p=sig.bit_length()-1;X=E+p
 if X>127:return (s<<15)|0x7f80
 if X>=-126:return (s<<15)|((X+127)<<7)|(((sig<<(3-p))&7)<<4)
 k=E+133
 if k>=0:sub=sig<<k
 else:
  r=-k;q=sig>>r;rem=sig&((1<<r)-1);half=1<<(r-1);sub=q+int(rem>half or (rem==half and q&1))
 return (s<<15)|sub

def main():
 assert not OUT.exists(),'use fresh output directory; preserved verdicts are immutable'
 paths=['tools/hdc_golden.py','tools/hdc_golden_v41.py','rtl/hdc/v41/ot_hdc_engram_gather.sv','rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','tools/arch_budget_v41.py','tools/uarch_model.py']
 sources={p:read(PIN,p) for p in paths};ns=dict(np=np,F=np.float32)
 for p,names in [('tools/hdc_golden.py',['bits','from_bits','to_bf16']),('tools/hdc_golden_v41.py',['_e4m3_table','decode_engram_rows'])]:
  nodes=[n for n in ast.parse(sources[p]).body if isinstance(n,ast.FunctionDef) and n.name in names];assert len(nodes)==len(names)
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned_golden_functions','exec'),ns)
 ns['E4M3']=ns['_e4m3_table']()
 codes=np.arange(256,dtype=np.uint8)[None,:].repeat(256,axis=0);exps=np.arange(256,dtype=np.int32)[:,None].repeat(8,axis=1)-127
 with np.errstate(over='ignore',invalid='ignore',under='ignore'):
  golden=ns['decode_engram_rows'](codes,exps,np.arange(256));bits=(ns['bits'](golden)>>16).astype(np.uint16)
 mismatches=[dict(code=c,scale=s,integer_bits=integer_decoder(c,s),golden_bits=int(bits[s,c])) for s in range(256) for c in range(256) if integer_decoder(c,s)!=int(bits[s,c])]
 assert not mismatches,mismatches[:10]
 base='results/quality/w16_w17_checkpoint_header_catalogue_20261001/';hcat=json.loads(read(CAT,base+'catalogue.json'))
 ec=json.loads(read(EC,'results/quality/w16_dsrom_engram_contract_20261001/contract.json'));snap=Path(hcat['snapshot']);rows=[];codes=[];scales=[];wire=[];payloadread=0
 for layer,t in ec['table_contracts'].items():
  L=int(layer);wc=ec['tensors'][f'layers.{L}.engram.embed.weight'];sc=ec['tensors'][f'layers.{L}.engram.embed.scale']
  for bank in t['column_banks']:
   rid=bank['global_row_offset'];pair=[];refs=[]
   for rec,width in [(wc,256),(sc,8)]:
    path=snap/rec['shard'];hb=hcat['shards'][rec['shard']];st=path.stat();assert st.st_size==hb['file_bytes']
    fd=os.open(path,os.O_RDONLY)
    try:
     assert sha(os.pread(fd,hb['header_bytes'],8))==hb['raw_header_sha256']
     offset=rec['absolute_file_offsets'][0]+rid*width;raw=os.pread(fd,width,offset);assert len(raw)==width
    finally:os.close(fd)
    aft=path.stat();assert (st.st_ino,st.st_size,st.st_mtime_ns)==(aft.st_ino,aft.st_size,aft.st_mtime_ns)
    pair.append(raw);payloadread+=width;refs.append(dict(shard=rec['shard'],absolute_offset=offset,length=width,raw_sha256=sha(raw),raw_header_sha256=hb['raw_header_sha256']))
   code,scale=pair;codes.append(list(code));scales.append(list(scale));beats=b''.join(code[b*32:(b+1)*32]+scale[b:b+1] for b in range(8));assert len(beats)==264;wire.append(beats)
   rows.append(dict(layer=L,column=bank['column'],global_row=rid,residue=0,row_selection='firstrow of eachprimecolumn region; fixture not golden-token hash coverage',source_regions=refs,scale_bytes=list(scale),heterogeneous_scale_blocks=len(set(scale))>1,wire_beats_sha256=sha(beats)))
 codearr=np.array(codes,dtype=np.uint8);exparr=np.array(scales,dtype=np.int32)-127
 with np.errstate(over='ignore',invalid='ignore',under='ignore'):
  actual_golden=ns['decode_engram_rows'](codearr,exparr,np.arange(48));actualbits=(ns['bits'](actual_golden)>>16).astype('<u2')
 expected=np.array([[integer_decoder(codearr[r,c].item(),scales[r][c//32]) for c in range(256)] for r in range(48)],dtype='<u2');assert np.array_equal(expected,actualbits)
 # Old beat0-scale interpretation, source-selected actualrows, exact signed bit comparison.
 old=np.array([[integer_decoder(codearr[r,c].item(),scales[r][0]) for c in range(256)] for r in range(48)],dtype='<u2');oldmismatch=int(np.count_nonzero(old!=actualbits));hetero=sum(r['heterogeneous_scale_blocks'] for r in rows)
 assert hetero>0 and oldmismatch>0
 OUT.mkdir(parents=True)
 (OUT/'actual_rows.codes.bin').write_bytes(codearr.tobytes());(OUT/'actual_rows.scales.bin').write_bytes(np.array(scales,dtype=np.uint8).tobytes());(OUT/'actual_rows.wire_beats.bin').write_bytes(b''.join(wire));(OUT/'actual_rows.golden_bf16.bin').write_bytes(actualbits.tobytes())
 result=dict(schema='opentallas.engram.eight-scale.binding-and-correction-spec.v1',status='PASS_SOFTWARE_BINDING_ORACLE_RTL_CANDIDATE_NOT_ADMITTED',source_commit=PIN,source_hashes={p:sha(b) for p,b in sources.items()},header_catalogue_commit=CAT,checkpoint_revision=hcat['checkpoint_revision'],generator_sha256=sha(Path(__file__).read_bytes()),preserved_old_RTL_witness_commit='1ba8abc0b122cbd22296c7c878e18cd14fabb9f6',preserved_old_RTL_mismatched_BF16_elements=224,
 beat_contract=dict(bits=264,beats_per_row=8,codes='bits[8*i+:8] =storedrow.code[32*beat+i],i0..31',scale='bits263:256 =storedrow.scale[beat]; ALL8sidebytes data, no padding',arithmetic='E4M3code *2^(UE8M0byte-127), castFP32 thenBF16RNE per golden; signedzero/NaN/subnormal/overflow included',request_tag='slot0/1 echoed onALL8orderedbeats perbank',ordering='perbank beats0..7 in order; interbank arbitration unrestricted; side/code/tag/address must latch fromsameacceptedbeat',write_address='{slot,column,beat}',ready='rdy only after all24*8 committedwrites/layer/slot',scale_source_rule='one matching exponent per32columns; never reusebeat0 scale forotherbeats'),
 minimal_correction_candidate=dict(spec_only=True,RTL_edit=False,selection_change='decode registeredcurrentbeat s1_side onALLbeats, not s1_b0?s1_side:s1_scl',retain=['arbiter','bankbeatcounter','s1_side+code/address/tagstage','decoder32lanes/layer','bufferwritestage','ready/release/slotprotocol'],retire=['perbank scl latch','selected gscl mux','s1_scl','s1_b0'],source_FF_delta=dict(bank_scale_latches_removed=2*24*8,selected_scale_pipeline_removed=2*8,beat0_flag_pipeline_removed=2,total_removed=402,current_beat_scale_pipeline_retained=16),new_arithmetic_lanes=0,new_ports=0,new_beat_width_bits=0,new_pipeline_stages=0),
 composed_sizing_pending=dict(owner='Ram',NL=2,NC=24,decoder_lanes=64,input_response_bits_per_layer=264,output_write_bits_per_layer=512,accepted_beats_per_layer=192,stored_response_bytes_per_layer=6336,decoded_write_bytes_per_layer=12288,response_service_cycles_per_layer_no_stalls=192,stream_clock_Hz=1200000000,serialization_ns_per_layer=160.0,decoded_buffer_slots=2,total_BF16_buffer_bytes=49152,bank_macro_home=None,route_cost=None,area_mm2=None,SS_FF_timing=None,CDC_and_broadcast_latency=None,composed_token_latency=None,admission=False,mandatory_correctness_gate=True,optional_one_percent_gate_applicable=False),
 software_validation=dict(all65536_code_scale_pairs_match_extracted_golden=True,actual_source_rows=48,actual_source_elements=12288,actual_rows_with_heterogeneous_scales=hetero,actual_source_expected_bits_exact=True,old_beat0_scale_mismatched_actual_row_elements=oldmismatch,checkpoint_payload_bytes_read=payloadread,fullweight_download=False,fullweight_sha=False,RTL_simulation=False,PnR=False),actual_rows=rows,artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in OUT.glob('*.bin')},fullprogram_binding='Godelconsumer/imageburst mapping pending; no uniform-row qualification credit',physical_capacity_credit=False,admission_claim=False)
 (OUT/'spec.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');(OUT/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(OUT.iterdir()) if p.name!='SHA256SUMS'))
 print(json.dumps(result['software_validation']))
if __name__=='__main__':main()
