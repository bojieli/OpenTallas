cd /
R=/home/ubuntu/.local/lib/fleet/kw38-spill-99d7dfcd/ot-run
echo "== ot-run: name tests touching epyc"; grep -nE "startswith\(.?.?(ot-)?epyc|'epyc|\"epyc" $R | grep -vE '^\s*[0-9]+:\s*#' | cut -c1-170 | head -30
echo "== kit_wave processes/config"; ps -eo pid,etimes,cmd | grep -E '[k]it_wave' | cut -c1-200 | head -8
echo "== coord tools with host lists"; grep -lE '"epyc6"|epyc6' ~/coord/tools/* ~/coord/bin/* 2>/dev/null | head -20
