#!/bin/bash
# S81-ROMOPT-A: stage the committed evidence (small files) into $D/evid and tar it to stdout
set -u; D=/srv/opentallas-scratch/claude/s81-romopt-a; O=$D/out; E=$D/evid; rm -rf $E; mkdir -p $E; cd $O
mkdir -p $E/static; cp step1/topo.txt step1/*.log $E/static/; cp -r step1/selftest_release step1/selftest_legacy $E/static/ 2>/dev/null
cp selftest_default_c.log $E/static/selftest_default_compact.log; cp -r selftest_default_c $E/static/selftest_default_compact
for f in step1/cap_*.json; do gzip -c $f > $E/static/$(basename $f).gz; done
for f in step2/cap_default_*.json; do gzip -c $f > $E/static/$(basename $f).gz; done; cp step2/*.log $E/static/
for c in fseq_o1 fseq_o1o2 fseq_o1o2c; do for d in $c/*/*/; do [ -f $d/summary.json ] || continue; t=$E/$d; mkdir -p $t
  cp $d/summary.json $d/check_*.json $d/check_*.log $d/sequence_gen.log $d/frame.json $t/ 2>/dev/null; for r in $d/run_*.log; do gzip -c $r > $t/$(basename $r).gz; done; done; done
cp fseq_o1*_u_f_*.log $E/ 2>/dev/null; mkdir -p $E/fseq_logs; mv $E/fseq_o1*_u_f_*.log $E/fseq_logs/ 2>/dev/null
for b in bench_o1 bench_o1o2 bench_o1o2c; do mkdir -p $E/$b; cp $b.log $E/$b/run.log; cp $b/summary.json $b/compiler_sources.json $b/binary.sha256 $b/verilator.version $b/rtl_sources.sha256 $b/rtl_sources_checked.log $E/$b/
  for v in $b/*/; do n=$(basename $v); mkdir -p $E/$b/$n; cp $v/check.log $E/$b/$n/ 2>/dev/null; gzip -c $v/run.log > $E/$b/$n/run.log.gz 2>/dev/null; done; done
for i in images_o1 images_o1o2 images_o1o2c; do mkdir -p $E/$i; cp $i/tie_*.json $i/tie_*.log $i/*.log $E/$i/ 2>/dev/null
  for m in $i/*/*/manifest.json; do mkdir -p $E/$(dirname $m); cp $m $E/$m; done; done
for f in fcal_*_u_s_*; do [ -d $f ] || continue; mkdir -p $E/compile/$f; cp $f.log $E/compile/$f.log; cp $f/die_field_calendar.json $E/compile/$f/
  for L in $f/L*; do mkdir -p $E/compile/$L; cp $L/field_calendar.json $L/is_d.txt $E/compile/$L/ 2>/dev/null; (cd $L && sha256sum *.hex) > $E/compile/$L/images.sha256 2>/dev/null; done; done
for B in v_h9nx_e5 v_h10_e2 v_h9MX_e1; do mkdir -p $E/rtl/$B; S=/srv/opentallas-scratch/claude/toksim-s81c-fseq/$B; cp $S/sources.sha256 $S/verilator.version $E/rtl/$B/
  sha256sum $S/obj/Vtb_toksim_fgu_seq | cut -c1-64 > $E/rtl/$B/binary.sha256; (cd $D/root && sha256sum -c $S/sources.sha256 > $E/rtl/$B/sources_checked_in_root.log 2>&1); done
du -sh $E >&2; cd $E && tar czf - .
