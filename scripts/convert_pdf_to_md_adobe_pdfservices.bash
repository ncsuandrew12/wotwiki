#!/bin/bash
set -e
verbosity=1
# Process arguments
help="$0
--input-file=<InputFilePath> Specifies the input PDF file path
--output-file=<OutputFilePath> Specifies the output Markdown file path"
SCRIPT_DIR=$(dirname "$0")
cfg_dir="${SCRIPT_DIR}/../cfg/adobe-pdf-services"
user_dir="${HOME}/.adobe-pdf-services"
for i in "$@"
do
  case ${i} in
    --input-file=*) input_file_path="${i#*=}"; shift;;
    --output-file=*) output_file_path="${i#*=}"; shift;;
    --help) echo -e ${help}; shift;;
    -q) verbosity=$((verbosity - 1));;
    --quiet) verbosity=$((verbosity - 1)); shift;;
    -v) verbosity=$((verbosity + 1)); shift;;
    --verbose) verbosity=$((verbosity + 1)); shift;;
    *) echo -e ${help}; echo "Unknown option: ${i}" >&2; exit 2;;
  esac
done
if [[ ${verbosity} -ge 2 ]]; then set -x; fi
if [[ -z "$input_file_path" || -z "$output_file_path" ]]; then echo -e ${help} >&2; echo "Missing input or output file path arguments" >&2; exit 2; fi
if [[ ! -e "${input_file_path}" ]]; then echo "File ${input_file_path} does not exist, cannot proceed" >&2; exit 2; fi
if [[ -e "${output_file_path}" ]]; then echo "File ${output_file_path} already exists, cannot proceed" >&2; exit 3; fi
input_hash=$(sha256sum "${input_file_path}" | awk '{print $1}')
if [[ ${verbosity} -ge 1 ]]; then echo "Input file: ${input_file_path} (SHA-256: ${input_hash})"; fi
output_file_path_hash=$(echo "${output_file_path}" | sha256sum | awk '{print $1}')
if [[ ${verbosity} -ge 1 ]]; then echo "Output file: \"${output_file_path}\" (SHA-256: ${output_file_path_hash})"; fi
# Install dependencies necessary to interface with Adobe PDF Services API
pip_args="-r ${cfg_dir}/adobe-pdfservices-requirements.txt"
if [[ ${verbosity} -lt 2 ]]; then pip_args="${pip_args} --quiet"; fi
pip install ${pip_args}
# Load credentials
export PDF_SERVICES_CLIENT_ID=`jq -r '.client_credentials.client_id' ${user_dir}/adobe-pdfservices-api-credentials.json`
export PDF_SERVICES_CLIENT_SECRET=`jq -r '.client_credentials.client_secret' ${user_dir}/adobe-pdfservices-api-credentials.json`
mkdir -p ./adobe-pdfservices
# Get access token
if [[ ! -e "${user_dir}/pdf_services_token_response.json" ]]; then
    curl --location 'https://pdf-services.adobe.io/token' \
        --header 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode "client_id=${PDF_SERVICES_CLIENT_ID}" \
        --data-urlencode "client_secret=${PDF_SERVICES_CLIENT_SECRET}" > ${user_dir}/pdf_services_token_response.json
fi
token=$(jq -r '.access_token' ${user_dir}/pdf_services_token_response.json)
working_dir=./adobe-pdfservices/adobe-pdftomarkdown/${input_hash}
mkdir -p ${working_dir}
echo "{\
    \"input_file_path\": \"${input_file_path}\",\
    \"input_hash\": \"${input_hash}\",\
    \"output_file_path\": \"${output_file_path}\",\
    \"output_file_path_hash\": \"${output_file_path_hash}\"\
}" > ${working_dir}/cfg.json
# Upload PDF to Adobe PDF Services and get asset ID
if [[ ! -e "${working_dir}/pdf_services_asset_response.json" ]]; then
    curl --location --request POST 'https://pdf-services.adobe.io/assets' \
        --header "X-API-Key: ${PDF_SERVICES_CLIENT_ID}" \
        --header "Authorization: Bearer ${token}" \
        --header 'Content-Type: application/json' \
        --data-raw '{
            "mediaType": "application/pdf"
        }' > ${working_dir}/pdf_services_asset_response.json
    curl --location -g --request PUT $(jq -r '.uploadUri' ${working_dir}/pdf_services_asset_response.json) \
        --header 'Content-Type: application/pdf' \
        --data-binary "@${input_file_path}" > ${working_dir}/pdf_services_upload_response.json
fi
if [[ ! -e "${working_dir}/pdf_services_upload_response.json" ]]; then
    curl --location -g --request PUT $(jq -r '.uploadUri' ${working_dir}/pdf_services_asset_response.json) \
        --header 'Content-Type: application/pdf' \
        --data-binary @${input_file_path} > ${working_dir}/pdf_services_upload_response.json
fi
# Submit job to convert PDF to Markdown
if [[ ! -e "${working_dir}/pdf_services_submit_headers.txt" ]]; then
    asset_id=$(jq -r '.assetID' ${working_dir}/pdf_services_asset_response.json)
    curl -D ${working_dir}/pdf_services_submit_headers.txt --location --request POST 'https://pdf-services.adobe.io/operation/pdftomarkdown' \
        --header "X-API-Key: ${PDF_SERVICES_CLIENT_ID}" \
        --header "Authorization: Bearer ${token}" \
        --header 'Content-Type: application/json' \
        --data-raw '{
            "assetID": "'"${asset_id}"'",
            "getFigures": true
        }' > ${working_dir}/pdf_services_submit_response.json
fi
location=`cat ${working_dir}/pdf_services_submit_headers.txt | grep -i "location:" | sed -e 's/location: //I' | tr -d '\r'`
# Wait for job to complete and get download link for converted Markdown
status=""
while [[ "${status}" != "done" ]]; do
    sleep 5
    curl --location -g --request GET "${location}" \
        --header "Authorization: Bearer ${token}" \
        --header "x-api-key: ${PDF_SERVICES_CLIENT_ID}" > ${working_dir}/pdf_services_status_response.json
    status=$(jq -r '.status' ${working_dir}/pdf_services_status_response.json)
    if [[ "${status}" != "done" ]]; then echo "Status: ${status}" >&2; exit 4; fi
done
# Even though we already checked this, it's possible the file was created in the time it took for the job to complete, so check again before downloading
if [[ -e "${output_file_path}" ]]; then echo "File ${output_file_path} already exists, cannot proceed" >&2; exit 3; fi
# Download converted Markdown
download=$(jq -r '.asset.downloadUri' ${working_dir}/pdf_services_status_response.json)
curl --location -g --request GET "${download}" > "${output_file_path}"
# Done
if [[ ${verbosity} -ge 1 ]]; then echo "Successfully converted ${input_file_path} to ${output_file_path}"; fi
