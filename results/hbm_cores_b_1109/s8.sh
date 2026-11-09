cd /
O="-n -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR"
echo "intel2 -> $(ssh $O ubuntu@93.115.25.103 'hostname; id -nG | tr " " ,' | tr '\n' ' ')"
for h in epyc2 epyc4; do echo "$h -> $(ssh -n -o ControlPath=none $h "ssh $O ubuntu@93.115.25.103 hostname" 2>&1 | tail -1)"; done
echo "== epyc2 ~/.local/bin"; ssh -n -o ControlPath=none epyc2 'ls -la ~/.local/bin | awk "{print \$5, \$NF}" | tr "\n" ";"; echo; ls ~/.local/lib; ls ~/.local/lib/fleet 2>/dev/null | head; du -sh ~/.local/lib/* 2>/dev/null | tr "\n" ";"'
echo "== rsync present"; ssh -n -o ControlPath=none epyc2 'which rsync pigz'; ssh -n -o ControlPath=none epyc4 'which rsync pigz'
