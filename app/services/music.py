from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class MusicMatch:
    title: str
    artist: str
    url: str | None = None


def make_music_links(title: str, artist: str) -> dict[str, str]:
    query = quote(f"{title} {artist}")

    return {
        "youtube": f"https://www.youtube.com/results?search_query={query}",
        "youtube_music": f"https://music.youtube.com/search?q={query}",
    }


class MusicProvider:
    async def search(self, query: str, limit: int = 3) -> list[MusicMatch]:
        """
        Пока не используем внешний музыкальный API.

        Gemini предлагает конкретный трек,
        а мы создаём прямые ссылки на его поиск.
        """
        return []