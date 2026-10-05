"""Metadata-only census. Reads pinned git objects, never checkpoint payloads."""
import ast, collections, hashlib, json, math, re, struct, subprocess
from pathlib import Path
CAT="25631b8754f4ec295d5d6415ca85e75f38564664"
CONTRACT="42e2471cf20dc081ea59f8f43478435848dc7256"
BASE="results/quality/w16_w17_checkpoint_header_catalogue_20261001/"
OUT=Path("results/quality/w16_w17_nonexpert_header_census_20261001")
def sha(b): return hashlib.sha256(b).hexdigest()
def read(c,p): return subprocess.check_output(["git","show",c+":"+p])
def family(k):
    if k.startswith("mtp."): return "MTP", "auxiliary_MTP"
    if k.startswith(("vision.","aligner.","image_")): return "vision_aligner_image", "auxiliary_vision"
    if k=="embed.weight": return "embedding", "main_text"
    if k=="head.weight": return "head", "main_text"
    if "engram" in k: return "Engram", "main_text"
    if "shared_experts" in k: return "shared_expert", "main_text"
    if "compressor" in k: return "compressor", "main_text"
    if "indexer" in k: return "index", "main_text"
    if re.search(r"\.hc_(attn|ffn)_",k): return "HC", "main_text"
    if "norm" in k: return "norm", "main_text"
    if ".attn." in k: return "dense_attention", "main_text"
    if ".ffn.gate." in k: return "router", "main_text"
    raise ValueError("Unclassified tensor "+k)
def coverage(shape,views):
    if all(v["rows"] is None and v["columns"] is None for v in views): return "full_reference_copies"
    axes=["rows","columns"]
    for axis,key in enumerate(axes):
        spans=[v[key] for v in views]
        if any(x is not None for x in spans):
            if any(x is None for x in spans): return "incomplete_or_mixed"
            pos=0
            for a,b in sorted(spans):
                if a!=pos or b<a or b>shape[axis]: return "incomplete_or_overlapping"
                pos=b
            if pos!=shape[axis]: return "incomplete_or_overlapping"
    return "exact_reference_partition"
def main():
    raw=read(CAT,BASE+"catalogue.json"); cat=json.loads(raw)
    configraw=read(CAT,BASE+cat["config_path"]); indexraw=read(CAT,BASE+cat["index_path"])
    assert sha(configraw)==cat["config_sha256"] and sha(indexraw)==cat["index_sha256"]
    cfg=json.loads(configraw); index=json.loads(indexraw); keys=index["weight_map"]
    allrecords={}; bindings={}
    widths={"F32":4,"BF16":2,"F8_E4M3":1,"F8_E8M0":1,"I8":1}
    for shard,b in cat["shards"].items():
        h=read(CAT,BASE+b["raw_header_path"])
        assert len(h)==b["header_bytes"] and sha(h)==b["raw_header_sha256"]
        assert sha(struct.pack("<Q",len(h))+h)==b["framed_header_sha256"]
        bindings[shard]={k:b[k] for k in ("raw_header_path","header_bytes","raw_header_sha256","framed_header_sha256","data_base")}
        spans=[]
        for k,v in json.loads(h).items():
            if k=="__metadata__": continue
            assert k not in allrecords and keys[k]==shard
            a,z=v["data_offsets"]; n=z-a
            assert n==math.prod(v["shape"])*widths[v["dtype"]]
            spans.append((a,z))
            allrecords[k]=dict(shard=shard,dtype=v["dtype"],stored_shape=v["shape"],data_offsets=[a,z],stored_bytes=n,absolute_file_offsets=[b["data_base"]+a,b["data_base"]+z])
        pos=0
        for a,z in sorted(spans): assert a==pos; pos=z
        assert pos+b["data_base"]==b["file_bytes"]
    assert set(keys)==set(allrecords)
    routed=re.compile(r"^layers\.\d+\.ffn\.experts\.\d+\.w[123]\.(weight|scale)$")
    parts={"main_routed_weights":[],"main_routed_scales":[],"non_main_routed":[]}
    for k in sorted(keys): parts["main_routed_"+("weights" if k.endswith("weight") else "scales") if routed.match(k) else "non_main_routed"].append(k)
    sources={p:read(CONTRACT,p) for p in ("tools/rtl_v41_fullshape_layer_campaign.py","tools/rtl_v41_rom_array.py","tools/hdc_replay_v41.py","tools/hdc_golden_v41.py")}
    tree=ast.parse(sources["tools/hdc_replay_v41.py"])
    shipped=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="SHIPPED" for t in n.targets))
    s={k.arg:ast.literal_eval(k.value) for k in shipped.keywords}; s["ratio"]=[0,0]+[2]*18+[1]*20
    tc=cfg["text_config"]
    for a,b in (("dim","hidden_size"),("moe_ff","moe_intermediate_size"),("n_exp","n_routed_experts"),("vocab","vocab_size")):
        assert s[a]==tc[b]
    lc=ast.parse(sources["tools/rtl_v41_fullshape_layer_campaign.py"])
    fn=next(n for n in lc.body if isinstance(n,ast.FunctionDef) and n.name=="die_slices")
    namespace={"R_KV_SRC":lambda:[2,8,14,20],"R_IDX_SRC":lambda:[2,8,14,20,24,28,32,36]}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"pinned_pure_metadata_die_slices","exec"),namespace)
    views=collections.defaultdict(list)
    for layer in range(40):
        for rank in range(4):
            for name,k,rows,cols in namespace["die_slices"](layer,rank,s,[],layer in (1,14)):
                assert k in allrecords
                views[k].append(dict(rank=rank,image_name=name,rows=rows,columns=cols))
    records={}; pairs={}; gaps=[]; groups=collections.defaultdict(lambda:dict(count=0,stored_bytes=0))
    for k in parts["non_main_routed"]:
        r=dict(allrecords[k]); f,scope=family(k); r.update(family=f,scope=scope,layer=int(k.split(".")[1]) if k.startswith(("layers.","mtp.")) else None)
        r["operator_family"]=re.sub(r"(?<=\.)\d+(?=\.|$)", "N", k).removesuffix(".weight").removesuffix(".scale")
        r["packing"]="two_E2M1_nibbles_low_then_high" if r["dtype"]=="I8" else "one_stored_scalar_per_dtype_element"
        r["kind"]="quantization_scale" if k.endswith(".scale") else "matrix_or_table" if len(r["stored_shape"])==2 else "tensor_parameter"
        shape=list(r["stored_shape"])
        if r["dtype"]=="I8":
            assert len(shape)==2
            shape[1]*=2
        r["decoded_logical_shape"]=shape
        r["logical_shape_contract"]="Checkpoint.get; I8 low nibble then high nibble, two E2M1 values per stored byte" if r["dtype"]=="I8" else "Checkpoint.get stored dimensions preserved"
        r["physical_encoding"]=None; r["physical_ROM_words"]=None; r["physical_replica_count"]=None; r["resident_owner"]=None
        r["paired_tensor"]=None
        if k.endswith(".weight") and k[:-6]+"scale" in keys:
            sk=k[:-6]+"scale"; pairs[k]=sk; r["paired_tensor"]=sk
            ss=allrecords[sk]["stored_shape"]
            expected=[shape[0],shape[1]//32] if "engram.embed" in k or r["dtype"]=="I8" else [(shape[0]+31)//32,(shape[1]+31)//32]
            assert ss==expected and allrecords[sk]["dtype"]=="F8_E8M0", (k,ss,expected)
            r["scale_granularity"]="per_row_32_columns" if "engram.embed" in k or r["dtype"]=="I8" else "32_rows_32_columns"
        elif k.endswith(".scale"):
            wk=k[:-5]+"weight"; assert wk in keys; r["paired_tensor"]=wk
        vv=views.get(k,[]); status=coverage(shape,vv) if vv else "unbound"
        r["reference_image_views"]=vv; r["reference_image_coverage"]=status
        r["qualified_reference_TP_assignment"]=vv if status in ("full_reference_copies","exact_reference_partition") else None
        r["reference_full_copy_count"]=len(vv) if status=="full_reference_copies" else None
        if status not in ("full_reference_copies","exact_reference_partition"):
            gaps.append(dict(tensor=k,status=status,logical_shape=shape,observed_views=vv))
        records[k]=r; groups[f]["count"]+=1; groups[f]["stored_bytes"]+=r["stored_bytes"]
    oldpath="results/quality/w16_w19_nonsm_residency_20261001/non_SM_source_inventory.json"
    oldraw=read("8c44707ebe238ecd3d7e8cfe29920e79c33a7cf7",oldpath); old=json.loads(oldraw)
    items=old["items"].values() if isinstance(old["items"],dict) else old["items"]
    reused=0
    for v in items:
        r=records[v["tensor"]]
        assert (r["dtype"],r["stored_shape"],r["stored_bytes"],r["data_offsets"],r["shard"])==(v["dtype"],v["shape"],v["stored_bytes"],v["data_offsets"],v["shard"])
        reused+=1
    summary={"partitions":{p:dict(count=len(ks),stored_bytes=sum(allrecords[k]["stored_bytes"] for k in ks)) for p,ks in parts.items()},"families":dict(groups),"nonexpert_weight_scale_pairs":len(pairs),"reused_prior_inventory_items":reused,"reference_contract_incomplete":[x for x in gaps if x["status"]!="unbound"],"scope_counts":dict(collections.Counter(r["scope"] for r in records.values())),"per_layer":{str(L):dict(count=sum(r["layer"]==L and r["scope"]=="main_text" for r in records.values()),stored_bytes=sum(r["stored_bytes"] for r in records.values() if r["layer"]==L and r["scope"]=="main_text")) for L in range(40)}}
    assert sum(x["stored_bytes"] for x in summary["partitions"].values())==index["metadata"]["total_size"]
    assert len(records)==3925 and reused==542
    result=dict(schema="opentallas.dsrom.non-main-routed.actual-header-census.v1",status="PASS_STORAGE_CENSUS_PHYSICAL_ASSIGNMENTS_UNBOUND",checkpoint_revision=cat["checkpoint_revision"],catalogue_commit=CAT,catalogue_path=BASE+"catalogue.json",catalogue_sha256=sha(raw),config_sha256=sha(configraw),index_sha256=sha(indexraw),contract_commit=CONTRACT,contract_sources={p:sha(b) for p,b in sources.items()},existing_inventory_reuse=dict(commit="8c44707ebe238ecd3d7e8cfe29920e79c33a7cf7",path=oldpath,sha256=sha(oldraw),items_verified=reused,hardware_contract_inherited=False),generator_sha256=sha(Path(__file__).read_bytes()),header_bindings=bindings,summary=summary,tensors=records,weight_scale_pairs=pairs,physical_capacity_credit=False,admission_claim=False,product_complete=False,notes=["Main routed expert weights and scales retained by reference to pinned catalogue; MTP experts belong to this census.","Decoded logical dimensions are software codec metadata, not ROM geometry.","Reference image copies/slices do not establish physical replicas or placement.","All index keys accounted once; auxiliary MTP and vision inclusion does not assert their decode deployment.","wo_a software LazyWeights converts decoded values to BF16; deployed storage remains unbound."])
    OUT.mkdir(parents=True,exist_ok=True)
    for name,obj in (("census.json",result),("summary.json",summary),("contract_gaps.json",gaps),("verification.json",dict(index_keys=len(keys),all_headers_verified=True,all_index_mappings_exact=True,all_stored_spans_valid=True,prior_542_metadata_exact=True,payload_reads=0,downloads=0))):
        (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    (OUT/"SHA256SUMS").write_text("".join(sha(p.read_bytes())+"  "+p.name+"\n" for p in sorted(OUT.glob("*.json"))))
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
