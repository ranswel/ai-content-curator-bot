from app.storage import InMemorySessionStore, Photo

def test_store_add_and_reset():
    store = InMemorySessionStore()
    assert store.add_photo(1, Photo("file"), 2) == 1
    store.reset(1)
    assert store.get(1).photos == []


def test_store_keeps_recent_results_and_format():
    store = InMemorySessionStore()
    store.set_format(1, "reels")
    store.save_result(1, "first")
    assert store.get(1).content_format == "reels"
    assert store.latest_result(1) == "first"
