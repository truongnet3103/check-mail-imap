# translate_api.py
from fastapi import FastAPI
from pydantic import BaseModel
from deep_translator import GoogleTranslator

app = FastAPI()

class TranslateRequest(BaseModel):
    text: str

@app.post("/translate")
def translate(req: TranslateRequest):
    translated = GoogleTranslator(source='auto', target='vi').translate(req.text)
    return {"translated_text": translated}
