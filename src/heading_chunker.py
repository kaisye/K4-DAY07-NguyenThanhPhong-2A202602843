from __future__ import annotations

import re

from .chunking import RecursiveChunker


class HeadingChunker:
    """Chunk Markdown-like documents by their semantic section headings.

    The source corpus contains both Markdown headings and all-caps headings
    copied from web pages.  A long section is delegated to RecursiveChunker,
    with its heading prepended to every resulting sub-chunk.
    """

    _markdown_heading = re.compile(r"^#{1,6}\s+\S")

    def __init__(self, chunk_size: int = 800) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        self.chunk_size = chunk_size

    @classmethod
    def _is_heading(cls, line: str) -> bool:
        stripped = line.strip()
        if cls._markdown_heading.match(stripped):
            return True

        # Some scraped pages use all-capital section labels instead of Markdown
        # headings, for example "CƠ HỘI VIỆC LÀM".
        letters = [character for character in stripped if character.isalpha()]
        return (
            3 <= len(stripped) <= 100
            and len(letters) >= 3
            and stripped == stripped.upper()
            and not stripped.endswith((".", ",", ";", ":"))
        )

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sections: list[tuple[str, list[str]]] = []
        current_heading = ""
        current_lines: list[str] = []
        for line in text.splitlines():
            if self._is_heading(line):
                if current_heading or current_lines:
                    sections.append((current_heading, current_lines))
                current_heading = line.strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_heading or current_lines:
            sections.append((current_heading, current_lines))

        chunks: list[str] = []
        for heading, lines in sections:
            body = "\n".join(lines).strip()
            section = "\n".join(part for part in (heading, body) if part).strip()
            if not section:
                continue
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            prefix = f"{heading}\n" if heading else ""
            available_size = max(1, self.chunk_size - len(prefix))
            parts = RecursiveChunker(chunk_size=available_size).chunk(body or heading)
            chunks.extend(f"{prefix}{part}".strip() for part in parts)
        return chunks
