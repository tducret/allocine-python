import json
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlencode

import pytest
import vcr
from syrupy.extensions.json import JSONSnapshotExtension
from vcr.request import Request

from allocine.cache import HttpResponse

CASSETTES = Path(__file__).parent / "cassettes"


@pytest.fixture
def json_snapshot(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


class JsonBodySerializer:
    @staticmethod
    def serialize(cassette):
        for interaction in cassette["interactions"]:
            response = interaction["response"]
            try:
                response["body"] = json.loads(response["body"]["string"])
            except json.decoder.JSONDecodeError:
                pass  # Probably HTML

        return json.dumps(cassette, ensure_ascii=False, indent=2) + "\n"

    @staticmethod
    def deserialize(cassette_string):
        cassette = json.loads(cassette_string)
        for interaction in cassette["interactions"]:
            response = interaction["response"]
            response_body = response["body"]
            if not isinstance(response_body, dict) or set(response_body) != {"string"}:
                body = json.dumps(response_body, ensure_ascii=False, separators=(",", ":"))
                response["body"] = {"string": body}
                response["headers"]["content-length"] = [str(len(body.encode()))]
        return cassette


def remove_response_cookies(response):
    response["headers"].pop("set-cookie", None)
    return response


@pytest.fixture
def allocine_vcr(request, monkeypatch):
    recorder = vcr.VCR(
        cassette_library_dir=str(CASSETTES),
        before_record_response=remove_response_cookies,
        filter_headers=["cookie"],
        record_mode="once",
    )
    recorder.register_serializer("json_body", JsonBodySerializer)
    recorder.serializer = "json_body"

    cassette_name = f"{request.node.name.removeprefix('test_')}.json"
    allocine = request.getfixturevalue("allocine")
    original_fetch = allocine._client._fetch

    with recorder.use_cassette(cassette_name) as cassette:

        def fetch(url, expected_status, *args, not_found_ok=False, **kwargs):
            query = urlencode(sorted((kwargs.get("params") or {}).items()), doseq=True)
            uri = f"{url}?{query}" if query else url
            recorded_request = Request("GET", uri, None, kwargs.get("headers") or {})

            if cassette.write_protected:
                recorded = cassette.play_response(recorded_request)
                body = recorded["body"]["string"]
                response = HttpResponse(
                    recorded["status"]["code"],
                    {name: values[0] for name, values in recorded["headers"].items()},
                    body if isinstance(body, bytes) else body.encode(),
                )
            else:
                response = original_fetch(url, expected_status, *args, not_found_ok=not_found_ok, **kwargs)
                cassette.append(
                    recorded_request,
                    {
                        "status": {
                            "code": response.status_code,
                            "message": HTTPStatus(response.status_code).phrase,
                        },
                        "headers": {name: [value] for name, value in response.headers.items()},
                        "body": {"string": response.content.decode("utf-8", errors="replace")},
                    },
                )

            if response.status_code not in {expected_status, 304} and not (
                not_found_ok and response.status_code == 404
            ):
                raise ValueError(
                    f"{url!r} : expected status {expected_status}, received {response.status_code}",
                )
            return response

        monkeypatch.setattr(allocine._client, "_fetch", fetch)
        yield cassette
