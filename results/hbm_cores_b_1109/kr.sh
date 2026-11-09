R=/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items
C=/srv/opentallas-scratch2/claude/kw35/src_c303p_lf
for x in dsdv_slice_c1x_C__t1:20 dsdv_slice_c1x_C__t4:26 dsdv_slice_c1x_C__t8:21 dsdv_slice_lepw_mus_C__t1:20 dsdv_slice_kv512_C__t1:13 dsdv_slice_c1x_C__t6:22 dsdv_slice_lepe_mu_C__t1:17; do
 i=${x%:*}; a=${x#*:}; f=$R/$i/attempt_$a/rtl/kit_rtl.f
 [ -f "$f" ] || continue
 echo "== $i@$a $(hostname) $(stat -c %y $f | cut -c1-16)"
 for b in ot_s81sl_xs4.sv ot_s81sl_rstopt_xo.sv ot_s81sl_xs_ctl.sv; do
  p=$(grep -m1 "/$b\$" $f); [ -z "$p" ] && continue
  c=$(find -L $C/rtl/dsrom_sys/s81_dv/slice -name $b | head -1)
  echo " $b kit=$(sha256sum "$p" 2>/dev/null | cut -c1-8) cur=$(sha256sum "$c" 2>/dev/null | cut -c1-8) ${p:0:90}"
 done
 du -sh --apparent-size $R/$i/attempt_$a 2>/dev/null | cut -f1
done
