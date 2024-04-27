# AI Translater using META NLLB Transformer model and Gradio UI(Gradio UI와 META NLLB 언어모델을 사용할수있는 AI 번역기)
# facebook/nllb-200-distilled-600M 모델을 사용하는 AI 번역기
# Ngrok 터널을 사용해서 외부에서 Gradio에 접근할수있습니다.
# 실행하면 로컬에서 웹브라우저로 Gradio 인터페이스에 접근할수있습니다.
# 번역할 문장을 입력하고 번역된 결과를 확인할수있습니다.

# 모델 정보 : https://huggingface.co/facebook/nllb-200-distilled-600M

import gradio as gr
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

# Load the model and tokenizer
model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")

def translate_text(text):
    # Tokenize the text(텍스트 토큰화)
    tokenized_text = tokenizer(text, return_tensors="pt", padding=True)

    # Perform the translation(번역 수행하는 단계)
    translation = model.generate(**tokenized_text)

    # Decode and return the translation(디코딩 및 번역 반환)
    translated_text = tokenizer.decode(translation[0], skip_special_tokens=True)
    return translated_text

# Create a Gradio interface(Gradio 인터페이스 생성)
app = gr.Interface(fn=translate_text, inputs="text", outputs="text", title="AI Translater", description="Translate text from one language to another using the META NLLB Transformer model.")
app.launch

# ngrok tunneling for access from external URL(Ngrok 터널링으로 외부 URL에서 접근하기)
pip install pyngrok
from pyngrok import ngrok
ngrok.set_auth_token("your_auth_token")
public_url = ngrok.connect(port=7860)
print(public_url)
