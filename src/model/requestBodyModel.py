from pydantic import BaseModel


class InvokeModel(BaseModel):
    conversation_id: str
    roles: str
    content: str
    email: str
    subject: str
