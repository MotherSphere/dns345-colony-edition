#!/ffp/bin/bash
# POST /colony-git/repo-delete.cgi
# Body: form-encoded "name=<repo>&confirm=<repo>"
# Auth: cookie session or HTTP Basic. Must own the repo.
# `confirm` must echo the repository name verbatim - mirrors GitHub's
# "type the name to confirm" safeguard.

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
[ "$LEN" -gt 4096 ] && err "body too large" "413 Payload Too Large"
BODY=""
[ "$LEN" -gt 0 ] && BODY=$(dd bs="$LEN" count=1 2>/dev/null)

NAME=$(form_get name "$BODY")
CONFIRM=$(form_get confirm "$BODY")

case "$NAME" in
    *.git) ;;
    *)     NAME="${NAME}.git" ;;
esac
case "${NAME%.git}" in
    ''|*[!A-Za-z0-9._-]*|.*|*..*) err "invalid repository name" "400 Bad Request" ;;
esac
DIR="$REPOS_ROOT/$NAME"
[ -d "$DIR" ] && [ -f "$DIR/HEAD" ] || err "repository not found" "404 Not Found"

OWNER=""
[ -f "$DIR/owner" ] && OWNER=$(head -n 1 "$DIR/owner" 2>/dev/null)
[ "$OWNER" = "$USER" ] || err "you are not the owner of this repository" "403 Forbidden"

# Confirmation must match the repo name (with or without .git suffix).
case "$CONFIRM" in
    "$NAME"|"${NAME%.git}") ;;
    *) err "confirmation does not match repository name" "400 Bad Request" ;;
esac

# Belt and braces: target must live inside REPOS_ROOT and end in .git.
case "$DIR" in
    "$REPOS_ROOT"/*.git) ;;
    *) err "refusing to delete a path outside the repos root" "500 Internal Server Error" ;;
esac

# Move-then-delete to make the removal atomic from the user's perspective:
# the repo disappears from listings the moment the rename completes, even
# if the recursive rm takes a moment on a large heavenandearth-godot-sized
# repo. The renamed dir starts with "." so shopt nullglob in repos.cgi
# skips it (the glob pattern is *.git).
TRASH="$REPOS_ROOT/.deleting-$$-$(date +%s)-$NAME"
if ! mv "$DIR" "$TRASH" 2>/dev/null; then
    err "failed to retire repository" "500 Internal Server Error"
fi
rm -rf "$TRASH"

emit_json "200 OK"
printf '{"ok":true,"name":"%s"}\n' "$NAME"
