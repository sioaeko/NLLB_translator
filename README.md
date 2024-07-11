# NLLB_translator 

Gradio Transformer Translator using Facebook's NLLB-200-distilled-600M model.

Model info : [Hugging Face](https://huggingface.co/docs/transformers/model_doc/nllb)

Demo on [Hugging Face Demo Space](https://huggingface.co/spaces/Asanari/Linguify)

![GitHub](https://img.shields.io/github/license/sioaeko/NLLB_translator)
![GitHub stars](https://img.shields.io/github/stars/sioaeko/NLLB_translator)
![GitHub forks](https://img.shields.io/github/forks/sioaeko/NLLB_translator)

## Overview

This project provides an AI translator that supports 200 languages using the NLLB (No Language Left Behind) model by Meta, which contains 600 million parameters. The application features a user-friendly interface built with Gradio, allowing users to input text and receive translations seamlessly.

## Features

- **Multi-language Support**: Translate between 200 languages.
- **Web Interface**: Utilize Gradio for easy text translation via a web interface.
- **External Access**: Use Ngrok tunneling for accessing the translator from external URLs.
- **Versatile Usage**: Available as a Python script for various environments.
- **Notebook Integration**: Supports Jupyter Notebooks, making it compatible with Runpod and Google Colab.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sioaeko/NLLB_translator.git

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
## Usage

### Using Python Script

Run the translator using the Python script:

```bash
python app.py
```

### Using Jupyter Notebook

Open and run the NLLB_translator.ipynb notebook in Jupyter or Colab for an interactive experience.

### Contributing

Feel free to submit issues and pull requests. Contributions are welcome!


### Project Tree

```text
NLLB_translator/
├── .github/
│   └── workflows/
│       └── python-app.yml  # GitHub Actions Setting file
├── models/
│   └── nllb_model.py       # Model file ( Example )
├── tests/
│   └── test_translator.py  # 테스트 파일
├── .gitignore
├── LICENSE
├── README.md
├── main.py                 
├── requirements.txt        # Python Dependency file
├── app.py                  # Main Application file
└── setup.sh                # install script file
```

## License

This project is licensed under the MIT License. For more information, see [LICENSE](https://github.com/sioaeko/NLLB_translator/blob/main/LICENSE) file.

