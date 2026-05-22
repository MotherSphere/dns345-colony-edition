#!/ffp/bin/bash
# POST /colony-git/token-create.cgi
# Body: form-encoded "label=<text>"
# Creates a new Personal Access Token for the current user.
# Returns JSON { "token": "<40 hex chars>", "id": "<8 hex>", "label": "...", "created": <epoch> }.
# The full token is the ONLY moment it is exposed - the UI must show it once
# and warn the user that it will not be recoverable.

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
[ "$LEN" -gt 4096 ] && err "body too large" "413 Payload Too Large"
BODY=""
[ "$LEN" -gt 0 ] && BODY=$(dd bs="$LEN" count=1 2>/dev/null)

LABEL=$(form_get label "$BODY")
# Default label so the list view never shows an empty cell.
[ -z "$LABEL" ] && LABEL="token"
# Reject control chars and the colon (file format separator).
case "$LABEL" in
    *:*|*$'\n'*|*$'\r'*) err "label may not contain ':' or newlines" "400 Bad Request" ;;
esac
[ "${#LABEL}" -gt 60 ] && err "label too long (max 60 chars)" "400 Bad Request"

mkdir -p "$TOKEN_DIR" 2>/dev/null
chmod 700 "$TOKEN_DIR"

# 20 bytes -> 40 hex chars from /dev/urandom.
TOKEN=$(/ffp/bin/head -c 20 /dev/urandom | /ffp/bin/od -An -tx1 | /ffp/bin/tr -d ' \n')
case "$TOKEN" in
    ''|*[!a-f0-9]*) err "token generation failed" "500 Internal Server Error" ;;
esac

CREATED=$(date +%s)
printf '%s:%s:%s\n' "$USER" "$LABEL" "$CREATED" > "$TOKEN_DIR/$TOKEN"
chmod 600 "$TOKEN_DIR/$TOKEN"

# JSON-escape the label.
LABEL_ESC=${LABEL//\\/\\\\}
LABEL_ESC=${LABEL_ESC//\"/\\\"}

emit_json "201 Created"
printf '{"token":"%s","id":"%s","label":"%s","created":%d}\n' \
    "$TOKEN" "${TOKEN:0:8}" "$LABEL_ESC" "$CREATED"
