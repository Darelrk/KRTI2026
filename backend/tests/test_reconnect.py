from backend.app.reconnect import ConnectionState, ReconnectPolicy


def test_backoff_is_bounded():
    policy = ReconnectPolicy(max_seconds=30)
    assert [policy.delay_for(index) for index in range(6)] == [1, 2, 4, 8, 16, 30]


def test_connection_states_are_explicit():
    assert [
        ConnectionState.DISCONNECTED,
        ConnectionState.CONNECTING,
        ConnectionState.READY,
        ConnectionState.STALE,
    ] == ["disconnected", "connecting", "ready", "stale"]
