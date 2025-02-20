import gradio as gr
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import os
from datetime import datetime
from functools import lru_cache
import torch
import numpy as np

# Language mappings
LANGUAGE_CODES = {
   "English": "eng_Latn",
   "Korean": "kor_Hang",
   "Japanese": "jpn_Jpan", 
   "Chinese": "zho_Hans",
   "Spanish": "spa_Latn",
   "French": "fra_Latn",
   "German": "deu_Latn",
   "Russian": "rus_Cyrl",
   "Portuguese": "por_Latn",
   "Italian": "ita_Latn",
   "Burmese": "mya_Mymr",
   "Thai": "tha_Thai"
}

class TranslationHistory:
   def __init__(self):
       self.history = []
       self.max_entries = 100
   
   def add(self, source, translated, src_lang, tgt_lang):
       entry = {
           "source": source,
           "translated": translated,
           "src_lang": src_lang,
           "tgt_lang": tgt_lang,
           "timestamp": datetime.now()
       }
       self.history.insert(0, entry)
       if len(self.history) > self.max_entries:
           self.history.pop()
       return entry

   def get_history(self):
       return self.history

   def clear(self):
       self.history = []

# Initialize history
translation_history = TranslationHistory()

# Load model and tokenizer with error handling
try:
   model_name = "facebook/nllb-200-distilled-600M"
   model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
   tokenizer = AutoTokenizer.from_pretrained(model_name)
   
   if torch.cuda.is_available():
       model = model.to("cuda")
       device = "cuda"
   else:
       device = "cpu"
       
except Exception as e:
   print(f"Error loading model: {str(e)}")
   raise

@lru_cache(maxsize=1000)
def cached_translate(text, src_lang, tgt_lang, max_length=128, temperature=0.7):
   try:
       if not text.strip():
           return ""
           
       # Convert friendly names to codes
       src_code = LANGUAGE_CODES.get(src_lang, src_lang)
       tgt_code = LANGUAGE_CODES.get(tgt_lang, tgt_lang)
       
       # Manually define language token mappings
       LANGUAGE_TOKENS = {
           "eng_Latn": tokenizer.convert_tokens_to_ids("eng_Latn"),
           "kor_Hang": tokenizer.convert_tokens_to_ids("kor_Hang"),
           "jpn_Jpan": tokenizer.convert_tokens_to_ids("jpn_Jpan"),
           "zho_Hans": tokenizer.convert_tokens_to_ids("zho_Hans"),
           "spa_Latn": tokenizer.convert_tokens_to_ids("spa_Latn"),
           "fra_Latn": tokenizer.convert_tokens_to_ids("fra_Latn"),
           "deu_Latn": tokenizer.convert_tokens_to_ids("deu_Latn"),
           "rus_Cyrl": tokenizer.convert_tokens_to_ids("rus_Cyrl"),
           "por_Latn": tokenizer.convert_tokens_to_ids("por_Latn"),
           "ita_Latn": tokenizer.convert_tokens_to_ids("ita_Latn"),
           "mya_Mymr": tokenizer.convert_tokens_to_ids("mya_Mymr"),
           "tha_Thai": tokenizer.convert_tokens_to_ids("tha_Thai")
       }

       inputs = tokenizer(text, return_tensors="pt", padding=True)
       if device == "cuda":
           inputs = {k: v.to("cuda") for k, v in inputs.items()}
           
       forced_bos_token_id = LANGUAGE_TOKENS.get(tgt_code, None)  # Use the manual mapping
       
       outputs = model.generate(
           **inputs,
           forced_bos_token_id=forced_bos_token_id,
           max_length=max_length,
           temperature=temperature,
           num_beams=5,
           length_penalty=0.6,
           early_stopping=True
       )
       
       translated = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
       
       # Add to history
       translation_history.add(text, translated, src_lang, tgt_lang)
       
       return translated
       
   except Exception as e:
       return f"Translation error: {str(e)}"

def translate_file_with_progress(file, src_lang, tgt_lang, max_length=128, temperature=0.7):
   try:
       content = file.read().decode('utf-8')
       lines = content.split('\n')
       translated_lines = []
       
       progress = gr.Progress()
       for i, line in enumerate(progress.tqdm(lines)):
           if line.strip():
               translated = cached_translate(
                   line, src_lang, tgt_lang, 
                   max_length=max_length,
                   temperature=temperature
               )
               translated_lines.append(translated)
           else:
               translated_lines.append("")
               
       output = '\n'.join(translated_lines)
       
       # Save output
       os.makedirs("translated", exist_ok=True) 
       output_path = os.path.join("translated", f"translated_{file.name}")
       with open(output_path, 'w', encoding='utf-8') as f:
           f.write(output)
           
       return f"Translation saved to {output_path}", output
       
   except Exception as e:
       return f"File translation error: {str(e)}", None

def swap_languages(src, tgt):
   return tgt, src

with gr.Blocks(css="footer {visibility: hidden}") as demo:
   gr.Markdown("""
   # Enhanced NLLB Translator
   Translate text between multiple languages using Facebook's NLLB model
   """)
   
   with gr.Tab("Text Translation"):
       with gr.Row():
           src_lang = gr.Dropdown(
               choices=sorted(LANGUAGE_CODES.keys()), 
               value="English",
               label="Source Language"
           )
           swap_btn = gr.Button("⇄", scale=0.15)
           tgt_lang = gr.Dropdown(
               choices=sorted(LANGUAGE_CODES.keys()),
               value="Korean", 
               label="Target Language"
           )
           
       with gr.Row():
           with gr.Column():
               input_text = gr.Textbox(
                   lines=5,
                   placeholder="Enter text to translate...",
                   label="Input Text"
               )
               
           with gr.Column():
               output_text = gr.Textbox(
                   lines=5,
                   label="Translated Text",
                   interactive=False
               )
               
       with gr.Row():
           translate_btn = gr.Button("Translate", variant="primary")
           clear_btn = gr.Button("Clear")
           
       with gr.Accordion("Advanced Options", open=False):
           max_length = gr.Slider(
               minimum=10,
               maximum=512,
               value=128,
               step=1,
               label="Maximum Length"
           )
           temperature = gr.Slider(
               minimum=0.1,
               maximum=2.0, 
               value=0.7,
               step=0.1,
               label="Temperature"
           )
           
       with gr.Accordion("Translation History", open=False):
           history_list = gr.JSON(translation_history.get_history)
           refresh_btn = gr.Button("Refresh History")
           clear_history_btn = gr.Button("Clear History")
   
   with gr.Tab("File Translation"):
       with gr.Row():
           file_input = gr.File(label="Upload file to translate")
           
       with gr.Row():
           file_src_lang = gr.Dropdown(
               choices=sorted(LANGUAGE_CODES.keys()),
               value="English",
               label="Source Language"
           )
           file_tgt_lang = gr.Dropdown(
               choices=sorted(LANGUAGE_CODES.keys()),
               value="Korean",
               label="Target Language" 
           )
           
       with gr.Row():
           file_output_status = gr.Textbox(label="Translation Status")
           file_output_text = gr.Textbox(
               label="Translated Text",
               visible=False,
               interactive=False
           )
           
       with gr.Accordion("Advanced Options", open=False):
           file_max_length = gr.Slider(
               minimum=10,
               maximum=512, 
               value=128,
               step=1,
               label="Maximum Length"
           )
           file_temperature = gr.Slider(
               minimum=0.1,
               maximum=2.0,
               value=0.7,
               step=0.1,
               label="Temperature" 
           )
           
       file_translate_btn = gr.Button("Translate File", variant="primary")
   
   # Event handlers
   translate_btn.click(
       fn=cached_translate,
       inputs=[input_text, src_lang, tgt_lang, max_length, temperature],
       outputs=output_text
   )
   
   file_translate_btn.click(
       fn=translate_file_with_progress,
       inputs=[file_input, file_src_lang, file_tgt_lang, file_max_length, file_temperature],
       outputs=[file_output_status, file_output_text]
   )
   
   swap_btn.click(
       fn=swap_languages,
       inputs=[src_lang, tgt_lang],
       outputs=[src_lang, tgt_lang]
   )
   
   clear_btn.click(
       lambda: ["", ""],
       outputs=[input_text, output_text]
   )
   
   refresh_btn.click(
       fn=translation_history.get_history,
       outputs=history_list
   )
   
   clear_history_btn.click(
       fn=translation_history.clear,
       outputs=history_list
   )

   gr.Markdown(f"""
   ### Model Information
   - Using {model_name}
   - Running on {device}
   - Cache size: 1000 entries
   """)

if __name__ == "__main__":
   demo.launch(share=True)
