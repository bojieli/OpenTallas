#!/usr/bin/env python3
"""Actual same dynamic-rank RTL under four boot straps and XOR lane wiring.

Component proof only: known payloads exercise transport, not native producers.
"""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from calendar import fmt1_calendar,fmt1_cycle_controls

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'rtl/dsrom_sys/s81_static_collective'
FILES=[ROOT/'rtl/link/ot_link_crc32.sv',D/'s81_static_fmt1_gearbox.sv',D/'s81_static_tp4_vm_producer.sv']+[D/(n+'.sv') for n in ['s81_static_tp4_endpoint_dynamic','s81_static_fmt1_codec_dynamic','s81_static_fmt1_lane_dynamic','s81_static_fmt1_core_dynamic','s81_static_fmt1_rank_dynamic_clocked','s81_static_fmt1_rank_dynamic','tb_s81_static_fmt1_dynamic']]

def main():
 out=ROOT/'results/rtl/s81_static_dynamic_rank_1014';out.mkdir(parents=True,exist_ok=True)
 records=[]
 with tempfile.TemporaryDirectory() as td:
  td=Path(td);binary=td/'sim'
  def build(files,dest):subprocess.run(['iverilog','-g2012','-s','tb_s81_static_fmt1_dynamic','-o',str(dest),*map(str,files)],check=True,capture_output=True,text=True)
  build(FILES,binary)
  subprocess.run(['iverilog','-g2012','-s','s81_static_fmt1_vm_rank_dynamic','-o',str(td/'vm'),*map(str,FILES),str(D/'s81_static_fmt1_vm_rank_dynamic.sv')],check=True,capture_output=True,text=True)
  for layer,kind in [(0,'a'),(20,'a'),(2,'a'),(0,'router')]:
   slots=fmt1_calendar(layer,16,kind=kind);p=out/f'{kind}_{len(slots)}.mem';b=out/f'{kind}_{len(slots)}_beats.mem'
   p.write_text(''.join(f'{(s.issue<<96)|(s.commit<<64)|(sum(r<<(15*k)for k,r in enumerate(s.rows))<<4)|(int(s.last)<<3):032x}\n'for s in slots))
   b.write_text(''.join(f'{v:02x}\n'for v in fmt1_cycle_controls(slots)))
   for rot in range(4):
    args=[str(binary),f'+N={len(slots)}',f'+PLAN={p}',f'+BEATS={b}',f'+ROT={rot}']
    result=subprocess.run(['vvp',*args],capture_output=True,text=True)
    log=out/f'{kind}_{len(slots)}_rot{rot}.log';log.write_text(result.stdout+result.stderr)
    if result.returncode or 'PASS dynamic-rank'not in result.stdout:raise RuntimeError(log.read_text())
    records.append(dict(layer=layer,kind=kind,records=len(slots),rotation=rot,log=str(log.relative_to(ROOT))))
  # Actual same compiled RTL must detect attempted boot-strap reconfiguration.
  args=[str(binary),'+N=28',f'+PLAN={out/"a_28.mem"}',f'+BEATS={out/"a_28_beats.mem"}','+ROT=0','+MUT=7']
  result=subprocess.run(['vvp',*args],capture_output=True,text=True);(out/'strap_change.log').write_text(result.stdout+result.stderr)
  if result.returncode or 'PASS dynamic-rank'not in result.stdout:raise RuntimeError('strap change escaped or bench failed '+result.stdout)
  args=[str(binary),'+N=28',f'+PLAN={out/"a_28.mem"}',f'+BEATS={out/"a_28_beats.mem"}','+ROT=2','+MUT=8']
  result=subprocess.run(['vvp',*args],capture_output=True,text=True);(out/'boot_edge_issue.log').write_text(result.stdout+result.stderr)
  if result.returncode or 'PASS dynamic-rank'not in result.stdout:raise RuntimeError('bootedge issue escaped '+result.stdout)
  # Functional mutation changes lane codec peer prefix, causing real writes to fail.
  path=D/'s81_static_fmt1_rank_dynamic_clocked.sv';mut=td/'rank_mut.sv'
  original=path.read_text();changed=original.replace("wire[1:0]peer=rank_q ^ 2'(g+1);", "wire[1:0]peer=rank_q ^ 2'(g);")
  assert changed!=original;mut.write_text(changed)
  build([mut if f==path else f for f in FILES],td/'mut')
  result=subprocess.run(['vvp',str(td/'mut'),'+N=28',f'+PLAN={out/"a_28.mem"}',f'+BEATS={out/"a_28_beats.mem"}','+ROT=1'],capture_output=True,text=True)
  (out/'mutant_wrong_xor_peer.log').write_text(result.stdout+result.stderr)
  if result.returncode==0 or 'fault cycle='not in result.stdout:raise RuntimeError('wrong XOR peer mutant escaped '+result.stdout)
 receipt=dict(status='DYNAMIC_RANK_COMPONENT_PASS',production_qualified=False,
  scope='One dynamic RTL implementation, four simultaneous ranks with runtime rotating boot straps and actual XOR physical mapping; synthetic payload source only',
  clock_contract='Independent clk_core and three clk_lane leaf inputs; common stream epoch required and physically unqualified',
  rank_configuration='First reset-released edge captures rank; subsequent change is sticky fault; first source must follow boot edge',
  lane_mapping='physical lane g0..2 peer = registered_rank XOR (g+1)',
  measured_issue_to_gather_edges=11,gather_metadata='tag32 seq16 last registered with vm_we/vm_rows/vm_data',
  cases=records,source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in FILES+[D/'s81_static_fmt1_vm_rank_dynamic.sv',Path(__file__)]},
  boot_configuration_guard='Actual attempted source issue on first boot-capture edge asserts fault before sampling edge; no source operation admitted before rank capture',
  mutation='Actual lane codec peer prefix uses rank XOR g, observed gather fault; boot strap change separately detected',
  blockers=['actual native VM source image','runtime rank die strap wiring','accepted dynamic controller/core/lane physical slots and pins','TT/FF/DRC0 and native clock/reset qualification'])
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(status=receipt['status'],cases=len(records),mutant_observed=True)))
if __name__=='__main__':main()
