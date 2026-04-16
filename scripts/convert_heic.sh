#!/usr/bin/env sh
set -eu

usage() {
  echo "Usage: $0 <source-dir> [output-dir]" >&2
  exit 1
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
fi

src_dir=$1
out_dir=${2:-$src_dir}

if [ ! -d "$src_dir" ]; then
  echo "Source directory not found: $src_dir" >&2
  exit 1
fi

if ! command -v magick >/dev/null 2>&1; then
  echo "ImageMagick 'magick' is required but was not found in PATH." >&2
  exit 1
fi

mkdir -p "$out_dir"

converted=0
skipped=0
tmp_list=$(mktemp)
trap 'rm -f "$tmp_list"' EXIT INT TERM

find "$src_dir" -maxdepth 1 -type f \( -iname '*.heic' -o -iname '*.heif' \) | sort > "$tmp_list"

while IFS= read -r file; do
  [ -n "$file" ] || continue
  base=$(basename "$file")
  name=${base%.*}
  output="$out_dir/$name.jpg"

  if [ -e "$output" ]; then
    echo "Skipping existing $output"
    skipped=$((skipped + 1))
    continue
  fi

  echo "Converting $file -> $output"
  magick "$file" -auto-orient -strip -quality 92 "$output"
  converted=$((converted + 1))
done < "$tmp_list"

echo "Done. Converted: $converted, skipped: $skipped"