from __future__ import print_function

import logging

import googleapiclient
import oauth2client
import app_identity
from constants.cdr_cleaner.clean_cdr import DataStage as stage

import bq_utils
from constants import bq_utils as bq_consts
from constants.cdr_cleaner import clean_cdr as cdr_consts

LOGGER = logging.getLogger(__name__)
FILENAME = '/tmp/cleaner.log'

FAILURE_MESSAGE_TEMPLATE = '''
The failed query was generated from the below module:
    module_name={module_name}
    function_name={function_name}
    line_no={line_no}

The failed query ran with the following configuration:
    project_id={project_id}
    destination_dataset_id={destination_dataset_id}
    destination_table={destination_table}
    disposition={disposition}
    query={query}
    exception={exception}
'''


def add_console_logging(add_handler):
    """

    This config should be done in a separate module, but that can wait
    until later.  Useful for debugging.

    """
    logging.basicConfig(
        level=logging.INFO,
        filename=FILENAME,
        filemode='a',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if add_handler:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)


def clean_dataset(project=None, statements=None, data_stage=stage.UNSPECIFIED):
    """
       Run the assigned cleaning rules.

       :param project:  the project name
       :param statements:  a list of dictionary objects to run the query
       :param data_stage:  an enum to indicate what stage of the cleaning this is
       """
    if project is None or project == '' or project.isspace():
        project = app_identity.get_application_id()
        LOGGER.info('Project name not provided.  Using default.')

    if statements is None:
        statements = []

    failures = 0
    successes = 0
    for statement in statements:
        rule_query = statement.get(cdr_consts.QUERY, '')
        legacy_sql = statement.get(cdr_consts.LEGACY_SQL, False)
        destination_table = statement.get(cdr_consts.DESTINATION_TABLE, None)
        retry = statement.get(cdr_consts.RETRY_COUNT,
                              bq_consts.BQ_DEFAULT_RETRY_COUNT)
        disposition = statement.get(cdr_consts.DISPOSITION,
                                    bq_consts.WRITE_EMPTY)
        destination_dataset = statement.get(cdr_consts.DESTINATION_DATASET,
                                            None)
        batch = statement.get(cdr_consts.BATCH, None)

        try:
            LOGGER.info("Running query %s", rule_query)
            results = bq_utils.query(rule_query,
                                     use_legacy_sql=legacy_sql,
                                     destination_table_id=destination_table,
                                     retry_count=retry,
                                     write_disposition=disposition,
                                     destination_dataset_id=destination_dataset,
                                     batch=batch)

        except (oauth2client.client.HttpAccessTokenRefreshError,
                googleapiclient.errors.HttpError) as exp:

            LOGGER.error(
                format_failure_message(project_id=project,
                                       statement=statement,
                                       exception=exp))
            failures += 1
            continue

        # wait for job to finish
        query_job_id = results['jobReference']['jobId']
        incomplete_jobs = bq_utils.wait_on_jobs([query_job_id])
        if incomplete_jobs:
            failures += 1
            raise bq_utils.BigQueryJobWaitError(incomplete_jobs)

        # check if the job is complete and an error has occurred
        is_errored, error_message = bq_utils.job_status_errored(query_job_id)

        if is_errored:
            LOGGER.error(
                format_failure_message(project_id=project,
                                       statement=statement,
                                       exception=error_message))
            failures += 1
        else:
            if destination_table is not None:
                updated_rows = results.get("totalRows")
                if updated_rows is not None:
                    LOGGER.info("Query returned %d rows for %s.%s",
                                updated_rows, destination_dataset,
                                destination_table)

            successes += 1

    if successes > 0:
        LOGGER.info("Successfully applied %d clean rules for %s.%s", successes,
                    project, data_stage)
    else:
        LOGGER.warning("No clean rules successfully applied to %s.%s", project,
                       data_stage)

    if failures > 0:
        LOGGER.warning("Failed to apply %d clean rules for %s.%s", failures,
                       project, data_stage)


def format_failure_message(project_id, statement, exception):

    query = statement.get(cdr_consts.QUERY, '')
    destination_table = statement.get(cdr_consts.DESTINATION_TABLE, None)
    disposition = statement.get(cdr_consts.DISPOSITION, bq_consts.WRITE_EMPTY)
    destination_dataset_id = statement.get(cdr_consts.DESTINATION_DATASET, None)
    module_name = statement.get(cdr_consts.MODULE_NAME,
                                cdr_consts.MODULE_NAME_DEFAULT_VALUE)
    function_name = statement.get(cdr_consts.FUNCTION_NAME,
                                  cdr_consts.FUNCTION_NAME_DEFAULT_VALUE)
    line_no = statement.get(cdr_consts.LINE_NO,
                            cdr_consts.LINE_NO_DEFAULT_VALUE)

    return FAILURE_MESSAGE_TEMPLATE.format(
        module_name=module_name,
        function_name=function_name,
        line_no=line_no,
        project_id=project_id,
        destination_dataset_id=destination_dataset_id,
        destination_table=destination_table,
        disposition=disposition,
        query=query,
        exception=exception)
