# AI Translater using META NLLB Transformer model and Gradio UI(Gradio UI와 META NLLB 언어모델을 사용할수있는 AI 번역기)

import gradio as gr
import torch
import torch.nn.functional as F
from transformers import MBartForConditionalGeneration, MBart50TokenizerFast

# Load the model and tokenizer(모델 및 토크나이저 로드)
model = MBartForConditionalGeneration.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")
tokenizer = MBart50TokenizerFast.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")

def translate_text(text, language)는
    # Translate the text to the target language(텍스트를 대상 언어로 번역)
    translated_text = model.generate(**tokenizer.prepare_translation_batch(src_texts=[text], tgt_langs=[language]))
    return tokenizer.batch_decode(translated_text, skip_special_tokens=True)[0]

# Create the Gradio interface(Gradio 인터페이스 만들기)
output_text = gr.outputs.Textbox()
gr.Interface(fn=translate_text, inputs=["text", "text"], outputs=output_text, title="AI Translator", description="Translate text to any of the 50+ languages supported by the model.").launch()

# Example translations:(예제 번역)
# "Hello, how are you?" -> "Bonjour, comment vas-tu?"
# "I am learning new things." -> "J'apprends de nouvelles choses."
# "Thank you for your help." -> "Merci pour votre aide."
# "Goodbye, see you later!" -> "Au revoir, à bientôt!"

# Using Ngrok to tunnel the Gradio interface(Gradio 인터페이스를 터널링하는 Ngrok 사용)
pip install pyngrok
ngrok_url = gr.Interface(fn=translate_text, inputs=["text", "text"], outputs=output_text, title="AI Translator", description="Translate text to any of the 50+ languages supported by the model.").launch(share=True)
print(ngrok_url)

# To stop the Gradio interface(Gradio 인터페이스를 중지)
gr.Interface(fn=translate_text, inputs=["text", "text"], outputs=output_text, title="AI Translator", description="Translate text to any of the 50+ languages supported by the model.").close()

# To stop the Ngrok tunnel(ngrok 터널을 중지)
pkill ngrok
