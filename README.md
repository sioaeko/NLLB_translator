# NLLB_Test_Translator
### facebook/nllb-200-distilled-600M를 사용할수있는 AI 변역기

* 200개의 언어를 지원하며, 600M의 파라미터를 가지고 있는 META의 NLLB 모델을 사용할수있는 변역기입니다.(AI translator that can use facebook/nllb-200-distilled-600M)

* Gradio UI를 사용해서 웹 인터페이스에서 텍스트를 번역할수있습니다.(Using Gradio UI to translate text in a web interface)
  
* Ngrok 터널링을 사용해서 외부에서 접근할수있습니다.(Using Ngrok tunneling to access from external URL)
  
* 번역할 문장을 입력하고 번역된 결과를 확인할수있습니다.(You can enter the sentence to be translated and check the translated result)

* py(파이썬 스크립트) 방식으로 광범위한 환경에서 손쉽게 사용할수있습니다.(You can easily use it in a wide range of environments with py method.)

* ipynb(주피터 노트북 스크립트) 방식또한 지원하여 런팟/코랩에서도 손쉽게 사용해볼수있습니다.(You can also easily use it in Runpod/Colabs with ipynb method.)

### 개발과정을 노션에도 기록하고 있어요!
> https://asanari.notion.site/Sideproject-e50001f7e16944128be6735bb461069c?pvs=4



### 프로젝트 구조 

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

## 라이선스

이 프로젝트는 MIT 라이선스에 따라 라이선스가 부여됩니다. 자세한 내용은 [LICENSE](https://github.com/sioaeko/OpenVoiceChanger/blob/main/LICENSE) 파일을 참조하십시오.

