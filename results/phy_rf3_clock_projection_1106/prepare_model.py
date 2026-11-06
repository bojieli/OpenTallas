import json,pathlib,re,hashlib,shutil,collections
R=pathlib.Path("/srv/opentallas-scratch2/claude/codex-kv-pad2-context")
B=R/"bind";O=pathlib.Path("/srv/opentallas-scratch3/claude/codex-phy-rf3-clock-model-1106")
O.mkdir(exist_ok=True)
sinks=json.loads((B/"bind_sinks.json").read_text())
rows={k:v for k,v in sinks.items() if isinstance(v,list) and len(v)>1 and re.search(r"\.(?:fh|rh)[0-3]\[[0-3]\]$",str(v[1]))}
assert len(rows)==1024
assert all(".pc__front_hbm_data[" in k or ".pc__return_hbm_data[" in k for k in rows)
cfg=json.loads((R/"asbuilt_pad2_426d.json").read_text())
assert len(cfg["core_splits"])==2
for rule in cfg["core_splits"]:
 assert {"hck","pc__front_hbm_data","pc__return_hbm_data"} <= set(rule["view_drop"])
P=pathlib.Path("/srv/opentallas-scratch2/claude/kw11/src_o/results/kv_host_regen_1/rtl_rf3")
expected={"qkd_kvs_pcc":"1ce0a9afb6b0db963d10aa9e36da151210faf2221bcc82a5854e05f32bcebea7","qkd_kvs_pcf":"a9601e0dabc3f768e56ef4caaae2aaa8e74e87e8e785b80576715a64297565d4","qkd_kvs_pcc_h_head_p":"befc3d7cd0fbb6fea6d89f0303c422dbd242bd0657e63030122968635fa17094","qkd_kvs_pcf_h_head_p":"cd863521153c322a262936567fcdad544fefd45bdd221c1a56972261bebd2dc8"}
providers={}
for n,sha in expected.items():
 p=P/n/(n+".sv");text=p.read_text()
 assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
 hd=text[text.index("module "):text.index(");")]
 assert not any(x in hd for x in ["front_hbm_data","return_hbm_data"," hck"])
 providers[n]={"path":str(p),"sha256":sha,"old_clock_ports":[]}
text=(B/"rtl/kv3_phy_part.sv").read_text()
widths={n:int(a)+1 for a,n in re.findall(r"wire\s*\[(\d+):0\]\s+(\w+)",text)}
projection={}
pat=r"ot_dp_st\s*#\(\.W\((\d+)\)\)\s+(u_bout_\w+)\s*\((.*?)\);"
for w,inst,body in re.findall(pat,text,re.S):
 d=re.search(r"\.d\((.*?)\),\s*\.ea",body,re.S).group(1)
 q=re.search(r"\.q\((\w+)\[(\d+):0\]\)",body)
 if not q or not re.search(r"w_core_[fr]h[0-3]",d): continue
 bits=[]
 for tok in d.strip().strip("{}").split(","):
  tok=tok.strip();m=re.fullmatch(r"(\w+)\[(\d+):(\d+)\]",tok)
  if m:
   n,a,z=m.groups();bits += [f"{n}[{i}]" for i in range(int(a),int(z)-1,-1)]
  else:
   m=re.fullmatch(r"(\w+)\[(\d+)\]",tok)
   if m:bits.append(tok)
   else:
    assert tok in widths,tok
    bits += [f"{tok}[{i}]" for i in range(widths[tok]-1,-1,-1)]
 assert len(bits)==int(w)
 old={len(bits)-1-i:tok for i,tok in enumerate(bits)}
 dead={i:tok for i,tok in old.items() if re.fullmatch(r"w_core_[fr]h[0-3]\[[0-3]\]",tok)}
 live=[i for i in range(int(w)+1) if i not in dead]
 projection[q[1]]={"source_transport":inst,"old_payload_bits":int(w),"epoch_old_bit":int(w),"removed_clock_bits":dead,"new_to_old_live_and_epoch":live,"new_payload_bits":len(live)-1}
assert sum(len(x["removed_clock_bits"]) for x in projection.values())==32
manifest={"schema":"opentallas.rf3.dead_clock_candidate.v1","status":"SOURCE_MODEL_ONLY; no physical activation or raw-native-clock equivalence","authority":"exact RF3 core_splits view_drop plus actual four fixed provider interfaces","mapped_clock_sinks":1024,"unexpected_consumers":0,"actual_post_split_provider_clock_port_uses":0,"providers":providers,"projection":projection,"preserves":["all live payload bits in order","epoch","reset","PHY internal clocks"],"added_cycles":0}
(O/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
(O/"source_rows.json").write_text(json.dumps(rows,indent=2)+"\n")
D=O/"rtl";D.mkdir(exist_ok=True)
for p in (P/"qkd_kvs_pcf").glob("*.sv"):shutil.copyfile(p,D/p.name)
print(json.dumps({"mapped":1024,"provider_clock_uses":0,"base_PHY_clock_transport_bits":32,"buses":list(projection)}))
