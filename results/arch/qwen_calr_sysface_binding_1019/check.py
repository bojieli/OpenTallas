#!/usr/bin/env python3
"""Finite source/codec extraction only. No simulator, compiler or implementation."""
import argparse,gzip,hashlib,importlib.util,json,pathlib,re,sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
S=P/'source'
def source(name):return next(S.glob('*__'+name))
def doc(name):return json.loads(source(name).read_text())
for r in json.loads((P/'sources.json').read_text()):
 b=(S/r['copy']).read_bytes()
 if r.get('compression')=='gzip':b=gzip.decompress(b)
 assert sha(b)==r['sha256'],r['copy']
pw=[int(s,16) for s in source('pw_metadata.hex').read_text().split()]
isa=[int(s,16) for s in source('program.hex').read_text().split()]
desc=doc('descriptor_cap1.json');meta=doc('ctlm_metadata_source.json');events=doc('sys_face_events.json')
assert len(pw)==1024 and len(isa)==25 and len(desc['descriptor'])==8
assert sha(source('program.hex').read_bytes())==desc['source']['programme_sha256']
assert sha(source('pw_metadata.hex').read_bytes())==desc['source']['metadata_pw_sha256']
assert all(pw[16*i+b]==(word>>(64*b))&((1<<64)-1) for i,word in enumerate(isa) for b in range(16))
assert all(v==0 for v in pw[400:976]) # no F16 template or changed metadata
assert desc['entries']==1009 and desc['ranges']['decode']['count']==406
assert all((x>>64)==0 for x in pw+desc['descriptor'])
# Run the exact source-owned packing function, NOT a surrogate event-file driver.
spec=importlib.util.spec_from_file_location('frozen_sys_face_image',source('sys_face_image.py'))
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
program=pw+desc['descriptor'];rows,rec=codec.build(events,program)
encoded=codec.viamap(rows);phys=[int(x,16) for x in encoded.splitlines()]
assert len(phys)==512 and all(len(x)==144 for x in encoded.splitlines())
# Independent inverse follows the actual macro's phys_row/phys_col contract.
restored=[]
for addr in range(4096):
 value=0
 for bit in range(72):value|=((phys[addr//8]>>(bit*8+addr%8))&1)<<bit
 restored.append(value)
assert restored==[rows.get(a,0) for a in range(4096)]
assert restored[:1032]==program and all(x>>64==0 for x in restored[:1032])
assert int(encoded.splitlines()[0],16)<1<<576
out=P/'new_serialization_PROPOSAL';out.mkdir(exist_ok=True)
(out/'sys_face_cfg.viamap.hex').write_text(encoded)
(out/'program.memh').write_text(''.join(f'{x:016x}\n' for x in program))
(out/'logical4096.memh').write_text(''.join(f'{x:018x}\n' for x in restored))
# Independent receipt digest mirrors source qkd_program_commit field ownership.
digest=0x51484f5354505247
for i,word in enumerate(program):
 digest=((digest<<7)|(digest>>57))&((1<<64)-1)
 digest^=word^((0 if i<1024 else 1<<10)|(i if i<1024 else i-1024))
assert f'{digest:016x}'==rec['program_digest']=='b8de77b060896115'
# Retain the original four incompatible ME source rows without retiming.
failures=[]
for pc,old,diagnostic in [(11,543,672),(12,2232,2459),(16,3883,3625),(20,4567,4447)]:
 row=next(x for x in meta['me_rows'] if x['pc']==pc)
 assert row['cycle']+meta['constants']['HEAD0']==old
 failures.append(dict(pc=pc,unchanged_source_edge=old,unqualified_diagnostic_edge=diagnostic,verdict='HOLD_ORIGINAL_MISMATCH'))
# Parse actual frozen GEN0 wires; do not treat manifest labels as wiring.
die=gzip.decompress((S/'gen0__die.v.gz').read_bytes()).decode()
assert sha(die.encode())=='7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7'
def instance(name):
 matches=[x for x in die.splitlines() if re.search(r'\s'+re.escape(name)+r'\s*\(',x)]
 assert len(matches)==1,(name,len(matches))
 return matches[0].strip()
def ports(name):return dict(re.findall(r'\.(\w+)\(([^()]*)\)',instance(name)))
sp,tt=ports('sys_face'),ports('tt_ctlm')
pw0,dh0,dh1=ports('rly_sf_tt_pw_0'),ports('rly_dvw_sys_face_seq_dh_0'),ports('rly_dvw_sys_face_seq_dh_1')
assert sp['ck']=='n_clk_d2d' and tt['ck']=='n_clk_r54'
assert sp['tt_pw']==pw0['a'] and pw0['b']==tt['pw']
assert sp['seq_dh']==dh0['a'] and dh0['b']==dh1['a'] and dh1['b']==tt['dh']
assert pw0['ck_s']==dh0['ck']==sp['ck'] and pw0['ck']==dh1['ck']==tt['ck']
lanes=doc('fwd_lanes.json')['lanes'];selected=[x for x in lanes if x['bid'] in ('sf_tt_pw','dvw_sys_face_seq_dh')]
assert len(selected)==2
wrong=next(x for x in selected if x['bid']=='sf_tt_pw')
assert wrong['src_ck']=='clk_r54' # retained causal manifest discrepancy
assert not events.get('L') and not events.get('E') and events['L_missing'] and events['E_missing']
assert rec['calendars']['L']==rec['calendars']['E']==[]
# Only extraction/control checks: these are not behavioral RTL mutants.
refusals={
 'missing_original_calr_expected_hex':'UNKNOWN original 1f5b521d bytes unavailable; no reconstruction identity',
 'full_selected_execution_profile':'REFUSED missing actual L/QSLOT and E/EMBW/FILL source calendars',
 'manifest_clock_used_as_wire':'REFUSED sf_tt_pw src_ck differs from actual GEN0 port connection',
 'equal_E1_implies_equal_native_age':'REFUSED native phase/reset epoch and actual transported receipts absent',
 'head_valid_with_calendar_payload':'REFUSED different 75-bit/187-bit transport ownership',
 'cap1_one_END_or_XT1_as_SYSFACE':'REFUSED diagnostic fixtures are not real producer binding',
 'retimed_four_ME_rows':'REFUSED original four timing failures remain unchanged',
 'public_CALR_activation':'REFUSED proposal-only source selection; no RTL changed',
}
summary=dict(schema='opentallas.qwen.calr-sysface-binding-extraction.v1',scope='SOURCE_ARTIFACT_EXTRACTION_ONLY',
 source_hash_checks=len(json.loads((P/'sources.json').read_text())),programme_words=25,pw_words=1024,dw_words=8,
 pw_isa_beats_checked=400,codec_rows_checked=4096,codec_bits_checked=4096*72,
 new_serialization={f.name:sha(f.read_bytes()) for f in out.iterdir()},authorized_digest=f'{digest:016x}',
 codec_source_sha256=sha(source('sys_face_image.py').read_bytes()),boot_records=rec['boot_records'],
 actual_profile_keys=list(events),missing_L=events['L_missing'],missing_E=events['E_missing'],
 image_status='NEW DISTINCT PROGRAMME-EXACT SERIALIZATION; INCOMPLETE EXECUTION PROFILE; NOT INSTALLED',
 original_expected_hex='UNKNOWN_1f5b521d_BYTES_MISSING',actual_SYSFACE_clock=sp['ck'],actual_CTLM_clock=tt['ck'],
 actual_SYSFACE_reset=sp['rst_n'],actual_CTLM_reset=tt['rst_n'],manifest_claimed_lanes=selected,
 native_transport_ages=None,native_clock_phase=None,first_use_epoch=None,ME_failures=failures,
 full_stage1='UNRESOLVED_FAIL_CLOSED',refusals=refusals)
(P/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
(P/'actual_connections.txt').write_text('\n'.join(instance(n) for n in ['sys_face','tt_ctlm','rly_sf_tt_pw_0','rly_dvw_sys_face_seq_dh_0','rly_dvw_sys_face_seq_dh_1'])+'\n')
print('PASS finite source hashes, exact 400 ISA beats + 8 DW, 4096-row/294912-bit independent codec inverse, unchanged four ME failures')
print('HOLD full connected Stage1: missing actual L/E producer calendars, clock manifest mismatch, native ages/reset/first-use unresolved')
print('NEW programme-only proposal digest',f'{digest:016x}','physical SHA',sha(encoded.encode()))
args=argparse.ArgumentParser();args.add_argument('--extraction-only',action='store_true');a=args.parse_args()
if not a.extraction_only:raise SystemExit(2)
