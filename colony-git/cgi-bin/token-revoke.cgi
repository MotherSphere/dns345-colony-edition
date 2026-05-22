#!/ffp/bin/bash
# POST /colony-git/token-revoke.cgi
# Body: form-encoded "id=<8 hex prefix>"
# Revokes one of the current user's tokens (matches by 8-hex prefix).

set -u

. "$(dirname "$0")/lib-auth.sh"

emit_json() {
    printf 'Content-Type: application/json; charset=utf-8\r\n'
    printf 'Cache-Control: no-store\r\n'
    [ -n "${1:-}" ] && printf 'Status: %s\r\n' "$1"
    printf '\r\n'
}

err() {
    emit_json "$2"
    printf '{"error":"%s","code":%d}\n' "$1" "${2%% *}"
    exit 0
}

USER=$(current_user)
[ -z "$USER" ] && err "authentication required" "401 Unauthorized"
[ "${REQUEST_METHOD:-}" = "POST" ] || err "POST required" "405 Method Not Allowed"

LEN=${CONTENT_LENGTH:-0}
case "$LEN" in ''|*[!0-9]*) err "invalid Content-Length" "400 Bad Request" ;; esac
[ "$LEN" -gt 1024 ] && err "body too large" "413 Payload Too Large"
BODY=""
[ "$LEN" -gt 0 ] && BODY=$(dd bs="$LEN" count=1 2>/dev/null)

ID=$(form_get id "$BODY")
case "$ID" in
    *[!a-f0-9]*) err "invalid token id" "400 Bad Request" ;;
esac
[ "${#ID}" -ge 4 ] || err "token id too short" "400 Bad Request"
[ "${#ID}" -le 40 ] || err "token id too long" "400 Bad Request"

found=""
shopt -s nullglob 2>/dev/null || true
for f in "$TOKEN_DIR"/${ID}*; do
    [ -f "$f" ] || continue
    line=$(cat "$f" 2>/dev/null)
    owner=${line%%:*}
    if [ "$owner" = "$USER" ]; then
        rm -f "$f"
        found=$(basename "$f")
        break
    fi
done

if [ -z "$found" ]; then
    err "token not found" "404 Not Found"
fi

emit_json "200 OK"
printf '{"ok":true,"id":"%s"}\n' "${found:0:8}"
