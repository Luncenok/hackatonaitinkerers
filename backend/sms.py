import os
from twilio.rest import Client


def get_twilio_client():
    return Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )


def send_sms(to: str, body: str):
    client = get_twilio_client()
    message = client.messages.create(
        body=body,
        from_=os.environ["TWILIO_PHONE_NUMBER"],
        to=to,
    )
    return message.sid
