# AI Translater using META NLLB Transformer model and Gradio UI(Gradio UI와 META NLLB 언어모델을 사용할수있는 AI 번역기)
# facebook/nllb-200-distilled-600M 모델을 사용하는 AI 번역기
# Ngrok 터널을 사용해서 외부에서 Gradio에 접근할수있습니다.
# 실행하면 로컬에서 웹브라우저로 Gradio 인터페이스에 접근할수있습니다.
# 번역할 문장을 입력하고 번역된 결과를 확인할수있습니다.

# 모델 정보 : https://huggingface.co/facebook/nllb-200-distilled-600M

import gradio as gr
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from pyngrok import ngrok

# Load the model and tokenizer
model_name = "facebook/nllb-200-distilled-600M"
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

def translate_text(text):
    # Tokenize the text
    tokenized_text = tokenizer(text, return_tensors="pt", padding=True)

    # Perform the translation
    translation = model.generate(**tokenized_text)

    # Decode and return the translation
    translated_text = tokenizer.decode(translation[0], skip_special_tokens=True)
    return translated_text

# Create a Gradio interface
app = gr.Interface(
    fn=translate_text,
    inputs=gr.inputs.Textbox(lines=2, placeholder="Enter text to translate..."),
    outputs="text",
    title="AI Translator",
    description="Translate text from one language to another using the META NLLB Transformer model."
)

# Launch the Gradio app
app.launch(share=True)

# Set up ngrok tunneling
ngrok.set_auth_token("your_auth_token")  # Replace with your actual ngrok auth token
public_url = ngrok.connect(port=7860)
print(f"Public URL: {public_url}")
