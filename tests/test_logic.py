"""
Tests for the stateless functions which encapsulate the behaviour of the
TextSmith platform.
"""
import pytest
from textsmith import logic
from textsmith import database


def setup_function():
    """
    Setup a clean database state.
    Invoked for every test function in the module.
    """
    database.OBJECTS = {}
    database.USERS = {}


def test_make_uuid():
    """
    Ensure the UUID is expressed as a string.
    """
    uuid = logic.make_uuid()
    assert isinstance(uuid, str)


def test_hash_check_password():
    """
    Ensure hashing and checking of passwords works.
    """
    password = "topsecret"
    hashed_password = logic.hash_password(password)
    assert logic.verify_password(hashed_password, password) is True
    assert logic.verify_password(hashed_password, "fail") is False


def test_add_object():
    """
    Ensure an object is added to the database.OBJECTS dictionary.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("object name", "object description", user)
    assert new_uuid in database.OBJECTS


def test_add_room():
    """
    Ensure a room is added to the database.OBJECTS dictionary.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("room name", "room description", user)
    assert new_uuid in database.OBJECTS


def test_add_exit():
    """
    Ensure an exit is added to the database.OBJECTS dictionary.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("source room", "room description", user)
    destination_uuid = logic.add_room("destination room", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    new_uuid = logic.add_exit("exit name", "description", user, source,
                              destination)
    assert new_uuid in database.OBJECTS


def test_add_exit_user_not_in_allow():
    """
    An exit cannot be added where the destination room as an "allow" list
    whose members don't include the user creating the exit. Such a user
    wouldn't be allowed into the room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("source room", "room description", user)
    destination_uuid = logic.add_room("destination room", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    destination['_meta']['allow'].append(logic.make_uuid)
    with pytest.raises(PermissionError):
        new_uuid = logic.add_exit("exit name", "description", user, source,
                                  destination)


def test_add_exit_user_in_exclude():
    """
    An exit cannot be added where the destination room's "exclude" list
    includes the user creating the exit. Such a user wouldn't be allowed into
    the room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("source room", "room description", user)
    destination_uuid = logic.add_room("destination room", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    destination['_meta']['exclude'].append(user_uuid)
    with pytest.raises(PermissionError):
        new_uuid = logic.add_exit("exit name", "description", user, source,
                                  destination)


def test_add_exit_duplicate():
    """
    An exit cannot be added where there is already an exit from the source
    room to the destination room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("source room", "room description", user)
    destination_uuid = logic.add_room("destination room", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    duplicate_uuid = logic.add_exit("exit name", "description", user, source,
                                    destination)
    with pytest.raises(ValueError):
        new_uuid = logic.add_exit("exit name", "description", user, source,
                                  destination)
