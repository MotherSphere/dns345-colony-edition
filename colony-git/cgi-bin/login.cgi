#!/ffp/bin/bash
# POST /colony-git/login.cgi
# Body: form-encoded "username=...&password=..."
# On success: 200 + Set-Cookie: colony_session=<token>; HttpOnly; SameSite=Strict
# On failure: 401 + JSON error

set -u

. "$(dirname "$0")/lib-auth.sh"

emit_json() {
    printf 'Content-Type: application/json; charset=utf-8\r\n'
    printf 'Cache-Control: no-store\r\n'
    if [ -n "${1:-}" ]; then
        printf 'Status: %s\r\n' "$1"
    fi
    if [ -n "${2:-}" ]; then
        printf 'Set-Cookie: %s\r\n' "$2"
    fi
    printf '\r\n'
}

err() {
    emit_json "$2"
    printf '{"error":"%s","code":%d}\n' "$1" "${2%% *}"
    exit 0
}

if [ "${REQUEST_METHOD:-}" != "POST" ]; then
    err "POST required" "405 Method Not Allowed"
fi

LEN=${CONTENT_LENGTH:-0}
case "$LEN" in
    ''|*[!0-9]*) err "invalid Content-Length" "400 Bad Request" ;;
esac
if [ "$LEN" -gt 4096 ]; then
    err "body too large" "413 Payload Too Large"
fi
BODY=""
if [ "$LEN" -gt 0 ]; then
    BODY=$(dd bs="$LEN" count=1 2>/dev/null)
fi

USER=$(form_get username "$BODY")
PASS=$(form_get password "$BODY")

if [ -z "$USER" ] || [ -z "$PASS" ]; then
    err "username and password required" "400 Bad Request"
fi

VERIFIED=$(verify_password "$USER" "$PASS")
if [ -z "$VERIFIED" ]; then
    # Avoid leaking whether the user exists.
    err "invalid credentials" "401 Unauthorized"
fi

TOKEN=$(create_session "$VERIFIED")
COOKIE="${COOKIE_NAME}=${TOKEN}; Path=/colony-git; HttpOnly; SameSite=Strict; Max-Age=${SESSION_TTL}"

emit_json "200 OK" "$COOKIE"
printf '{"ok":true,"user":"%s"}\n' "$VERIFIED"
