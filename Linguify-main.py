import gradio as gr
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from pyngrok import ngrok
import os

# Load the model and tokenizer
model_name = "facebook/nllb-200-distilled-600M"
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Get all available language codes
available_languages = list(tokenizer.lang_code_to_id.keys())

def translate_text(text, src_lang, tgt_lang):
    try:
        # Tokenize the text with source language
        inputs = tokenizer(text, return_tensors="pt", src_lang=src_lang)
        
        # Generate translation
        translated = model.generate(
            **inputs, 
            forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang],
            max_length=128
        )
        
        # Decode the translation
        translated_text = tokenizer.batch_decode(translated, skip_special_tokens=True)[0]
        return translated_text
    except Exception as e:
        return f"Translation error: {str(e)}"

# Create a Gradio interface
with gr.Blocks() as app:
    gr.Markdown("# AI Translator using META NLLB Model")
    
    with gr.Row():
        src_lang = gr.Dropdown(choices=available_languages, label="Source Language")
        tgt_lang = gr.Dropdown(choices=available_languages, label="Target Language")
    
    with gr.Row():
        input_text = gr.Textbox(lines=5, label="Enter text to translate")
        output_text = gr.Textbox(lines=5, label="Translated text")
    
    translate_btn = gr.Button("Translate")
    translate_btn.click(fn=translate_text, inputs=[input_text, src_lang, tgt_lang], outputs=output_text)

# Launch the Gradio app
app.launch(share=True)

# Set up ngrok tunneling (optional)
if os.environ.get('USE_NGROK'):
    ngrok_token = os.environ.get('NGROK_TOKEN')
    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)
        public_url = ngrok.connect(port=7860)
        print(f"Public URL: {public_url}")
    else:
        print("NGROK_TOKEN not set. Skipping ngrok tunnel.")
