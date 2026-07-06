import re
from dataclasses import dataclass

from app.services.extraction import PageText

PARAGRAPH_PATTERN = re.compile(r"\n\s*\n")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    page_number: int | None = None


@dataclass
class _Segment:
    text: str
    page_number: int | None
    join_with: str = "\n\n"


def _buffer_length(parts: list[_Segment]) -> int:
    if not parts:
        return 0
    total = len(parts[0].text)
    for segment in parts[1:]:
        total += len(segment.join_with) + len(segment.text)
    return total


def _join_segments(parts: list[_Segment]) -> str:
    if not parts:
        return ""
    result = parts[0].text
    for segment in parts[1:]:
        result += segment.join_with + segment.text
    return result


def _split_oversized(segment: _Segment, chunk_size: int, depth: int = 0) -> list[_Segment]:
    if len(segment.text) <= chunk_size:
        return [segment]

    if depth == 0:
        parts = [part.strip() for part in SENTENCE_PATTERN.split(segment.text) if part.strip()]
        join_with = " "
    elif depth == 1:
        parts = segment.text.split()
        join_with = " "
    else:
        return [
            _Segment(
                text=segment.text[i : i + chunk_size],
                page_number=segment.page_number,
                join_with=" " if i > 0 else segment.join_with,
            )
            for i in range(0, len(segment.text), chunk_size)
        ]

    if len(parts) <= 1:
        return _split_oversized(segment, chunk_size, depth + 1)

    result: list[_Segment] = []
    for index, part in enumerate(parts):
        sub = _Segment(
            text=part,
            page_number=segment.page_number,
            join_with=join_with if index > 0 or segment.join_with != "\n\n" else segment.join_with,
        )
        result.extend(_split_oversized(sub, chunk_size, depth + 1))
    return result


def _page_to_segments(page: PageText) -> list[_Segment]:
    if not page.text.strip():
        return []

    paragraphs = [part.strip() for part in PARAGRAPH_PATTERN.split(page.text) if part.strip()]
    return [
        _Segment(text=paragraph, page_number=page.page_number, join_with="\n\n")
        for paragraph in paragraphs
    ]


def _normalize_segments(pages: list[PageText], chunk_size: int) -> list[_Segment]:
    segments: list[_Segment] = []
    for page in pages:
        for segment in _page_to_segments(page):
            segments.extend(_split_oversized(segment, chunk_size))
    return segments


def _overlap_prefix(chunk_text: str, overlap: int) -> str:
    if overlap <= 0 or not chunk_text:
        return ""

    seed = chunk_text[-overlap:] if len(chunk_text) > overlap else chunk_text

    sentence_matches = list(SENTENCE_PATTERN.finditer(seed))
    if sentence_matches:
        return seed[sentence_matches[-1].end() :]

    paragraph_match = PARAGRAPH_PATTERN.search(seed)
    if paragraph_match:
        return seed[paragraph_match.end() :]

    return seed


def _merge_segments(
    segments: list[_Segment],
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    buffer: list[_Segment] = []
    pending_overlap: _Segment | None = None

    def emit_buffer() -> None:
        nonlocal buffer, pending_overlap
        if not buffer:
            return

        text = _join_segments(buffer)
        start_page = next((segment.page_number for segment in buffer if segment.page_number is not None), None)
        chunks.append(TextChunk(text=text, chunk_index=len(chunks), page_number=start_page))

        overlap_text = _overlap_prefix(text, overlap)
        if overlap_text:
            pending_overlap = _Segment(
                text=overlap_text,
                page_number=start_page,
                join_with=" ",
            )
        else:
            pending_overlap = None
        buffer = []

    for segment in segments:
        if pending_overlap:
            buffer = [pending_overlap]
            pending_overlap = None

        candidate_len = _buffer_length(buffer)
        if buffer:
            candidate_len += len(segment.join_with) + len(segment.text)
        else:
            candidate_len = len(segment.text)

        if buffer and candidate_len > chunk_size:
            emit_buffer()
            buffer = [segment]
        elif not buffer:
            buffer = [segment]
        else:
            buffer.append(segment)

    if buffer:
        emit_buffer()

    return chunks


def chunk_document(
    pages: list[PageText],
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    if not pages or all(not page.text.strip() for page in pages):
        return []

    segments = _normalize_segments(pages, chunk_size)
    if not segments:
        return []

    return _merge_segments(segments, chunk_size, overlap)
