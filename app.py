import gradio as gr
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import os

model_name = "facebook/nllb-200-distilled-600M"
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

available_languages = list(tokenizer.lang_code_to_id.keys())

def translate(text, src_lang, tgt_lang):
    try:
        inputs = tokenizer(text, return_tensors="pt", src_lang=src_lang)
        outputs = model.generate(
            **inputs, 
            forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang],
            max_length=128
        )
        translated_text = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
        return translated_text
    except Exception as e:
        return f"Translation error: {str(e)}"

def translate_file(file, src_lang, tgt_lang):
    try:
        content = file.read().decode('utf-8')
        translated = translate(content, src_lang, tgt_lang)
        output_path = os.path.join("translated", f"translated_{file.name}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(translated)
        return f"Translation saved to {output_path}"
    except Exception as e:
        return f"File translation error: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("# NLLB Translator")
    
    with gr.Tab("Text Translation"):
        with gr.Row():
            src_lang = gr.Dropdown(choices=available_languages, label="Source Language")
            tgt_lang = gr.Dropdown(choices=available_languages, label="Target Language")
        input_text = gr.Textbox(lines=5, label="Input Text")
        output_text = gr.Textbox(lines=5, label="Translated Text")
        translate_btn = gr.Button("Translate Text")
        translate_btn.click(fn=translate, inputs=[input_text, src_lang, tgt_lang], outputs=output_text)
    
    with gr.Tab("File Translation"):
        file_input = gr.File(label="Upload file to translate")
        file_src_lang = gr.Dropdown(choices=available_languages, label="Source Language")
        file_tgt_lang = gr.Dropdown(choices=available_languages, label="Target Language")
        file_output = gr.Textbox(label="Translation Status")
        file_translate_btn = gr.Button("Translate File")
        file_translate_btn.click(fn=translate_file, inputs=[file_input, file_src_lang, file_tgt_lang], outputs=file_output)

    gr.Markdown("Currently using the facebook/nllb-200-distilled-600M AI translation model")

demo.launch()
