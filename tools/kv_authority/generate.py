#!/usr/bin/env python3
"""Verification-only generator for the exact archived G7 WSQK cut. No HDL elaborator."""
import argparse, hashlib, json, pathlib, re
CUT_SHA = 'eb75139931390368b0c74320092e5221851b6fe8b616f3f62d5b35251caa0c1f'
FRONTIER_SHA = 'b87fcc8d9ced3d5522750567e4ff743c13fa67d48b51a6895b67ba91d7899f2f'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, msg):
    if not ok: raise ValueError(msg)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--cut',type=pathlib.Path,required=True)
    ap.add_argument('--frontiers',type=pathlib.Path,required=True)
    ap.add_argument('--source-dir',type=pathlib.Path,required=True,help='archived g7_frozen_*.sv directory')
    ap.add_argument('--out',type=pathlib.Path,required=True); a=ap.parse_args()
    require(digest(a.cut)==CUT_SHA,'unsupported cut/source hash')
    f=json.loads(a.frontiers.read_text())
    for p in f['valid_paths'].values():
        require(all(x['type'] in ('assign','qkd_rlys_1','qkd_rlys_36','qkd_rlys_528') for x in p['path']),'unsupported primitive')
    require(digest(a.frontiers)==FRONTIER_SHA,'unsupported frontier manifest hash')
    checks=json.loads(pathlib.Path(__file__).with_name('g7_sources.json').read_text())
    actual={}
    for name,sha in checks.items():
        p=a.source_dir/('g7_frozen_'+name); require(digest(p)==sha,'source hash mismatch: '+name); actual[name]=sha
    paths=f['valid_paths']; require(len(paths)==18,'requires all 18 paths')
    names=list(paths); order=names[:2]+[n for n in names if n.startswith('n_krq_')]+[n for n in names if n.startswith('n_pvvq_')]
    expected=[9,5,69,69,67,63,56,47,34,51,6,4,6,4,6,4,6,4]
    sv=['// Verification only. Exact G7 source identities are in authority_manifest.json.',
        '`ifndef KVA_AUTH_DUT','`define KVA_AUTH_DUT dut','`endif',
        '// KVA_AUTH_ADMIT must be actual source command acceptance at its sampling edge.',
        'wire [17:0] kva_authority_known;', 'wire [31:0] kva_authority_errors [0:17];',
        'integer kva_authority_admission_errors = 0;',
        'always @(posedge `KVA_AUTH_DUT.n_clk_core_c[0]) begin',
        '  if ($isunknown(`KVA_AUTH_ADMIT)) begin',
        '    kva_authority_admission_errors = kva_authority_admission_errors + 1;',
        '    $display("AUTHORITY_FAIL unknown authoritative admission");', '  end',
        '  if (`KVA_AUTH_ADMIT === 1\'b1 && kva_authority_known !== 18\'h3ffff) begin',
        '    kva_authority_admission_errors = kva_authority_admission_errors + 1;',
        '    $display("AUTHORITY_FAIL admission before all frontiers");', '  end','end']
    manifest=[]
    def net(b):
        require(re.fullmatch(r'\w+',b[0]) is not None and isinstance(b[1],int),'unsupported bit mapping')
        return '`KVA_AUTH_DUT.'+b[0]+'['+str(b[1])+']'
    for i,n in enumerate(order):
        p=paths[n]; chain=list(reversed(p['path'])); require(p['registered_edges']==expected[i],'wrong depth')
        require(all(x['type']!='assign' for x in chain),'valid combinational transform unsupported')
        cur=p['end']; clocks=set()
        for x in chain:
            require(x['a']==cur,'unordered/disconnected hop'); cur=x['out']; clocks.add(x['clock'])
        require(cur==[n,0] and len(clocks)==1,'wrong terminal or clock')
        clk=clocks.pop(); require(clk in ('n_clk_core_c[0]','n_clk_core_WS[0]'),'unsupported clock')
        if i<2:
            producer='kvs_attn'; base='kvs_attn.u_attn'; reset=base+'.rst_n'
            source=base+('.ctl.g_txl.tx_v_l' if i==0 else '.g_prg.prg_rv')
        elif i<10:
            producer='ectl_WS_'+str(i-2); base=producer+'.u_a.u_k'; reset=base+'.rn'; source=base+'.req_valid'
        else:
            j=i-10;producer='vport_WS_'+str(j//2);base=producer; reset=base+'.rn';source=base+'.vq'+str(j%2)+'_valid'
        require(producer in f['producers'],'missing producer')
        hop_expr='{'+','.join(net(x['out']) for x in reversed(chain))+'}'
        sv += [f'kva_authority_path #(.DEPTH({expected[i]}), .ID({i})) kva_auth_{i} (',
               f' .clk(`KVA_AUTH_DUT.{clk}), .source_rst_n(`KVA_AUTH_DUT.{reset}),',
               f' .source_valid(`KVA_AUTH_DUT.{source}), .source_alias({net(p["end"])}),',
               f' .hop_q({hop_expr}), .known(kva_authority_known[{i}]), .errors(kva_authority_errors[{i}]) );']
        manifest.append(dict(index=i,observer=n,source=source,effective_reset=reset,clock=clk,depth=expected[i],hops=chain))
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'authority.svh').write_text('\n'.join(sv)+'\n')
    (a.out/'authority_manifest.json').write_text(json.dumps(dict(cut_sha256=CUT_SHA,frontiers_sha256=FRONTIER_SHA,sources=actual,paths=manifest),indent=2)+'\n')
    print('AUTHORITY_GENERATE_PASS paths=18 captures='+str(sum(expected)))
if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,OSError,TypeError) as e: raise SystemExit('AUTHORITY_GENERATE_FAIL '+str(e))
