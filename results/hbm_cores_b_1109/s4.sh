ssh -n -o ControlPath=none epyc6 'cd ~/ot-fleet-install && tar czf - --exclude=evidence --exclude=epyc6_retire --exclude=operations . ' 
