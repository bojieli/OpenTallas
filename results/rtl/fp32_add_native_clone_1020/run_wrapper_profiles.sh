#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$PWD;W=$R/wrapper_profiles;mkdir -p "$W"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/prepare_fp32_fan32_models.py --out "$W/cells.v" > "$W/model_identity.log"
sha256sum rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v rtl/test/hdc/tb_fp32_add_fan32_profiles.sv "$W/cells.v" > "$W/source_identity.sha256"
SRC=(rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v "$W/cells.v" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
"$VL" --binary --timing --x-initial unique --x-assign unique -j 8 -Wno-fatal -Wno-WIDTH --top-module tb_fp32_add_fan32_profiles -Mdir "$W/obj" -o sim "${SRC[@]}" rtl/test/hdc/tb_fp32_add_fan32_profiles.sv > "$W/build.log" 2>&1
for seed in 1 15 51;do
 "$W/obj/sim" +verilator+rand+reset+2 +verilator+seed+$seed > "$W/seed$seed.log" 2>&1
 head -1 "$W/seed$seed.log"
done
cat > "$W/bad.sv" <<'SV'
module fp32_bad_profile #(parameter integer LAT=7,DRST=0,CUTS=-1,SAFE_DIST=1)(input clk,rst_n,valid_in,input[31:0]a,b,output[31:0]y,output[1:0]err,output valid_out);
ot_hdc_fp32_add_lat_fan32 #(.LAT(LAT),.DRST(DRST),.CUTS(CUTS),.SAFE_DIST(SAFE_DIST)) u(.*);
endmodule
SV
for profile in lat5 drst1 cuts15 safe2;do
 case $profile in lat5) OPT=(-GLAT=5);;drst1)OPT=(-GDRST=1);;cuts15)OPT=(-GCUTS=15);;safe2)OPT=(-GSAFE_DIST=2);;esac
 if "$VL" --lint-only -Wno-fatal -Wno-WIDTH --top-module fp32_bad_profile "${OPT[@]}" "${SRC[@]}" "$W/bad.sv" > "$W/refused_$profile.log" 2>&1;then
  echo "FAIL unsupported profile silently accepted $profile";exit 1
 fi
 grep -q 'OT_HDC_FAN32_UNSUPPORTED_PROFILE_REQUIRES_SAFE1_LAT7_DRST0_CUTS_MINUS1' "$W/refused_$profile.log"
 echo "FAN32_PROFILE_REFUSED $profile"
done
