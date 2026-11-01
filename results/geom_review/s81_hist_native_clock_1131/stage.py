"""Stage ONE exact retained histogram graph extraction, TT+FF, no signoff replay."""
import hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'helpers'))
import child_clock_witness as W
kit=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
base=kit/'run/results/asap7/kl_ot_s81ph_native_sel_hist_bank_hrB20/base'
manifest={'scope':'ROOT_AUTHORIZED_RETAINED_HISTOGRAM_GRAPH_ONLY','native':{n:W.sha(base/n) for n in ['6_final.odb','6_final.v','6_final.spef']},'corners':{}}
commands=['#!/bin/bash','set -uo pipefail','status=0']
for c in ['tt','ff']:
    old=kit/'signoff'/c
    dst=out/c;dst.mkdir(exist_ok=True)
    receipt=json.loads((old/'libraries.json').read_text())
    assert receipt['status']=='LOADED' and receipt['corner']==c.upper()
    assert W.sha(kit/'config.mk')==receipt['config_sha256'],'original configuration changed'
    original=(old/'session.tcl').read_text()
    prefix=original.split('# ---- related flop-pair skew with CPPR',1)[0]
    assert len(prefix)<len(original) and 'read_spef /base/6_final.spef' in prefix
    # Drop only nonmutating reports/timing queries; preserve original constraints,
    # overlays and the original set/unset sensitivity derate sequence verbatim.
    prefix='\n'.join(line for line in prefix.splitlines() if not re.match(r'^(so_timing (SDC|STD)|report_checks |so OCV5_WNS_)',line))+'\n'
    load=[]
    for row in receipt['libraries']:
        p,h=row['path'],row['sha256']
        assert re.fullmatch('[0-9a-f]{64}',h) and '{' not in p and '}' not in p
        load += [f'if {{[lindex [exec sha256sum -- {{{p}}}] 0] ne "{h}"}} {{error "retained library identity changed"}}',f'read_liberty {{{p}}}']
    prefix,n=re.subn(r'^ot_lib_load '+c.upper()+r' /out/libraries.json$',lambda m:'\n'.join(load),prefix,flags=re.M)
    assert n==1,'exact original library-loader anchor missing'
    constraints=re.findall(r'^read_sdc (/\S+)$',prefix,re.M)
    assert '/sdc/golden.sdc' in constraints
    witness=W.tcl(Path(__file__).resolve().parent/'helpers',c,[r['path'] for r in receipt['libraries']],constraints)
    (dst/'session.tcl').write_text(prefix+witness+'exit\n')
    (dst/'libraries.json').write_bytes((old/'libraries.json').read_bytes())
    manifest['corners'][c]={'original_session_sha256':W.sha(old/'session.tcl'),'witness_session_sha256':W.sha(dst/'session.tcl'),'libraries_sha256':W.sha(old/'libraries.json'),'golden_sdc_sha256':W.sha(old/'sdcdir/golden.sdc')}
    cmd=['docker run --rm --name codex-hist-clock-'+c+'-1101 --cpus 2',f'-v {base}:/base:ro',f'-v {kit}:/work:ro',f'-v {old}/sdcdir:/sdc:ro',f'-v {dst}:/out','openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/session.tcl',f'> {dst}/sta.log 2>&1',f'&& grep -q "OT_CHILD_CLOCK_WITNESS {c} COMPLETE" {dst}/sta.log || status=1']
    commands.append(' '.join(cmd))
commands.append('exit "$status"')
(out/'run.sh').write_text('\n'.join(commands)+'\n')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
