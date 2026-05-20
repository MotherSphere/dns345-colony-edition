#!/ffp/bin/sh
# Colony Edition boot hook.
#
# Runs every boot via fun_plug's /ffp/etc/rc → /ffp/start/colony.sh.
# Walks the Colony overlay tree and bind-mounts each file over the
# corresponding D-Link web UI file. The squashfs at /usr/local/modules/
# stays untouched on NAND - only the live mount namespace shows our files.
#
# To revert: unmount everything we mounted (handled by stop()), or reboot
# without colony.sh installed (Add-Ons UI: Delete the module).

# Where Colony assets live on Volume_1, after fun_plug extracted us.
COLONY_ROOT=/ffp/colony
OVERLAY_DIR="$COLONY_ROOT/overlay"

# Where the D-Link web UI mount lives (squashfs from /dev/loop0).
WEB_ROOT=/usr/local/modules/web

LOG_FILE=/ffp/var/log/colony.log
STATE_FILE=/ffp/var/run/colony-mounts.list

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATE_FILE")"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE"
}

start() {
    log "=== colony.sh start ==="
    : > "$STATE_FILE"

    if [ ! -d "$OVERLAY_DIR" ]; then
        log "ERROR: overlay dir missing: $OVERLAY_DIR"
        return 1
    fi
    if [ ! -d "$WEB_ROOT" ]; then
        log "ERROR: D-Link web root missing: $WEB_ROOT (firmware mounted yet?)"
        return 1
    fi

    # Walk overlay tree, bind-mount each file over its target.
    find "$OVERLAY_DIR" -type f | while read -r src; do
        # Compute target path: strip overlay prefix, prepend web root.
        rel="${src#$OVERLAY_DIR/}"
        dst="$WEB_ROOT/$rel"

        if [ ! -e "$dst" ]; then
            log "skip: target does not exist in D-Link UI: $dst"
            continue
        fi

        # Skip if already bound (idempotent boot).
        if mount | grep -q " on $dst type"; then
            log "skip: already bound: $dst"
            continue
        fi

        if mount --bind "$src" "$dst" 2>>"$LOG_FILE"; then
            log "bound: $src -> $dst"
            echo "$dst" >> "$STATE_FILE"
        else
            log "FAIL: mount --bind $src $dst"
        fi
    done

    log "=== colony.sh start done: $(wc -l < "$STATE_FILE") binds ==="
}

stop() {
    log "=== colony.sh stop ==="
    if [ ! -s "$STATE_FILE" ]; then
        log "no state file, nothing to unmount"
        return 0
    fi
    # Unmount in reverse order to handle dependencies cleanly.
    tac "$STATE_FILE" 2>/dev/null | while read -r dst; do
        if mount | grep -q " on $dst type"; then
            if umount "$dst" 2>>"$LOG_FILE"; then
                log "unbound: $dst"
            else
                log "FAIL: umount $dst"
            fi
        fi
    done
    : > "$STATE_FILE"
    log "=== colony.sh stop done ==="
}

case "${1:-start}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; start ;;
    status)
        if [ -s "$STATE_FILE" ]; then
            printf 'Colony Edition active: %s bind mounts\n' "$(wc -l < "$STATE_FILE")"
            cat "$STATE_FILE"
        else
            echo "Colony Edition: not active"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}" >&2
        exit 1
        ;;
esac
