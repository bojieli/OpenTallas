import json,os,sys,importlib.util
from pathlib import Path
W=Path(__file__).resolve().parents[2];O=Path(os.environ['OUT']);sys.path[:0]=[str(W),str(W/'tools/qwen_kv_die')]
from tools.qwen_kv_die.kv_static_kvjf_join import die_cfg_image
boot=json.load(open(O/'prep_native2/boot_ages_bound_padded.json'));contract=json.load(open(O/'native_contract.json'))
assert boot['error'] is None and len(boot['words'])==19
words=die_cfg_image(contract['ectl_a'],contract['ectl_b'],contract['ectl_c'],contract['reset_words'],1,ages=boot['words'])
assert len(words)==96
A=O/'assets';A.mkdir(exist_ok=True)
(A/'native_dcfg_target10.hex').write_text(''.join(f'{w:016x}\n' for w in words))
(A/'native_boot_age_words.hex').write_text(''.join(f'{w:08x}\n' for w in boot['words']))
C=json.load(open(O/'kv_constants2.json'))['constants'];Q=json.load(open(O/'qc_constants2.json'))['constants']
pair=dict(schema='opentallas.kv.pair_image_txdp.v1',status='CURRENT_BOUND_TRANSPORT_ONLY_FULL_PAIR_PROGRAMME_PENDING',D2D_TXDP_K=C['D2D_TXDP_K']['value'],D2D_TXDP_C=Q['D2D_TXDP_C']['value'],sv_literal=C['D2D_TXDP_K']['sv_literal'],XDIE_SEAM_K=C['XDIE_SEAM_K']['value'],XDIE_DIE_STAGES=C['XDIE_DIE_STAGES']['value'],source=dict(kv=os.environ.get('KV_SRC_LABEL',str(os.environ.get('KV_BIND'))),qc=os.environ.get('QC_SRC_LABEL',str(os.environ.get('QC_BIND')))),formula='KV byte0 = KS_TXS + codec2 + SK_TXP + pinreg2; other bytes unchanged',note='Transport constants only. Both dies must bind the same subsequently qualified programme; oldv7/B48 image is not authority.')
(A/'pair_transport_txdp.json').write_text(json.dumps(pair,indent=1)+'\n')
missing=['Current QC100 TT/GI source-local qualification (selected u_gi master, input sampling/output producer offsets).','Current held HEAD_PREP descriptor/cohort source qualification and stage costs through actual QC GEN.','Current complete pair programme profile (MU/RoPE/admission/embedding/source capabilities) on these exact QC+KV bind facts.','QC100 collective source mismatch LS376 vs current regen407 must be resolved by ONEQC owner.']
manifest=dict(status='CURRENT_NATIVE_COMPONENT_ASSETS_NOT_FULL_BOOT_BUNDLE_OR_G5',source=pair['source'],native_dcfg_words=96,native_boot_age_words=19,capacity1=1,boot_ages=boot['ages'],physical_new_W_pads=json.load(open(O/'prep_native2/vport_dq_pads.json'))['pad_flops'],native_contract='source-derived NRST43/CAP1/AGES1 plus160actual ECTLcfg sink bits',pair_transport=pair,remaining_profile_facts=missing,limits='Target10 data and transport constants only; no oldprogramme/defaultprofile substitution. Full native bundle and QC+KV token replay remain NOT RUN.')
(A/'manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
# Correct the native producer hook's stale transport record, retaining an explicit programme hold.
p=W/'physical/die_plan/qwen_kvsys/bind/kvbind1025/pair_image_txdp.json'
p.write_text(json.dumps(pair,indent=1)+'\n')
print('NATIVE_COMPONENT_ASSETS',len(words),'DCFG',len(boot['words']),'AGE','Wpad_new',manifest['physical_new_W_pads'])
