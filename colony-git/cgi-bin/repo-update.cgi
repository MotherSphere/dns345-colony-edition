#!/ffp/bin/bash
# POST /colony-git/repo-update.cgi
# Body: form-encoded "name=<repo>&description=<text>"
# Auth: cookie session or HTTP Basic. Must own the repo.

set -u

. "$(dirname "$0")/lib-auth.sh"

REPOS_ROOT=${COLONY_GIT_REPOS_ROOT:-/mnt/HD/HD_a2/git}

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
[ "$LEN" -gt 8192 ] && err "body too large" "413 Payload Too Large"
BODY=""
[ "$LEN" -gt 0 ] && BODY=$(dd bs="$LEN" count=1 2>/dev/null)

NAME=$(form_get name "$BODY")
DESC=$(form_get description "$BODY")

# Repo name validation (must already exist).
case "$NAME" in
    *.git) ;;
    *)     NAME="${NAME}.git" ;;
esac
case "${NAME%.git}" in
    ''|*[!A-Za-z0-9._-]*|.*|*..*) err "invalid repository name" "400 Bad Request" ;;
esac
DIR="$REPOS_ROOT/$NAME"
[ -d "$DIR" ] && [ -f "$DIR/HEAD" ] || err "repository not found" "404 Not Found"

# Ownership check.
OWNER=""
[ -f "$DIR/owner" ] && OWNER=$(head -n 1 "$DIR/owner" 2>/dev/null)
[ "$OWNER" = "$USER" ] || err "you are not the owner of this repository" "403 Forbidden"

# Description (free text, single line, max 200 chars).
case "$DESC" in
    *$'\n'*|*$'\r'*) err "description must be a single line" "400 Bad Request" ;;
esac
[ "${#DESC}" -gt 200 ] && err "description too long (max 200)" "400 Bad Request"

if [ -n "$DESC" ]; then
    printf '%s\n' "$DESC" > "$DIR/description"
else
    printf 'Unnamed repository; edit this file to name the repository.\n' > "$DIR/description"
fi
chmod 644 "$DIR/description"

emit_json "200 OK"
printf '{"ok":true,"name":"%s","description":"%s"}\n' "$NAME" "$(printf '%s' "$DESC" | sed 's/\\/\\\\/g; s/"/\\"/g')"
