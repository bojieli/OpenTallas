import json,collections,re,sys
d=json.load(open(sys.argv[1]))
I={i['n']:i for i in d['insts']}
tr=collections.defaultdict(collections.Counter)
for b in d['buses']:
  if b['c']=='clock_trunk':
    for x in b['e'][1:]: tr[x[0]][b['b']]+=1
def cen(n): i=I[n]; return (i['x']+i['w']/2,i['y']+i['h']/2)
VM_N=('sp_vector_memory',)
SU_N=re.compile(r'(sp_su64_sfu|seq_su|xs_tap|embed_prov|native59|cbuf_g_\d+|crom_g_\d+|selector_fork_\d+)$')
TT_N=re.compile(r'(tt_ctlm|res_train_issue|b2_word_status|command_fork_\d+|sys_face|up4_sel_station)$')
PORT=re.compile(r'(sp_port_tiles|sp_halfband|sp_halfres)_(\d)(_f1)?$')
def region(n):
  if n in VM_N: return 'CORE_VM'
  if SU_N.fullmatch(n): return 'CORE_SU'
  if TT_N.fullmatch(n): return 'CORE_TT'
  m=PORT.fullmatch(n)
  if m:
    k=int(m.group(2)); side='E' if (m.group(3) or (m.group(1)!='sp_port_tiles' and k%2==1)) else 'W'
    if m.group(1)=='sp_port_tiles': band=k
    else: band={0:0,1:0,2:1,3:1,4:2,5:2}[k]
    return f'P{side}{band}'
  if re.fullmatch(r'(tt_up4_leaf\d+|up4_sel_branch\d+|rstseq_rom)',n): return 'PW0'
  if re.fullmatch(r'(io_\w+|clk_rx|bump_pkg_\w+|bump_die_\w+)',n): return 'IO'
  if re.fullmatch(r'(d2d_rom|ucie_kv|ckb_rom|rs_bump|bump_fwd_\w+)',n): return 'KV'
  t=tr.get(n)
  if t and re.fullmatch(r'(t|s|h)_\d+(_\d+)?',n):
    x,y=cen(n); side='W' if x<16500 else 'E'
    # array regions: 4-column groups x row bands of the existing trunk footprints
    return 'A'+side+':'+t.most_common(1)[0][0]
  return 'OTHER:'+n
