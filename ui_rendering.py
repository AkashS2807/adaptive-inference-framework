"""Presentation-only normalization for Streamlit's Markdown math delimiters."""
import re

_MATH_OR_CODE = re.compile(
    r'(?P<code>(?P<fence>`{3,}|~{3,})[^\n]*\n.*?(?P=fence)'
    r'|(?P<ticks>`+).*?(?P=ticks))'
    r'|(?<!\\)\\\[(?P<display>.*?)\\\]'
    r'|(?<!\\)\\\((?P<inline>.*?)\\\)',
    re.DOTALL,
)


def response_markdown(text):
    """Convert paired LaTeX delimiters for display, leaving code untouched."""
    def replace(match):
        if match.group('code') is not None:
            return match.group(0)
        if match.group('display') is not None:
            return '\n\n$$\n' + match.group('display').strip() + '\n$$\n\n'
        return '$' + match.group('inline').strip() + '$'

    return _MATH_OR_CODE.sub(replace, text)
