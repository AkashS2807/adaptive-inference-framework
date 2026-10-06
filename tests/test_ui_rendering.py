import unittest

from ui_rendering import response_markdown


class ResponseRenderingTests(unittest.TestCase):
    def test_common_math_and_markdown(self):
        text = r'**Area:** \[\text{Area}=s \times s=s^{2}.\] Ratio: \(4\).'
        self.assertEqual(
            response_markdown(text),
            '**Area:** \n\n$$\n' + r'\text{Area}=s \times s=s^{2}.' + '\n$$\n\n Ratio: $4$.',
        )
        self.assertIn(r'\frac{\text{New Area}}{\text{Original Area}}=4',
                      response_markdown(r'\[\frac{\text{New Area}}{\text{Original Area}}=4\]'))

    def test_code_and_existing_markdown_are_unchanged(self):
        text = '**Bold** $x$\n\n$$y$$\n' + r'`\(literal\)` and ``\[literal\]``' + '\n'
        text += '```python\n' + r'print("\[literal\]")' + '\n```\n'
        text += '~~~text\n' + r'\(literal\)' + '\n~~~\n'
        self.assertEqual(response_markdown(text), text)
        self.assertEqual(response_markdown(r'Unpaired \[ and <script>alert(1)</script>'),
                         r'Unpaired \[ and <script>alert(1)</script>')
