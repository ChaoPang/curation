import common
from constants.cdr_cleaner import clean_cdr as clean_consts
import constants.cdr_cleaner.clean_cdr as cdr_consts
from notebooks import bq
from constants import bq_utils as bq_consts
import resources

# Select rows where the person_id is in the person table
SELECT_EXISTING_PERSON_IDS = (
    'SELECT {fields} FROM `{project}.{dataset}.{table}` AS entry '
    'JOIN `{project}.{dataset}.person` AS person '
    'ON entry.person_id = person.person_id')

PERSON_TABLE_QUERY = """
SELECT table_name
FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
WHERE COLUMN_NAME = 'person_id'
"""


def get_tables_with_person_id(project_id, dataset_id):
    """
    Get list of tables that have a person_id column
    """
    person_table_query = PERSON_TABLE_QUERY.format(project=project_id,
                                                   dataset=dataset_id)
    person_tables_df = bq.query(person_table_query)
    person_table_list = list(person_tables_df.table_name.get_values())

    #remove mapping tables
    for item in person_table_list:
        if item.startswith('_mapping'):
            person_table_list.remove(item)

    return person_table_list


def get_sandbox_queries(project_id, dataset_id, sandbox_query, ticket_number):
    person_tables_list = get_tables_with_person_id(project_id, dataset_id)
    queries_list = []

    for table in person_tables_list:
        sandbox_queries = dict()
        sandbox_queries[cdr_consts.QUERY] = sandbox_query.format(
            dataset=dataset_id,
            project=project_id,
            table=table,
            sandbox_dataset=dataset_id + '_sandbox',
            intermediary_table=table + '_' + ticket_number)
        queries_list.append(sandbox_queries)

    return queries_list


def get_remove_personid_queries(project_id, dataset_id, delete_query):
    person_tables_list = get_tables_with_person_id(project_id, dataset_id)
    queries_list = []

    for table in person_tables_list:
        delete_queries = delete_query.format(project=project_id,
                                             dataset=dataset_id,
                                             table=table)
        queries_list.append({
            clean_consts.QUERY: delete_queries,
            clean_consts.DESTINATION_TABLE: table,
            clean_consts.DESTINATION_DATASET: dataset_id,
            clean_consts.DISPOSITION: bq_consts.WRITE_TRUNCATE
        })

    return queries_list


def get_queries(project=None, dataset=None):
    """
    Return a list of queries to remove data for missing persons.

    Removes data from person_id linked tables for any persons which do not
    exist in the person table.

    :return:  A list of string queries that can be executed to delete data from
        other tables for non-person users.
    """
    query_list = []
    for table in common.CLINICAL_DATA_TABLES:
        field_names = [
            'entry.' + field['name'] for field in resources.fields_for(table)
        ]
        fields = ', '.join(field_names)

        delete_query = SELECT_EXISTING_PERSON_IDS.format(project=project,
                                                         dataset=dataset,
                                                         table=table,
                                                         fields=fields)

        query_list.append({
            clean_consts.QUERY: delete_query,
            clean_consts.DESTINATION_TABLE: table,
            clean_consts.DESTINATION_DATASET: dataset,
            clean_consts.DISPOSITION: bq_consts.WRITE_TRUNCATE,
        })

    return query_list
