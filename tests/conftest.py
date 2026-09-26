import json
from pathlib import Path

import pytest
import vcr
from syrupy.extensions.json import JSONSnapshotExtension

CASSETTES = Path(__file__).parent / "cassettes"


@pytest.fixture
def json_snapshot(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


class JsonBodySerializer:
    @staticmethod
    def serialize(cassette):
        for interaction in cassette["interactions"]:
            response = interaction["response"]
            response["body"] = json.loads(response["body"]["string"])
        return json.dumps(cassette, ensure_ascii=False, indent=2) + "\n"

    @staticmethod
    def deserialize(cassette_string):
        cassette = json.loads(cassette_string)
        for interaction in cassette["interactions"]:
            response = interaction["response"]
            body = json.dumps(response["body"], ensure_ascii=False, separators=(",", ":"))
            response["body"] = {"string": body}
            response["headers"]["content-length"] = [str(len(body.encode()))]
        return cassette


def remove_response_cookies(response):
    response["headers"].pop("set-cookie", None)
    return response


@pytest.fixture
def allocine_vcr(request):
    recorder = vcr.VCR(
        cassette_library_dir=str(CASSETTES),
        before_record_response=remove_response_cookies,
        decode_compressed_response=True,
        filter_headers=["cookie"],
        record_mode="once",
    )
    recorder.register_serializer("json_body", JsonBodySerializer)
    recorder.serializer = "json_body"

    cassette_name = f"{request.node.name.removeprefix('test_')}.json"
    with recorder.use_cassette(cassette_name):
        yield recorder
