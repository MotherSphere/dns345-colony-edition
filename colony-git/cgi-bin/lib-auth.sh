#!/ffp/bin/bash
# Shared auth helpers for Colony Git CGIs.
#
# Two authentication channels coexist:
#   1. Session cookie `colony_session=<token>` for the web SPA (set by
#      login.cgi after a successful form POST, cleared by logout.cgi).
#   2. HTTP Basic auth for git CLI clients (handled per-CGI as before -
#      git-http.cgi still verifies via htpasswd directly because the git
#      client cannot manage cookies).
#
# Sessions are flat files at $SESSION_DIR/<token>. Content: a single line
#   <username>:<expires_epoch>
# The token is 32 hex chars from /dev/urandom. Cookies are 30 days.

HTPASSWD=${COLONY_GIT_HTPASSWD:-/mnt/HD/HD_a2/ffp/etc/colony-git.htpasswd}
SESSION_DIR=${COLONY_GIT_SESSION_DIR:-/mnt/HD/HD_a2/ffp/etc/colony-git-sessions}
SESSION_TTL=${COLONY_GIT_SESSION_TTL:-2592000}   # 30 days in seconds
COOKIE_NAME=colony_session

# Verify a plain password against the stored $1$ MD5-crypt hash for a
# username in $HTPASSWD. Echoes the username on success, nothing on
# failure. Exits 0 either way - callers check the echoed string.
verify_password() {
    local user=$1 pass=$2
    case "$user" in
        ''|*[!A-Za-z0-9_-]*) return 1 ;;
    esac
    [ -f "$HTPASSWD" ] || return 1
    local line=$(grep "^${user}:" "$HTPASSWD" 2>/dev/null | head -n 1)
    [ -n "$line" ] || return 1
    local stored=${line#*:}
    case "$stored" in
        \$1\$*) ;;
        *) return 1 ;;
    esac
    local rest=${stored#\$1\$}
    local salt=${rest%%\$*}
    local computed=$(/ffp/bin/openssl passwd -1 -salt "$salt" "$pass" 2>/dev/null)
    [ "$computed" = "$stored" ] || return 1
    printf '%s' "$user"
}

# Generate a 32-hex-char session token from /dev/urandom.
gen_token() {
    # od + tr is portable; head reads exactly the bytes we need.
    /ffp/bin/head -c 16 /dev/urandom | /ffp/bin/od -An -tx1 | /ffp/bin/tr -d ' \n'
}

# Write a session file for the given username. Echoes the token.
create_session() {
    local user=$1
    mkdir -p "$SESSION_DIR"
    chmod 700 "$SESSION_DIR"
    local token=$(gen_token)
    local expires=$(( $(date +%s) + SESSION_TTL ))
    local path="$SESSION_DIR/$token"
    printf '%s:%s\n' "$user" "$expires" > "$path"
    chmod 600 "$path"
    printf '%s' "$token"
}

# Look up the username for a token, or empty if invalid/expired.
# Side effect: deletes the file if expired (lazy GC).
session_user() {
    local token=$1
    case "$token" in
        ''|*[!a-f0-9]*) return 1 ;;
    esac
    local path="$SESSION_DIR/$token"
    [ -f "$path" ] || return 1
    local line=$(cat "$path" 2>/dev/null)
    local user=${line%%:*}
    local expires=${line#*:}
    case "$expires" in
        ''|*[!0-9]*) rm -f "$path"; return 1 ;;
    esac
    local now=$(date +%s)
    if [ "$now" -ge "$expires" ]; then
        rm -f "$path"
        return 1
    fi
    printf '%s' "$user"
}

# Destroy a session by token.
delete_session() {
    local token=$1
    case "$token" in
        ''|*[!a-f0-9]*) return 0 ;;
    esac
    rm -f "$SESSION_DIR/$token"
}

# Extract the cookie token from $HTTP_COOKIE, or empty.
cookie_token() {
    local hdr=${HTTP_COOKIE:-}
    local IFS=';'
    set -- $hdr
    for kv; do
        # strip leading whitespace
        kv=${kv# }
        local k=${kv%%=*}
        local v=${kv#*=}
        if [ "$k" = "$COOKIE_NAME" ]; then
            printf '%s' "$v"
            return 0
        fi
    done
    printf ''
}

# Try to identify the current user via cookie OR Basic auth, in that order.
# Echoes the username on success, nothing on failure.
current_user() {
    local token=$(cookie_token)
    if [ -n "$token" ]; then
        local u=$(session_user "$token")
        if [ -n "$u" ]; then
            printf '%s' "$u"
            return 0
        fi
    fi
    local auth=${HTTP_AUTHORIZATION:-}
    case "$auth" in
        Basic\ *)
            local b64=${auth#Basic }
            local decoded=$(printf '%s' "$b64" | /ffp/bin/base64 -d 2>/dev/null)
            local u=${decoded%%:*}
            local p=${decoded#*:}
            verify_password "$u" "$p"
            ;;
        *)
            return 1
            ;;
    esac
}

# URL-decode helper.
url_decode() {
    local s=${1//+/ }
    printf '%b' "${s//%/\\x}"
}

# Extract a value from a form-encoded body.
form_get() {
    local key=$1 body=$2 kv k v IFS='&'
    set -- $body
    for kv; do
        k=${kv%%=*}
        v=${kv#*=}
        if [ "$k" = "$key" ]; then
            url_decode "$v"
            return 0
        fi
    done
    printf ''
}
