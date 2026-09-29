from dataclasses import dataclass, field
from typing import Any


@dataclass
class Photo:
    file_id: str
    file_size: int | None = None


@dataclass
class SavedResult:
    content_format: str
    idea: Any


@dataclass
class UserSession:
    photos: list[Photo] = field(default_factory=list)
    brief: str = ""
    content_format: str = "post"
    history: list[SavedResult] = field(default_factory=list)
    collages: list[Any] = field(default_factory=list)


class InMemorySessionStore:
    """MVP state: disappears after restart; use Redis in production."""
    HISTORY_LIMIT = 5

    def __init__(self) -> None:
        self._sessions: dict[int, UserSession] = {}

    def get(self, user_id: int) -> UserSession:
        return self._sessions.setdefault(user_id, UserSession())

    def add_photo(self, user_id: int, photo: Photo, limit: int) -> int:
        session = self.get(user_id)
        if len(session.photos) >= limit:
            raise ValueError("photo_limit")
        session.photos.append(photo)
        return len(session.photos)

    def set_brief(self, user_id: int, brief: str) -> None:
        self.get(user_id).brief = brief.strip()[:1000]

    def set_format(self, user_id: int, content_format: str) -> None:
        if content_format not in {"post", "stories", "reels"}:
            raise ValueError("unknown_format")
        self.get(user_id).content_format = content_format

    def save_result(self, user_id: int, idea: Any) -> None:
        session = self.get(user_id)
        session.history.append(SavedResult(session.content_format, idea))
        del session.history[:-self.HISTORY_LIMIT]

    def latest_result(self, user_id: int) -> Any | None:
        history = self.get(user_id).history
        return history[-1].idea if history else None

    def save_collages(self, user_id: int, collages: list[Any]) -> None:
        self.get(user_id).collages = collages

    def collage(self, user_id: int, number: int) -> Any | None:
        collages = self.get(user_id).collages
        return next((item for item in collages if item.number == number), None)

    def reset(self, user_id: int) -> None:
        self._sessions[user_id] = UserSession()
