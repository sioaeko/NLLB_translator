import gradio as gr
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

model_name = "facebook/nllb-200-distilled-600M"
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

def translate(text, src_lang, tgt_lang):
    inputs = tokenizer(text, return_tensors="pt", padding=True)
    outputs = model.generate(inputs["input_ids"])
    translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return translated_text

with gr.Blocks() as demo:
    gr.Markdown("# NLLB Test Translator for Everyone")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 1. Select files to translate")
            file_input = gr.File(label="files", file_types=['text'], file_count="multiple")
        
        with gr.Column():
            gr.Markdown("### 2. Running a translation")
            model_info = gr.Markdown("Currently using the facebook/nllb-200-distilled-600M AI translation model")
            translate_button = gr.Button("Running a translation")
            status_info = gr.Textbox(label="Status information", value="Waiting for translation...")
            open_folder_button = gr.Button("Open the Done folder")

    translate_button.click(fn=translate, inputs=[file_input], outputs=status_info)

demo.launch()
