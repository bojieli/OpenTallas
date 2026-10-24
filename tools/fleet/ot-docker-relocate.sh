#!/bin/bash
# ot-docker-relocate.sh [--wait SEC] (FLEET-DISK 2026-10-24, owner: never use root disks for work)
# Moves /var/lib/containerd (images: docker uses the containerd snapshotter) and /var/lib/docker onto the scratch disk
# (/srv/opentallas-scratch2/system/) and bind-mounts them back (fstab, x-systemd.requires-mounts-for), so no docker or
# containerd config changes.  Runs ONLY when no container is running: with --wait it re-checks every SEC seconds (max
# 72 h) and needs 3 consecutive idle checks 60 s apart.  Stops docker+containerd for the copy (~1 min for 6.5 GB),
# verifies the ORFS image digests afterwards and rolls back to the old directories on any failure.  Never stops a
# running container.
set -u
D=/srv/opentallas-scratch2/system
log() { echo "$(date '+%F %T') $*"; }
[ "$(stat -c %d /srv/opentallas-scratch2)" != "$(stat -c %d /)" ] || { log "no separate scratch disk"; exit 0; }
findmnt -n /var/lib/containerd >/dev/null && { log "already relocated"; exit 0; }
idle() { [ -z "$(sudo docker ps -q)" ] && ! pgrep -x 'docker' >/dev/null; }
end=$(( $(date +%s) + 72*3600 ))
while :; do
    n=0; while idle && [ $n -lt 3 ]; do n=$((n+1)); [ $n -lt 3 ] && sleep 60; done
    [ $n = 3 ] && break
    [ "${1:-}" = --wait ] || { log "NOT RUN: $(sudo docker ps -q | wc -l) container(s) running; scheduled retry needs --wait"; exit 2; }
    [ $(date +%s) -gt $end ] && { log "GAVE UP after 72 h (containers never idle)"; exit 2; }
    sleep "${2:-300}"
done
before=$(sudo docker images --digests --format '{{.Repository}}:{{.Tag}} {{.ID}}' | sort)
log "idle; stopping docker/containerd; images: $(echo $before)"
sudo systemctl stop docker.socket docker containerd || exit 1
ok=1
sudo mkdir -p $D/containerd $D/docker
for v in containerd docker; do
    sudo rsync -aHAX --delete /var/lib/$v/ $D/$v/ || ok=0
done
if [ $ok = 1 ]; then
    for v in containerd docker; do
        sudo mv /var/lib/$v /var/lib/$v.ot-root-old && sudo mkdir /var/lib/$v || ok=0
        grep -q " /var/lib/$v none bind" /etc/fstab || echo "$D/$v /var/lib/$v none bind,nofail,x-systemd.requires-mounts-for=/srv/opentallas-scratch2 0 0" | sudo tee -a /etc/fstab >/dev/null
        sudo mount --bind $D/$v /var/lib/$v || ok=0
    done
fi
sudo systemctl daemon-reload
sudo systemctl start containerd docker.socket docker
after=$(sudo docker images --digests --format '{{.Repository}}:{{.Tag}} {{.ID}}' | sort)
if [ $ok = 1 ] && [ "$before" = "$after" ] && sudo docker run --rm openroad/orfs:latest true; then
    sudo rm -rf /var/lib/containerd.ot-root-old /var/lib/docker.ot-root-old
    log "RELOCATED /var/lib/containerd + /var/lib/docker -> $D (bind); images identical; root fs $(df --output=pcent / | tail -1)"
else
    log "FAILED (ok=$ok); rolling back"
    sudo systemctl stop docker.socket docker containerd
    for v in containerd docker; do
        findmnt -n /var/lib/$v >/dev/null && sudo umount /var/lib/$v
        [ -d /var/lib/$v.ot-root-old ] && sudo rmdir /var/lib/$v 2>/dev/null; [ -d /var/lib/$v.ot-root-old ] && sudo mv /var/lib/$v.ot-root-old /var/lib/$v
        sudo sed -i "\# /var/lib/$v none bind#d" /etc/fstab
    done
    sudo systemctl daemon-reload; sudo systemctl start containerd docker.socket docker
    exit 1
fi
