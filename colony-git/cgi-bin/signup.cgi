#!/ffp/bin/bash
# POST /colony-git/signup.cgi
# Body: form-encoded "username=...&password=...&password2=..."
# Creates a new git HTTP user by appending an htpasswd entry.
#
# Auth model: open self-service signup, LAN-only (RFC1918 source IPs).
# The .htpasswd file is the source of truth for git HTTP basic auth and is
# referenced by lighttpd's auth.backend.htpasswd.userfile directive.
#
# Hash format: {SHA}base64(sha1(password))  - mod_auth standard.

set -u

HTPASSWD=${COLONY_GIT_HTPASSWD:-/mnt/HD/HD_a2/ffp/etc/colony-git.htpasswd}

emit_json() {
    printf 'Content-Type: application/json; charset=utf-8\r\n'
    printf 'Cache-Control: no-store\r\n'
    printf '\r\n'
}

emit_err() {
    emit_json
    printf '{"error":"%s","code":%d}\n' "$1" "$2"
    exit 0
}

# -- LAN-only gate ----------------------------------------------------------
# REMOTE_ADDR is set by lighttpd. Allow RFC1918 + loopback.
case "${REMOTE_ADDR:-}" in
    192.168.*|10.*|127.*) ;;
    172.1[6-9].*|172.2[0-9].*|172.3[0-1].*) ;;
    *) emit_err "signup is LAN-only" 403 ;;
esac

# -- Method check -----------------------------------------------------------
if [ "${REQUEST_METHOD:-}" != "POST" ]; then
    emit_err "POST required" 405
fi

# -- Read body --------------------------------------------------------------
LEN=${CONTENT_LENGTH:-0}
case "$LEN" in
    ''|*[!0-9]*) emit_err "invalid Content-Length" 400 ;;
esac
# Cap body size at 4KB - all form fields combined fit easily.
if [ "$LEN" -gt 4096 ]; then
    emit_err "body too large" 413
fi
BODY=""
if [ "$LEN" -gt 0 ]; then
    BODY=$(dd bs=1 count="$LEN" 2>/dev/null)
fi

# -- Parse form fields ------------------------------------------------------
form_get() {
    local key=$1 kv k v IFS='&'
    set -- $BODY
    for kv; do
        k=${kv%%=*}
        v=${kv#*=}
        if [ "$k" = "$key" ]; then
            # URL decode: '+' -> space, %XX -> byte
            v=${v//+/ }
            printf '%b' "${v//%/\\x}"
            return 0
        fi
    done
    printf ''
}

USER=$(form_get username)
PASS=$(form_get password)
PASS2=$(form_get password2)

# -- Validate username ------------------------------------------------------
ULEN=${#USER}
if [ "$ULEN" -lt 3 ] || [ "$ULEN" -gt 20 ]; then
    emit_err "username must be 3 to 20 characters" 400
fi
case "$USER" in
    *[!A-Za-z0-9_-]*) emit_err "username may only contain letters, digits, _ and -" 400 ;;
esac
# Disallow leading hyphen/underscore for hygiene.
case "$USER" in
    -*|_*) emit_err "username must start with a letter or digit" 400 ;;
esac

# -- Validate password ------------------------------------------------------
PLEN=${#PASS}
if [ "$PLEN" -lt 5 ] || [ "$PLEN" -gt 64 ]; then
    emit_err "password must be 5 to 64 characters" 400
fi
if [ "$PASS" != "$PASS2" ]; then
    emit_err "passwords do not match" 400
fi
# Reject the colon - it's the htpasswd field separator and would corrupt the file.
case "$PASS" in
    *:*) emit_err "password may not contain a colon" 400 ;;
esac

# -- Ensure htpasswd file exists --------------------------------------------
mkdir -p "$(dirname "$HTPASSWD")" 2>/dev/null
if [ ! -f "$HTPASSWD" ]; then
    : > "$HTPASSWD"
    chmod 600 "$HTPASSWD"
fi

# -- Reject duplicate username ---------------------------------------------
if grep -q "^${USER}:" "$HTPASSWD" 2>/dev/null; then
    emit_err "username already taken" 409
fi

# -- Hash password (MD5 crypt $1$...) --------------------------------------
# lighttpd 1.4.28's "plain" auth backend confusingly expects HASHED passwords
# in crypt(3) format, NOT literal plain text (see http_auth.c "opening
# plain-userfile / expected 'username:hashed password'"). Use openssl to
# generate a $1$ MD5 crypt hash, which lighttpd then verifies with crypt(3).
HASH=$(/ffp/bin/openssl passwd -1 "$PASS" 2>/dev/null)
if [ -z "$HASH" ]; then
    emit_err "internal hashing failure" 500
fi

# -- Append atomically -------------------------------------------------------
# Temp+rename to avoid partial line on concurrent signup.
TMP=$(mktemp "${HTPASSWD}.XXXXXX")
cat "$HTPASSWD" > "$TMP"
printf '%s:%s\n' "$USER" "$HASH" >> "$TMP"
chmod 600 "$TMP"
mv "$TMP" "$HTPASSWD"

# -- Per-user sidecar (joined timestamp, future profile fields) -------------
USERS_DIR=${COLONY_GIT_USERS_DIR:-/mnt/HD/HD_a2/ffp/etc/colony-git-users}
mkdir -p "$USERS_DIR" 2>/dev/null
chmod 755 "$USERS_DIR"
printf 'joined=%s\n' "$(date +%s)" > "$USERS_DIR/$USER"
chmod 644 "$USERS_DIR/$USER"

# -- Success ----------------------------------------------------------------
emit_json
printf '{"ok":true,"user":"%s"}\n' "$USER"
