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
import json
import textsmith.database as database
from quart import render_template_string
from datetime import datetime


LOOK_TEMPLATE = """## {{name}}

[**{{fqn}}**]

{% if alias %}
Alias: {{ alias|join(', ') }}
{% endif %}

{{ description }}

{% if typeof=="room" %}
**You can see**: {{ contents|join(', ') }}

**Exits**: {{ exits|join(', ') }}
{% elif typeof=="exit" %}
This leads to "{{ destination }}".
{% elif typeof=="user" %}
They are carrying: {{ inventory|join(', ') }}
{% endif %}
"""


DETAIL_TEMPLATE = """<div class="detail">
    <ul>
        <li><strong>Name</strong>: {{ name }}</li>
        <li>UUID: {{ uuid }}</li>
        <li>Owner: {{ owner }}</li>
        <li>Fully Qualified Name: {{ fqn }}</li>
        <li>Alias: {{ alias }}</li>
        <li>Type of: {{ typeof }}</li>
        <li>Public: {{ public }}</li>
        {% if typeof=="room" %}
        <li>Contents: {{ contents }}</li>
        <li>Exits out: {{ exits_out }}</li>
        <li>Allowed Users: {{ allowed }}</li>
        <li>Excluded Users: {{ excluded }}</li>
        {% elif typeof=="exit" %}
        <li>Source Room: {{ source }}</li>
        <li>Destination Room: {{ destination }}</li>
        {% elif typeof=="user" %}
        <li>Inventory: {{ inventory }}</li>
        <li>Owns: {{ owns }}</li>
        <li>Current Location: {{ location }}</li>
        <li>User Created on: {{ created_on }}</li>
        <li>Last Login: {{ last_login }}</li>
        {% endif %}
        <li><strong>Attributes:</strong>
            {% if attributes %}
            <dl>
                {% for k, v in attributes.items() %}
                <dt>{{ k }}</dt>
                <dd><pre>{{ v }}</pre></dd>
                {% endfor %}
            </dl>
            {% else %}None{% endif %}
        </li>
    </ul>
</div>
"""


def make_uuid():
    """
    Returns a string based universally unique identification.
    """
    return str(uuid.uuid4())


def is_valid_object_name(name):
    """
    Returns a boolean indication if the referenced name is a valid object name.

    Currently object names must only contain alphanumeric characters.
    """
    return name.isalnum()


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
    database. The object will be added to the user's inventory.

    Will raise an exception if:

    * The name is not alphanumeric.
    * The name of the room is not unique for this user.
    """
    if not is_valid_object_name(name):
        raise ValueError("Object names can only contain alphanumeric "
                         "characters.")
    fqn = "{}/{}".format(user["_meta"]["name"], name)
    if fqn in user["_meta"]["fqns"]:
        raise ValueError("Object name already exists for this user.")
    new_uuid = make_uuid()
    alias = []
    owner = user["_meta"]["uuid"]
    public = True
    database.OBJECTS[new_uuid] = database.make_object(new_uuid, name, fqn,
                                                      description, alias,
                                                      owner, public)
    user["_meta"]["owns"].append(new_uuid)
    user["_meta"]["fqns"].append(fqn)
    user["_meta"]["inventory"].append(new_uuid)
    return new_uuid


def add_room(name, description, user):
    """
    Given a name, description and user object, return the UUID of a newly
    created room with default values, which has been added to the object
    database.

    Will raise an exception if:

    * The name is not alphanumeric.
    * The name of the room is not unique for this user.
    """
    if not is_valid_object_name(name):
        raise ValueError("Room names can only contain alphanumeric "
                         "characters.")
    fqn = "{}/{}".format(user["_meta"]["name"], name)
    if fqn in user["_meta"]["fqns"]:
        raise ValueError("Object name already exists for this user.")
    new_uuid = make_uuid()
    alias = []
    owner = user["_meta"]["uuid"]
    public = True
    contents = []
    fqns = []
    exits_in = []
    exits_out = []
    allow = []
    exclude = []
    database.OBJECTS[new_uuid] = database.make_room(new_uuid, name, fqn,
                                                    description, alias,
                                                    owner, public, contents,
                                                    fqns, exits_in, exits_out,
                                                    allow, exclude)
    user["_meta"]["owns"].append(new_uuid)
    user["_meta"]["fqns"].append(fqn)
    return new_uuid


def add_exit(name, description, user, source_room, destination_room):
    """
    Given a name, description, user object, source room and destination room,
    return the UUID of a newly created exit from the source room to the
    destination room, with default values, which has been added to the object
    database.

    Will raise an exception if:

    * The name is not alphanumeric.
    * The name is not unique for this user.
    * The user is NOT in the allow or IS in the exclude lists of the
      destination room.
    * There is already an exit linking the source room to the destination room.
    """
    if not is_valid_object_name(name):
        raise ValueError("Exit names can only contain alphanumeric "
                         "characters.")
    fqn = "{}/{}".format(user["_meta"]["name"], name)
    if fqn in user["_meta"]["fqns"]:
        raise ValueError("Object name already exists for this user.")
    new_uuid = make_uuid()
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
            raise KeyError("Exit to destination already exists.")
    # An exit can't connect a room to itself.
    if source_room["_meta"]["uuid"] == destination_room["_meta"]["uuid"]:
        raise ValueError("You cannot create an exit to connect a room to "
                         "itself.")
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
    user["_meta"]["fqns"].append(fqn)
    return new_uuid


def add_user(name, description, raw_password, email):
    """
    Given a name, description, raw (unhashed) password and an email address
    return the UUID of a newly created user, with default values, which has
    been added to the object database.

    Will raise an exception if:

    * The name is not alphanumeric.
    * A user with that username already exists.
    """
    if not is_valid_object_name(name):
        raise ValueError("Usernames can only contain alphanumeric "
                         "characters.")
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
    fqns = [fqn, ]  # A user always owns themselves.
    hashed_password = hash_password(raw_password)
    created_on = time.time()
    last_login = None
    superuser = False
    database.OBJECTS[new_uuid] = database.make_user(new_uuid, name, fqn,
                                                    description, alias,
                                                    owner, public, location,
                                                    inventory, owns, fqns,
                                                    hashed_password, email,
                                                    created_on, last_login,
                                                    superuser)
    database.USERS[name] = new_uuid
    return new_uuid


def get_object_from_context(name, room, user):
    """
    Given an object name, will attempt to return the object[s] from the
    contents of the referenced room or the user's inventory. Will also check
    item aliases when finding matches. The objects must be visible to the
    referenced user.
    """
    result = []
    if name is None:
        return result
    if "/" in name:
        # We're looking for a FQN!
        # FQN = Fully Qualified Name (i.e. an unambiguous unique name of the
        # form ownername/objectname - hence checking for backslash).
        # Check room.
        for item_id in room["_meta"]["contents"]:
            item = database.OBJECTS[item_id]
            if item["_meta"]["fqn"] == name:
                if is_visible(item, user):
                    result.append(item)
                    # FQN's are unique, once found, abort.
                    break
        # Check user's inventory.
        for item_id in user["_meta"]["inventory"]:
            item = database.OBJECTS[item_id]
            if item["_meta"]["fqn"] == name:
                if is_visible(item, user):
                    result.append(item)
                    # FQN's are unique, once found, abort.
                    break
    else:
        # Looking for a single word name.
        # Check room.
        for item_id in room["_meta"]["contents"]:
            item = database.OBJECTS[item_id]
            if item["_meta"]["name"] == name or name in item["_meta"]["alias"]:
                if is_visible(item, user):
                    result.append(item)
        # Check user's inventory.
        for item_id in user["_meta"]["inventory"]:
            item = database.OBJECTS[item_id]
            if item["_meta"]["name"] == name or name in item["_meta"]["alias"]:
                if is_visible(item, user):
                    result.append(item)
    return result


def is_owner(obj, user):
    """
    Returns a boolean indicating if the referenced user owns the referenced
    object.
    """
    superuser = user["_meta"]["superuser"]
    owner = user["_meta"]["uuid"] == obj["_meta"]["owner"]
    return bool(superuser or owner)


def is_visible(obj, user):
    """
    Return a boolean to indicate if the referenced object if visible to the
    given user.
    """
    if is_owner(obj, user):
        # Owners always see their own objects.
        return True
    else:
        # Just return whatever the value of the "public" flag is.
        return obj["_meta"]["public"]


def set_visible(obj, public, user):
    """
    Set the visibility of the object's public flag given the user requesting
    such a change.

    Will raise a PermissionError if the user isn't the owner or a superuser.
    """
    if obj["_meta"]["typeof"] != "object":
        raise TypeError("Cannot change visibility of that sort of thing.")
    superuser = user["_meta"]["superuser"]
    owner = is_owner(obj, user)
    if superuser or owner:
        obj["_meta"]["public"] = bool(public)
    else:
        raise PermissionError("Cannot change the visibility of object.")


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
                # Remove the object from the "owns" and "fqns" lists of the
                # owner of the object.
                fqn = to_delete["_meta"]["fqn"]
                owner_user = database.OBJECTS[to_delete["_meta"]["owner"]]
                owner_user["_meta"]["owns"].remove(uuid)
                owner_user["_meta"]["fqns"].remove(fqn)
                # Delete the object from the database and lookup table.
                del database.OBJECTS[uuid]
                del database.FQNS[fqn]
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
                # Remove the object from the "owns" and "fqns" lists of the
                # owner of the object.
                fqn = room["_meta"]["fqn"]
                owner_user = database.OBJECTS[room["_meta"]["owner"]]
                owner_user["_meta"]["owns"].remove(uuid)
                owner_user["_meta"]["fqns"].remove(fqn)
                # Delete the room itself.
                del database.OBJECTS[uuid]
                del database.FQNS[fqn]
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
                # Remove the object from the "owns" and "fqns" lists of the
                # owner of the object.
                fqn = exit["_meta"]["fqn"]
                owner_user = database.OBJECTS[exit["_meta"]["owner"]]
                owner_user["_meta"]["owns"].remove(uuid)
                owner_user["_meta"]["fqns"].remove(fqn)
                # Delete the exit.
                del database.OBJECTS[uuid]
                del database.FQNS[fqn]
                return True
    return False


async def move(obj_id, exit_id, user_id):
    """
    Move the referenced object, via the referenced exit from one room to
    another. The referenced user (making the request for the move) must own
    the object to be moved.
    """
    obj = database.OBJECTS.get(obj_id)
    exit = database.OBJECTS.get(exit_id)
    user = database.OBJECTS.get(user_id)
    # Ensure the object, exit and user exist.
    if not (obj and exit and user):
        raise ValueError("Missing object.")
    # The user must own the object to be moved.
    if not is_owner(obj, user):
        raise KeyError("Object not owned by user.")
    # Only these types of object may be moved via an exit.
    moveable_types = ["object", "user"]
    if obj["_meta"]["typeof"] not in moveable_types:
        raise TypeError("Objects of this type cannot be moved via an exit.")
    source_id = exit["_meta"]["source"]
    destination_id = exit["_meta"]["destination"]
    source = database.OBJECTS[source_id]
    destination = database.OBJECTS[destination_id]
    # Ensure the obj is in the current source room of the exit.
    if obj_id not in source["_meta"]["contents"]:
        raise ValueError("The object must be in the room containing the exit.")
    # Ensure the obj is allowed into the destination room of the exit.
    if (destination["_meta"]["allow"] and
            obj["_meta"]["owner"] not in destination["_meta"]["allow"]):
        raise PermissionError("Object's owner not allowed in the destination.")
    if obj["_meta"]["owner"] in destination["_meta"]["exclude"]:
        raise PermissionError("Object excluded from entering the destination.")
    # Change state to reflect the move and signal the move to the users.
    source["_meta"]["contents"].remove(obj_id)
    source["_meta"]["fqns"].remove(obj["_meta"]["fqn"])
    destination["_meta"]["contents"].append(obj_id)
    destination["_meta"]["fqns"].append(obj["_meta"]["fqn"])
    exclude = []
    if obj["_meta"]["typeof"] == "user":
        exclude.append(obj_id)
        obj["_meta"]["location"] = destination_id
        leave_user = exit["leave_user"].format(username=obj["_meta"]["name"])
        await emit_to_user(obj_id, leave_user)
    leave_room = exit["leave_room"].format(username=obj["_meta"]["name"])
    await emit_to_room(source_id, leave_room, exclude=exclude)
    arrive_room = exit["arrive_room"].format(username=obj["_meta"]["name"])
    await emit_to_room(destination_id, arrive_room, exclude=exclude)


async def teleport(user_id, dest_fqn):
    """
    Teleport a user into a target room.
    """
    user = database.OBJECTS.get(user_id)
    destination_id = database.FQNS.get(dest_fqn)
    destination = database.OBJECTS.get(destination_id)
    # Ensure the user exist and destination exits.
    if not (user and destination):
        raise ValueError("Missing object.")
    # Cannot teleport a user into their current location.
    if user_id in destination["_meta"]["contents"]:
        raise ValueError("Cannot teleport user to their current location.")
    # Change the state to reflect the teleportation.
    current_room_id = user["_meta"]["location"]
    current_room = database.OBJECTS[current_room_id]
    current_room["_meta"]["contents"].remove(user_id)
    current_room["_meta"]["fqns"].remove(user["_meta"]["fqn"])
    destination["_meta"]["contents"].append(user_id)
    destination["_meta"]["fqns"].append(user["_meta"]["fqn"])
    user["_meta"]["location"] = destination_id
    username = user["_meta"]["name"]
    await emit_to_user(user_id, "You teleport away.")
    await emit_to_room(current_room_id, f"{username} teleports away.",
                       exclude=[user_id, ])
    await emit_to_room(destination_id, f"{username} teleports in.",
                       exclude=[user_id, ])


def build(name, description, user, exit_name=None, return_name=None,
          exit_description="", return_description=""):
    """
    Build a new room with an optional exits to/from the user's current location
    and the new location. Returns the new room's ID if successful, may raise
    exceptions if adding a room or exit fails their specific constraints.
    """
    new_room_id = add_room(name, description, user)
    if exit_name and return_name:
        current_room_id = user["_meta"]["location"]
        current_room = database.OBJECTS[current_room_id]
        new_room = database.OBJECTS[new_room_id]
        add_exit(exit_name, exit_description, user, current_room,
                 new_room)
        add_exit(return_name, return_description, user, new_room,
                 current_room)
    return new_room_id


def clone(source_id, target_name, user):
    """
    Clone an existing object to a brand new object with the specified target
    name to belong to the referenced user. Will only work with things that
    have a typeof "object".

    This will fail if the user already owns an object with the target name.

    Returns the clone's UUID if successful. Raises a PermissionError if the
    source object is not public. May raise further exceptions if creating
    the cloned object fails certain other constraints.
    """
    old_obj = database.OBJECTS[source_id]
    if old_obj["_meta"]["typeof"] != "object":
        raise ValueError("Can only clone objects.")
    if is_visible(old_obj, user):
        # Create a new (cloned) object that belongs to the referenced user.
        new_object_id = add_object(target_name, old_obj["description"], user)
        new_object = database.OBJECTS[new_object_id]
        # Copy all the non-_meta attributes of the old object onto the new
        # clone.
        for k, v in old_obj.items():
            if k != "_meta":
                new_object[k] = v
        return new_object_id
    else:
        raise PermissionError("You can't clone that object.")


def take(obj_id, user):
    """
    Move an object from the current location of the user, into the inventory
    of the user. Can only take things with typeof "object".

    Returns True if successful, may raise exceptions if constraints fail.
    """
    obj = database.OBJECTS[obj_id]
    if obj["_meta"]["typeof"] != "object":
        return False
    location_id = user["_meta"]["location"]
    location = database.OBJECTS[location_id]
    if obj_id in location["_meta"]["contents"]:
        # Update database state.
        location["_meta"]["contents"].remove(obj_id)
        location["_meta"]["fqns"].remove(obj["_meta"]["fqn"])
        user["_meta"]["inventory"].append(obj_id)
        return True
    return False


def give(obj_id, giver, recipient_id):
    """
    Give an object from one user to another (remove from the giver's inventory
    and place the object into the recipients inventory, while updating the
    object's location). It's only possible to give things with typeof "object".

    Giving can only happen if users are in the same location.

    Returns True if successful, otherwise False.
    """
    # Only works if the object is in the giver's inventory.
    if obj_id not in giver["_meta"]["inventory"]:
        return False
    obj = database.OBJECTS[obj_id]
    # Only handle things that are "objects"
    if obj["_meta"]["typeof"] != "object":
        return False
    recipient = database.OBJECTS[recipient_id]
    # Only give between users in the same location.
    if giver["_meta"]["location"] != recipient["_meta"]["location"]:
        return False
    giver["_meta"]["inventory"].remove(obj_id)
    recipient["_meta"]["inventory"].append(obj_id)
    return True


def drop(obj_id, user):
    """
    Drop the referenced object from the user's inventory into the current
    location of the user. It's only possible to drop things in the user's
    inventory.

    Returns True if successful, otherwise False.
    """
    # Only works if the object is in the giver's inventory.
    if obj_id not in user["_meta"]["inventory"]:
        return False
    obj = database.OBJECTS[obj_id]
    room = database.OBJECTS[user["_meta"]["location"]]
    user["_meta"]["inventory"].remove(obj_id)
    room["_meta"]["contents"].append(obj_id)
    room["_meta"]["fqns"].append(obj["_meta"]["fqn"])
    return True


async def look(obj_id, user):
    """
    Give basic information (name, alias and description) of the referenced
    object to the referenced user. If the object is a room a list of the
    exits and things in the room is appended. If it's an exit, display details
    of the destination. If it's a user, also list their inventory.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_visible(obj, user):
        typeof = obj["_meta"]["typeof"]
        context = {
            "name": obj["_meta"]["name"],
            "fqn": obj["_meta"]["fqn"],
            "alias": obj["_meta"]["alias"],
            "description": obj["description"],
            "typeof": typeof,
            "contents": [],
            "exits": [],
            "destination": "",
            "inventory": []
        }
        if typeof == "room":
            # Prepare public contents and exits.
            contents = []
            for item_id in obj["_meta"]["contents"]:
                item = database.OBJECTS[item_id]
                if is_visible(item, user):
                    contents.append(item["_meta"]["name"])
            context["contents"] = contents
            exits = []
            for exit_id in obj["_meta"]["exits_out"]:
                exit = database.OBJECTS[exit_id]
                if is_visible(exit, user):
                    exits.append(exit["_meta"]["name"])
            context["exits"] = exits
        elif typeof == "exit":
            destination_id = obj["_meta"]["destination"]
            destination_obj = database.OBJECTS[destination_id]
            context["destination"] = destination_obj["_meta"]["name"]
        elif typeof == "user":
            inventory = []
            for item_id in obj["_meta"]["inventory"]:
                item = database.OBJECTS[item_id]
                if is_visible(item, user):
                    inventory.append(item["_meta"]["name"])
            context["inventory"] = inventory
        message = await render_template_string(LOOK_TEMPLATE, **context)
        await emit_to_user(user["_meta"]["uuid"], message)


async def detail(obj_fqn, user):
    """
    Give all the details about the referenced object to the referenced user.
    """
    obj_id = database.FQNS[obj_fqn]
    obj = database.OBJECTS[obj_id]
    if obj and is_visible(obj, user):
        typeof = obj["_meta"]["typeof"]
        owner = database.OBJECTS[obj["_meta"]["owner"]]
        context = {
            "uuid": obj_id,
            "name": obj["_meta"]["name"],
            "owner": owner["_meta"]["name"],
            "fqn": obj["_meta"]["fqn"],
            "alias": ", ".join(obj["_meta"]["alias"]),
            "typeof": typeof,
            "public": str(obj["_meta"]["public"]),
        }
        if typeof == "room":
            contents = []
            for item_id in obj["_meta"]["contents"]:
                item = database.OBJECTS[item_id]
                if is_visible(item, user):
                    contents.append(item["_meta"]["name"])
            exits_out = []
            for exit_id in obj["_meta"]["exits_out"]:
                exit = database.OBJECTS[exit_id]
                if is_visible(exit, user):
                    exits_out.append(exit["_meta"]["name"])
            allow = []
            for item_id in obj["_meta"]["allow"]:
                item = database.OBJECTS[item_id]
                if is_visible(item, user):
                    allow.append(item["_meta"]["name"])
            exclude = []
            for item_id in obj["_meta"]["exclude"]:
                item = database.OBJECTS[item_id]
                if is_visible(item, user):
                    exclude.append(item["_meta"]["name"])
            context.update({
                "contents": ", ".join(contents),
                "exits_out": ", ".join(exits_out),
                "allow": ", ".join(allow),
                "exclude": ", ".join(exclude),
            })
        elif typeof == "exit":
            context.update({
                "from": database.OBJECTS[obj["_meta"]["source"]],
                "to": database.OBJECTS[obj["_meta"]["destination"]],
            })
        elif typeof == "user":
            inventory = []
            for item_id in obj["_meta"]["inventory"]:
                item = database.OBJECTS[item_id]
                if is_visible(item, user):
                    inventory.append(item["_meta"]["name"])
            owns = []
            for item_id in obj["_meta"]["owns"]:
                item = database.OBJECTS[item_id]
                if is_visible(item, user):
                    owns.append(item["_meta"]["name"])

            created_on = datetime.utcfromtimestamp(obj["_meta"]["created_on"])
            last_login = obj["_meta"]["last_login"]
            login_date = "Unknown"
            if last_login:
                last_login = datetime.utcfromtimestamp(last_login)
                login_date = last_login.strftime('%Y-%m-%d %H:%M:%S')
            location = "Unknown"
            if obj["_meta"]["location"]:
                location = database.OBJECTS[obj["_meta"]["location"]]
            context.update({
                "inventory": ", ".join(inventory),
                "owns": ", ".join(owns),
                "location": location,
                "created_on": created_on.strftime('%Y-%m-%d %H:%M:%S'),
                "last_login": login_date,
            })
        context.update({
            "attributes": {k: repr(v) for (k, v) in obj.items()
                           if k != "_meta"},
        })
        message = await render_template_string(DETAIL_TEMPLATE, **context)
        await emit_to_user(user["_meta"]["uuid"], message, raw=True)


def add_alias(obj_id, user, alias):
    """
    Add a new alias (a valid object name) to the alias list of the referenced
    object. The object must belong to the referenced user. Returns True if
    succeeded.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_owner(obj, user):
        if is_valid_object_name(alias):
            if alias not in obj["_meta"]["alias"]:
                obj["_meta"]["alias"].append(alias)
                return True
    return False


def remove_alias(obj_id, user, alias):
    """
    Attempt to remove the alias from the referenced object. The object must
    belong to the referenced user. Returns True is success.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_owner(obj, user):
        if alias in obj["_meta"]["alias"]:
            obj["_meta"]["alias"].remove(alias)
            return True
    return False


def set_attribute(obj_id, user, name, value):
    """
    Sets a public attribute on the object. The name of the attribute must be
    a valid object name. The value must be JSON serializable. The object must
    belong to the referenced user. Returns True if success.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_owner(obj, user):
        if is_valid_object_name(name):
            try:
                json.dumps(value)
            except Exception:
                # Swallow the error.
                return False
            obj[name] = value
            return True
    return False


def remove_attribute(obj_id, user, attribute):
    """
    Remove the attribute from the referenced object. The object myst belong to
    the referenced user. The user may NOT remove attributes found in an
    exclusion list found within this function (these are used by the
    game). Returns True if success.
    """
    exclude = ["_meta", "description", "leave_user", "leave_room",
               "arrive_room", ]
    if attribute not in exclude:
        obj = database.OBJECTS[obj_id]
        if obj and is_owner(obj, user):
            if attribute in obj:
                del obj[attribute]
                return True
    return False


def add_allow(obj_id, user, username):
    """
    Add a referenced user to the "allow" list of users associated with a room.
    If this list contains members ONLY users in this list are allowed to
    enter the room. This overrides the "exclude" list. Returns boolean
    indication of success.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_owner(obj, user):
        if obj["_meta"]["typeof"] == "room":
            user_id = database.USERS.get(username)
            if user_id and user_id not in obj["_meta"]["allow"]:
                obj["_meta"]["allow"].append(user_id)
                return True
    return False


def remove_allow(obj_id, user, username):
    """
    Remove the referenced user from a room's "allow" list. Returns a boolean
    indication of success.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_owner(obj, user):
        if obj["_meta"]["typeof"] == "room":
            user_id = database.USERS.get(username)
            if user_id and user_id in obj["_meta"]["allow"]:
                obj["_meta"]["allow"].remove(user_id)
                return True
    return False


def add_exclude(obj_id, user, username):
    """
    Add a referenced user to the "exclude" list of users associated with a
    room. If this list contains members ONLY users NOT IN this list are allowed
    to enter the room. This can be overridden by the "allow" list. Returns
    boolean indication of success.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_owner(obj, user):
        if obj["_meta"]["typeof"] == "room":
            user_id = database.USERS.get(username)
            if user_id and user_id not in obj["_meta"]["exclude"]:
                obj["_meta"]["exclude"].append(user_id)
                return True
    return False


def remove_exclude(obj_id, user, username):
    """
    Remove the referenced user from a room's "exclude" list. Returns a boolean
    indication of success.
    """
    obj = database.OBJECTS[obj_id]
    if obj and is_owner(obj, user):
        if obj["_meta"]["typeof"] == "room":
            user_id = database.USERS.get(username)
            if user_id and user_id in obj["_meta"]["exclude"]:
                obj["_meta"]["exclude"].remove(user_id)
                return True
    return False


async def emit_to_room(room_id, message, exclude=None):
    """
    Emit a message to all the users in the referenced room except those whose
    UUIDs are in the "exclude" list.
    """
    if exclude is None:
        exclude = []
    room = database.OBJECTS[room_id]
    users = []
    for uuid in room["_meta"]["contents"]:
        item = database.OBJECTS[uuid]
        if item["_meta"]["typeof"] == "user":
            if uuid not in exclude:
                users.append(item["_meta"]["uuid"])
    for user in users:
        await emit_to_user(user, message)


async def emit_to_user(user_id, message, raw=False):
    """
    Emit a message to the referenced user. All messages are run through
    Markdown unless raw is True.
    """
    ws = database.CONNECTIONS.get(user_id)
    if ws:
        await ws.send(str(message))
