#!/ffp/bin/bash
# GET /colony-git/api/languages?name=<repo>&ref=<ref>
# Walks the tree at <ref>, sums byte counts per file extension (excluding
# known binary types), and returns the breakdown.
#
# Output:
#   {"ref":"master","total":12345,"extensions":{".rs":8000,".md":1000,...}}
#
# The frontend maps extensions to (language_name, color) since taxonomy
# changes faster than the NAS shell does. Files without an extension are
# bucketed under "" (empty key) and rendered as "Other" by the SPA.

set -u
. "$(dirname "$0")/lib.sh"

name=$(qs_get name)
ref=$(sanitize_ref "$(qs_get ref)")
repo_dir=$(resolve_repo "$name")

emit_headers

# --- cache lookup ---
# Cache key: the commit hash that <ref> resolves to right now. If the cache
# file's first line matches, replay the rest of the file (the JSON body).
# Else compute and overwrite atomically (write then mv).
head_hash=$(git_in "$repo_dir" rev-parse "$ref" 2>/dev/null)
cache_dir="$repo_dir/colony-cache"
cache_file="$cache_dir/languages-$head_hash.json"

if [ -n "$head_hash" ] && [ -f "$cache_file" ]; then
    cat "$cache_file"
    exit 0
fi

# Stream computation to a tmp file in the cache dir, then mv into place
# (atomic on the same filesystem) so concurrent requests can't see a
# partial cache file.
mkdir -p "$cache_dir" 2>/dev/null
# Drop other (older) cached results for this repo to bound disk usage.
# We keep one entry per HEAD at a time; HEAD changes invalidate the rest.
find "$cache_dir" -name 'languages-*.json' -type f ! -name "languages-$head_hash.json" -delete 2>/dev/null
tmp_cache="$cache_dir/.tmp-langs-$$"
trap 'rm -f "$tmp_cache"' EXIT

# Binary extensions we always skip (case-insensitive comparison done in awk).
SKIP_EXTS=".png .jpg .jpeg .gif .ico .webp .bmp .tiff
.pdf .zip .tar .gz .tgz .bz2 .xz .7z .rar
.exe .dll .so .a .o .obj .class .jar .wasm
.ttf .otf .woff .woff2 .eot
.mp3 .mp4 .mov .avi .wav .ogg .flac .m4a .webm
.db .sqlite .sqlite3 .mdb
.pyc .pyo .o
.bin .iso .img .dmg"

# `ls-tree -r -l` output:
#   <mode> SP blob SP <hash> TAB <size_right_aligned> TAB <path>
git_in "$repo_dir" ls-tree -r -l "$ref" 2>/dev/null \
| /ffp/bin/awk -v skip_exts="$SKIP_EXTS" -v ref="$ref" '
    BEGIN {
        # build skip set
        n = split(skip_exts, list, /[ \n]+/);
        for (i = 1; i <= n; i++) skip[tolower(list[i])] = 1;
    }
    {
        # Fields: $1=mode, $2=type, $3=hash, then size + TAB + path
        if ($2 != "blob") next;
        # rebuild the rest after first three fields
        rest = $0;
        # strip "mode SP type SP hash" by finding 3rd TAB-like split
        # The format from ls-tree -l is space-separated mode/type/hash, then TAB, then size, then TAB, then path.
        # Easier: split on TAB.
        # ls-tree -l format: "<mode> blob <hash>   <size>\t<path>" — exactly ONE tab.
        n = split($0, parts, "\t");
        if (n < 2) next;
        # parts[1] = "<mode> blob <hash>" + maybe right-padded size? No - size is parts[2].
        # Actually: parts[1] contains "<mode> blob <hash>          <size_part_or_so>"
        # because the size is right-aligned with spaces BEFORE a TAB.
        # The real layout per git docs:
        #   "<mode> SP <type> SP <object>   SIZE\t<file>"
        # only ONE TAB total (between size and file). So parts[2] = path.
        path = parts[2];
        if (path == "") next;

        # Pull size out of parts[1] - last space-separated token.
        m = split(parts[1], tok, /[ ]+/);
        size = tok[m];
        if (size !~ /^[0-9]+$/) next;

        # Extract extension (suffix from last dot; "" if none or starts with dot).
        ext = "";
        slash = 0;
        for (i = length(path); i >= 1; i--) {
            c = substr(path, i, 1);
            if (c == "/") { slash = i; break; }
            if (c == ".") { ext = tolower(substr(path, i)); break; }
        }
        # Hidden-only files (.bashrc) -> treat as no-extension if leading dot
        # and no other dot after the last slash.
        basename = (slash > 0) ? substr(path, slash+1) : path;
        if (substr(basename, 1, 1) == "." && index(substr(basename, 2), ".") == 0) {
            ext = "";
        }

        if (ext in skip) next;

        bytes[ext] += size + 0;
        total += size + 0;
        file_count += 1;
    }
    END {
        gsub(/\\/, "\\\\", ref);
        gsub(/"/,  "\\\"", ref);
        printf("{\"ref\":\"%s\",\"total\":%d,\"file_count\":%d,\"extensions\":{", ref, total, file_count);
        first = 1;
        for (k in bytes) {
            if (!first) printf(",");
            first = 0;
            # JSON-escape k: shouldnt contain quotes/backslashes but be safe
            gsub(/\\/, "\\\\", k);
            gsub(/"/,  "\\\"", k);
            printf("\"%s\":%d", k, bytes[k]);
        }
        printf("}}\n");
    }
' > "$tmp_cache"

# Emit the body to the HTTP response.
cat "$tmp_cache"

# Atomically install in cache (mv is atomic on same filesystem). If the
# rename fails (rare), drop the tmp and move on - the next request will
# recompute.
if [ -n "$head_hash" ]; then
    mv "$tmp_cache" "$cache_file" 2>/dev/null || rm -f "$tmp_cache"
fi
