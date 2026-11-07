import json,hashlib
A='/srv/opentallas-scratch2/claude/s81-rck-3/'; b='/srv/opentallas-scratch2/claude/s81-rck-4/'
sha=lambda f:hashlib.sha256(open(f,'rb').read()).hexdigest()
p=json.load(open(A+'vE_plan.json'))
T=[l.strip() for l in open(A+'vE_types.txt') if l.strip()]
s=lambda j:f"u_rck_transport4\\.g_reg\\.r\\[{j}\\]\\[(55[0-3]|54[5-9])\\]"
ce={"chains":[["u_face_p_d\\.q","u_rck_transport4|u_syn\\.x0"],["u_enc\\.p_d","u_txl\\."],["u_face_p_v\\.q","u_rck_transport4|u_syn\\.pv\\$"],["u_rm\\.r_m","u_rm\\.r_d"]],
    "groups":[["am","u_face_am3\\.parts",[s(0),s(1),s(2),"u_rck_transport4\\.q\\[(55[0-3]|54[5-9])\\]"],"u_syn\\.am_ok\\$","u_syn\\.(lock|cand|wc|miss)"]]}
for t in T: p["partition_types"][t]["chain_even"]=ce; p["partition_types"][t]["reset_relay_full"]=True
json.dump(p,open(b+'vF_plan.json','w'),indent=1)
json.dump(ce,open(b+'chain_even_key.json','w'),indent=1)
orig='/srv/opentallas-scratch3/claude/codex-wave-bind-1106/src_28fc7/rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv'
repl=b+'src_rtl/ot_pdie_serdes.sv'
mods=["ot_pdie_serdes","ot_pdie_ucie","ot_s81_pma_bm","ot_s81_rate_match"]
ov=json.load(open(A+'vC_overrides3.json')); ov['util']=0.35
for t in T:
    d=json.load(open(A+f'vE_profile_{t}.json'))
    d['replacements'].append(dict(original=orig,original_sha256=sha(orig),replacement=repl,replacement_sha256=sha(repl),original_modules=mods,replacement_modules=mods))
    d["defines"]=d["defines"]+["OT_S81_RM_STAGED","OT_S81_SERDES_RST_COPIES"]
    d['model']['added_rx_clk_PIN_cycles']=1
    d['proof']=d['proof']+' + results/s81_rck_1107/rm_staged'
    json.dump(d,open(b+f'vF_profile_{t}.json','w'),indent=1)
    o=dict(ov); o['library_profile']=b+f'vF_profile_{t}.json'
    json.dump(o,open(b+f'vF_overrides_{t}.json','w'),indent=1)
print(T)
