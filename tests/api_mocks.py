class MockResponse:

    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class MockNeoomApi:

    def __init__(self, state):
        self.state = state
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append({
            "method": "GET",
            "url": url,
            "headers": headers,
            "timeout": timeout,
        })
        return MockResponse(self.state)


class MockEaseeApi:

    def __init__(self, charger_state=None):
        self.charger_state = charger_state or {
            "isEnabled": False,
            "dynamicChargerCurrent": 0,
        }
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append({
            "method": "GET",
            "url": url,
            "headers": headers,
            "timeout": timeout,
        })
        return MockResponse(self.charger_state)

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({
            "method": "POST",
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        })
        return MockResponse()
