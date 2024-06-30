import unittest
from app import translate

class TestTranslator(unittest.TestCase):

    def test_english_to_french(self):
        result = translate("Hello, world!", "eng_Latn", "fra_Latn")
        self.assertIn("Bonjour", result)

    def test_french_to_english(self):
        result = translate("Bonjour le monde", "fra_Latn", "eng_Latn")
        self.assertIn("Hello", result)

    def test_error_handling(self):
        result = translate("Test", "invalid_lang", "eng_Latn")
        self.assertIn("error", result.lower())

if __name__ == '__main__':
    unittest.main()
