"""
Functions for game logic.

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
import os
import uuid
import hashlib
import binascii
import time
import textsmith.database as database


def make_uuid():
    """
    Returns a string based universally unique identification.
    """
    return str(uuid.uuid4())


def hash_password(password):
    """
    Hash a password for storing.
    """
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                  salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def verify_password(stored_password, provided_password):
    """
    Verify a stored password against one provided by user.
    """
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512',
                                  provided_password.encode('utf-8'),
                                  salt.encode('ascii'),
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_password


def add_object(name, description, user):
    """
    Given a name, description and user object, returns the UUID of a newly
    created object with default values which has been added to the object
    database.
    """
    new_uuid = make_uuid()
    fqn = "{}/{}".format(user["_meta"]["name"], name)
    alias = []
    owner = user["_meta"]["uuid"]
    public = True
    database.OBJECTS[new_uuid] = database.make_object(new_uuid, name, fqn,
                                                      description, alias,
                                                      owner, public)
    user["_meta"]["owns"].append(new_uuid)
    return new_uuid


def add_room(name, description, user):
    """
    Given a name, description and user object, return the UUID of a newly
    created room with default values, which has been added to the object
    database.
    """
    new_uuid = make_uuid()
    fqn = "{}/{}".format(user["_meta"]["name"], name)
    alias = []
    owner = user["_meta"]["uuid"]
    public = True
    contents = []
    exits_in = []
    exits_out = []
    allow = []
    exclude = []
    database.OBJECTS[new_uuid] = database.make_room(new_uuid, name, fqn,
                                                    description, alias,
                                                    owner, public, contents,
                                                    exits_in, exits_out, allow,
                                                    exclude)
    user["_meta"]["owns"].append(new_uuid)
    return new_uuid


def add_exit(name, description, user, source_room, destination_room):
    """
    Given a name, description, user object, source room and destination room,
    return the UUID of a newly created exit from the source room to the
    destination room, with default values, which has been added to the object
    database.

    Will raise an exception if:

    * The user is NOT in the allow or IS in the exclude lists of the
      destination room.
    * There is already an exit linking the source room to the destination room.
    """
    new_uuid = make_uuid()
    fqn = "{}/{}".format(user["_meta"]["name"], name)
    alias = []
    owner = user["_meta"]["uuid"]
    public = True
    # Check permissions.
    allow = destination_room["_meta"]["allow"]
    exclude = destination_room["_meta"]["exclude"]
    if allow and owner not in allow:
        raise PermissionError("User not on allow list.")
    if owner in exclude:
        raise PermissionError("User in exclude list.")
    # Check duplications.
    for exit_id in source_room["_meta"]["exits_out"]:
        if exit_id in destination_room["_meta"]["exits_in"]:
            raise ValueError("Exit to destination already exists.")
    # Add room to object database.
    source_id = source_room["_meta"]["uuid"]
    destination_id = destination_room["_meta"]["uuid"]
    destination_name = destination_room["_meta"]["name"]
    source_name = source_room["_meta"]["name"]
    leave_user = f'You leave "{source_name}" via "{name}".'
    leave_room = ("{username} "
                  f'leaves for "{destination_name}" via "{name}".')
    arrive_room = "{username} " + f'arrives from "{source_name}".'
    new_exit = database.make_exit(new_uuid, name, fqn, description, alias,
                                  owner, public, source_id, destination_id,
                                  leave_user, leave_room, arrive_room)
    source_room["_meta"]["exits_out"].append(new_uuid)
    destination_room["_meta"]["exits_in"].append(new_uuid)
    database.OBJECTS[new_uuid] = new_exit
    user["_meta"]["owns"].append(new_uuid)
    return new_uuid


def add_user(name, description, raw_password, email):
    """
    Given a name, description, raw (unhashed) password and an email address
    return the UUID of a newly created user, with default values, which has
    been added to the object database.

    Will raise an exception if:

    * A user with that username already exists.
    """
    new_uuid = make_uuid()
    fqn = "{}/{}".format(name, name)  # A user always owns themselves.
    alias = []
    owner = new_uuid  # A user always owns themselves.
    public = True
    if name in database.USERS:
        raise ValueError("Username already exists.")
    location = None  # A user's start location is "nowhere".
    inventory = []
    owns = [new_uuid, ]  # A user always owns themselves.
    hashed_password = hash_password(raw_password)
    created_on = time.time()
    last_login = None
    superuser = False
    database.OBJECTS[new_uuid] = database.make_user(new_uuid, name, fqn,
                                                    description, alias,
                                                    owner, public, location,
                                                    inventory, owns,
                                                    hashed_password, email,
                                                    created_on, last_login,
                                                    superuser)
    database.USERS[name] = new_uuid
    return new_uuid


def is_owner(obj, user):
    """
    Returns a boolean indicating if the referenced user owns the referenced
    object.
    """
    return user["_meta"]["uuid"] == obj["_meta"]["owner"]


def delete_object(uuid, user):
    """
    Given an object's UUID and an object representing the user requesting
    the deletion, attempt to delete the referenced object. This will only work
    if either the user is the object's owner, or the user is a superuser.

    Return True if successful, else False.
    """
    to_delete = database.OBJECTS.get(uuid)
    if to_delete:  # Does the object with this UUID exits?
        if to_delete["_meta"]["typeof"] == "object":  # Is this only an object?
            superuser = user["_meta"]["superuser"]
            owner = is_owner(to_delete, user)
            if superuser or owner:  # Is the user the owner or superuser?
                # Remove the object from the "owns" list of the owner of the
                # object.
                owner_user = database.OBJECTS[to_delete["_meta"]["owner"]]
                owner_user["_meta"]["owns"].remove(uuid)
                # Delete the object from the database.
                del database.OBJECTS[uuid]
                return True
    return False


def delete_room(uuid, user):
    """
    Given a room's UUID and an object representing the user requesting the
    deletion of the room, attempt to delete the room. This can only work if
    either the user is the room's owner, or the user is a superuser.

    If there are users in the room, they are transported to the front door
    (the location where all users start upon first connection).

    All objects in the room are put into the inventory list of their owners.

    All exits which have the room as the destination will be deleted.

    Return True if successful, else False
    """
    room = database.OBJECTS.get(uuid)
    if room:  # Does an object with this UUID exist?
        if room["_meta"]["typeof"] == "room":  # Is the object a room?
            superuser = user["_meta"]["superuser"]
            owner = is_owner(room, user)
            if superuser or owner:  # Check user can delete the room.
                # Set new state for all objects contained within the room.
                for item_id in room["_meta"]["contents"]:
                    obj = database.OBJECTS.get(item_id)
                    if obj:
                        if obj["_meta"]["typeof"] == "user":
                            # It's a user. So set location to "None" (default
                            # starting state).
                            obj["_meta"]["location"] = None
                        else:
                            # It's some other sort of object. Add it to the
                            # inventory of the user who owns the object (so the
                            # object exists *somewhere* in the game world).
                            owner_id = obj["_meta"]["owner"]
                            owner = database.OBJECTS.get(owner_id)
                            if owner:
                                owner["_meta"]["inventory"].append(item_id)
                # Delete all exit objects which have this room as a
                # destination. Since the user may not own the exits in
                # question, but we don't want the game to have exits to
                # nowhere, force delete them.
                for exit_id in room["_meta"]["exits_in"]:
                    delete_exit(exit_id, user, force=True)
                for exit_id in room["_meta"]["exits_out"]:
                    delete_exit(exit_id, user, force=True)
                # Remove the object from the "owns" list of the owner of the
                # object.
                owner_user = database.OBJECTS[room["_meta"]["owner"]]
                owner_user["_meta"]["owns"].remove(uuid)
                # Delete the room itself.
                del database.OBJECTS[uuid]
                return True
    return False


def delete_exit(uuid, user, force=False):
    """
    Given an exit's UUID and an object representing the user requesting the
    deletion of the exit, attempt to delete the exit. This can only work if
    either the user is the exit's owner, or the user is a superuser. The force
    flag is ONLY used when another user is deleting a room *they* own, but need
    to clean up exits that link to it.

    References to the exit are first deleted from the rooms which the exit
    connects, then the exit itself is deleted.
    """
    exit = database.OBJECTS.get(uuid)
    if exit:  # Does an object with this UUID exist?
        if exit["_meta"]["typeof"] == "exit":  # Is the object an exit?
            superuser = user["_meta"]["superuser"]
            owner = is_owner(exit, user)
            if superuser or owner or force:  # Check user can delete the exit.
                # Remove the exit ID from the source and destination rooms.
                source_id = exit["_meta"]["source"]
                destination_id = exit["_meta"]["destination"]
                source = database.OBJECTS[source_id]
                destination = database.OBJECTS[destination_id]
                if source and destination:
                    if uuid in source["_meta"]["exits_out"]:
                        source["_meta"]["exits_out"].remove(uuid)
                    if uuid in destination["_meta"]["exits_in"]:
                        destination["_meta"]["exits_in"].remove(uuid)
                # Remove the object from the "owns" list of the owner of the
                # object.
                owner_user = database.OBJECTS[exit["_meta"]["owner"]]
                owner_user["_meta"]["owns"].remove(uuid)
                # Delete the exit.
                del database.OBJECTS[uuid]
                return True
    return False
