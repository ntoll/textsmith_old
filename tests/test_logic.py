"""
Tests for the stateless functions which encapsulate the behaviour of the
TextSmith platform.
"""
import time
import pytest
import asynctest
from quart import Quart
from textsmith import logic
from textsmith import database


app = Quart(__name__)


def setup_function():
    """
    Setup a clean database state.
    Invoked for every test function in the module.
    """
    database.OBJECTS = {}
    database.USERS = {}
    database.CONNECTIONS = {}


def test_make_uuid():
    """
    Ensure the UUID is expressed as a string.
    """
    uuid = logic.make_uuid()
    assert isinstance(uuid, str)


def test_is_valid_object_name():
    """
    Object names must be alphanumeric.
    """
    assert logic.is_valid_object_name("ThisIsValid123") is True
    assert logic.is_valid_object_name("This isn't valid.") is False


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
    new_uuid = logic.add_object("objectname", "object description", user)
    assert new_uuid in database.OBJECTS
    new_obj = database.OBJECTS[new_uuid]
    assert new_obj["_meta"]["fqn"] in database.FQNS
    assert new_uuid in user["_meta"]["owns"]


def test_add_object_invalid_name():
    """
    Ensure the object has a valid name.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    with pytest.raises(ValueError):
        new_uuid = logic.add_object("object name", "object description", user)


def test_add_object_duplicate_name():
    """
    Ensure the object has a unique fqn.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    assert new_uuid in database.OBJECTS
    assert new_uuid in user["_meta"]["owns"]
    with pytest.raises(ValueError):
        new_uuid = logic.add_object("objectname", "object description", user)


def test_add_room():
    """
    Ensure a room is added to the database.OBJECTS dictionary.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("roomname", "room description", user)
    assert new_uuid in database.OBJECTS
    new_room = database.OBJECTS[new_uuid]
    assert new_room["_meta"]["fqn"] in database.FQNS
    assert new_uuid in user["_meta"]["owns"]


def test_add_room_invalid_name():
    """
    Ensure the room has a valid name.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    with pytest.raises(ValueError):
        new_uuid = logic.add_room("room name", "room description", user)


def test_add_room_duplicate_name():
    """
    Ensure the room has a unique fqn.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("roomname", "room description", user)
    assert new_uuid in database.OBJECTS
    assert new_uuid in user["_meta"]["owns"]
    with pytest.raises(ValueError):
        new_uuid = logic.add_room("roomname", "room description", user)


def test_add_exit():
    """
    Ensure an exit is added to the database.OBJECTS dictionary.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("sourceroom", "room description", user)
    destination_uuid = logic.add_room("destinationroom", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    new_uuid = logic.add_exit("exitname", "description", user, source,
                              destination)
    assert new_uuid in database.OBJECTS
    new_exit = database.OBJECTS[new_uuid]
    assert new_exit["_meta"]["fqn"] in database.FQNS
    assert new_uuid in user["_meta"]["owns"]
    assert new_uuid in source["_meta"]["exits_out"]
    assert new_uuid in destination["_meta"]["exits_in"]


def test_add_exit_invalid_name():
    """
    Ensure the exit has a valid name.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    with pytest.raises(ValueError):
        new_uuid = logic.add_exit("exit name", "room description", user, "to",
                                  "from")


def test_add_exit_duplicate_name():
    """
    Ensure an exit has a unique fqn.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("sourceroom", "room description", user)
    destination_uuid = logic.add_room("destinationroom", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    new_uuid = logic.add_exit("exitname", "description", user, source,
                              destination)
    assert new_uuid in database.OBJECTS
    assert new_uuid in user["_meta"]["owns"]
    assert new_uuid in source["_meta"]["exits_out"]
    assert new_uuid in destination["_meta"]["exits_in"]
    with pytest.raises(ValueError):
        new_uuid = logic.add_exit("exitname", "description", user, source,
                                  destination)


def test_add_exit_connect_room_to_itself():
    """
    Ensure an exit must start/end in different rooms. ;-)
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("sourceroom", "room description", user)
    source = database.OBJECTS[source_uuid]
    with pytest.raises(ValueError):
        new_uuid = logic.add_exit("exitname", "description", user, source,
                                  source)


def test_add_exit_user_not_in_allow():
    """
    An exit cannot be added where the destination room as an "allow" list
    whose members don't include the user creating the exit. Such a user
    wouldn't be allowed into the room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("sourceroom", "room description", user)
    destination_uuid = logic.add_room("destinationroom", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    destination['_meta']['allow'].append(logic.make_uuid)
    with pytest.raises(PermissionError):
        new_uuid = logic.add_exit("exitname", "description", user, source,
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
    source_uuid = logic.add_room("sourceroom", "room description", user)
    destination_uuid = logic.add_room("destinationroom", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    destination['_meta']['exclude'].append(user_uuid)
    with pytest.raises(PermissionError):
        new_uuid = logic.add_exit("exitname", "description", user, source,
                                  destination)


def test_add_exit_duplicate_source_destination():
    """
    An exit cannot be added where there is already an exit from the source
    room to the destination room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    source_uuid = logic.add_room("sourceroom", "room description", user)
    destination_uuid = logic.add_room("destinationroom", "room description",
                                      user)
    source = database.OBJECTS[source_uuid]
    destination = database.OBJECTS[destination_uuid]
    duplicate_uuid = logic.add_exit("exitname", "description", user, source,
                                    destination)
    with pytest.raises(KeyError):
        new_uuid = logic.add_exit("exitname2", "description", user, source,
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
    # User is in the USERS and FQNS lookup tables.
    assert user["_meta"]["name"] in database.USERS
    assert user["_meta"]["fqn"] in database.FQNS


def test_add_user_invalid_name():
    """
    Ensure the exit has a valid name.
    """
    with pytest.raises(ValueError):
        user_uuid = logic.add_user("user name", "description", "password",
                                   "mail@example.com")


def test_add_user_duplicate():
    """
    It's not possible to add a user if the desired username is already taken.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    with pytest.raises(ValueError):
        duplicate_uuid = logic.add_user("username", "description", "password",
                                        "mail@example.com")


def test_get_object_from_context_no_name():
    """
    If the passed in name is None, an empty list is returned since there's
    nothing to search for in the context. This may happen if the direct or
    indirect objects have not been specified in the parser layer.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room_id = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_id]
    assert logic.get_object_from_context(None, room, user) == []


def test_get_object_from_room_by_fqn():
    """
    Ensure objects with matching names or aliases are returned if they are
    contained within the referenced room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room_id = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_id]
    obj1_id = logic.add_object("obj1name", "object description", user)
    obj2_id = logic.add_object("obj2name", "object description", user)
    obj3_id = logic.add_object("obj3name", "object description", user)
    obj2 = database.OBJECTS[obj2_id]
    obj2["_meta"]["alias"].append("obj1name")  # Just for testing.
    room["_meta"]["contents"] = [obj1_id, obj2_id, obj3_id, ]
    user["_meta"]["inventory"] = []
    result = logic.get_object_from_context("username/obj1name", room, user)
    assert len(result) == 1
    assert result[0]["_meta"]["uuid"] == obj1_id


def test_get_object_from_room_by_name():
    """
    Ensure objects with matching names or aliases are returned if they are
    contained within the referenced room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room_id = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_id]
    obj1_id = logic.add_object("obj1name", "object description", user)
    obj2_id = logic.add_object("obj2name", "object description", user)
    obj3_id = logic.add_object("obj3name", "object description", user)
    obj2 = database.OBJECTS[obj2_id]
    obj2["_meta"]["alias"].append("obj1name")  # Just for testing.
    room["_meta"]["contents"] = [obj1_id, obj2_id, obj3_id, ]
    user["_meta"]["inventory"] = []
    result = logic.get_object_from_context("obj1name", room, user)
    assert len(result) == 2
    assert result[0]["_meta"]["uuid"] == obj1_id
    assert result[1]["_meta"]["uuid"] == obj2_id


def test_get_object_from_user_by_fqn():
    """
    Ensure objects with matching names or aliases are returned if they are
    contained within the referenced user's inventory.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room_id = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_id]
    obj1_id = logic.add_object("obj1name", "object description", user)
    obj2_id = logic.add_object("obj2name", "object description", user)
    obj3_id = logic.add_object("obj3name", "object description", user)
    obj2 = database.OBJECTS[obj2_id]
    obj2["_meta"]["alias"].append("obj1name")  # Just for testing.
    result = logic.get_object_from_context("username/obj1name", room, user)
    assert len(result) == 1
    assert result[0]["_meta"]["uuid"] == obj1_id


def test_get_object_from_user_by_name():
    """
    Ensure objects with matching names or aliases are returned if they are
    contained within the referenced user's inventory.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room_id = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_id]
    obj1_id = logic.add_object("obj1name", "object description", user)
    obj2_id = logic.add_object("obj2name", "object description", user)
    obj3_id = logic.add_object("obj3name", "object description", user)
    obj2 = database.OBJECTS[obj2_id]
    obj2["_meta"]["alias"].append("obj1name")  # Just for testing.
    result = logic.get_object_from_context("obj1name", room, user)
    assert len(result) == 2
    assert result[0]["_meta"]["uuid"] == obj1_id
    assert result[1]["_meta"]["uuid"] == obj2_id


def test_is_owner():
    """
    The is_owner function returns True if the referenced user is the owner of
    the referenced object. Otherwise False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otherobj_uuid = logic.add_object("objectname", "object description",
                                     otheruser)
    otherobj = database.OBJECTS[otherobj_uuid]
    assert logic.is_owner(new_obj, user) is True
    assert logic.is_owner(otherobj, user) is False


def test_is_visible_superuser():
    """
    Returns True if the user is a superuser.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    new_uuid = logic.add_object("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    assert logic.is_visible(new_obj, otheruser) is True


def test_is_visible_owner():
    """
    Returns True if the user is the object's owner.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    assert logic.is_visible(new_obj, user) is True


def test_is_visible_non_owner():
    """
    Returns the value of "public" meta attribute for all other users.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    new_obj["_meta"]["public"] = False
    assert logic.is_visible(new_obj, otheruser) is False


def test_set_visibile_not_object():
    """
    Only objects which are typeof "object" can have their visibility changed.
    Users, rooms and exits are always public.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    with pytest.raises(TypeError):
        logic.set_visible(new_obj, False, user)


def test_set_visibile_superuser():
    """
    Sets visibility if superuser.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    new_uuid = logic.add_object("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    logic.set_visible(new_obj, False, otheruser)
    assert new_obj["_meta"]["public"] is False


def test_set_visible_owner():
    """
    Sets visibility if object owner.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    logic.set_visible(new_obj, False, user)
    assert new_obj["_meta"]["public"] is False


def test_set_visible_non_owner():
    """
    Cannot set visibility if user is not the object owner.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    new_obj = database.OBJECTS[new_uuid]
    with pytest.raises(PermissionError):
        logic.set_visible(new_obj, False, otheruser)


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
    new_uuid = logic.add_room("roomname", "room description", user)
    assert logic.delete_object(new_uuid, user) is False


def test_delete_object_user_not_owner():
    """
    It's not possible to delete an object if the user isn't the object's owner.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
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
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    assert logic.delete_object(new_uuid, otheruser) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]
    assert obj["_meta"]["fqn"] not in user["_meta"]["fqns"]
    assert obj["_meta"]["fqn"] not in database.FQNS


def test_delete_object_as_owner():
    """
    It's possible to delete the object if the user is the object's owner.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    assert logic.delete_object(new_uuid, user) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]
    assert obj["_meta"]["fqn"] not in user["_meta"]["fqns"]
    assert obj["_meta"]["fqn"] not in database.FQNS


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
    new_uuid = logic.add_object("objectname", "object description", user)
    assert logic.delete_room(new_uuid, user) is False


def test_delete_room_not_owner():
    """
    If the user isn't the owner of the room, they can't delete it.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("roomname", "room description", user)
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
    new_uuid = logic.add_room("roomname", "room description", user)
    otherroom_uuid = logic.add_room("othername", "room description", user)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    # Add objects to the room, place users in there too and make some exits.
    new_room = database.OBJECTS[new_uuid]
    other_room = database.OBJECTS[otherroom_uuid]
    into = logic.add_exit("exit1", "description", user, new_room, other_room)
    outfrom = logic.add_exit("exit2", "description", user, other_room,
                             new_room)
    obj_uuid = logic.add_object("objectname", "object description", user)
    room = database.OBJECTS[new_uuid]
    room["_meta"]["contents"].append(obj_uuid)
    room["_meta"]["contents"].append(user_uuid)
    # Delete the room and check all the expected state.
    assert logic.delete_room(new_uuid, otheruser) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]
    assert room["_meta"]["fqn"] not in user["_meta"]["fqns"]
    assert room["_meta"]["fqn"] not in database.FQNS
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
    new_uuid = logic.add_room("roomname", "room description", user)
    otherroom_uuid = logic.add_room("othername", "room description", user)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["location"] = logic.make_uuid()
    # Add objects to the room, place users in there too and make some exits.
    new_room = database.OBJECTS[new_uuid]
    other_room = database.OBJECTS[otherroom_uuid]
    into = logic.add_exit("exit1", "description", user, new_room, other_room)
    outfrom = logic.add_exit("exit2", "description", user, other_room,
                             new_room)
    obj_uuid = logic.add_object("objectname", "object description", user)
    room = database.OBJECTS[new_uuid]
    room["_meta"]["contents"].append(obj_uuid)
    room["_meta"]["contents"].append(otheruser_uuid)
    # Delete the room and check all the expected state.
    assert logic.delete_room(new_uuid, user) is True
    assert new_uuid not in database.OBJECTS
    assert new_uuid not in user["_meta"]["owns"]
    assert room["_meta"]["fqn"] not in user["_meta"]["fqns"]
    assert room["_meta"]["fqn"] not in database.FQNS
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
    new_uuid = logic.add_object("objectname", "object description", user)
    assert logic.delete_exit(new_uuid, user) is False


def test_delete_exit_not_owner():
    """
    If the user isn't the owner of the room, they cannot delete it.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
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
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    otheruser["_meta"]["superuser"] = True
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    exit = database.OBJECTS[exit_id]
    assert exit_id in room1["_meta"]["exits_out"]
    assert exit_id in room2["_meta"]["exits_in"]
    assert exit_id in user["_meta"]["owns"]
    assert logic.delete_exit(exit_id, otheruser) is True
    assert exit_id not in database.OBJECTS
    assert exit_id not in room1["_meta"]["exits_out"]
    assert exit_id not in room2["_meta"]["exits_in"]
    assert exit_id not in user["_meta"]["owns"]
    assert exit["_meta"]["fqn"] not in user["_meta"]["fqns"]
    assert exit["_meta"]["fqn"] not in database.FQNS


def test_delete_exit_as_owner():
    """
    If the user is the owner, they can delete the exit and it results in
    the expected state (exit is deleted and no longer referenced by the
    source, target or owner).
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    exit = database.OBJECTS[exit_id]
    assert exit_id in room1["_meta"]["exits_out"]
    assert exit_id in room2["_meta"]["exits_in"]
    assert exit_id in user["_meta"]["owns"]
    assert logic.delete_exit(exit_id, user) is True
    assert exit_id not in database.OBJECTS
    assert exit_id not in room1["_meta"]["exits_out"]
    assert exit_id not in room2["_meta"]["exits_in"]
    assert exit_id not in user["_meta"]["owns"]
    assert exit["_meta"]["fqn"] not in user["_meta"]["fqns"]
    assert exit["_meta"]["fqn"] not in database.FQNS


def test_delete_exit_as_forced():
    """
    If called with the force flag, they can delete the exit and it results in
    the expected state (exit is deleted and no longer referenced by the
    source, target or owner).
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    exit = database.OBJECTS[exit_id]
    assert exit_id in room1["_meta"]["exits_out"]
    assert exit_id in room2["_meta"]["exits_in"]
    assert exit_id in user["_meta"]["owns"]
    assert logic.delete_exit(exit_id, otheruser, force=True) is True
    assert exit_id not in database.OBJECTS
    assert exit_id not in room1["_meta"]["exits_out"]
    assert exit_id not in room2["_meta"]["exits_in"]
    assert exit_id not in user["_meta"]["owns"]
    assert exit["_meta"]["fqn"] not in user["_meta"]["fqns"]
    assert exit["_meta"]["fqn"] not in database.FQNS


@pytest.mark.asyncio
async def test_move_no_obj():
    """
    Cannot move, if the referenced object to move does not exist.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    obj["_meta"]["location"] = room1_uuid
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    with pytest.raises(ValueError):
        await logic.move(logic.make_uuid(), exit_id, user_uuid)


@pytest.mark.asyncio
async def test_move_no_exit():
    """
    Cannot move, if the referenced exit does not exist.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    obj["_meta"]["location"] = room1_uuid
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    with pytest.raises(ValueError):
        await logic.move(user_uuid, logic.make_uuid(), user_uuid)


@pytest.mark.asyncio
async def test_move_no_user():
    """
    Cannot move, if the referenced user does not exist.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    obj["_meta"]["location"] = room1_uuid
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    with pytest.raises(ValueError):
        await logic.move(user_uuid, exit_id, logic.make_uuid())


@pytest.mark.asyncio
async def test_move_user_not_owner():
    """
    If the referenced user requesting the move is not the owner of the object
    to be moved, then fail.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    obj["_meta"]["location"] = room1_uuid
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    with pytest.raises(KeyError):
        await logic.move(user_uuid, exit_id, otheruser_uuid)


@pytest.mark.asyncio
async def test_move_wrong_typeof():
    """
    The object may only be moved if it is a typeof "object" or "user".
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    obj["_meta"]["location"] = room1_uuid
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    with pytest.raises(TypeError):
        await logic.move(room1_uuid, exit_id, user_uuid)


@pytest.mark.asyncio
async def test_move_obj_not_in_source_room():
    """
    For the object to move via the exit, it MUST be in the source room
    associated with the exit.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    obj["_meta"]["location"] = logic.make_uuid()
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    with pytest.raises(ValueError):
        await logic.move(new_uuid, exit_id, user_uuid)


@pytest.mark.asyncio
async def test_move_obj_owner_not_in_allow_of_destination():
    """
    If the destination room associated with the exit has an "allow" list, and
    the object's owner is NOT in the list, then it cannot be moved.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room1["_meta"]["contents"].append(new_uuid)
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    room2["_meta"]["allow"].append(logic.make_uuid())
    with pytest.raises(PermissionError):
        await logic.move(new_uuid, exit_id, user_uuid)


@pytest.mark.asyncio
async def test_move_obj_in_exclude_list_of_destination():
    """
    If the object's owner is on the destination room's exclude list, then
    the object cannot be moved.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room1["_meta"]["contents"].append(new_uuid)
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    room2["_meta"]["exclude"].append(user_uuid)
    with pytest.raises(PermissionError):
        await logic.move(new_uuid, exit_id, user_uuid)


@pytest.mark.asyncio
async def test_move_object():
    """
    Assuming all constrains are met, change the state of the database to
    reflect the move.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room1["_meta"]["contents"].append(new_uuid)
    room1["_meta"]["fqns"].append(obj["_meta"]["fqn"])
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    with asynctest.patch("textsmith.logic.emit_to_room") as mock_etr:
        await logic.move(new_uuid, exit_id, user_uuid)
        assert mock_etr.call_count == 2
    assert new_uuid not in room1["_meta"]["contents"]
    assert obj["_meta"]["fqn"] not in room1["_meta"]["fqns"]
    assert new_uuid in room2["_meta"]["contents"]
    assert obj["_meta"]["fqn"] in room2["_meta"]["fqns"]


@pytest.mark.asyncio
async def test_move_user():
    """
    Assuming all constrains are met, change the state of the database to
    reflect the move.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    room1 = database.OBJECTS[room1_uuid]
    room1["_meta"]["contents"].append(user_uuid)
    room1["_meta"]["fqns"].append(user["_meta"]["fqn"])
    room2 = database.OBJECTS[room2_uuid]
    exit_id = logic.add_exit("exit1", "description", user, room1, room2)
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu, \
            asynctest.patch("textsmith.logic.emit_to_room") as mock_etr:
        await logic.move(user_uuid, exit_id, user_uuid)
        assert mock_etu.call_count == 1
        assert mock_etr.call_count == 2
    assert user_uuid not in room1["_meta"]["contents"]
    assert user["_meta"]["fqn"] not in room1["_meta"]["fqns"]
    assert user_uuid in room2["_meta"]["contents"]
    assert user["_meta"]["fqn"] in room2["_meta"]["fqns"]


@pytest.mark.asyncio
async def test_teleport_non_existent_destination():
    """
    If the destination does not exist then the teleport fails.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    fqn = user["_meta"]["fqn"]
    room1_uuid = logic.add_room("room1name", "room description", user)
    with pytest.raises(ValueError):
        await logic.teleport(user_uuid, "foo/bar")


@pytest.mark.asyncio
async def test_teleport_non_existent_user():
    """
    If the user does not exist, then the teleport fails.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    with pytest.raises(ValueError):
        await logic.teleport("foo/bar", room1_uuid)


@pytest.mark.asyncio
async def test_teleport_to_current_location():
    """
    A user cannot teleport into the room they're currently in.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    user["_meta"]["location"] = room1_uuid
    room1 = database.OBJECTS[room1_uuid]
    room1["_meta"]["contents"].append(user_uuid)
    fqn = room1["_meta"]["fqn"]
    with pytest.raises(ValueError):
        await logic.teleport(user_uuid, fqn)


@pytest.mark.asyncio
async def test_teleport():
    """
    Ensure a user can teleport to a new location.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    room2_uuid = logic.add_room("room2name", "room description", user)
    user["_meta"]["location"] = room1_uuid
    room1 = database.OBJECTS[room1_uuid]
    room2 = database.OBJECTS[room2_uuid]
    room1["_meta"]["contents"].append(user_uuid)
    room1["_meta"]["fqns"].append(user["_meta"]["fqn"])
    fqn = room2["_meta"]["fqn"]
    await logic.teleport(user_uuid, fqn)
    assert user_uuid not in room1["_meta"]["contents"]
    assert user["_meta"]["fqn"] not in room1["_meta"]["fqns"]
    assert user_uuid in room2["_meta"]["contents"]
    assert user["_meta"]["fqn"] in room2["_meta"]["fqns"]
    assert user["_meta"]["location"] == room2_uuid


def test_build():
    """
    Calling build with the expected arguments results in the expected room
    and exits to have been build.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room1_uuid = logic.add_room("room1name", "room description", user)
    user["_meta"]["location"] = room1_uuid
    new_room_id = logic.build("newroom", "a room description", user,
                              exit_name="exit", return_name="return",
                              exit_description="exit description",
                              return_description="return description")
    assert len(database.OBJECTS) == 5
    assert len(user["_meta"]["owns"]) == 5
    assert len(user["_meta"]["fqns"]) == 5
    assert new_room_id in database.OBJECTS
    room1 = database.OBJECTS[room1_uuid]
    new_room = database.OBJECTS[new_room_id]
    assert len(new_room["_meta"]["exits_out"]) == 1
    assert len(room1["_meta"]["exits_out"]) == 1
    assert len(new_room["_meta"]["exits_in"]) == 1
    assert len(room1["_meta"]["exits_in"]) == 1
    assert new_room["_meta"]["exits_out"][0] == room1["_meta"]["exits_in"][0]
    assert new_room["_meta"]["exits_in"][0] == room1["_meta"]["exits_out"][0]


def test_clone_not_an_object():
    """
    It's only possible to clone things that are just "objects" (not rooms,
    exits or users).
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("roomname", "room description", user)
    with pytest.raises(ValueError):
        clone_id = logic.clone(new_uuid, "my clone", user)


def test_clone_not_a_public_object():
    """
    It's only possible to clone objects that are public.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    obj["_meta"]["public"] = False
    with pytest.raises(PermissionError):
        clone_id = logic.clone(new_uuid, "my clone", otheruser)


def test_clone():
    """
    Check the state of the source object is correctly cloned onto a new
    object belonging to the referenced user.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@example.com")
    otheruser = database.OBJECTS[otheruser_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    clone_id = logic.clone(new_uuid, "myclone", otheruser)
    clone = database.OBJECTS[clone_id]
    for k, v in clone.items():
        if k != "_meta":
            assert obj[k] == clone[k]
    meta = clone["_meta"]
    assert meta["uuid"] == clone_id
    assert meta["name"] == "myclone"
    assert meta["fqn"] == "otherusername/myclone"
    assert meta["owner"] == otheruser_uuid
    assert meta["typeof"] == "object"
    assert meta["public"] == obj["_meta"]["public"]


def test_take_not_an_object():
    """
    If the user is trying to take something that's not an object, then return
    False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_room("roomname", "room description", user)
    assert logic.take(new_uuid, user) is False


def test_take_not_in_location():
    """
    If the object to be taken isn't in the user's current location, then
    return False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    new_room = logic.add_room("roomname", "room description", user)
    user["_meta"]["location"] = new_room
    new_uuid = logic.add_object("objectname", "object description", user)
    assert logic.take(new_uuid, user) is False


def test_take():
    """
    Assuming all the constraints are met, a taken object is removed from the
    room and put into the user's inventory.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@example.com")
    user = database.OBJECTS[user_uuid]
    room_id = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_id]
    user["_meta"]["location"] = room_id
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    room["_meta"]["contents"].append(new_uuid)
    room["_meta"]["fqns"].append(obj["_meta"]["fqn"])
    assert logic.take(new_uuid, user) is True
    assert new_uuid in user["_meta"]["inventory"]
    assert new_uuid not in room["_meta"]["contents"]
    assert obj["_meta"]["fqn"] not in room["_meta"]["fqns"]


def test_give_object_not_in_inventory():
    """
    You can't give an object you're not holding.
    """
    user1_uuid = logic.add_user("username1", "description", "password",
                                "mail@eample.com")
    user1 = database.OBJECTS[user1_uuid]
    user2_uuid = logic.add_user("username2", "description", "password",
                                "mail@example.com")
    new_uuid = logic.add_object("objectname", "object description", user1)
    user1["_meta"]["inventory"].remove(new_uuid)
    assert logic.give(new_uuid, user1, user2_uuid) is False


def test_give_something_not_an_object():
    """
    You can't give something that's not an object.
    """
    user1_uuid = logic.add_user("username1", "description", "password",
                                "mail@eample.com")
    user1 = database.OBJECTS[user1_uuid]
    user2_uuid = logic.add_user("username2", "description", "password",
                                "mail@example.com")
    new_uuid = logic.add_room("roomname", "room description", user1)
    user1["_meta"]["inventory"].append(new_uuid)
    assert logic.give(new_uuid, user1, user2_uuid) is False


def test_give_users_not_in_same_location():
    """
    You can only give an object to someone else in the same location as you.
    """
    user1_uuid = logic.add_user("username1", "description", "password",
                                "mail@eample.com")
    user1 = database.OBJECTS[user1_uuid]
    user1["_meta"]["location"] = logic.make_uuid()
    user2_uuid = logic.add_user("username2", "description", "password",
                                "mail@example.com")
    user2 = database.OBJECTS[user2_uuid]
    user2["_meta"]["location"] = logic.make_uuid()
    new_uuid = logic.add_object("objectname", "object description", user1)
    assert logic.give(new_uuid, user1, user2_uuid) is False


def test_give():
    """
    Assuming all the constraints are met, remove the object from one user's
    inventory and add it to another user's inventory.
    """
    location = logic.make_uuid()
    user1_uuid = logic.add_user("username1", "description", "password",
                                "mail@eample.com")
    user1 = database.OBJECTS[user1_uuid]
    user1["_meta"]["location"] = location
    user2_uuid = logic.add_user("username2", "description", "password",
                                "mail@example.com")
    user2 = database.OBJECTS[user2_uuid]
    user2["_meta"]["location"] = location
    new_uuid = logic.add_object("objectname", "object description", user1)
    assert logic.give(new_uuid, user1, user2_uuid) is True
    assert new_uuid not in user1["_meta"]["inventory"]
    assert new_uuid in user2["_meta"]["inventory"]


def test_drop_object_not_in_inventory():
    """
    It's only possible to drop an object if it's in the user's inventory.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    user["_meta"]["inventory"].remove(new_uuid)
    assert logic.drop(new_uuid, user) is False


def test_drop():
    """
    Dropping an object removes it from the user's inventory and adds it to the
    contents of the room in which the user is situated.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_id = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_id]
    user["_meta"]["location"] = room_id
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    assert logic.drop(new_uuid, user) is True
    assert new_uuid not in user["_meta"]["inventory"]
    assert new_uuid in room["_meta"]["contents"]
    assert obj["_meta"]["fqn"] in room["_meta"]["fqns"]


@pytest.mark.asyncio
async def test_look_object():
    """
    Ensure a message is sent to the user containing the name, alias and
    description of the object.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    obj["_meta"]["alias"] = ["alias1", "alias2", ]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.look(new_uuid, user)
        expected = ("## objectname\n\n"
                    "[**username/objectname**]\n\n\n"
                    "Alias: alias1, alias2\n\n\n"
                    "object description\n\n")
        mock_etu.assert_called_once_with(user_uuid, expected)


@pytest.mark.asyncio
async def test_look_room():
    """
    Ensure a message is sent to the user containing name, alias, description,
    contents (both @user and object) and exits.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    room["_meta"]["alias"] = ["alias1", "alias2", ]
    room["_meta"]["contents"] = [user_uuid, new_uuid, ]
    otherroom_uuid = logic.add_room("otherroomname", "room description", user)
    otherroom = database.OBJECTS[otherroom_uuid]
    exit_id = logic.add_exit("exitname", "exit description", user, room,
                             otherroom)
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.look(room_uuid, user)
        expected = ("## roomname\n\n"
                    "[**username/roomname**]\n\n\n"
                    "Alias: alias1, alias2\n\n\n"
                    "room description\n\n\n"
                    "**You can see**: username, objectname\n\n"
                    "**Exits**: exitname\n")
        mock_etu.assert_called_once_with(user_uuid, expected)


@pytest.mark.asyncio
async def test_look_exit():
    """
    Ensure a message is sent to the user containing name, alias, description
    and destination name.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    otherroom_uuid = logic.add_room("otherroomname", "room description", user)
    otherroom = database.OBJECTS[otherroom_uuid]
    exit_id = logic.add_exit("exitname", "exit description", user, room,
                             otherroom)
    exit = database.OBJECTS[exit_id]
    exit["_meta"]["alias"] = ["alias1", "alias2", ]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.look(exit_id, user)
        expected = ("## exitname\n\n"
                    "[**username/exitname**]\n\n\n"
                    "Alias: alias1, alias2\n\n\n"
                    "exit description\n\n\n"
                    'This leads to "otherroomname".\n')
        mock_etu.assert_called_once_with(user_uuid, expected)


@pytest.mark.asyncio
async def test_look_user():
    """
    Ensure a message is sent to the user containing name, alias, description
    and destination name.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    user["_meta"]["alias"] = ["alias1", "alias2", ]
    new_uuid = logic.add_object("objectname", "object description", user)
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.look(user_uuid, user)
        expected = ("## username\n\n"
                    "[**username/username**]\n\n\n"
                    "Alias: alias1, alias2\n\n\n"
                    "description\n\n\n"
                    "They are carrying: objectname\n")
        mock_etu.assert_called_once_with(user_uuid, expected)


@pytest.mark.asyncio
async def test_detail_object():
    """
    Ensure a raw HTML message is sent to the user containing details of the
    object.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    obj["_meta"]["alias"] = ["alias1", "alias2", ]
    obj["foo"] = "bar"
    fqn = obj["_meta"]["fqn"]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.detail(fqn, user)
        assert mock_etu.call_count == 1
        assert mock_etu.call_args_list[0][1] == {"raw": True}  # Raw HTML.


@pytest.mark.asyncio
async def test_detail_room():
    """
    Ensure a raw HTML message is sent to the user containing details of the
    room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    room["_meta"]["alias"] = ["alias1", "alias2", ]
    room["_meta"]["contents"] = [user_uuid, new_uuid, ]
    room["_meta"]["allow"] = [user_uuid, ]
    room["_meta"]["exclude"] = [user_uuid, ]
    otherroom_uuid = logic.add_room("otherroomname", "room description", user)
    otherroom = database.OBJECTS[otherroom_uuid]
    exit_id = logic.add_exit("exitname", "exit description", user, room,
                             otherroom)
    fqn = room["_meta"]["fqn"]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.detail(fqn, user)
        assert mock_etu.call_count == 1
        assert mock_etu.call_args_list[0][1] == {"raw": True}  # Raw HTML.


@pytest.mark.asyncio
async def test_detail_exit():
    """
    Ensure a raw HTML message is sent to the user containing details of the
    exit.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    otherroom_uuid = logic.add_room("otherroomname", "room description", user)
    otherroom = database.OBJECTS[otherroom_uuid]
    exit_id = logic.add_exit("exitname", "exit description", user, room,
                             otherroom)
    exit = database.OBJECTS[exit_id]
    exit["_meta"]["alias"] = ["alias1", "alias2", ]
    exit["foo"] = "bar"
    fqn = exit["_meta"]["fqn"]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.detail(fqn, user)
        assert mock_etu.call_count == 1
        assert mock_etu.call_args_list[0][1] == {"raw": True}  # Raw HTML.


@pytest.mark.asyncio
async def test_detail_user():
    """
    Ensure a raw HTML message is sent to the user containing the code details
    of the object.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    user["_meta"]["alias"] = ["alias1", "alias2", ]
    user["foo"] = "bar"
    user["_meta"]["last_login"] = time.time()
    room_uuid = logic.add_room("roomname", "room description", user)
    user["_meta"]["location"] = room_uuid
    fqn = user["_meta"]["fqn"]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        async with app.app_context():
            await logic.detail(fqn, user)
        assert mock_etu.call_count == 1
        assert mock_etu.call_args_list[0][1] == {"raw": True}  # Raw HTML.


def test_add_alias():
    """
    Users who own an object are allowed to add an alias.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    assert logic.add_alias(new_uuid, user, "aliasname") is True
    obj = database.OBJECTS[new_uuid]
    assert "aliasname" in obj["_meta"]["alias"]


def test_add_alias_fail():
    """
    An incorrect call to add_alias returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    # Invalid name.
    assert logic.add_alias(new_uuid, user, "alias name") is False


def test_remove_alias():
    """
    Users who own an object are allowed to remove an alias.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    obj["_meta"]["alias"] = ["aliasname", ]
    assert logic.remove_alias(new_uuid, user, "aliasname") is True
    assert "aliasname" not in obj["_meta"]["alias"]


def test_remove_alias_fail():
    """
    An incorrect call to remove_alias returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    # Alias does not exist.
    assert logic.remove_alias(new_uuid, user, "aliasname") is False


def test_set_attribute():
    """
    A user who owns an object can add arbtrary attributes to it.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    assert logic.set_attribute(new_uuid, user, "attr", "value") is True
    obj = database.OBJECTS[new_uuid]
    assert obj["attr"] == "value"


def test_set_attribute_fails():
    """
    An incorrect call to set_attribute returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    # Invalid attribute name (contains spaces).
    assert logic.set_attribute(new_uuid, user, "attr name", "hello") is False


def test_set_attribute_not_json_serializable():
    """
    An incorrect call to set_attribute returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    # Value is not JSON serializable.
    assert logic.set_attribute(new_uuid, user, "attrname", set()) is False


def test_remove_attribute():
    """
    A user who owns an object can remove arbitrary attributes from it so long
    as they are not on the "reserved" list.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    obj = database.OBJECTS[new_uuid]
    obj["attr"] = "value"
    assert logic.remove_attribute(new_uuid, user, "attr") is True
    assert "attr" not in obj


def test_remove_attribute_on_exclude_list():
    """
    Users cannot remove attributes on the "reserved" list.
    """
    reserved = ["_meta", "description", "leave_user", "leave_room",
                "arrive_room", ]
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    new_uuid = logic.add_object("objectname", "object description", user)
    for attr in reserved:
        assert logic.remove_attribute(new_uuid, user, attr) is False


def test_add_allow():
    """
    Users who own a room can add usernames to the "allow" list.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@eample.com")
    assert logic.add_allow(room_uuid, user, "otherusername") is True
    assert otheruser_uuid in room["_meta"]["allow"]


def test_add_allow_fail():
    """
    A problem call to add_allow returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    assert logic.add_allow(room_uuid, user, "otherusername") is False


def test_remove_allow():
    """
    Users who own a room can remove usernames from the "allow" list.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@eample.com")
    room["_meta"]["allow"].append(otheruser_uuid)
    assert logic.remove_allow(room_uuid, user, "otherusername") is True
    assert otheruser_uuid not in room["_meta"]["allow"]


def test_remove_allow_fail():
    """
    A problem call to remove_allow returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    assert logic.remove_allow(room_uuid, user, "otherusername") is False


def test_add_exclude():
    """
    Users who own a room can add usernames to the "exclude" list.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@eample.com")
    assert logic.add_exclude(room_uuid, user, "otherusername") is True
    assert otheruser_uuid in room["_meta"]["exclude"]


def test_add_exclude_fail():
    """
    A problem call to add_exclude returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    assert logic.add_exclude(room_uuid, user, "otherusername") is False


def test_remove_exlude():
    """
    Users who own a room can remove usernames from the "exclude" list.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    otheruser_uuid = logic.add_user("otherusername", "description", "password",
                                    "mail@eample.com")
    room["_meta"]["exclude"].append(otheruser_uuid)
    assert logic.remove_exclude(room_uuid, user, "otherusername") is True
    assert otheruser_uuid not in room["_meta"]["exclude"]


def test_remove_exclude_fail():
    """
    A problem call to remove_exclude returns False.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    assert logic.remove_exclude(room_uuid, user, "otherusername") is False


@pytest.mark.asyncio
async def test_emit_to_room():
    """
    Emitting to the room simply emits the passed in message to all users
    currently in the room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    room["_meta"]["contents"] = [user_uuid, ]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        await logic.emit_to_room(room_uuid, "hello")
        mock_etu.assert_called_once_with(user_uuid, "hello")


@pytest.mark.asyncio
async def test_emit_to_room_with_exclude():
    """
    Emitting to the room simply emits the passed in message to all users
    currently in the room.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    user = database.OBJECTS[user_uuid]
    room_uuid = logic.add_room("roomname", "room description", user)
    room = database.OBJECTS[room_uuid]
    room["_meta"]["contents"] = [user_uuid, ]
    with asynctest.patch("textsmith.logic.emit_to_user") as mock_etu:
        await logic.emit_to_room(room_uuid, "hello", [user_uuid, ])
        assert mock_etu.call_count == 0


@pytest.mark.asyncio
async def test_emit_to_user():
    """
    Ensure the message is sent via the connection associated with the
    referenced user_id.
    """
    user_uuid = logic.add_user("username", "description", "password",
                               "mail@eample.com")
    mock_ws = asynctest.MagicMock()
    mock_ws.send = asynctest.CoroutineMock()
    database.CONNECTIONS[user_uuid] = mock_ws
    await logic.emit_to_user(user_uuid, "hello")
    mock_ws.send.assert_called_once_with("hello")
