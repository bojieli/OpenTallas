from pathlib import Path
import gzip,json,re,subprocess,tempfile,time,argparse,hashlib

def procs(source):
 s=Path(source).read_text()
 return '\n'.join(re.search(r'^proc '+n+r' .*?^}\n',s,re.M|re.S).group(0)for n in ('cland_occupy','cland_put_column','cland_put'))

MOCK=r'''
array set cw {};array set ch {};array set cn {};array set cx {};array set cy {};array set co {};array set cs {}
proc mst {k op args} {switch $op {getWidth {return $::cw($k)} getHeight {return $::ch($k)} getName {return BUFx1} isBlock {return 0}}}
proc ins {k op args} {switch $op {getName {return $::cn($k)} getMaster {return m$k} getPlacementStatus {if {[info exists ::cs($k)]} {return $::cs($k)};return PLACED} setLocation {lassign $args ::cx($k) ::cy($k)} setOrient {set ::co($k) [lindex $args 0]} setPlacementStatus {set ::cs($k) [lindex $args 0]}}}
proc mk {k} {interp alias {} m$k {} mst $k;interp alias {} i$k {} ins $k;return i$k}
set f [open [lindex $argv 0] r]
gets $f line;lassign [split $line "\t"] ff_x0 ff_y0 ff_x1 ff_y1 ff_dbu ff_rh ff_sw cursor
set ff_orient {};set cland_occ {};set cland_done {};set cland_n 0;set cland_cursor {};set cland_col_cursor {}
set ::env(OT_CLAND_FIT_RESERVE) 1
set cland_fh [open /dev/null w]
set started [clock microseconds]
while {[gets $f line]>=0 && $line ne "ENDROWS"} {lassign [split $line "\t"] y o;dict set ff_orient $y $o}
while {[gets $f line]>=0 && $line ne "ENDOBS"} {cland_occupy {*}[split $line "\t"]}
set ready [clock microseconds]
set k 0;set failed 0
while {[gets $f line]>=0} {
 set a [split $line "\t"];lassign $a cn($k) cw($k) ch($k) ax ay bx by tag
 set sp {};if {[string match {*+x+ff} $tag]} {set sp 1.0}
 set code [catch {cland_put [mk $k] [list $ax $ay $bx $by] $tag $sp $cursor} why]
 if {$code} {puts "FAILED\t$k\t$why";set failed 1;break}
 puts "XY\t$k\t$cx($k)\t$cy($k)\t$co($k)"
 incr k
}
close $f
puts "TIMING\t[expr {([clock microseconds]-$ready)/1e6}]\t[expr {($ready-$started)/1e6}]\t$k"
'''

def run(source,data,limit=None,column=False,cursor=0):
 rows=data['rows'];cells=data['cells'][:limit]if limit else data['cells']
 lines=['\t'.join(map(str,data['core'][:5]+[data['row_height'],data['site_width'],cursor]))]
 lines+=['\t'.join(map(str,x))for x in rows]+['ENDROWS']
 lines+=['\t'.join(map(str,x))for x in data['obstacles']]+['ENDOBS']
 for name,w,h,x,y,rect,tag in cells:
  if column:tag+='+x+ff'
  lines.append('\t'.join(map(str,[name,w,h,*rect,tag])))
 with tempfile.TemporaryDirectory()as tmp:
  p=Path(tmp);(p/'input.tsv').write_text('\n'.join(lines)+'\n');(p/'replay.tcl').write_text(procs(source)+MOCK)
  t=time.perf_counter();r=subprocess.run(['tclsh',str(p/'replay.tcl'),str(p/'input.tsv')],text=True,capture_output=True,check=True);wall=time.perf_counter()-t
  out=r.stdout.splitlines();xy=[tuple(x.split('\t')[2:])for x in out if x.startswith('XY\t')];fail=[x for x in out if x.startswith('FAILED\t')];tm=next(x for x in out if x.startswith('TIMING\t')).split('\t')
  return dict(positions=xy,fail=fail,placement_s=float(tm[1]),setup_s=float(tm[2]),wall_s=wall,placed=int(tm[3]),stderr=r.stderr)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('baseline');ap.add_argument('candidate');ap.add_argument('fixture');ap.add_argument('out');ap.add_argument('--limit',type=int);a=ap.parse_args()
 with gzip.open(a.fixture,'rt')as f:d=json.load(f)
 old=run(a.baseline,d,a.limit);new=run(a.candidate,d,a.limit)
 expected=[(str(c[3]),str(c[4]),dict(d['rows'])[c[4]])for c in d['cells'][:a.limit]]if a.limit else[(str(c[3]),str(c[4]),dict(d['rows'])[c[4]])for c in d['cells']]
 report={k:{x:y for x,y in v.items()if x!='positions'}for k,v in [('baseline',old),('candidate',new)]}
 report.update(actual_cells=len(expected),initial_obstacles=len(d['obstacles']),old_new_differences=sum(x!=y for x,y in zip(old['positions'],new['positions'])),old_native_differences=sum(x!=y for x,y in zip(old['positions'],expected)),new_native_differences=sum(x!=y for x,y in zip(new['positions'],expected)),all_positions_equal=old['positions']==new['positions']==expected,position_sha256=hashlib.sha256(json.dumps(new['positions']).encode()).hexdigest(),placement_speedup=old['placement_s']/new['placement_s']if new['placement_s']else None)
 Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not report['all_positions_equal']or old['fail']or new['fail']:raise SystemExit(1)
