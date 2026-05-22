#!/ffp/bin/bash
# POST /colony-git/repo-create.cgi
# Body: form-encoded "name=...&description=..."
# Authenticated (cookie session or HTTP Basic). The acting user becomes the
# owner. Creates a bare repo at REPOS_ROOT/<name>.git, writes the owner +
# description files, and installs the standard post-receive hook so the
# language cache is precomputed on first push.

set -u

. "$(dirname "$0")/lib-auth.sh"

REPOS_ROOT=${COLONY_GIT_REPOS_ROOT:-/mnt/HD/HD_a2/git}
GIT_BIN=${COLONY_GIT_BIN:-/ffp/bin/git}
HOOK_SRC=${COLONY_GIT_HOOK_SRC:-/ffp/colony/colony-git/hooks/post-receive}

emit_json() {
    printf 'Content-Type: application/json; charset=utf-8\r\n'
    printf 'Cache-Control: no-store\r\n'
    if [ -n "${1:-}" ]; then
        printf 'Status: %s\r\n' "$1"
    fi
    printf '\r\n'
}

err() {
    emit_json "$2"
    printf '{"error":"%s","code":%d}\n' "$1" "${2%% *}"
    exit 0
}

# -- Auth ------------------------------------------------------------------
USER=$(current_user)
if [ -z "$USER" ]; then
    err "authentication required" "401 Unauthorized"
fi

# -- Method ----------------------------------------------------------------
if [ "${REQUEST_METHOD:-}" != "POST" ]; then
    err "POST required" "405 Method Not Allowed"
fi

LEN=${CONTENT_LENGTH:-0}
case "$LEN" in
    ''|*[!0-9]*) err "invalid Content-Length" "400 Bad Request" ;;
esac
if [ "$LEN" -gt 8192 ]; then
    err "body too large" "413 Payload Too Large"
fi
BODY=""
if [ "$LEN" -gt 0 ]; then
    BODY=$(dd bs="$LEN" count=1 2>/dev/null)
fi

NAME=$(form_get name "$BODY")
DESC=$(form_get description "$BODY")

# -- Validate name --------------------------------------------------------
# Strip a trailing .git so the user can type either "foo" or "foo.git".
NAME=${NAME%.git}
NLEN=${#NAME}
if [ "$NLEN" -lt 1 ] || [ "$NLEN" -gt 50 ]; then
    err "repository name must be 1 to 50 characters" "400 Bad Request"
fi
case "$NAME" in
    *[!A-Za-z0-9._-]*) err "name may only contain letters, digits, . _ -" "400 Bad Request" ;;
    .*|*..*)           err "name must not start with a dot or contain .."  "400 Bad Request" ;;
esac

DIR="$REPOS_ROOT/$NAME.git"
if [ -e "$DIR" ]; then
    err "a repository named '$NAME.git' already exists" "409 Conflict"
fi

# -- Validate description (free text, no newlines, max 200 chars) ----------
case "$DESC" in
    *$'\n'*|*$'\r'*) err "description must be a single line" "400 Bad Request" ;;
esac
if [ "${#DESC}" -gt 200 ]; then
    err "description too long (max 200 chars)" "400 Bad Request"
fi

# -- Create bare repo ------------------------------------------------------
if ! "$GIT_BIN" init --bare --quiet "$DIR" 2>/dev/null; then
    err "git init failed" "500 Internal Server Error"
fi

# -- Owner + description files --------------------------------------------
printf '%s\n' "$USER" > "$DIR/owner"
chmod 644 "$DIR/owner"

if [ -n "$DESC" ]; then
    printf '%s\n' "$DESC" > "$DIR/description"
else
    # default description stub matches git's: keep it but mark it empty so
    # repos.cgi displays "no description".
    printf 'Unnamed repository; edit this file to name the repository.\n' > "$DIR/description"
fi
chmod 644 "$DIR/description"

# -- Install post-receive hook --------------------------------------------
if [ -f "$HOOK_SRC" ]; then
    cp "$HOOK_SRC" "$DIR/hooks/post-receive"
    chmod 755 "$DIR/hooks/post-receive"
fi

# -- Success ---------------------------------------------------------------
emit_json "201 Created"
printf '{"ok":true,"name":"%s.git","owner":"%s"}\n' "$NAME" "$USER"
