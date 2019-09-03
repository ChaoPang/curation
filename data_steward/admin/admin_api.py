import logging
import os

from flask import Flask
from google.appengine.api import app_identity
from google.appengine.api import mail

import api_util
import key_rotation

SENDER_ADDRESS = 'curation-eng-alert@{project}.appspotmail.com'.format(project=app_identity.get_application_id())
NOTIFICATION_ADDRESS = os.environ.get('NOTIFICATION_ADDRESS')
SUBJECT = 'Project {project}: Service account key notices'.format(project=app_identity.get_application_id())
BODY = '''This is only a test of the alert system (see https://github.com/mark-velez/curation/tree/curation-eng-alert). Information below is NOT real.

# Expired keys deleted
service_account,key_id,created_by,created_on
test@pmi-ops.org,abc123,someone@pmi-ops.org,2018-01-01

# Keys expiring soon
service_account,key_id,created_by,expires
test@pmi-ops.org,xyz456,someone@pmi-ops.org,2019-09-04
'''

PREFIX = '/admin/v1/'
REMOVE_EXPIRED_KEYS_RULE = PREFIX + 'RemoveExpiredServiceAccountKeys'

app = Flask(__name__)


# @api_util.auth_required_cron
def remove_expired_keys():
    project_id = app_identity.get_application_id()
    logging.info('Started removal of expired service account keys for %s' % project_id)
    # suppressing so tests do not disrupt
    # key_rotation.delete_expired_keys(project_id)
    logging.info('Completed removal of expired service account keys for %s' % project_id)

    if NOTIFICATION_ADDRESS is not None:
        print('Success')
        # mail.send_mail(sender=SENDER_ADDRESS,
        #                to=NOTIFICATION_ADDRESS,
        #                subject=SUBJECT,
        #                body=BODY)

    return 'remove-expired-keys-complete'


app.add_url_rule(
    REMOVE_EXPIRED_KEYS_RULE,
    view_func=remove_expired_keys,
    methods=['GET'])

if __name__ == '__main__':
    remove_expired_keys()
