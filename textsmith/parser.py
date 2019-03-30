"""
Functions for parsing user input. Calls into the game logic layer to make
stuff happen, once the instructions from the user have been parsed.

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
import random
from textsmith import logic, database


async def eval(user_id, message):
    """
    Evaluate the user's input message. If there's an error, recover by sending
    the error message from the associated exception object.
    """
    try:
        await parse(user_id, message)
    except Exception as ex:
        # TODO: Log this somewhere
        await handle_exception(ex, user_id)


async def handle_exception(exception, user_id):
    """
    Given an exception raised in the logic or parsing layer of the application,
    extract the useful message which explains what the problem is, and turn
    it into a message back to the referenced user.
    """
    await logic.emit_to_user(user_id, str(exception))


async def parse(user_id, message):
    """
    Parse the incoming message from the referenced user.

    There are four special characters which, if they start the message, act as
    shortcuts for common activities:

    " - make it appear like the user is saying whatever follows in the message.
    ! - make it appear like the user is shouting the message.
    : - "emote" the message directly as "username " + message
    @ - make it appear like the user is saying something directly to another.

    Next the parser expects the first word of the message to be a verb. If this
    verb is one of several built-in commands, the remainder of the message is
    passed as a single string into the relevant function for that verb (as
    defined in this module).

    If the verb isn't built into the game engine, then the parser breaks the
    raw input apart into sections that follow the following patterns:

    VERB
    VERB DIRECT-OBJECT
    VERB DIRECT-OBJECT PREPOSITION INDIRECT-OBJECT

    Examples of these patterns are:

    look
    take sword
    give sword to andrew
    say "Hello there" to nicholas

    (Note, English articles ("a", "the" etc) shouldn't be used in commands.)

    Anything enclosed in double-quotes (") is treated as a single entity if
    in the direct-object or indirect-object position. The parser will try to
    match objects against available aliases available in the current room's
    context. The following reserved words are synonyms:

    "me" - the player.
    "here" - the current location.

    At this point the parser has identified the verb string, and the direct and
    indirect objects. It looks for a matching verb on the four following
    objects (in order or precedence):

    1. The player.
    2. The room the player is in (including where the verb is an exit name).
    3. The direct object (if an object in the database).
    4. The indirect object (if an object in the database).

    The game checks each object in turn and, if it finds an attribute that
    matches the verb it attempts to "execute" it.

    For now, the attribute's value will be returned.

    In later iterations (hopefully) there will be a simply scripting language
    an attributes may contain code to run. If these "executable" attributes
    are found them the associated code will be run with the following objects
    in scope:

    this - a reference to the object which matched the verb.
    player - a reference to the player who issued the command.
    room - a reference to the room in which the player is situated.
    direct_object - either the matching object or raw string for the direct
      object. This could be None.
    preposition - a string containing the preposition. This could be None.
    indirect_object - either the matching object or raw string for the indirect
      object. This could be None.

    The player, room, direct_object and indirect_object objects can all be
    passed to a special "emit" function along with a message to display to
    that object (if the object is a user, it'll be sent just to them, if the
    object is a room, the message will be sent to all players in that room).

    That's it!
    """
    # Don't do anything with empty messages.
    if not message.strip():
        return

    # Grab the objects needed to help parse the message.
    user = database.OBJECTS[user_id]
    room = database.OBJECTS[user["_meta"]["location"]]

    # Check and process special "shortcut" characters.
    message = message.lstrip()
    if message.startswith('"'):
        # " The user is saying something to everyone in their location.
        return await say(user, room, message[1:])
    elif message.startswith("!"):
        # ! The user is shouting something to everyone in their location.
        return await shout(user, room, message[1:])
    elif message.startswith(":"):
        # : The user is emoting something to everyone in their location.
        return await emote(user, room, message[1:])
    elif message.startswith("@"):
        # @ The user is saying something to a specific person.
        return await tell(user, room, message[1:])

    # Check for verbs built into the game.
    verb_split = message.split(" ", 1)
    verb = verb_split[0]  # The first word in the message is the verb.
    args = ""
    if len(verb_split) == 2:
        # The remainder of the message contains the "arguments" to use with the
        # verb, and may ultimately contain the direct and indirectt objects
        # (if needed).
        args = verb_split[1]
    # Builtins is a dictionary. The key is a tuple of strings. Each string in
    # the tuple is an alias for a builtin verb. The associated value is an
    # async function with a common call signature which should be awaited from
    # if the verb entered by the user is found in the key/tuple.
    for k in BUILTINS:
        if verb in k:
            # Verb name or alias found, so return the result of running the
            # async function associated with the key.
            return await BUILTINS[k](user, room, args)

    # Attempt to grab the objects needed for further parsing.
    direct_obj, preposition, indirect_obj = await get_objects(user, room, args)

    # Try to return a result by interrogating the user, room, direct and
    # indirect objects. Ensure the game doesn't inadvertently reveal the
    # contents of _meta.
    if verb != "_meta":
        if verb in user:
            return await logic.emit_to_user(user_id, user[verb])
        elif verb in room:
            return await logic.emit_to_user(user_id, room[verb])
        elif isinstance(direct_obj, dict) and verb in direct_obj:
            return await logic.emit_to_user(user_id, direct_obj[verb])
        elif isinstance(indirect_obj, dict) and verb in indirect_obj:
            return await logic.emit_to_user(user_id, indirect_obj[verb])

    # If the verb is the name or alias of an exit in the current room, then
    # follow that exit to a new location.
    for exit_id in room["_meta"]["exits_out"]:
        exit = database.OBJECTS[exit_id]
        name = exit["_meta"]["name"]
        alias = exit["_meta"]["alias"]
        if verb == name or verb in alias:
            return await logic.move(user_id, exit_id, user_id)

    # Getting here means the parser can't work out how to process the user's
    # input, so say something cheerful, helpful, funny or, if defined as an
    # attribute of the room, whatever is in "huh". :-)
    if "huh" in room:
        # The owner of the room has defined a response for not understanding
        # user input.
        return await logic.emit_to_user(user_id, room["huh"])
    else:
        # As a last resort, choose a stock fun response. ;-)
        response = random.choice([
            "I don't understand that.",
            "Nope. No idea what you're on about.",
            "I don't know what you mean.",
            "Try explaining that in a way I can understand.",
            "Yeah right... as if I know what you're on about. :-)",
            "Let me try tha... nope. I have no idea what you're on about.",
            "Ummm... you're not making sense. Try again, but with feeling!",
            "No idea. Try giving me something I understand.",
            "Huh? I don't understand. Maybe ask someone for help?",
            "Try using commands I understand.",
        ])
        i_give_up = f'"{message}", ' + response
        return await logic.emit_to_user(user_id, i_give_up)


async def get_objects(user, room, args):
    """
    Given a string representing the remaining input after the verb, return a
    the direct object, preposition and indirect object in a tuple. These three
    values may all be None, if no such objects are found within the string. The
    objects may be multiple words if they're bound by double quotes ("). E.g.
    "large troll" might be an individual valid matching object.

    If the strings identifying the direct and indirect objects refer to objects
    in the current room or the user's inventory either by name or alias, return
    the *objects* (not strings) instead.
    """
    # Nothing left in the message, nothing more to do.
    if not args:
        return (None, None, None)
    direct_obj = None
    preposition = None
    indirect_obj = None
    word_pos = 0
    words = args.split()
    word_len = len(words)
    direct_obj = words[word_pos]
    if direct_obj.startswith('"'):
        direct_obj = direct_obj[1:]  # cut off leading quote.
        while word_pos < word_len:
            # Keep adding words to the direct object until...
            word_pos += 1
            direct_obj += " " + words[word_pos].strip()
            if '"' in direct_obj:
                # ...a word contains a quotation mark.
                if direct_obj.endswith('"'):
                    direct_obj = direct_obj[:-1]  # Remove trailing quote.
                    break
                else:
                    # The quotation mark is in the wrong place. Report the
                    # problem.
                    raise ValueError("Unclosed quotation marks.")
    # The next word MUST be a preposition (which we ignore for now).
    if word_pos < word_len - 1:
        word_pos += 1
        preposition = words[word_pos]
    # Finally, process the indirect object.
    if word_pos < word_len - 1:
        word_pos += 1
        # Indirect object must be made up from all the remaining words.
        indirect_obj = words[word_pos:]
        if len(indirect_obj) == 1:
            indirect_obj = indirect_obj[0]  # Indirect object is single word.
            if indirect_obj.startswith('"') or indirect_obj.endswith('"'):
                # The indirect object was not quoted as expected, so report
                # the problem.
                raise ValueError("Unclosed quotation marks.")
        else:
            indirect_obj = ' '.join(indirect_obj)  # Join all remaining words.
            if indirect_obj.startswith('"') and indirect_obj.endswith('"'):
                indirect_obj = indirect_obj[1:-1]  # Remove quotes.
            else:
                # The indirect object was not quoted as expected, so report
                # the problem.
                raise ValueError("Unclosed quotation marks.")
    # If the direct_obj or indirect_obj refer to an object in scope (either
    # contained within the current room, or in the user's inventory), replace
    # the string with the referenced object instead.
    dobj_match = logic.get_object_from_context(direct_obj, room, user)
    iobj_match = logic.get_object_from_context(indirect_obj, room, user)
    dobj_len = len(dobj_match)
    iobj_len = len(iobj_match)
    if dobj_len == 1:
        # There's exactly one object that matches, so make that the
        # direct object.
        direct_obj = dobj_match[0]
    elif dobj_len > 1:
        # Too many matches, so raise an error telling the user to disambiguate.
        matches = [x["_meta"]["name"] + "(" + x["_meta"]["fqn"] + ")"
                   for x in dobj_match]
        msg = ("Multiple matches (via direct object name or alias). "
               "Please disambiguate between: " + ', '.join(matches))
        raise ValueError(msg)
    if iobj_len == 1:
        # There's exactly one object that matches, so make that the
        # indirect object.
        indirect_obj = iobj_match[0]
    elif iobj_len > 1:
        # Too many matches, so raise an error telling the user to disambiguate.
        matches = [x["_meta"]["name"] + "(" + x["_meta"]["fqn"] + ")"
                   for x in iobj_match]
        msg = ("Multiple matches (via indirect object name or alias). "
               "Please disambiguate between: " + ', '.join(matches))
        raise ValueError(msg)
    # Got them!
    return (direct_obj, preposition, indirect_obj)


# BUILTIN FUNCTIONS
async def say(user, room, message):
    """
    Say a message to the the whole room.
    """
    if message:
        user_message = f'> You say, "*{message}*".'
        username = user["_meta"]["name"]
        room_message = f'> {username} says, "*{message}*".'
        user_id = user["_meta"]["uuid"]
        room_id = room["_meta"]["uuid"]
        await logic.emit_to_user(user_id, user_message)
        await logic.emit_to_room(room_id, room_message, exclude=[user_id, ])


async def shout(user, room, message):
    """
    Say a message to the the whole room.
    """
    if message:
        user_message = f'> You shout , "**{message}**".'
        username = user["_meta"]["name"]
        room_message = f'> {username} shouts, "**{message}**".'
        user_id = user["_meta"]["uuid"]
        room_id = room["_meta"]["uuid"]
        await logic.emit_to_user(user_id, user_message)
        await logic.emit_to_room(room_id, room_message, exclude=[user_id, ])


async def emote(user, room, message):
    """
    Emote something to the the whole room.
    """
    if message:
        username = user["_meta"]["name"]
        emote = f'{username} {message}'
        room_id = room["_meta"]["uuid"]
        await logic.emit_to_room(room_id, emote)


async def tell(user, room, message):
    """
    Emote something to the the whole room.
    """
    if message:
        split = message.split(" ", 1)
        if len(split) == 2:
            recipient = split[0]
            # Check the recipient exists.
            if recipient not in database.USERS:
                raise ValueError("I don't know who {recipient} is.")
            recipient_id = database.USERS.get(recipient)
            recipient_obj = database.OBJECTS[recipient_id]
            # Check the recipient user is in the room.
            if recipient_obj["_meta"]["location"] != room["_meta"]["uuid"]:
                raise ValueError("Can't do that, {recipient} isn't here.")
            message = split[1]
            user_message = f'> You say to {recipient}, "*{message}*".'
            username = user["_meta"]["name"]
            recipient_message = f'> {username} says, "*{message}*" to you.'
            room_message = f'> {username} says to {recipient}, "*{message}*".'
            user_id = user["_meta"]["uuid"]
            room_id = room["_meta"]["uuid"]
            await logic.emit_to_user(user_id, user_message)
            await logic.emit_to_user(recipient_id, recipient_message)
            await logic.emit_to_room(room_id, room_message,
                                     exclude=[user_id, recipient_id])


async def create(user, room, message):
    """
    Of the form:

    create newobjname A brief description of the object.
    """
    split_message = message.split(' ', 1)
    if len(split_message) == 2:
        name = split_message[0]
        description = split_message[1]
        logic.add_object(name, description, user)
        msg = f'Created object called "{name}". Check your inventory.'
        return await logic.emit_to_user(user["_meta"]["uuid"], msg)
    else:
        raise RuntimeError("Not enough arguments to create object.")


async def build(user, room, message):
    """
    Of the form:

    build newroomname A description of the new room.
    """
    split_message = message.split(' ', 1)
    if len(split_message) == 2:
        name = split_message[0]
        description = split_message[1]
        room_id = logic.build(name, description, user)
        room = database.OBJECTS[room_id]
        fqn = room["_meta"]["fqn"]
        msg = (f"Created new room {name} ({fqn}). Use the 'connect' command "
               "to connect it to other rooms.")
        return await logic.emit_to_user(user["_meta"]["uuid"], msg)
    else:
        raise RuntimeError("Not enough arguments to create object.")


async def connect(user, room, message):
    """
    Of the form:

    connect room/fqn exitname A description of the new exit.
    """
    split_message = message.split(' ', 2)
    if len(split_message) == 3:
        destination_fqn = split_message[0]
        destination_id = database.FQNS.get(destination_fqn)
        if destination_id is None:
            raise ValueError(f"The room {destination_fqn} does not exist.")
        destination = database.OBJECTS[destination_id]
        exitname = split_message[1]
        description = split_message[2]
        exit_id = logic.add_exit(exitname, description, user, room,
                                 destination)
        exit = database.OBJECTS[exit_id]
        fqn = exit["_meta"]["fqn"]
        sname = room["_meta"]["name"]  # source room name.
        dname = destination["_meta"]["name"]  # destination room name.
        msg = f"Created new exit {exitname} ({fqn}) from {sname} to {dname}."
        return await logic.emit_to_user(user["_meta"]["uuid"], msg)
    else:
        raise RuntimeError("Not enough arguments to create object.")


async def describe(user, room, message):
    """
    Of the form:

    describe objectname A description of the object.
    """
    split_message = message.split(' ', 1)
    if len(split_message) == 2:
        name = split_message[0]
        matches = logic.get_object_from_context(name, room, user)
        if len(matches) == 1:
            obj_id = matches[0]["_meta"]["uuid"]
            description = split_message[1]
            if logic.set_attribute(obj_id, user, "description", description):
                msg = "Description updated."
                return await logic.emit_to_user(user["_meta"]["uuid"], msg)
            else:
                raise PermissionError("You can't do that.")
        elif matches:
            # Too many matches, tell the user to disambiguate.
            matches = [x["_meta"]["name"] + "(" + x["_meta"]["fqn"] + ")"
                       for x in matches]
            msg = ("Multiple matches (via direct object name or alias). "
                   "Please disambiguate between: " + ', '.join(matches))
            raise ValueError(msg)
        else:
            raise ValueError("No such object.")
    else:
        raise RuntimeError("Not enough arguments to describe object.")


async def delete(user, room, message):
    """
    Of two forms:

    1. Delete an object/room/exit:

    delete object/fqn

    2. Delete an attribute from an object:

    delete object/fqn attributename
    """
    split_message = message.split()
    if len(split_message) == 1:
        # Delete an object.
        obj_fqn = split_message[0]
        obj_id = database.FQNS.get(obj_fqn)
        if obj_id:
            obj = database.OBJECTS[obj_id]
            typeof = obj["_meta"]["typeof"]
            result = False
            if typeof == "object":
                # Delete a vanilla object.
                result = logic.delete_object(obj_id, user)
            elif typeof == "room":
                # Delete a room.
                result = await logic.delete_room(obj_id, user)
            elif typeof == "exit":
                # Delete an exit.
                result = logic.delete_exit(obj_id, user)
            else:
                # You can't delete users!
                raise ValueError("You cannot delete users.")
            name = obj["_meta"]["fqn"]
            if result:
                msg = f"Deleted {name}."
                return await logic.emit_to_user(user["_meta"]["uuid"], msg)
            else:
                raise RuntimeError(f"Could not delete {name}.")
        else:
            raise ValueError(f"There is no object called {obj_fqn}.")
    elif len(split_message) == 2:
        # Delete an attribute from an object.
        obj_fqn = split_message[0]
        obj_id = database.FQNS.get(obj_fqn)
        if obj_id:
            obj = database.OBJECTS[obj_id]
            attr = split_message[1]
            no_delete = ["_meta", "description"]
            if attr not in no_delete:
                del obj[attr]
                msg = f"Deleted {attr} from the object {obj_fqn}."
                return await logic.emit_to_user(user["_meta"]["uuid"], msg)
            else:
                raise RuntimeError("You cannot delete that attribute.")
        else:
            raise ValueError(f"There is no object called {obj_fqn}.")
    else:
        raise RuntimeError("Wrong number of arguments to delete an object "
                           "or attribute.")


async def teleport(user, room, message):
    """
    Of the form:

    teleport room/fqn
    """
    split_message = message.split()
    if len(split_message) == 1:
        fqn = split_message[0]
        obj_id = database.FQNS.get(fqn)
        if obj_id:
            obj = database.OBJECTS[obj_id]
            if obj["_meta"]["typeof"] == "room":
                return await logic.teleport(user["_meta"]["uuid"], fqn)
            else:
                raise TypeError("You can only teleport to a room.")
        else:
            raise ValueError(f"No room called {fqn}.")
    else:
        raise RuntimeError("Wrong number of arguments to teleport.")


async def clone(user, room, message):
    """
    Of the form:

    clone object/fqn newname
    """
    split_message = message.split()
    if len(split_message) == 2:
        fqn = split_message[0]
        obj_id = database.FQNS.get(fqn)
        target = split_message[1]
        if obj_id:
            obj = database.OBJECTS[obj_id]
            if obj["_meta"]["typeof"] == "object":
                if logic.clone(obj_id, target, user):
                    msg = f"Cloned object {fqn} as {target}"
                    return await logic.emit_to_user(user["_meta"]["uuid"], msg)
                else:
                    raise RuntimeError(f"Could not clone {fqn}.")
            else:
                raise TypeError("You can only clone an object.")
        else:
            raise ValueError(f"No object called {fqn}.")
    else:
        raise RuntimeError("Wrong number of arguments to clone.")


async def inventory(user, room, message):
    """
    Of the form:

    inventory
    """
    items = [database.OBJECTS[i]["_meta"]["name"]
             for i in user["_meta"]["inventory"]]
    msg = f"You are carrying: {items}"
    return await logic.emit_to_user(user["_meta"]["uuid"], msg)


async def take(user, room, message):
    """
    Of the form:

    take objectname
    """
    split_message = message.split()
    if len(split_message) == 1:
        name = split_message[0]
        matches = logic.get_object_from_context(name, room, user)
        if len(matches) == 1:
            obj_id = matches[0]["_meta"]["uuid"]
            if logic.take(obj_id, user):
                msg = "You take the {name}."
                return await logic.emit_to_user(user["_meta"]["uuid"], msg)
            else:
                raise RuntimeError("You can't take the {name}.")
        elif matches:
            # Too many matches, tell the user to disambiguate.
            matches = [x["_meta"]["name"] + "(" + x["_meta"]["fqn"] + ")"
                       for x in matches]
            msg = ("Multiple matches (via direct object name or alias). "
                   "Please disambiguate between: " + ', '.join(matches))
            raise ValueError(msg)
        else:
            raise ValueError("No such object.")
    else:
        raise RuntimeError("Wrong number of arguments to take an object.")


async def drop(user, room, message):
    """
    Of the form:

    drop objectname
    """
    split_message = message.split()
    if len(split_message) == 1:
        name = split_message[0]
        for obj_id in user["_meta"]["inventory"]:
            obj = database.OBJECTS[obj_id]
            if obj["_meta"]["name"] == name:
                if logic.drop(obj_id, user):
                    usr_msg = f"You drop the {name}."
                    username = user["_meta"]["name"]
                    room_msg = f"{username} drops {name} here."
                    user_id = user["_meta"]["uuid"]
                    room_id = room["_meta"]["uuid"]
                    await logic.emit_to_user(user_id, usr_msg)
                    await logic.emit_to_room(room_id, room_msg,
                                             exclude=[user_id, ])
                    break
                else:
                    raise RuntimeError(f"You can't drop {name} here.")
        else:
            raise ValueError("No such object.")
    else:
        raise RuntimeError("Wrong number of arguments to take an object.")


async def annotate(user, room, message):
    """
    Of the form:

    set object/fqn attr Some value to place in the attribute on the object.
    """
    split_message = message.split(' ', 2)
    if len(split_message) == 3:
        obj_fqn = split_message[0]
        obj_id = database.FQNS.get(obj_fqn)
        if obj_id is None:
            raise ValueError(f"The object {obj_fqn} does not exist.")
        attribute = split_message[1]
        value = split_message[2]
        if logic.set_attribute(obj_id, user, attribute, value):
            msg = f"Annotated attribute {attribute} onto object {obj_fqn}."
            return await logic.emit_to_user(user["_meta"]["uuid"], msg)
        else:
            raise RuntimeError(f"You can't annotate the object {obj_fqn}.")
    else:
        raise RuntimeError("Not enough arguments to create object.")


async def look(user, room, message):
    """
    Of the form:

    look objectname

    or (for the current room):

    look
    """
    split_message = message.split()
    name = ""
    if len(split_message) == 0:
        name = "here"
    if len(split_message) == 1:
        name = split_message[0]
    if name:
        matches = logic.get_object_from_context(name, room, user)
        if len(matches) == 1:
            obj_id = matches[0]["_meta"]["uuid"]
            return await logic.look(obj_id, user)
        elif matches:
            # Too many matches, tell the user to disambiguate.
            matches = [x["_meta"]["name"] + "(" + x["_meta"]["fqn"] + ")"
                       for x in matches]
            msg = ("Multiple matches (via direct object name or alias). "
                   "Please disambiguate between: " + ', '.join(matches))
            raise ValueError(msg)
        else:
            raise ValueError("No such object.")
    else:
        raise RuntimeError("Wrong number of arguments to look.")


async def detail(user, room, message):
    """
    Of the form:

    detail object/fqn
    """
    split_message = message.split()
    if len(split_message) == 1:
        fqn = split_message[0]
        if fqn in database.FQNS:
            return await logic.detail(fqn, user)
        else:
            raise ValueError("Unknown object.")
    else:
        raise RuntimeError("Wrong number of arguments for object details.")


async def show_help(user, room, message):
    """
    Of the form:

    help
    """
    msg = "Help is available [on this page](/help)."
    return await logic.emit_to_user(user["_meta"]["uuid"], msg)


# Contain references to the game's builtin functions.
BUILTINS = {
    # Create a new object.
    ("create", "make", "cr", "mk"): create,
    # Build a new room.
    ("build", ): build,
    # Connect two rooms together.
    ("connect", "co"): connect,
    # Set the description of an object/room/exit/user.
    ("describe", "desc"): describe,
    # Destroy an object or delete an attribute on an object.
    ("remove", "delete", "destroy", "rm", "del", ): delete,
    # Teleport the user somewhere else.
    ("teleport", ): teleport,
    # Clone an object.
    ("clone", "copy", "cp", ): clone,
    # List the objects in the user's inventory which are visible.
    ("inventory", "inv", ): inventory,
    # Take an object from the room into the user's inventory.
    ("take", "get", ): take,
    # Drop an object from the user's inventory into the room.
    ("drop", "leave", ): drop,
    # Set an attribute on an object with associated value.
    ("set", "attr", "annotate"): annotate,
    # Look at either the current room or a specific object.
    ("look", "lk", "l"): look,
    # Get a detailed summary of the specified object or current room.
    ("detail", "examine", "ex"): detail,
    # Display a link to help.
    ("help", "?"): show_help,
}

"""
To be added at a later time...

    # Set the visibility of an object.
    ["visibility", "viz", "vis", ]:
    # Move to another place via an exit.
    ["go", "move", "exit", "mv", ]:
    # Give an object to another user.
    ["give", ]:
    # Add an alias to the specified object.
    ["addalias", "alias+", "ali+", ]:
    # Remove an alias from the specified object.
    ["rmalias", "alias-", "ali-", ]:
    # Add a user to the allow list for the current room.
    ["addallow", "allow+", "alw+", ]:
    # Remove a user from the allow list for the current room.
    ["rmallow", "allow-", "alw-", ]:
    # Add a user to the exclude list for the current room.
    ["addexclude", "exclude+", "ex+"]:
    # Remove a user from the exclude list for the current room.
    ["rmexclude", "exclude-", "ex-"]:
"""
