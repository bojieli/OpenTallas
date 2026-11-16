import gzip,hashlib,json,re,subprocess,sys
from pathlib import Path
W,B,O=map(lambda p:Path(p).resolve(),sys.argv[1:])
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((O/'cmp_mu833/kv_p6_summary.json').read_text())
assert s['native_die_config_words']==96 and s['images']['10']==96 and s['images']['1']==471, 'native MU/target10 contract missing'
subprocess.run(['sha256sum','--check',str(O/'targets.sha256')],cwd=O/'cmp_mu833',check=True)
cal=json.loads((O/'img_bnd/program/calendar.json').read_text());image=(O/'img_bnd/d2d_cal_image.svh').read_text();txd={}
for end in ('C','K'):
 m=re.search(r"D2D_TXDP_"+end+r"\s*=\s*32'h([0-9a-fA-F]{8})",image);assert m, 'compiled image TXDP missing'
 word=int(m.group(1),16);v=[(word>>(8*i))&255 for i in range(4)];assert v==cal['txdp'][end]['ports'], 'calendar/include disagreement';txd[end]=v
BG=B/'bus_groups.json'
if not BG.exists():BG=O/'bus_groups.json'
kst=W/'physical/die_plan/qwen_kvsys/boot_v36/kst.py'
def stages(flag=None):
 return subprocess.check_output(['python3',str(kst)]+([flag]if flag else[])+[str(BG)],text=True).strip()
ks=stages();hrt=int(stages('--host-rt'));ert=int(stages('--emb-rt'))
knames=('KS_RXV','KS_RXP','KS_TXS','KS_TXK','KS_TXB','SK_TXV','SK_TXP');cnames=('CS_TXS','CS_RXV','CS_RXP','CS_X3S','SC_TX','SC_X3')
assert ks==','.join(str(cal['die_stages'][k])for k in knames), 'compiled seam differs from actual bind'
assert txd['K'][1]==hrt+4 and txd['K'][2]==ert+3, 'compiled host/embedding return capture differs from bind'
cst=','.join(str(cal['die_stages'][k])for k in cnames);packed=sum(v<<(8*i)for i,v in enumerate(txd['K']))
r=dict(schema='opentallas.kv.pair_image_txdp.v1',status='COMPILED_NATIVE_CONTRACT_PASS_FULL_PAIR_REPLAY_PENDING',D2D_TXDP_K=txd['K'],D2D_TXDP_C=txd['C'],sv_literal="32'h%08x"%packed,XDIE_SEAM_K=ks,XDIE_DIE_STAGES=cst+'/'+ks,HOST_REC_RT=hrt,EMB_RT=ert,source=dict(bind=str(B),compiled_image=str(O/'img_bnd/d2d_cal_image.svh'),image_sha256=digest(O/'img_bnd/d2d_cal_image.svh'),calendar_sha256=digest(O/'img_bnd/program/calendar.json'),native_summary=str(O/'cmp_mu833/kv_p6_summary.json')),note='Generated from actual compiled calendar/include and coherent bind. Not native pair runtime qualification. Review before replacing committed transport record; both dies must bind the same programme.')
(O/'pair_image_txdp.generated.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
