#!/ffp/bin/bash
# Shared helpers for Colony Git CGI scripts.
#
# Conventions:
#   - All endpoints emit Content-Type: application/json and a UTF-8 JSON body.
#   - On any handled error, emit a JSON {"error":"...","code":<int>} and exit 0.
#   - Inputs come from $QUERY_STRING (parsed via qs_get) and $PATH_INFO.
#   - Repo names MUST end in ".git" and match [A-Za-z0-9._-]+.git
#   - Refs MUST match [A-Za-z0-9._/-]+ (covers branches, tags, short hashes).
#   - Paths inside repos MUST NOT contain "..", may be empty (= repo root).

REPOS_ROOT=${COLONY_GIT_REPOS_ROOT:-/mnt/HD/HD_a2/git}
GIT_BIN=${COLONY_GIT_BIN:-/ffp/bin/git}

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

emit_headers() {
    printf 'Content-Type: application/json; charset=utf-8\r\n'
    printf 'Cache-Control: no-store\r\n'
    printf '\r\n'
}

emit_error() {
    local msg=$1 code=${2:-500}
    emit_headers
    printf '{"error":"%s","code":%d}\n' "$(json_escape_value "$msg")" "$code"
    exit 0
}

# Escape a string value for inclusion inside JSON double-quotes.
# Handles backslash, double-quote, newline, CR, tab. Other control chars
# are stripped (git output rarely contains them; safest to drop than to
# emit invalid JSON).
#
# WARNING: bash's ${s//pattern/replacement} is O(n^2) on bash 4.1.x (which
# ships with this NAS). Fine for short strings (filenames, short subjects,
# dates), DON'T pipe a multi-KB payload through this. For big blobs (READMEs,
# diffs, stat output) escape via streaming awk - see repo.cgi / commit.cgi
# for the pattern.
json_escape_value() {
    local s=$1
    s=${s//\\/\\\\}
    s=${s//\"/\\\"}
    s=${s//$'\r'/}
    s=${s//$'\n'/\\n}
    s=${s//$'\t'/\\t}
    printf '%s' "$s"
}

# ---------------------------------------------------------------------------
# Query-string parsing
# ---------------------------------------------------------------------------

# qs_get KEY  -> echoes the URL-decoded value of KEY from $QUERY_STRING, or
# empty if absent. Doesn't handle repeated keys.
qs_get() {
    local key=$1 qs=${QUERY_STRING:-} kv k v
    local IFS='&'
    set -- $qs
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

url_decode() {
    local s=${1//+/ }
    printf '%b' "${s//%/\\x}"
}

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Verify $1 is a safe repo name (ends in .git, alphanumeric + _.- only).
# Echoes the absolute git-dir path on success; emits error and exits otherwise.
resolve_repo() {
    local name=$1
    case "$name" in
        ''|*..*|*/*|*[!A-Za-z0-9._-]*)
            emit_error "invalid repo name" 400
            ;;
    esac
    case "$name" in
        *.git) ;;
        *) emit_error "repo name must end in .git" 400 ;;
    esac
    local path=$REPOS_ROOT/$name
    if [ ! -d "$path" ] || [ ! -f "$path/HEAD" ]; then
        emit_error "repo not found: $name" 404
    fi
    printf '%s' "$path"
}

# Verify $1 is a safe ref (branch, tag, or short hash).
# Defaults to "HEAD" if empty.
sanitize_ref() {
    local ref=$1
    if [ -z "$ref" ]; then
        printf 'HEAD'
        return
    fi
    case "$ref" in
        *..*|*[!A-Za-z0-9._/-]*)
            emit_error "invalid ref" 400
            ;;
    esac
    printf '%s' "$ref"
}

# Verify $1 is a safe in-repo path. Empty = repo root.
sanitize_path() {
    local p=$1
    case "$p" in
        *..*)
            emit_error "invalid path" 400
            ;;
    esac
    # strip leading slash
    p=${p#/}
    printf '%s' "$p"
}

# ---------------------------------------------------------------------------
# git wrappers
# ---------------------------------------------------------------------------

git_in() {
    local gitdir=$1
    shift
    "$GIT_BIN" --git-dir="$gitdir" "$@"
}
