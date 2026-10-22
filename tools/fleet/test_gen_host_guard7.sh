#!/bin/bash
# Fake-dir test of gen_host_guard7.sh dropstale(): a held copy with only src*/syn is deleted, one with real data is kept.
# ssh is stubbed on PATH (runs the remote command locally); the guard's dropstale() line is evaluated as written.
set -u; G=$(dirname "$0")/gen_host_guard7.sh; T=$(mktemp -d); trap 'rm -rf $T' EXIT
mkdir -p $T/bin $T/p/chainsM.hbmc_hold/{src,src_a133ab55c,syn,syn_partial_hbmc} $T/q/chainsM.hbmc_hold/{src,syn,case_b}
printf '#!/bin/bash\nexec bash -c "${@: -1}"\n' > $T/bin/ssh; chmod +x $T/bin/ssh; export PATH=$T/bin:$PATH
eval "$(grep '^dropstale()' $G)"
N=t; HOSTS=h1
B=$T/p/chainsM; dropstale
B=$T/q/chainsM; dropstale
rc=0
[ ! -e $T/p/chainsM.hbmc_hold ] && echo "PASS partial dropped" || { echo "FAIL partial kept"; rc=1; }
[ -d $T/q/chainsM.hbmc_hold/case_b ] && echo "PASS real copy kept" || { echo "FAIL real copy removed"; rc=1; }
exit $rc
