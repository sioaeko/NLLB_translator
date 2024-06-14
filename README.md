# Linguify - NLLB Test Translator

Demo Gradio Interface AI Translator using Facebook's NLLB-200-distilled-600M model.

![GitHub](https://img.shields.io/github/license/sioaeko/NLLB_Test_Translator)
![GitHub stars](https://img.shields.io/github/stars/sioaeko/NLLB_Test_Translator)
![GitHub forks](https://img.shields.io/github/forks/sioaeko/NLLB_Test_Translator)

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
   git clone https://github.com/sioaeko/NLLB_Test_Translator.git

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
## Usage

### Using Python Script

Run the translator using the Python script:

```bash
python NLLB-translator.py
```

### Using Jupyter Notebook

Open and run the NLLB_Test_Translator_Notebook.ipynb notebook in Jupyter or Colab for an interactive experience.

### Contributing

Feel free to submit issues and pull requests. Contributions are welcome!


### Project Tree

```text
NLLB_Test_Translator/
├── .github/
│   └── workflows/
│       └── python-app.yml  # GitHub Actions Setting file
├── models/
│   └── nllb_model.py       # Model file ( Example )
├── static/
│   └── css/
│   └── js/
├── templates/
│   └── index.html          # HTML Template file
├── tests/
│   └── test_translator.py  # 테스트 파일
├── NLLB_Test_Translator_Notebook.ipynb         # Jupyter Notebook file
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt        # Python Dependency file
├── app.py                  # Main Application file
└── setup.sh                # install script file
```

## License

This project is licensed under the MIT License. For more information, see [LICENSE](https://github.com/sioaeko/OpenVoiceChanger/blob/main/LICENSE) file.

