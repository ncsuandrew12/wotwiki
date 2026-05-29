#!/bin/bash
set -e
verbosity=1
# Process arguments
help="$0"
SCRIPT_DIR=$(dirname "$0")
dir="${SCRIPT_DIR}/../source-material"
for i in "$@"
do
  case ${i} in
    --dir=*) dir="${i#*=}"; shift;;
    --help) echo -e ${help}; shift;;
    -q) verbosity=$((verbosity - 1));;
    --quiet) verbosity=$((verbosity - 1)); shift;;
    -v) verbosity=$((verbosity + 1)); shift;;
    --verbose) verbosity=$((verbosity + 1)); shift;;
    *) echo -e ${help}; echo "Unknown option: ${i}" >&2; exit 2;;
  esac
done
if [[ ${verbosity} -ge 2 ]]; then set -x; fi
pushd .
convert_script=$(realpath "${SCRIPT_DIR}/convert_pdf_to_md_adobe_pdfservices.bash")
cd "${dir}"
for file in *.pdf; do
    if [[ ${verbosity} -ge 1 ]]; then echo "Processing file: ${file}"; fi
    filename=$(basename -- "${file}")
    filename_no_ext="${filename%.*}"
    output_file="${filename_no_ext}.md"
    if [[ -e "${output_file}" ]]; then
        if [[ ${verbosity} -ge 1 ]]; then echo "${output_file} already exists, skipping conversion for ${file}"; fi
    else
        "${convert_script}" --input-file="${file}" --output-file="${output_file}"
    fi
done
popd
if [[ ${verbosity} -ge 1 ]]; then echo "Done converting PDF files in ${dir}"; fi