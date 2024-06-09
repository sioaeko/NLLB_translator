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

iface = gr.Interface(
    fn=translate, 
    inputs=["text", "text", "text"], 
    outputs="text",
    examples=[
        ["Hello, world!", "en", "fr"]
    ]
)

if __name__ == "__main__":
    iface.launch()
