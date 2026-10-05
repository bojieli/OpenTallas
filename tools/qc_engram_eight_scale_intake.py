#!/usr/bin/env python3
"""Bounded read-only Engram spec intake. Never invoke the checkpoint generator.

Uses committed blobs only, extracts existing decoder/golden functions unchanged,
and compares both owner and previously qualified QC recipes. No codec rewrite,
checkpoint access, RTL invocation, model edit or physical admission.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np

SPEC_PIN='9b5ca5767c4c03be4c587d77ad8c4ca8ff6f1f39'
PARENT_PIN='441cd7e372735445c4206121230b6980bd93b83f'
QC_PIN='d717b95df47d107b86341d58a55b38c1c72d50d0'
BASE='results/quality/w16_engram_eight_scale_binding_20261001'
PARENT='results/quality/parent_engram_eight_scale_binding_review_20261001/review.json'
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(commit,path):return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
def require(x,msg):
    if not x:raise ValueError(msg)
def extract(raw,names,ns):
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    require({n.name for n in nodes}==set(names),'function extraction')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'unchanged-pinned-recipe','exec'),ns)
    return ns

def inputs():
    specraw=blob(SPEC_PIN,BASE+'/spec.json');spec=json.loads(specraw);parentraw=blob(PARENT_PIN,PARENT);parent=json.loads(parentraw)
    data={n:blob(SPEC_PIN,BASE+'/'+n) for n in ['actual_rows.codes.bin','actual_rows.scales.bin','actual_rows.wire_beats.bin','actual_rows.golden_bf16.bin','spec.json']}
    sums=blob(SPEC_PIN,BASE+'/SHA256SUMS')
    listed={}
    for line in sums.decode().splitlines():
        h,name=line.split();require(name in data and name not in listed,'manifest file set');listed[name]=h
    require(set(listed)==set(data),'complete manifest')
    for n,raw in data.items():require(sha(raw)==listed[n],'manifest SHA '+n)
    for n,v in spec['artifacts'].items():require(n in data and len(data[n])==v['bytes'] and sha(data[n])==v['sha256'],'artifact size/hash '+n)
    sourcebytes={n:blob(spec['source_commit'],n) for n in spec['source_hashes']}
    for n,raw in sourcebytes.items():require(sha(raw)==spec['source_hashes'][n],'source SHA '+n)
    require(parent['source_spec_commit']==SPEC_PIN and parent['source_spec_sha256']==sha(specraw),'parent spec provenance')
    require(parent['source_pins_verified']==spec['source_hashes'],'parent source pins')
    catalogue_raw=blob(spec['header_catalogue_commit'],'results/quality/w16_w17_checkpoint_header_catalogue_20261001/catalogue.json')
    catalogue=json.loads(catalogue_raw)
    ecraw=blob('a9d1fad2835d96e4c0585a150b6a9d484b9791cc','results/quality/w16_dsrom_engram_contract_20261001/contract.json');ec=json.loads(ecraw)
    require(catalogue['checkpoint_revision']==spec['checkpoint_revision'],'checkpoint revision provenance')
    for row in spec['actual_rows']:
        L=row['layer'];bank=ec['table_contracts'][str(L)]['column_banks'][row['column']]
        require(row['global_row']==bank['global_row_offset'] and row['residue']==0,'actual primebank source row')
        for region,part,width in zip(row['source_regions'],['weight','scale'],[256,8]):
            tensor=ec['tensors'][f'layers.{L}.engram.embed.{part}']
            require(region['shard']==tensor['shard'] and region['absolute_offset']==tensor['absolute_file_offsets'][0]+row['global_row']*width and region['length']==width,'actual source extent binding')
            require(region['raw_header_sha256']==catalogue['shards'][region['shard']]['raw_header_sha256'],'actual source header binding')
    generator=blob(SPEC_PIN,'tools/engram_eight_scale_binding_spec.py')
    require(sha(generator)==spec['generator_sha256'],'generator SHA')
    qcraw=blob(QC_PIN,'tools/qc_engram_numeric_service.py');ns={};extract(qcraw,['code_word'],ns);qc=ns['code_word']
    ownerns={};extract(generator,['integer_decoder'],ownerns);owner=ownerns['integer_decoder']
    gold=dict(np=np,F=np.float32)
    extract(sourcebytes['tools/hdc_golden.py'],['bits','from_bits','to_bf16'],gold)
    extract(sourcebytes['tools/hdc_golden_v41.py'],['_e4m3_table','decode_engram_rows'],gold);gold['E4M3']=gold['_e4m3_table']()
    return spec,parent,data,qc,owner,gold,dict(spec=sha(specraw),parent=sha(parentraw),SHA256SUMS=sha(sums),QC_recipe=sha(qcraw),Avic_recipe=sha(generator),catalogue=sha(catalogue_raw),Engram_contract=sha(ecraw))

def wire_check(spec,data):
    require(len(data['actual_rows.codes.bin'])==48*256 and len(data['actual_rows.scales.bin'])==48*8 and len(data['actual_rows.wire_beats.bin'])==48*264 and len(data['actual_rows.golden_bf16.bin'])==48*256*2,'full retained fixture sizes')
    codes=np.frombuffer(data['actual_rows.codes.bin'],np.uint8).reshape(48,256)
    scales=np.frombuffer(data['actual_rows.scales.bin'],np.uint8).reshape(48,8)
    wire=np.frombuffer(data['actual_rows.wire_beats.bin'],np.uint8).reshape(48,8,33)
    require(np.array_equal(wire[:,:,:32],codes.reshape(48,8,32)),'wire code binding')
    require(np.array_equal(wire[:,:,32],scales),'wire matching beat scale binding')
    require(len(spec['actual_rows'])==48 and {(r['layer'],r['column']) for r in spec['actual_rows']}=={(L,c) for L in [1,14] for c in range(24)},'48 column coverage')
    for j,r in enumerate(spec['actual_rows']):
        require(r['residue']==0 and r['scale_bytes']==scales[j].tolist(),'row scale metadata')
        require(sha(wire[j].tobytes())==r['wire_beats_sha256'],'row wire SHA')
        for raw,region in zip([codes[j].tobytes(),scales[j].tobytes()],r['source_regions']):
            require(len(raw)==region['length'] and sha(raw)==region['raw_sha256'],'retained source region hash')
    return codes,scales,wire

def validate(spec,parent,data,qc,owner,gold):
    codes,scales,wire=wire_check(spec,data)
    expected=np.frombuffer(data['actual_rows.golden_bf16.bin'],dtype='<u2').reshape(48,256)
    corrected=np.array([[qc(int(c),int(scales[j,k//32])) for k,c in enumerate(row)] for j,row in enumerate(codes)],dtype='<u2')
    avic=np.array([[owner(int(c),int(scales[j,k//32])) for k,c in enumerate(row)] for j,row in enumerate(codes)],dtype='<u2')
    old=np.array([[qc(int(c),int(scales[j,0])) for c in row] for j,row in enumerate(codes)],dtype='<u2')
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        oracle=(gold['bits'](gold['decode_engram_rows'](codes,scales.astype(np.int32)-127,np.arange(48)))>>16).astype('<u2')
    require(np.array_equal(corrected,expected) and np.array_equal(avic,expected) and np.array_equal(oracle,expected),'retained BF16 equality')
    mismatches=int(np.count_nonzero(old!=expected));require(mismatches==4032==parent['old_beat0_scale_mismatches']==spec['software_validation']['old_beat0_scale_mismatched_actual_row_elements'],'old failure witness')
    cc=np.broadcast_to(np.arange(256,dtype=np.uint8),(256,256)).copy();ss=np.broadcast_to(np.arange(256,dtype=np.int32)[:,None]-127,(256,8)).copy()
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        full=(gold['bits'](gold['decode_engram_rows'](cc,ss,np.arange(256)))>>16).astype('<u2')
    pairs=np.array([[qc(c,s) for c in range(256)] for s in range(256)],dtype='<u2')
    ownerpairs=np.array([[owner(c,s) for c in range(256)] for s in range(256)],dtype='<u2')
    require(np.array_equal(pairs,full) and np.array_equal(ownerpairs,full),'65536 recipe pairs')
    require(parent['matching_per_beat_scale_mismatches']==0 and parent['wire_beats_checked']==384 and parent['BF16_elements']==12288,'parent counts')
    require(not spec['admission_claim'] and not spec['physical_capacity_credit'] and not spec['composed_sizing_pending']['admission'],'spec admission refused')
    require(not parent['model_admission'] and not parent['physical_fit'] and not parent['SS_FF_closed'] and parent['token_cycles'] is None,'parent qualification refused')
    return dict(rows=48,prime_column_regions=48,wire_beats=384,wire_bytes=12672,BF16_outputs=12288,corrected_mismatches=0,old_beat0_mismatches=mismatches,code_scale_pairs=65536,owner_recipe_mismatches=0,QC_recipe_mismatches=0,retained_golden_sha256=sha(expected.tobytes()),exhaustive_golden_BF16_sha256=sha(full.tobytes()))

def review():
    spec,parent,data,qc,owner,gold,pins=inputs();counts=validate(spec,parent,data,qc,owner,gold)
    local_pins={}
    for path in ['tools/qc_engram_eight_scale_intake.py','tests/test_qc_engram_eight_scale_intake.py']:
        committed=blob('HEAD',path);require((ROOT/path).read_bytes()==committed,'executed source pin '+path);local_pins[path]=sha(committed)
    return dict(schema='opentallas.qc.engram-eight-scale-retained-intake.v1',verdict='PASS_BOUNDED_SOFTWARE_SPEC_REVIEW',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),spec_commit=SPEC_PIN,parent_commit=PARENT_PIN,QC_recipe_commit=QC_PIN,input_hashes=pins,review_source_pins=local_pins,historical_source_pins=spec['source_hashes'],counts=counts,scope='committed blobs only; unchanged extracted owner/QC/golden functions, no generator invocation or new checkpoint reads',new_checkpoint_reads=0,RTL_jobs=[],physical_jobs=[],physical_owner=None,model_admission=False,adoption=False,mandatory_correctness_fix=True,optional_one_percent_gate_applicable=False,preserved_old_RTL_failure=spec['preserved_old_RTL_witness_commit'],remaining='Ram whole area/port/routes/bank home/RF+service/SSFF composition before RTL or PnR; fullprogram token/hash/slot timing not proved by firstrow fixture',QC_NAM='original FAIL unchanged')

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--out',type=Path);cli.add_argument('--archive',type=Path);a=cli.parse_args()
    require(not(a.out and a.archive),'one output mode')
    r=review()
    if a.archive:
        old=json.loads(a.archive.read_text());require({k:v for k,v in r.items() if k!='source_commit'}=={k:v for k,v in old.items() if k!='source_commit'},'committed review replay')
    if a.out:
        require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'clean source required')
        require(not a.out.exists(),'immutable output')
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(verdict=r['verdict'],**r['counts'])))
if __name__=='__main__':main()
