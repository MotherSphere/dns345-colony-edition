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

    log "binds applied: $(wc -l < "$STATE_FILE")"

    # --- gitweb persistence ---
    # The D-Link firmware regenerates /etc/lighttpd/lighttpd.conf in tmpfs
    # at every boot, so our gitweb additions disappear. Re-apply them by
    # bind-mounting our extended config over the regenerated one, then
    # restart lighttpd so it re-reads.
    if [ -f "$COLONY_ROOT/lighttpd-colony.conf" ] && [ -f "$COLONY_ROOT/gitweb-colony.css" ]; then
        log "applying gitweb persistence"

        # Bind-mount our extended lighttpd.conf
        if ! mount | grep -q " on /etc/lighttpd/lighttpd.conf "; then
            if mount --bind "$COLONY_ROOT/lighttpd-colony.conf" /etc/lighttpd/lighttpd.conf 2>>"$LOG_FILE"; then
                log "bound: lighttpd.conf -> Colony version"
                echo "/etc/lighttpd/lighttpd.conf" >> "$STATE_FILE"
            fi
        fi

        # Bind-mount Colony gitweb CSS
        GW_CSS=/ffp/share/gitweb/static/gitweb.css
        if [ -f "$GW_CSS" ] && ! mount | grep -q " on $GW_CSS "; then
            if mount --bind "$COLONY_ROOT/gitweb-colony.css" "$GW_CSS" 2>>"$LOG_FILE"; then
                log "bound: gitweb.css -> Colony version"
                echo "$GW_CSS" >> "$STATE_FILE"
            fi
        fi

        # Restart lighttpd-angel so the new config gets read.
        # The angel script wraps lighttpd with -m /usr/lighty_lib for module paths.
        # Poll until the old processes fully exit (up to 10s) rather than
        # sleeping a hopeful 1s - a slow ARMv5 box under I/O load can take a
        # surprising amount of time to release :80, and restarting too soon
        # leaves the new lighttpd in EADDRINUSE.
        if pgrep lighttpd >/dev/null 2>&1; then
            killall lighttpd-angel lighttpd 2>/dev/null
            t=0
            while [ $t -lt 10 ] && pgrep lighttpd >/dev/null 2>&1; do
                sleep 1
                t=$((t + 1))
            done
            /usr/sbin/lighttpd-angel -D -m /usr/lighty_lib -f /etc/lighttpd/lighttpd.conf &
            log "lighttpd restarted (waited ${t}s for old procs to exit)"
        fi
    fi

    log "=== colony.sh start done ==="
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
