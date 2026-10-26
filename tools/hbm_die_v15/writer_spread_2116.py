#!/usr/bin/env python3
"""Die-owned exact full-face writer pins, preserving the v4 source and outline."""
import copy,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
import ref_tile as RT
import spread_face_pins as SP
s=json.loads((ROOT/'physical/ref_tile/hcoll_vmwrite_static_v4/spec.json').read_text())
s.update(name='hcoll_vmwrite_static_v4_spread',io_tcl='physical/hbm_coll_writer_spread_2116/io.tcl',pin_regs=dict(enable=False,reason='RTL captures all producer/control ports in boundary registers; rst_n reaches only rst_q; outputs kq/launch_done/fault are registers. Keep recipe2 pin flop anchoring and avoid adding redundant stages to the exact compiler calendar.'))
widths=SP.port_widths(s,ROOT);W=s['outline']['w'];H=s['outline']['h'];assignments=[];pins=[];margin=4.32
pg=[];k=0
while 2.16+.3+5.4*k-.06<W:
 a=2.16+.3+5.4*k-.06;pg.extend([(a,a+.12),(a+.192,a+.312)]);k+=1
for face,names in s['pins'].items():
 bits=[(n,i,v) for n in names for i in range(widths[n][0]) for v in [widths[n][1]]]
 # Put the clock into the middle of its face rather than at its first slot.
 clocks=[b for b in bits if b[0]=='clk'];bits=[b for b in bits if b[0]!='clk'];bits[len(bits)//2:len(bits)//2]=clocks
 span=W if face in 'NS' else H;layer='M5' if face in 'NS' else 'M4'
 legal=[];i=0
 while .012+.048*i<=span-margin+1e-9:
  c=round(.012+.048*i,6);i+=1
  if c<margin:continue
  if layer=='M5' and any(c+.036>a-1e-9 and c-.036<b+1e-9 for a,b in pg):continue
  legal.append(c)
 assert len(legal)>=2*len(bits),(face,len(bits),len(legal))
 selected=[legal[int((j+.5)*len(legal)/len(bits))] for j in range(len(bits))]
 assert all(b-a>=.096-1e-9 for a,b in zip(selected,selected[1:]))
 for (n,bit,vector),c in zip(bits,selected):assignments.append(dict(port=f'{n}[{bit}]' if vector else n,base=n,face=face,layer=layer,centre_um=c))
 for n in names:
  aa=[a for a in assignments if a['base']==n];cs=[a['centre_um'] for a in aa];nb,vector=widths[n]
  pins.append(dict(name=f'{n}[{nb-1}:0]' if vector else n,face=face,layer=layer,offset=round(sum(cs)/len(cs),6),span_um=[round(min(cs)-.048,6),round(max(cs)+.048,6)],bit_centres_um=cs,bit_pitch_um=min([b-a for a,b in zip(cs,cs[1:])] or [.096])))
hd=ROOT/'physical/hbm_coll_writer_spread_2116';hd.mkdir(parents=True,exist_ok=True)
lines=['# Exact die-owned full-face pin assignment; M5 centres PG-clear, all centres on actual tracks.','source /src/physical/common_flow/assigned_pin_exact.tcl']
for a in assignments:lines.append(f'ot_assigned_pin_exact {{{a["port"]}}} {a["layer"]} {a["face"]} {a["centre_um"]:.6f}')
(hd/'io.tcl').write_text('\n'.join(lines)+'\n')
s['job'].update(owner='Codex:HBM2116',branch='codex/hbm-takeover-2116',tag='spread1',purpose='Native capture repair of CLOSED writer v4 (TT143.57/FF6.87/DRC0; capture192.8ps>190 on tkw_d[482]). Owner-inspected S-face central569pinstrip and unused W/Eends: spread each face over full legal tracks, preserving buses/faces/bit order and N-centre clock. Same actual v4 RTL/outline/latency. Structural correction to crowding; route contingent on inspected placement/GRT and native audit.')
s['job']['structural_change']=s['job']['purpose'];s['job']['extra_paths']+=['physical/hbm_coll_writer_spread_2116','physical/common_flow/assigned_pin_exact.tcl','results/arch/hbm_die_v15/takeover_2116']
reason=dict(kind='pin_register',source='results/arch/hbm_die_v15/takeover_2116/README.md',cell=s['top'],launch_ps=195.6,capture_ps=192.8,fix='Spread S capture pins over whole PG-clear width and W/E registered buses over whole height; same outline, actual registered source and cycles.')
s['job']['reroute_reason']=reason;s['reroute_reason']=reason
out=ROOT/'physical/ref_tile/hcoll_vmwrite_static_v4_spread';out.mkdir(parents=True,exist_ok=True);spec=out/'spec.json';spec.write_text(json.dumps(s,indent=1)+'\n');RT.gen(str(spec))
# Exact geometry is accepted as a child-pin grant only; parent timing remains OPEN.
p=ROOT/'results/arch/hier_contract_1015/hbm_v15.json';g=json.loads(p.read_text());sha=hashlib.sha256((ROOT/s['sources'][0]).read_bytes()).hexdigest()
for slot in g['slots']:
 if not re.fullmatch(r'coll_(SW|SE|NW|NE)_writer0',slot['name']):continue
 slot.update(pins=copy.deepcopy(pins),source=s['sources'][0],source_sha256=sha,logical_cycles='v4 captureC; lowlaunchC+2/highlaunchC+3; faultC+1. Native spread adds0edges.',qualification_scope='Die-owned full-face pin-spread candidate at same outline. Prior CLOSED route is diagnostic; new physical/native capture and parent incident-path qualification OPEN.',source_change='v4 registered one-hot selects and extra operand relay; reset input pin flop. This grant changes pins only.',source_proof='64acceb45 v4 exact/mutant bench and sw_slice_parent native composition',measured_std_um2=None,measured_ff=None)
 slot.pop('CTS_receipt',None)
g['writer_spread_pins_2116']=dict(pins_file=str((hd/'io.tcl').relative_to(ROOT)),sha256=hashlib.sha256((hd/'io.tcl').read_bytes()).hexdigest(),bits=len(assignments),new_data_cycles=0,prior_capture_ps=192.8,capture_budget_ps=190.0,production_binding_adopted=False,clock_rule='Each child clock receives phi minus its own measured insertion; new source-bound insertion pending.',reason=s['job']['purpose'])
p.write_text(json.dumps(g,indent=1)+'\n');print('Generated',len(assignments),'source-exact track/PG-clear full-face pins at unchanged103.68x388.8outline')
