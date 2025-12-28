"""
Style Loader
Utility class for loading and applying CSS styles to Streamlit components
"""
import streamlit as st
from pathlib import Path


class StyleLoader:
    """Manager for loading and applying CSS styles"""

    def __init__(self):
        """
        Initialize StyleLoader

        Args:
            styles_dir: Path to the styles directory. If None, uses current file's parent directory.
        """
        self.styles_dir = Path(__file__).parent / "styles"

    def load_css(self, filename: str) -> str:
        """
        Load CSS content from a file

        Args:
            filename: Name of the CSS file to load

        Returns:
            CSS content as string
        """
        css_file = self.styles_dir / filename
        if not css_file.exists():
            raise FileNotFoundError(f"CSS file not found: {css_file}")

        with open(css_file, 'r', encoding='utf-8') as f:
            return f.read()

    def apply_css(self, filename: str) -> None:
        """
        Load and apply CSS styles to the current Streamlit app

        Args:
            filename: Name of the CSS file to load and apply
        """
        css = self.load_css(filename)
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    def apply_inline_css(self, css_content: str) -> None:
        """
        Apply inline CSS styles to the current Streamlit app

        Args:
            css_content: CSS content as string
        """
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

    def apply_multiple(self, *filenames: str) -> None:
        """
        Load and apply multiple CSS files at once

        Args:
            *filenames: Variable number of CSS filenames to load and apply
        """
        combined_css = []
        for filename in filenames:
            combined_css.append(self.load_css(filename))

        css_content = "\n\n".join(combined_css)
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
