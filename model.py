from pydantic import BaseModel


class PubSubMessage(BaseModel):
    data: str


class PubSubRequest(BaseModel):
    message: PubSubMessage


class Document(object):
    id: str
    email: str
    filename: str

    def __init__(self, id, email, filename):
        self.id = id
        self.email = email
        self.filename = filename
