from googleapiclient.discovery import build
from oauth2client.client import GoogleCredentials
from google.appengine.api import app_identity
from google.appengine.api import mail

if __name__ == '__main__':
    credentials = GoogleCredentials.get_application_default()
    service = build('logging', 'v2', credentials=credentials)

    request_body = {
        "projectIds": [
            "aou-res-curation-test"
        ],
        "filter": "protoPayload.methodName=\"google.iam.admin.v1.DeleteServiceAccountKey\" AND timestamp>\"2019-08-25T16:43:16.939073979Z\"",
        "pageSize": 5
    }
    entries__list = service.entries().list(body=request_body).execute()
    print(entries__list["entries"][0])
    sender = 'chaopang229@gmail.com'
    mail.send_mail(sender=sender,
                   to=sender,
                   subject='Your account has been approved',
                   body='Testing')

    print(app_identity.get_application_id())
