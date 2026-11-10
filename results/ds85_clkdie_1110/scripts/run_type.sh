#!/bin/bash
# DS85 CLKDIE-S81: run type_clk.tcl on one type dir D (6_final.v, 6_final.spef, top.txt, optional extra_libs/*.lib) for TT and FF.
set -euo pipefail
D=$(readlink -f "$1"); S=$(readlink -f "$(dirname "$0")")
if [ ! -s "$D/top.txt" ]; then   # top = the one module no other module instantiates (s81p_<type> or <clone type>)
  python3 -I -c 'import re,sys; v=open(sys.argv[1]).read(); m=re.findall(r"^module\s+(\w+)",v,re.M); t=[x for x in m if not re.search(r"^\s*"+x+r"\s+\S+\s*\(",v,re.M)]; print(t[-1] if t else "")' "$D/6_final.v" > "$D/top.txt"
fi
TOP=$(cat "$D/top.txt")
[ -n "$TOP" ] || { echo "no top" > "$D/sta_TT.log"; exit 1; }
PORTS=$(grep -oE '^\s*input (\[[0-9:]+\] )?(clk|clk_t[0-9]+|fclk_in_[A-Za-z0-9_]+)\s*;' "$D/6_final.v" | sed -E 's/.*input (\[[0-9:]+\] )?//; s/\s*;//' | sort -u | tr '\n' ' ')
echo "$PORTS" > "$D/ports.txt"
for C in TT FF; do
  L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
  LIBS="$L/asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz $L/asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz $L/asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz $L/asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib $L/asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz"
  for x in "$D"/extra_libs/${C}/*; do [ -e "$x" ] && LIBS="$LIBS /d/extra_libs/${C}/$(basename "$x")"; done
  docker run --rm --name "ds85-clk-type-$(basename "$D")-$C" --memory=24g --cpus=2 -v "$D:/d" -v "$S:/s:ro" \
    -e CORNER=$C -e TOP="$TOP" -e V=/d/6_final.v -e SPEF=/d/6_final.spef -e LIBS="$LIBS" -e OUT=/d/arr_$C.txt \
    -e PORTS="$PORTS" -e TAPSLEW=40 openroad/orfs:asap7lock \
    /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -no_init -exit /s/type_clk.tcl > "$D/sta_$C.log" 2>&1 || echo "FAIL $C" >> "$D/sta_$C.log"
done
