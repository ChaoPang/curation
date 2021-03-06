#!/usr/bin/env bash

# Copy prefixed tables from one dataset to another, removing (or replacing) prefix
# Note: Attempts to create the target dataset before copying
#
# # Example Usages
#
# ## Copy `dataset1.prefix_tableA` to `dataset2.tableA`
# > tools/table_copy.sh --source_app_id project --target_app_id project
#                       --source_dataset dataset1 --source_prefix prefix_ --target_dataset dataset2
#
# ## Copy `dataset1.tableA` to `dataset1.prefix_tableA`
# > tools/table_copy.sh --source_app_id project --target_app_id project
#                       --source_dataset dataset1 --target_prefix prefix_ --target_dataset dataset1

SYNC=''
USAGE="tools/table_copy.sh
[--source_app_id <SOURCE_APPLICATION_ID>]
[--target_app_id <TARGET_APPLICATION_ID>]
--source_dataset <SOURCE_DATASET>
[--source_prefix <SOURCE_PREFIX:''>]
--target_dataset <TARGET_DATASET>
[--target_prefix <TARGET_PREFIX:''>]
[--sync <true|false:true>]"

while true; do
  case "$1" in
  --source_app_id)
    SOURCE_APPLICATION_ID=$2
    shift 2
    ;;
  --target_app_id)
    TARGET_APPLICATION_ID=$2
    shift 2
    ;;
  --source_dataset)
    SOURCE_DATASET=$2
    shift 2
    ;;
  --target_dataset)
    TARGET_DATASET=$2
    shift 2
    ;;
  --source_prefix)
    SOURCE_PREFIX=$2
    shift 2
    ;;
  --target_prefix)
    TARGET_PREFIX=$2
    shift 2
    ;;
  --sync)
    SYNC=$2
    shift 2
    ;;
  --)
    shift
    break
    ;;
  *) break ;;
  esac
done

bq mk --dataset ${TARGET_APPLICATION_ID}:${TARGET_DATASET}

if [[ -z "${TARGET_PREFIX}" ]]; then
  TARGET_PREFIX=""
fi

if [[ -z "${SOURCE_PREFIX}" ]]; then
  SOURCE_PREFIX=""
fi

if [[ -z "${SOURCE_DATASET}" ]] || [[ -z "${TARGET_DATASET}" ]]; then
  echo "Usage: $USAGE"
  exit 1
fi

if [[ "$SYNC" == "false" ]]; then
  SYNC="--nosync"
fi

SOURCE_DATASET=$([[ "${SOURCE_APPLICATION_ID}" ]] && echo "${SOURCE_APPLICATION_ID}:${SOURCE_DATASET}" || echo "${SOURCE_DATASET}")
TARGET_DATASET=$([[ "${TARGET_APPLICATION_ID}" ]] && echo "${TARGET_APPLICATION_ID}:${TARGET_DATASET}" || echo "${TARGET_DATASET}")

# Copy the tables
#( [[ "${SOURCE_PREFIX}" ]] && grep ${SOURCE_PREFIX} || cat )) essentially is and if/else statement
# if SOURCE_PREFIX is not empty then grep for SOURCE_PREFIX else CAT the input
for t in $(bq ls -n 10000 ${SOURCE_DATASET} |
  grep TABLE |
  awk '{print $1}' |
  #           grep -v ^\_ |  #Tables beginning with underscore "_" are skipped
  ([[ "${SOURCE_PREFIX}" ]] && grep ${SOURCE_PREFIX} || cat)); do
  TARGET_TABLE=${t//${SOURCE_PREFIX}/} #replace all occurrences, use ${parameter//pattern/replacement_string}
  CP_CMD="bq ${SYNC} --project_id ${TARGET_APPLICATION_ID} cp -f ${SOURCE_DATASET}.${t} ${TARGET_DATASET}.${TARGET_PREFIX}${TARGET_TABLE}"
  echo $(${CP_CMD})
done
