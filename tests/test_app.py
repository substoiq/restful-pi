import pytest

from app import create_app
from conftest import gpio_is_on
from pins import DEFAULT_PINS


@pytest.fixture
def client():
    return create_app().test_client()


def test_root_redirects_to_docs(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/docs")


def test_docs_and_swagger_are_served(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/swagger.json").status_code == 200


def test_lists_default_pins_all_off(client):
    pins = client.get("/pins/").json
    assert len(pins) == len(DEFAULT_PINS)
    assert all(pin["state"] == "off" for pin in pins)
    assert [pin["pin_num"] for pin in pins] == [pin["pin_num"] for pin in DEFAULT_PINS]


def test_patch_switches_the_gpio_pin(client):
    response = client.patch("/pins/1", json={"state": "on"})
    assert response.status_code == 200
    assert response.json["state"] == "on"
    assert gpio_is_on(23)

    client.patch("/pins/1", json={"state": "off"})
    assert not gpio_is_on(23)


def test_put_needs_every_field(client):
    response = client.put("/pins/1", json={"state": "on"})
    assert response.status_code == 400
    assert not gpio_is_on(23)


def test_put_replaces_the_pin(client):
    response = client.put("/pins/1", json={"pin_num": 23, "color": "orange", "state": "on"})
    assert response.status_code == 200
    assert response.json == {"id": 1, "pin_num": 23, "color": "orange", "state": "on"}
    assert gpio_is_on(23)


def test_invalid_state_is_rejected(client):
    response = client.patch("/pins/1", json={"state": "blink"})
    assert response.status_code == 400
    assert client.get("/pins/1").json["state"] == "off"


def test_pin_number_outside_header_is_rejected(client):
    response = client.post("/pins/", json={"pin_num": 40, "color": "red", "state": "on"})
    assert response.status_code == 400


def test_id_in_payload_is_ignored(client):
    response = client.patch("/pins/1", json={"id": 99, "state": "on"})
    assert response.json["id"] == 1
    assert client.get("/pins/99").status_code == 404


def test_create_and_delete(client):
    response = client.post("/pins/", json={"pin_num": 5, "color": "white", "state": "on"})
    assert response.status_code == 201
    new_id = response.json["id"]
    assert gpio_is_on(5)

    assert client.delete(f"/pins/{new_id}").status_code == 204
    assert not gpio_is_on(5)
    assert client.get(f"/pins/{new_id}").status_code == 404


def test_gpio_pin_can_only_be_used_once(client):
    response = client.post("/pins/", json={"pin_num": 23, "color": "red", "state": "on"})
    assert response.status_code == 409
    response = client.patch("/pins/2", json={"pin_num": 23})
    assert response.status_code == 409


def test_moving_a_pin_releases_the_old_gpio(client):
    client.patch("/pins/1", json={"state": "on"})
    response = client.patch("/pins/1", json={"pin_num": 5})
    assert response.status_code == 200
    assert not gpio_is_on(23)
    assert gpio_is_on(5)
    # The old pin is free again
    assert client.post("/pins/", json={"pin_num": 23, "color": "red", "state": "off"}).status_code == 201


def test_unknown_pin_gives_404(client):
    response = client.patch("/pins/999", json={"state": "on"})
    assert response.status_code == 404
    assert response.json["message"] == "pin 999 doesn't exist"
