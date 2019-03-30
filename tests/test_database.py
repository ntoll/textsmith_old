"""
Tests to ensure the database module works properly.
"""
import os
import time
from textsmith import database
from textsmith.logic import add_object, add_user, add_room, make_uuid


def setup_function():
    """
    Setup a clean database state.
    Invoked for every test function in the module.
    """
    database.OBJECTS = {}
    database.USERS = {}


def test_save_load_database():
    """
    Ensure the database is saved and loaded as expected.
    """
    temp_file = os.path.abspath("temp_db.json")
    user_id = add_user("testuser", "a test user", "password",
                       "mail@example.com")
    user = database.OBJECTS[user_id]
    room_id = add_room("roomname", "a test room", user)
    room = database.OBJECTS[room_id]
    room["_meta"]["default_room"] = True
    obj_id = add_object("testobject", "a test object", user)
    # Save the data!
    database.save_database(temp_file)
    # Delete the in-memory data.
    database.OBJECTS = None
    database.USERS = None
    # Load the data!
    database.load_database(temp_file)
    assert database.USERS["testuser"] == user_id
    assert len(database.OBJECTS) == 3
    assert user_id in database.OBJECTS
    assert obj_id in database.OBJECTS
    assert room_id in database.OBJECTS
    assert database.DEFAULT_ROOM == room["_meta"]["fqn"]
    # Delete the temporary file.
    os.remove(temp_file)


def test_make_object():
    """
    Ensure the expected dictionary object is returned.
    """
    uuid = make_uuid()
    name = "objname"
    fqn = "username/objname"
    description = "a description"
    alias = ["objalias", ]
    owner = make_uuid()
    typeof = "object"
    public = True
    result = database.make_object(uuid, name, fqn, description, alias, owner,
                                  public, typeof)
    expected = {
        "description": description,
        "_meta": {
            "alias": alias,
            "uuid": uuid,
            "name": name,
            "fqn": fqn,
            "owner": owner,
            "typeof": typeof,
            "public": public,
        }
    }
    assert result == expected


def test_make_room():
    """
    Ensure the expected dictionary object is returned.
    """
    uuid = make_uuid()
    name = "objname"
    fqn = "username/objname"
    description = "a description"
    alias = ["roomalias", ]
    owner = make_uuid()
    typeof = "room"
    public = True
    contents = [make_uuid(), ]
    fqns = ["foo/bar", ]
    exits_out = [make_uuid(), ]
    exits_in = [make_uuid(), ]
    allow = [make_uuid(), ]
    exclude = [make_uuid(), ]
    result = database.make_room(uuid, name, fqn, description, alias, owner,
                                public, contents, fqns, exits_out, exits_in,
                                allow, exclude)
    expected = {
        "description": description,
        "_meta": {
            "alias": alias,
            "uuid": uuid,
            "name": name,
            "fqn": fqn,
            "owner": owner,
            "typeof": typeof,
            "public": public,
            "contents": contents,
            "fqns": fqns,
            "exits_out": exits_out,
            "exits_in": exits_in,
            "allow": allow,
            "exclude": exclude,
        }
    }
    assert result == expected


def test_make_exit():
    """
    Ensure the expected dictionary object is returned.
    """
    uuid = make_uuid()
    name = "objname"
    fqn = "username/objname"
    description = "a description"
    alias = ["exitalias", ]
    owner = make_uuid()
    typeof = "exit"
    public = True
    source = make_uuid()
    destination = make_uuid()
    leave_user = "You leave."
    leave_room = "User leaves."
    arrive_room = "User arrives."
    result = database.make_exit(uuid, name, fqn, description, alias, owner,
                                public, source, destination, leave_user,
                                leave_room, arrive_room)
    expected = {
        "description": description,
        "leave_user": leave_user,
        "leave_room": leave_room,
        "arrive_room": arrive_room,
        "_meta": {
            "alias": alias,
            "uuid": uuid,
            "name": name,
            "fqn": fqn,
            "owner": owner,
            "typeof": typeof,
            "public": public,
            "source": source,
            "destination": destination,
        }
    }
    assert result == expected


def test_make_user():
    """
    Ensure the expected dictionary object is returned.
    """
    uuid = make_uuid()
    name = "username"
    fqn = "username/username"
    description = "a description"
    alias = ["Dread Pirate Roberts", ]  # ;-)
    owner = make_uuid()
    typeof = "user"
    public = True
    location = make_uuid()
    inventory = [make_uuid(), ]
    owns = [make_uuid(), ]
    fqns = ["foo/bar", ]
    password = "password"
    email = "email@example.com"
    created_on = time.time()
    last_login = None
    superuser = False
    result = database.make_user(uuid, name, fqn, description, alias, owner,
                                public, location, inventory, owns, fqns,
                                password, email, created_on, last_login,
                                superuser)
    expected = {
        "description": description,
        "_meta": {
            "alias": alias,
            "uuid": uuid,
            "name": name,
            "fqn": fqn,
            "owner": owner,
            "typeof": typeof,
            "public": public,
            "location": location,
            "inventory": inventory,
            "owns": owns,
            "fqns": fqns,
            "password": password,
            "email": email,
            "created_on": created_on,
            "last_login": last_login,
            "superuser": superuser,
        }
    }
    assert result == expected
