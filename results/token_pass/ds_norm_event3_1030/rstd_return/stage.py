import hashlib,json,shutil,sys
from pathlib import Path
R=Path(sys.argv[1]);S=Path('/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source');M=Path('/srv/opentallas-scratch2/claude/codex-ds-current-rescale-1030')
stage=json.load(open(M/'stage.json'));files=list(stage['source_sha256'])
for n in files:
 p=S/n;assert hashlib.sha256(p.read_bytes()).hexdigest()==stage['source_sha256'][n]
 d=R/'src'/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
for n in['rtl/common/ot_dp_clk_landing.sv','rtl/common/ot_meso_fifo.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv']:
 d=R/'src'/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/n,d);files.append(n)
shutil.copyfile('/srv/opentallas-scratch2/claude/die-s81-34/ev3bind/out/rtl/bind_cells.sv',R/'src/bind_cells.sv');files.append('bind_cells.sv')
(R/'source.f').write_text('\n'.join('src/'+n for n in files)+'\n')
for n in['defines.f','entry.memh','partial.memh','actual_rstd.hex','expected_y.memh']:shutil.copyfile(M/n,R/n)
(R/'stage.json').write_text(json.dumps(dict(source_sha256={n:hashlib.sha256((R/'src'/n).read_bytes()).hexdigest()for n in files},
 selected_return='dn_s_0S_L2: actual595data+epoch,resetcarrierD6,XRresetD7,sourceboundary,actualW596cland,6actualot_dp_st,destboundary',
 packet_fields=dict(reset=0,RSTDvalid=68,RSTDdata=[36,67]),
 clock_profiles='C.clk=transitL0.clk=destL2.clk explicitlysame833ps reference; C.exportclk_t2 shift0/+166/-166ps are conditionalprofiles only,notphysicalauthority',
 physical_clock_phases_qualified=False,global_GO_qualified=False,physical_START_qualified=False),indent=1)+'\n')
