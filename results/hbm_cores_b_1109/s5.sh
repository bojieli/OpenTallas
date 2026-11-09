ssh -n -o ControlPath=none epyc6 'cd /usr/local; tar czf - bin/ot-heavy bin/ot-heavy-reconcile lib/ot-heavy/ot-heavy-exit lib/ot-heavy/bin/docker; '
