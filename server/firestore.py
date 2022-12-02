import fireo

from google.auth.credentials import Credentials
from fireo.models import Model
from fireo.fields import DateTime, IDField, NumberField, TextField


class Video(Model):
    id = IDField(required=True, validator=lambda v: len(v) == 11)
    title = TextField(max_length=100, required=True)
    description = TextField(required=True)
    created = DateTime(required=True)
    published = DateTime(required=True)
    duration = NumberField(int_only=True, required=True)
    thumbnail_url = TextField(required=False)
    audio_size = NumberField(default=0, int_only=True, required=False)
    audio_type = TextField(max_length=255, required=False)


def init_firestore(credentials: Credentials):
    fireo.connection(credentials=credentials)
