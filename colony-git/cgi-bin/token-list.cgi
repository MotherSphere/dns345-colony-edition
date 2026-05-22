#!/ffp/bin/bash
# GET /colony-git/token-list.cgi
# Lists the current user's Personal Access Tokens.
# Returns JSON: { "tokens": [ { "id": "<8-hex prefix>", "label": "...", "created": <epoch> } ] }
# We NEVER echo the full token back - it is only shown once at creation time.

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

mkdir -p "$TOKEN_DIR" 2>/dev/null
chmod 700 "$TOKEN_DIR"

emit_json
printf '{"tokens":['
first=1
shopt -s nullglob 2>/dev/null || true
for f in "$TOKEN_DIR"/*; do
    [ -f "$f" ] || continue
    line=$(cat "$f" 2>/dev/null)
    owner=${line%%:*}
    [ "$owner" = "$USER" ] || continue
    rest=${line#*:}
    label=${rest%:*}
    created=${rest##*:}
    token_id=$(basename "$f")
    # Only expose the first 8 hex chars as the "id" so the user can
    # identify a token in the UI without the full secret leaking.
    short=${token_id:0:8}
    label_esc=${label//\\/\\\\}
    label_esc=${label_esc//\"/\\\"}
    [ $first -eq 0 ] && printf ','
    first=0
    printf '{"id":"%s","label":"%s","created":%d}' "$short" "$label_esc" "${created:-0}"
done
printf ']}\n'
