import unittest
from app import translate

class TestTranslator(unittest.TestCase):

    def test_translation(self):
        result = translate("Hello, world!", "en", "fr")
        self.assertEqual(result, "Bonjour, le monde!")

if __name__ == '__main__':
    unittest.main()
