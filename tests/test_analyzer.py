import asyncio
from types import SimpleNamespace

import pytest

from app.services.analyzer import GeminiImageAnalyzer, parse_idea

ANSWER = '''{"visual_story":"тепло","content_format":"post","composition_options":[{"title":"1","layout":["a"]},{"title":"2","layout":["b"]},{"title":"3","layout":["c"]}],"editing_notes":["2"],"caption_variants":["один","два","три"],"hashtag_sets":[["#test"],["#two"],["#three"]],"music_options":[{"mood":"мягко","suggestions":["A — B"],"search_query":"indie"},{"mood":"ярко","suggestions":["C — D"],"search_query":"pop"},{"mood":"тихо","suggestions":["E — F"],"search_query":"ambient"}]}'''


def test_parse_idea_accepts_fence():
    assert parse_idea(f"```json\n{ANSWER}\n```").hashtag_sets[0] == ["#test"]


def test_parse_idea_needs_all_fields():
    with pytest.raises(ValueError):
        parse_idea('{"caption":"x"}')


def test_gemini_analyzer_sends_all_images_and_format_in_one_request():
    calls = []
    def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=ANSWER)
    analyzer = object.__new__(GeminiImageAnalyzer)
    analyzer.model = "gemini-3.6-flash"
    analyzer.client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    idea = asyncio.run(analyzer.analyze([b"first", b"second"], "test brief", "reels"))
    assert idea.caption_variants[0] == "один"
    assert calls[0]["model"] == "gemini-3.6-flash"
    assert len(calls[0]["contents"]) == 3
