#!/ffp/bin/bash
# GET /colony-git/api/blob?name=<repo>&ref=<ref>&path=<path>
# Returns the raw blob content.
#
# Detects binary vs text via the first 8 KB: if any NUL byte is present
# we treat it as binary and refuse with HTTP 415 JSON, since the SPA
# can't usefully render arbitrary bytes inline.
#
# Output:
#   - 200 with Content-Type: text/plain; charset=utf-8 on text blobs
#   - 415 JSON {"error":"binary blob, size <N>"} on binary
#   - 404 JSON when the path/ref combo doesn't resolve

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
ref=$(sanitize_ref "$(qs_get ref)")
path=$(sanitize_path "$(qs_get path)")
repo_dir=$(resolve_repo "$name")

if [ -z "$path" ]; then
    emit_error "path is required" 400
fi

target="${ref}:${path}"

# Capture the blob to a temp file ON THE NAS VOLUME (NOT tmpfs which is
# 9.7MB only). Use the repo's parent dir as scratch space.
scratch="$REPOS_ROOT/.colony-git-scratch-$$"
trap 'rm -f "$scratch"' EXIT
if ! git_in "$repo_dir" show "$target" >"$scratch" 2>/dev/null; then
    emit_error "blob not found: $path @ $ref" 404
fi

# Binary detection: first 8 KB containing a NUL = binary.
head_bytes=$(/ffp/bin/head -c 8192 "$scratch" | tr -d '\000' | wc -c)
total_head=$(/ffp/bin/head -c 8192 "$scratch" | wc -c)
if [ "$head_bytes" != "$total_head" ]; then
    size=$(stat -c '%s' "$scratch" 2>/dev/null)
    printf 'Content-Type: application/json; charset=utf-8\r\n'
    printf 'Cache-Control: no-store\r\n'
    printf '\r\n'
    printf '{"error":"binary blob","size":%d,"path":"%s"}\n' \
        "${size:-0}" "$(json_escape_value "$path")"
    exit 0
fi

# Plain text response: stream the file out.
printf 'Content-Type: text/plain; charset=utf-8\r\n'
printf 'Cache-Control: no-store\r\n'
printf '\r\n'
cat "$scratch"
