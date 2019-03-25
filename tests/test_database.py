"""
Tests to ensure the database module works properly.
"""
import os
import time
from textsmith import database
from textsmith.logic import add_object, add_user, make_uuid


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
    user_id = add_user("test user", "a test user", "password",
                       "mail@example.com")
    user = database.OBJECTS[user_id]
    obj_id = add_object("test object", "a test object", user)
    # Save the data!
    database.save_database(temp_file)
    # Delete the in-memory data.
    database.OBJECTS = None
    database.USERS = None
    # Load the data!
    database.load_database(temp_file)
    assert database.USERS["test user"] == user_id
    assert len(database.OBJECTS) == 2
    assert user_id in database.OBJECTS
    assert obj_id in database.OBJECTS
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
    alias = []
    owner = make_uuid()
    typeof = "object"
    public = True
    result = database.make_object(uuid, name, fqn, description, alias, owner,
                                  public, typeof)
    expected = {
        "description": description,
        "alias": alias,
        "_meta": {
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
    alias = []
    owner = make_uuid()
    typeof = "room"
    public = True
    contents = []
    exits = []
    allow = []
    exclude = []
    result = database.make_room(uuid, name, fqn, description, alias, owner,
                                public, contents, exits, allow, exclude)
    expected = {
        "description": description,
        "alias": alias,
        "_meta": {
            "uuid": uuid,
            "name": name,
            "fqn": fqn,
            "owner": owner,
            "typeof": typeof,
            "public": public,
            "contents": contents,
            "exits": exits,
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
    alias = []
    owner = make_uuid()
    typeof = "exit"
    public = True
    destination = make_uuid()
    leave_user = "You leave."
    leave_room = "User leaves."
    arrive_room = "User arrives."
    result = database.make_exit(uuid, name, fqn, description, alias, owner,
                                public, destination, leave_user, leave_room,
                                arrive_room)
    expected = {
        "description": description,
        "alias": alias,
        "leave_user": leave_user,
        "leave_room": leave_room,
        "arrive_room": arrive_room,
        "_meta": {
            "uuid": uuid,
            "name": name,
            "fqn": fqn,
            "owner": owner,
            "typeof": typeof,
            "public": public,
            "destination": destination,
        }
    }
    assert result == expected


def test_make_user():
    """
    Ensure the expected dictionary object is returned.
    """
    uuid = make_uuid()
    name = "objname"
    fqn = "username/objname"
    description = "a description"
    alias = []
    owner = make_uuid()
    typeof = "user"
    public = True
    location = make_uuid()
    inventory = []
    owns = []
    password = "password"
    email = "email@example.com"
    created_on = time.time()
    last_login = None
    superuser = False
    result = database.make_user(uuid, name, fqn, description, alias, owner,
                                public, location, inventory, owns, password,
                                email, created_on, last_login, superuser)
    expected = {
        "description": description,
        "alias": alias,
        "_meta": {
            "uuid": uuid,
            "name": name,
            "fqn": fqn,
            "owner": owner,
            "typeof": typeof,
            "public": public,
            "location": location,
            "inventory": inventory,
            "owns": owns,
            "password": password,
            "email": email,
            "created_on": created_on,
            "last_login": last_login,
            "superuser": superuser,
        }
    }
    assert result == expected
