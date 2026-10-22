set -e
L=/srv/opentallas-scratch/claude/s81-rtlgap-idx-1021; G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git; cd $L; SHA=$(cat sha.txt)
for c in tt ff; do
  python3 tools/s81_dv/dv_rtl_kit.py --repo $G --ref $SHA --port-bind die/port_bind_min.json --top-v cut_idx72_$c/idx72_top.sv --top idx72_top --out kit_$c > kit_$c.log 2>&1 || { tail -5 kit_$c.log; exit 1; }
  tail -1 kit_$c.log | cut -c1-200
done
mkdir -p var tbsrc
python3 mk_tb72.py tb_dsdv_idx_rg3.sv cut_idx72_tt/slice_ports.json tb_idx72.sv
grep -n "INVx2_ASAP7_75t_R" kit_tt/src/top/idx72_top.sv | cut -c1-160
cp kit_tt/src/top/idx72_top.sv var/asis_tt.sv
sed -E 's/INVx2_ASAP7_75t_R (rinv_(irg_0[0-7]|iqf)) /BUFx8_ASAP7_75t_R \1 /' kit_tt/src/top/idx72_top.sv > var/rstfix_tt.sv
sed -E 's/INVx2_ASAP7_75t_R (rinv_(irg_0[0-7]|iqf)) /BUFx8_ASAP7_75t_R \1 /' kit_ff/src/top/idx72_top.sv > var/rstfix_ff.sv
sed -E 's/(dsdv_idx_rg3(_nq)? #\(\.SRAM_MACRO\(1\))\)/\1, .MUT(1))/' var/rstfix_tt.sv > var/m1_tt.sv
for v in rstfix_tt rstfix_ff m1_tt; do echo "$v INV $(grep -c 'INVx2_ASAP7_75t_R rinv_' var/$v.sv) BUF $(grep -c 'BUFx8_ASAP7_75t_R rinv_' var/$v.sv) MUT1 $(grep -c 'MUT(1)' var/$v.sv)"; done
: > tb_extra.f
for f in rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv; do
  if grep -q "src/$f\$" kit_tt/kit.f; then echo "in kit: $f"; else mkdir -p tbsrc/$(dirname $f); git --git-dir=$G show $SHA:$f > tbsrc/$f; echo "$L/tbsrc/$f" >> tb_extra.f; fi
done
cat tb_extra.f
