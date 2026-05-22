#!/ffp/bin/bash
# GET /colony-git/whoami.cgi
# Basic-auth gated. Returns {"user":"<name>"} on success, 401 + WWW-Authenticate
# on missing/bad creds. Used by the SPA "Sign in" button to trigger the
# browser's basic-auth popup and discover the current user without ever
# storing a session server-side.

set -u

HTPASSWD=${COLONY_GIT_HTPASSWD:-/mnt/HD/HD_a2/ffp/etc/colony-git.htpasswd}
REALM="Colony Git"

deny() {
    printf 'Status: 401 Unauthorized\r\n'
    printf 'WWW-Authenticate: Basic realm="%s"\r\n' "$REALM"
    printf 'Content-Type: application/json; charset=utf-8\r\n'
    printf 'Cache-Control: no-store\r\n'
    printf '\r\n'
    printf '{"error":"%s","code":401}\n' "$1"
    exit 0
}

AUTH=${HTTP_AUTHORIZATION:-}
case "$AUTH" in
    Basic\ *) ;;
    *) deny "authentication required" ;;
esac
B64=${AUTH#Basic }
DECODED=$(printf '%s' "$B64" | /ffp/bin/base64 -d 2>/dev/null)
USER=${DECODED%%:*}
PASS=${DECODED#*:}

case "$USER" in
    ''|*[!A-Za-z0-9_-]*) deny "invalid username" ;;
esac

if [ ! -f "$HTPASSWD" ]; then
    deny "user database missing"
fi
LINE=$(grep "^${USER}:" "$HTPASSWD" 2>/dev/null | head -n 1)
if [ -z "$LINE" ]; then
    deny "invalid credentials"
fi
STORED=${LINE#*:}

case "$STORED" in
    \$1\$*)
        REST=${STORED#\$1\$}
        SALT=${REST%%\$*}
        COMPUTED=$(/ffp/bin/openssl passwd -1 -salt "$SALT" "$PASS" 2>/dev/null)
        ;;
    *) deny "unsupported password format" ;;
esac

if [ "$COMPUTED" != "$STORED" ]; then
    deny "invalid credentials"
fi

printf 'Content-Type: application/json; charset=utf-8\r\n'
printf 'Cache-Control: no-store\r\n'
printf '\r\n'
printf '{"user":"%s"}\n' "$USER"
