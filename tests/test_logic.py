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
    assert new_uuid in user["_meta"]["owns"]


def test_add_room():
    """
    Ensure a room is added to the database.OBJECTS dictionary.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("room name", "room description", user)
    assert new_uuid in database.OBJECTS
    assert new_uuid in user["_meta"]["owns"]


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
    assert new_uuid in user["_meta"]["owns"]
    assert new_uuid in source["_meta"]["exits_out"]
    assert new_uuid in destination["_meta"]["exits_in"]


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


def test_add_user():
    """
    Ensure a user is added to the database.OBJECTS dictionary.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    assert user_uuid in database.OBJECTS
    user = database.OBJECTS[user_uuid]
    # Check the password is hashed!
    assert user["_meta"]["password"] != "password"
    # Default start location is "nowhere"
    assert user["_meta"]["location"] is None
    # Users own themselves.
    assert user_uuid in user["_meta"]["owns"]


def test_add_user_duplicate():
    """
    It's not possible to add a user if the desired username is already taken.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    with pytest.raises(ValueError):
        duplicate_uuid = logic.add_user("username", "description", "password",
                                        "mail@example.com")


def test_is_owner():
    """
    The is_owner function returns True if the referenced user is the owner of
    the referenced object. Otherwise False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("object name", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otherobj_uuid = logic.add_object("object name", "object description",
                                     otheruser)
    otherobj = database.OBJECTS[otherobj_uuid]
    assert logic.is_owner(new_obj, user) is True
    assert logic.is_owner(otherobj, user) is False


def test_delete_object_does_not_exist():
    """
    It's not possible to delete a non-existent object.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    assert logic.delete_object(logic.make_uuid, user) is False


def test_delete_object_not_an_object():
    """
    It's only possible to delete objects that have a typeof "object". I.e. it's
    not possible to delete rooms, exits or users in this fashion.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("room name", "room description", user)
    assert logic.delete_object(new_uuid, user) is False


def test_delete_object_user_not_owner():
    """
    It's not possible to delete an object if the user isn't the object's owner.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("object name", "object description", user)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    assert logic.delete_object(new_uuid, otheruser) is False


def test_delete_object_as_superuser():
    """
    It's possible to delete the object if the user is a superuser.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("object name", "object description", user)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    assert logic.delete_object(new_uuid, otheruser) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]


def test_delete_object_as_owner():
    """
    It's possible to delete the object if the user is the object's owner.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("object name", "object description", user)
    assert logic.delete_object(new_uuid, user) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]


def test_delete_room_does_not_exits():
    """
    It's not possible to delete a room that doesn't exist.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    assert logic.delete_room(logic.make_uuid, user) is False


def test_delete_room_not_a_room():
    """
    If the referenced object is NOT a room, DO NOT delete it.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("object name", "object description", user)
    assert logic.delete_room(new_uuid, user) is False


def test_delete_room_not_owner():
    """
    If the user isn't the owner of the room, they can't delete it.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("room name", "room description", user)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    assert logic.delete_room(new_uuid, otheruser) is False


def test_delete_room_as_superuser():
    """
    It's possible to delete the room if the user is a superuser.
    """
    # Create the context for the user, room and superuser.
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    user["_meta"]["location"] = logic.make_uuid()
    new_uuid = logic.add_room("room name", "room description", user)
    otherroom_uuid = logic.add_room("other name", "room description", user)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    # Add objects to the room, place users in there too and make some exits.
    new_room = database.OBJECTS[new_uuid]
    other_room = database.OBJECTS[otherroom_uuid]
    into = logic.add_exit("exit 1", "description", user, new_room, other_room)
    outfrom = logic.add_exit("exit ", "description", user, other_room,
                             new_room)
    obj_uuid = logic.add_object("object name", "object description", user)
    room = database.OBJECTS[new_uuid]
    room["_meta"]["contents"].append(obj_uuid)
    room["_meta"]["contents"].append(user_uuid)
    # Delete the room and check all the expected state.
    assert logic.delete_room(new_uuid, otheruser) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]
    # Objects that were in the room, are now in their owners inventory.
    assert obj_uuid in user["_meta"]["inventory"]
    # Users who were in the room and now at the default "nowhere" location.
    assert user["_meta"]["location"] is None
    # Exits no longer exist.
    assert into not in database.OBJECTS
    assert outfrom not in database.OBJECTS
    assert into not in user["_meta"]["owns"]
    assert outfrom not in user["_meta"]["owns"]


def test_delete_room_as_owner():
    """
    It's possible to delete the room if the user is the room's owner.
    """
    # Create the context for the user, room and superuser.
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("room name", "room description", user)
    otherroom_uuid = logic.add_room("other name", "room description", user)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["location"] = logic.make_uuid()
    # Add objects to the room, place users in there too and make some exits.
    new_room = database.OBJECTS[new_uuid]
    other_room = database.OBJECTS[otherroom_uuid]
    into = logic.add_exit("exit 1", "description", user, new_room, other_room)
    outfrom = logic.add_exit("exit ", "description", user, other_room,
                             new_room)
    obj_uuid = logic.add_object("object name", "object description", user)
    room = database.OBJECTS[new_uuid]
    room["_meta"]["contents"].append(obj_uuid)
    room["_meta"]["contents"].append(otheruser_uuid)
    # Delete the room and check all the expected state.
    assert logic.delete_room(new_uuid, user) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]
    # Objects that were in the room, are now in their owners inventory.
    assert obj_uuid in user["_meta"]["inventory"]
    # Users who were in the room and now at the default "nowhere" location.
    assert otheruser["_meta"]["location"] is None
    # Exits no longer exist.
    assert into not in database.OBJECTS
    assert outfrom not in database.OBJECTS
    assert into not in user["_meta"]["owns"]
    assert outfrom not in user["_meta"]["owns"]


def test_delete_exit_does_not_exist():
    """
    It's not possible to delete an exit that doesn't exist.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    assert logic.delete_exit(logic.make_uuid, user) is False


def test_delete_exit_not_an_exit():
    """
    It's only possible to delete exits with the delete_exit function!
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("object name", "object description", user)
    assert logic.delete_exit(new_uuid, user) is False


def test_delete_exit_not_owner():
    """
    If the user isn't the owner of the room, they cannot delete it.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1 name", "room description", user)
    room2_uuid = logic.add_room("room2 name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    assert logic.delete_exit(exit_id, otheruser) is False


def test_delete_exit_as_superuser():
    """
    If the user is a superuser, they can delete the exit and it results in
    the expected state (exit is deleted and no longer referenced by the
    source, target or owner).
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1 name", "room description", user)
    room2_uuid = logic.add_room("room2 name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    assert exit_id in room1["_meta"]["exits_out"]
    assert exit_id in room2["_meta"]["exits_in"]
    assert exit_id in user["_meta"]["owns"]
    assert logic.delete_exit(exit_id, otheruser) is True
    assert exit_id not in database.OBJECTS
    assert exit_id not in room1["_meta"]["exits_out"]
    assert exit_id not in room2["_meta"]["exits_in"]
    assert exit_id not in user["_meta"]["owns"]


def test_delete_exit_as_owner():
    """
    If the user is the owner, they can delete the exit and it results in
    the expected state (exit is deleted and no longer referenced by the
    source, target or owner).
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1 name", "room description", user)
    room2_uuid = logic.add_room("room2 name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    assert exit_id in room1["_meta"]["exits_out"]
    assert exit_id in room2["_meta"]["exits_in"]
    assert exit_id in user["_meta"]["owns"]
    assert logic.delete_exit(exit_id, user) is True
    assert exit_id not in database.OBJECTS
    assert exit_id not in room1["_meta"]["exits_out"]
    assert exit_id not in room2["_meta"]["exits_in"]
    assert exit_id not in user["_meta"]["owns"]


def test_delete_exit_as_forced():
    """
    If called with the force flag, they can delete the exit and it results in
    the expected state (exit is deleted and no longer referenced by the
    source, target or owner).
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1 name", "room description", user)
    room2_uuid = logic.add_room("room2 name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    assert exit_id in room1["_meta"]["exits_out"]
    assert exit_id in room2["_meta"]["exits_in"]
    assert exit_id in user["_meta"]["owns"]
    assert logic.delete_exit(exit_id, otheruser, force=True) is True
    assert exit_id not in database.OBJECTS
    assert exit_id not in room1["_meta"]["exits_out"]
    assert exit_id not in room2["_meta"]["exits_in"]
    assert exit_id not in user["_meta"]["owns"]
