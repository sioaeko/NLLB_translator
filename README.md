# NLLB_Test_Translator

Demo Gradio Interface AI Translator using Facebook's NLLB-200-distilled-600M model.

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

Open and run the omnitrans.ipynb notebook in Jupyter or Colab for an interactive experience.

### Contributing

Feel free to submit issues and pull requests. Contributions are welcome!


### Project Tree

```text
NLLB_Test_Translator/
├── .github/
│   └── workflows/
│       └── python-app.yml  # GitHub Actions 설정 파일
├── models/
│   └── nllb_model.py       # 모델 파일 (예시)
├── static/
│   └── css/
│   └── js/
├── templates/
│   └── index.html          # HTML 템플릿 파일
├── tests/
│   └── test_translator.py  # 테스트 파일
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt        # Python 의존성 파일
├── app.py                  # 메인 애플리케이션 파일
└── setup.sh                # 설치 스크립트 파일
```

## License

This project is licensed under the MIT License. 자세한 내용은 [LICENSE](https://github.com/sioaeko/OpenVoiceChanger/blob/main/LICENSE) 파일을 참조하십시오.

