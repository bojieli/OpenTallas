#!/usr/bin/env python3
"""Independent bounded Engram demand intake; no owner generator invocation.

Reads committed metadata and exactly two existing retained BF16 artifacts.
No checkpoint payload, compiler, image production, RTL or physical jobs.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
import subprocess
import numpy as np
PIN='b0cfaee4c9b4ab64606fc33d0d246e2ed685f559'
BASE='results/quality/w16_engram_home_service_demand_20261001'
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def require(x,msg):
    if not x:raise ValueError(msg)

def metadata():
    raw=blob(PIN,BASE+'/demand.json');d=json.loads(raw)
    sums=blob(PIN,BASE+'/SHA256SUMS').decode().split()
    require(sums==[sha(raw),'demand.json'],'owner manifest')
    require(sha(blob(PIN,'tools/engram_home_service_demand.py'))==d['generator_sha256'],'owner generator pin')
    modelraw=blob(d['model_commit'],d['model_path']);require(sha(modelraw)==d['model_sha256'],'model pin')
    model=json.loads(modelraw)
    ecraw=blob(d['actual_contract_commit'],'results/quality/w16_dsrom_engram_contract_20261001/contract.json');require(sha(ecraw)==d['actual_contract_sha256'],'contract pin')
    specraw=blob(d['eight_scale_spec_commit'],'results/quality/w16_engram_eight_scale_binding_20261001/spec.json');require(sha(specraw)==d['eight_scale_spec_sha256'],'spec pin')
    h=d['HBM_candidate'];source=blob(h['existing_service_source_commit'],h['existing_service_path']);require(sha(source)==h['existing_service_sha256'],'HBM source pin')
    defaults={k:int(v) for k,v in re.findall(r'parameter integer (\w+)\s*=\s*(\d+)',source.decode())}
    require(defaults['AW']==h['source_default_sector_address_bits'] and defaults['DW']==h['existing_sector_bits'],'HBM source address/beat defaults')
    for name,value in h['source_model_timing_ps'].items():require(defaults[name+'_PS']==value,'HBM source timing default '+name)
    require(defaults['MEM_WORDS']==4096 and 'mem[q_addr[p][slot] % MEM_WORDS]' in source.decode(),'behavioral memory scope')
    return d,json.loads(ecraw),model,dict(HBM_default_MEM_WORDS=4096,HBM_modulo_memory_aliasing=True,owner=sha(raw),model=sha(modelraw),contract=sha(ecraw),eight_scale_spec=sha(specraw),HBM_source=sha(source))

def check_geometry(d,ec,model):
    rom=d['ROM_candidate'];h=d['HBM_candidate'];cols=rom['columns'];require(len(cols)==48,'48 column selectors')
    require({(c['layer'],c['column']) for c in cols}=={(L,j) for L in [1,14] for j in range(24)},'primebank coverage')
    rows=words=macros=padding=0
    for c in cols:
        b=ec['table_contracts'][str(c['layer'])]['column_banks'][c['column']]
        require(c['rows']==b['rows'] and c['global_row_offset']==b['global_row_offset'],'actual primebank geometry')
        n=c['rows']*8;m=(n+4095)//4096
        require(c['words']==n and c['macros']==m and c['capacity_words']==m*4096 and c['padding_words']==m*4096-n,'perbank word/macro arithmetic')
        require(c['macro_rows']==4096 and c['word_container_bits']==274 and c['macro_capacity_bits']==m*4096*274,'macro bit geometry')
        require(c['request_residue_bits']==24 and c['word_address_bits']==27 and c['rows']<2**24 and n<2**27,'residue/word address')
        rows+=c['rows'];words+=n;macros+=m;padding+=m*4096-n
    require(words==6144182800==rom['word_containers'] and macros==1500067==rom['physical4096x274_macros'],'whole ROM counts')
    require(rows*264==202758032400==rom['stored_useful_bytes'] and rows==rom['table_rows'],'table useful bytes')
    require(padding==rom['padding_words'] and macros*4096*274==rom['macro_capacity_bits'] and macros*4096*274//8==rom['macro_capacity_bytes'],'ROM capacity/padding')
    require(all(r*8//4096==(r*8+7)//4096 for r in range(512)),'row never crosses4096word macro')
    # Compact row start residues cycle through 0,8,16,24: all touch9 sectors.
    compact=[(offset+264+31)//32 for offset in [0,8,16,24]]
    require(compact==[9]*4,'compact sector intersections')
    require(h['sectors_per_token']==48*9==432 and h['transferred32byte_sector_bytes_per_token']==432*32==13824,'HBM transfer demand')
    require(h['transfer_overhead_bytes_per_token']==13824-48*264==1152,'sector overhead')
    sectors=(rows*264+31)//32;bits=(sectors-1).bit_length()
    require(bits==33==h['compact_whole_table_flat_sector_address_bits'] and h['source_default_sector_address_bits']==24 and not h['whole_table_default_aperture_sufficient'],'HBM aperture')
    require(h['formats']['rowaligned9sectors']['backing_bytes']==rows*288 and h['formats']['compact_interleaved8beats']['backing_bytes']==rows*264 and h['formats']['separate_code_scale_tables']['backing_bytes']==rows*264,'format backing arithmetic')
    for f in h['formats'].values():require(f['sectors32_per_row']==9,'format nine sectors')
    t=h['source_model_timing_ps']
    require(h['one_PC_burst_serialization_floor_ns']==432*t['BURST']/1000 and h['per_layer_single_PC_burst_floor_ns']==216*t['BURST']/1000,'source burst floors')
    require(abs(h['one_PC_same_bank_tCCDL_issue_span_ns']-431*t['TCCDL']/1000)<1e-9,'source tCCDL span')
    c=d['generated_constants'];m=model['constants'];home=m['selected_minimal_home']
    require(c['required_new_CROM64_words']==2*20480==m['mandatory_generated_Engram_product_words'],'two layer generated coefficients')
    require(c['resulting_CROM64_words']==m['actual_writer_words_per_rank']+40960==549760,'generated logical words')
    require(c['prior_capacity_excess_words']==549760-m['logical_capacity_words']==25472,'prior capacity overflow')
    require(home['physical_4096x274_banks']==c['model_selected_packed_banks_per_rank']==45 and home['logical_64bit_word_capacity']==45*4096*3==c['logical_words_capacity']==552960,'packed scalar capacity')
    require(c['spare_logical_words']==552960-549760==3200 and c['logical20bit_address'] and c['scalar_ports']==1 and c['unrelated_reads_serialized'],'scalar aperture/service')
    require(not c['L1']['source_pair_complete'] and c['L1']['raw_source_paths'] is None and c['L1']['product_SHA'] is None and not c['complete_generated_source_pair'],'L1 must remain unbound')
    require(not rom['qualification'] and not h['capacity_credit'] and not d['full_home_admission'],'no home admission')
    return dict(table_rows=rows,ROM_words=words,ROM_macros=macros,ROM_capacity_bytes=rom['macro_capacity_bytes'],ROM_padding_words=padding,column_selectors=48,max_macros_per_selector=max(c['macros'] for c in cols),HBM_sectors=432,HBM_sector_bytes=13824,useful_bytes_per_token=12672,HBM_overhead_bytes=1152,flat_sector_bits=bits,default_sector_bits=24,default_aperture_bytes=2**24*32,minimum_default_aperture_regions=(sectors+2**24-1)//2**24,region_count_is_not_physical_stack_count=True)

def retained_L14(d):
    c=d['generated_constants'];o=c['L14_oracle'];pair=[];reads=[]
    for part in ['q_weight','k_weight']:
        e=c['retained_sources']['layers.14.engram.'+part];manifestraw=blob(e['existing_manifest_commit'],e['existing_manifest_path'])
        require(sha(manifestraw)==e['existing_manifest_sha256'],'retained image manifest pin');manifest=json.loads(manifestraw)
        path=Path(e['path']);require(path.name=='w.engram.'+part+'.bin' and path.parent==Path(manifest['scratch_path_at_generation']),'retained artifact location')
        require(e['dtype']=='BF16' and e['logical_shape']==[4,5120] and e['bytes']==40960,'retained artifact geometry')
        before=path.stat();raw=path.read_bytes();after=path.stat()
        require((before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns),'retained artifact changed during read')
        require(len(raw)==40960 and sha(raw)==e['sha256']==manifest['files']['w.engram.'+part]['sha256'],'retained artifact SHA')
        pair.append((np.frombuffer(raw,dtype='<u2').astype('<u4')<<16).view('<f4'))
        reads.append(dict(path=str(path),bytes=40960,sha256=sha(raw)))
    graw=blob(o['golden_mul_source_commit'],'tools/hdc_golden.py');require(sha(graw)==o['golden_mul_source_sha256'],'golden multiplication source')
    nodes=[n for n in ast.parse(graw).body if isinstance(n,ast.FunctionDef) and n.name in ['z','mul']];require(len(nodes)==2,'unchanged mul extraction')
    ns=dict(np=np,F=np.float32);exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned-G-mul-only','exec'),ns)
    product=ns['mul'](*pair).astype('<f4');bits=product.view('<u4')
    crom=np.zeros((20480,2),dtype='<u4');crom[:,0]=bits # hash-only encoding; no file/image writer
    result=dict(FP32_product_coefficients=len(product),finite_coefficients=int(np.isfinite(product).sum()),nonfinite_coefficients=int((~np.isfinite(product)).sum()),zero_coefficients=int((product==0).sum()),negative_zero_bits=int((bits==0x80000000).sum()),FP32_product_bits_sha256=sha(bits.tobytes()),CROM64bit_product_slice_sha256=sha(crom.tobytes()))
    for key,v in result.items():require(v==o[key],'retained L14 oracle '+key)
    require(result['finite_coefficients']==20480 and not o['physical_or_software_image_produced'],'L14 finite/hash-only scope')
    return result,reads

def review():
    d,ec,model,pins=metadata();geometry=check_geometry(d,ec,model);l14,reads=retained_L14(d)
    local={}
    for p in ['tools/qc_engram_home_intake.py','tests/test_qc_engram_home_intake.py']:
        b=blob('HEAD',p);require((ROOT/p).read_bytes()==b,'review source pin');local[p]=sha(b)
    return dict(schema='opentallas.qc.engram-home-independent-intake.v1',verdict='PASS_BOUNDED_DEMAND_AND_RETAINED_L14_REVIEW',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),owner_commit=PIN,input_hashes=pins,model_commit=d['model_commit'],historical_HBM_source_commit=d['HBM_candidate']['existing_service_source_commit'],requested_f270_pin='not resolved among local Git objects; authoritative owner JSON pins64c6model/821709HBM',review_source_pins=local,geometry=geometry,L14=l14,L1='NULL/source pair incomplete; no coefficient/image credit',retained_artifacts_read=reads,checkpoint_payload_bytes_read=0,compiler_runs=0,new_images=0,RTL_jobs=[],PnR_jobs=[],physical_owner=None,admission=False,
        missing_costs=[dict(owner='Ram',cost='ROM macro area/die count and SSclk->q for1500067macros;48registeredselectors up to31252each plus requestfanout/returnroute',priced=False),dict(owner='Ram',cost='HBM explicit33bit flat-equivalent sharding overAW24 regions;PC/bank placement and capacity;command/return issue ports;ACT/PRE/RCD/CL/cache-state random row service;4096sector modulo-alias behavioral storage is not actual203GB table backing',priced=False),dict(owner='Ram/Halley',cost='9sector-to8beat matching-scale reassembly; finite response lease/tag/credits, adapter SRAM and CDC/fence/consumer acceptance',priced=False),dict(owner='Ram',cost='two264bit ingress and two512bit decoder-write paths;49152B decoded doublebuffer ports/release and route occupancy',priced=False),dict(owner='Ram/Fermat',cost='L1 q/k source completion;45bank scalarhome writer/unpack/registeredselect/oneport arbitration and dependentconsumer release',priced=False),dict(owner='Ram',cost='bind wkv producer157286400MAC/layer, raw6336B vs projected51200B/layer boundary, keynorm/h readiness and exact delayedgate to the same fulltoken calendar',priced=False)],
        limits='432BURST=442.368ns and431tCCDL=1103.36ns are source-model conditional floors/spans, not total row/random latency or token deadline; region minimum not stack count; scalar capacity not admitted writer/port/route',QC_NAM='original FAIL unchanged')

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--out',type=Path);cli.add_argument('--archive',type=Path);a=cli.parse_args();require(not(a.out and a.archive),'one mode');r=review()
    if a.archive:
        old=json.loads(a.archive.read_text());require({k:v for k,v in r.items() if k!='source_commit'}=={k:v for k,v in old.items() if k!='source_commit'},'archive replay')
    if a.out:
        require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'clean source');require(not a.out.exists(),'immutable output');a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(verdict=r['verdict'],**r['geometry'],L14_finite=r['L14']['finite_coefficients'],L1=None)))
if __name__=='__main__':main()
