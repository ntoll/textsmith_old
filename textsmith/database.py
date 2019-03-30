"""
Data containers and functions to interact with the data.

Copyright (C) 2019 Nicholas Tollervey and Andrew Smith.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import json


USERS = {}  # Key = username, Value = object ID for user.
FQNS = {}  # Key = fqn of object, Value = UUID for object.
OBJECTS = {}  # All objects are a UUID referencing a dictionary.
CONNECTIONS = {}  # Key = user's uuid, Value = an open websocket connect.
DEFAULT_DATAFILE = "database.json"  # Where to dump the database.
DEFAULT_ROOM = ""  # Where players in limbo get sent.


def load_database(filename=DEFAULT_DATAFILE):
    """
    Load the object database from the JSON content in the referenced file.
    """
    # Load the database.
    global OBJECTS
    global USERS
    global DEFAULT_ROOM
    global FQNS
    with open(filename, "r") as f:
        OBJECTS = json.load(f)
    # Update the USERS and FQNS convenience lookup tables.
    USERS = {}
    FQNS = {}
    for uuid, obj in OBJECTS.items():
        default_room = obj["_meta"].get("default_room")
        if default_room:
            DEFAULT_ROOM = obj["_meta"]["fqn"]
        FQNS[obj["_meta"]["fqn"]] = obj["_meta"]["uuid"]
        if obj["_meta"]["typeof"] == "user":
            USERS[obj["_meta"]["name"]] = obj["_meta"]["uuid"]


def save_database(filename=DEFAULT_DATAFILE):
    """
    Save the object database to the referenced file as JSON.
    """
    with open(filename, "w") as f:
        json.dump(OBJECTS, f, indent=2)


def make_object(uuid, name, fqn, description, alias, owner, public,
                typeof="object"):
    """
    All game objects have the following attributes:

    uuid - a computer friendly universally unique id for the object.
    name - the name of the object given to it by its owner.
    fqn - the human readable unique fully qualified name of the object. This is
      the unique name of the owner followed by a backslash and then the unique
      name of the object in the owner's namespace. E.g. "ntoll/tuba"
    description - a human readable description of the object. When a user
      looks a this object, the name and this description is displayed.
    alias - other, non-unique names which could refer to this object.
    owner - the uuid of the user who owns this object.
    public - boolean flag to show if this object is public or private (visible
      only to the user).
    typeof - either "object", "room", "exit" or "user".

    Metadata for the object, used by the game system and only revealed to the
    users via the game itself, is found in the _meta sub_dictionary.
    """
    global FQNS
    FQNS[fqn] = uuid
    return {
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


def make_room(uuid, name, fqn, description, alias, owner, public, contents,
              fqns, exits_out, exits_in, allow, exclude):
    """
    In addition to the attributes for a base object, all rooms have the
    following attributes:

    contents - a list of object UUIDs which this room contains.
    fqns - the fqns of objects in the room.
    exits_out - a list of object UUIDs which represent the exits from this
      room.
    exits_in - a list of object UUIDs which represent the exits that have this
      room as a destination (a cache that saves expensive lookups).
    allow - a list of usernames of people allowed to enter this room. If this
      contains items then anyone not on the list is automatically excluded.
    exclude - a list of usernames of people to exclude from this room.

    Allow takes precedence over exclude.
    """
    obj = make_object(uuid, name, fqn, description, alias, owner, public,
                      typeof="room")
    obj["_meta"].update({
        "contents": contents,
        "fqns": fqns,
        "exits_out": exits_out,
        "exits_in": exits_in,
        "allow": allow,
        "exclude": exclude,
    })
    return obj


def make_exit(uuid, name, fqn, description, alias, owner, public,
              source, destination, leave_user, leave_room, arrive_room):
    """
    In addition to the attributes for a base object, all exits have the
    following attributes:

    source - the UUID of the room FROM which this exit takes you.
    destination - the UUID of the room TO which this exit takes you.
    leave_user - the message to relay to the user as they use the exit.
    leave_room - the message to relay to the source room as the user leaves.
    arrive_room - the message to relay to the destination room as the user
      arrives.
    """
    obj = make_object(uuid, name, fqn, description, alias, owner, public,
                      typeof="exit")
    obj['_meta'].update({
        "source": source,
        "destination": destination,
    })
    obj.update({
        "leave_user": leave_user,
        "leave_room": leave_room,
        "arrive_room": arrive_room,
    })
    return obj


def make_user(uuid, name, fqn, description, alias, owner, public, location,
              inventory, owns, fqns, password, email, created_on, last_login,
              superuser):
    """
    In addition to the attributes for a base object, all users have the
    following attributes:

    location - UUID of the room containing the player.
    inventory - UUIDs of objects carried by the user.
    owns - UUIDs of objects owned by the user.
    fqns - the fqns of objects owned by the user.
    password - a hash of the password with the UUID as the salt.
    email - the user's email address (used for Gravatar too).
    created_on - timestamp of user creation.
    last_login - timestamp of last login.
    superuser - a boolean indicating if the user is a super user.
    """
    obj = make_object(uuid, name, fqn, description, alias, owner, public,
                      typeof="user")
    obj['_meta'].update({
        "location": location,
        "inventory": inventory,
        "owns": owns,
        "fqns": fqns,
        "password": password,
        "email": email,
        "created_on": created_on,
        "last_login": last_login,
        "superuser": superuser,
    })
    return obj
