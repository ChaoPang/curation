# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import os
import slack

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def sendgrid_noticiation():
    message = Mail(
        from_email='cp3016@cumc.columbia.edu',
        to_emails='cp3016@cumc.columbia.edu',
        subject='Sending with Twilio SendGrid is Fun',
        html_content='<strong>and easy to do anywhere, even with Python</strong>')
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


def slack_notification():
    client = slack.WebClient(os.environ["SLACK_TOKEN"])

    client.chat_postMessage(
        channel="#test_channel",
        text="Hello from your app!",
        verify=False
    )


if __name__ == '__main__':
    slack_notification()
