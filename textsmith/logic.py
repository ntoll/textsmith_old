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
    exits = []
    allow = []
    exclude = []
    database.OBJECTS[new_uuid] = database.make_room(new_uuid, name, fqn,
                                                    description, alias,
                                                    owner, public, contents,
                                                    exits, allow, exclude)
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
    destination = destination_room["_meta"]["uuid"]
    for exit_id in source_room["_meta"]["exits"]:
        exit = database.OBJECTS[exit_id]
        if exit["_meta"]["destination"] == destination:
            raise ValueError("Exit to destination already exists.")
    # Add room to object database.
    destination_name = destination_room["_meta"]["name"]
    source_name = source_room["_meta"]["name"]
    leave_user = f'You leave "{source_name}" via "{name}".'
    leave_room = ("{username} "
                  f'leaves for "{destination_name}" via "{name}".')
    arrive_room = "{username} " + f'arrives from "{source_name}".'
    new_exit = database.make_exit(new_uuid, name, fqn, description, alias,
                                  owner, public, destination, leave_user,
                                  leave_room, arrive_room)
    source_room["_meta"]["exits"].append(new_uuid)
    database.OBJECTS[new_uuid] = new_exit
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
    location = None
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
    the function, attempt to delete the referenced object. This will only work
    if either the user is the object's owner, or the user is a superuser.

    Return True is successful, else False.
    """
    to_delete = database.OBJECTS.get(uuid)
    if to_delete:
        superuser = user["_meta"]["superuser"]
        owner = is_owner(to_delete, user)
        if superuser or owner:
            del database.OBJECTS[uuid]
            return True
    return False


def delete_room(uuid, user):
    """
    """


def delete_exit(uuid, user):
    """
    """
