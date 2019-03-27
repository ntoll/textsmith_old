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
from textsmith import logic


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

    Anything enclosed in double-quotes (") is treated as a single entity. The
    parser will try to match objects against available aliases available in the
    current room's context. The following reserved words are synonyms:

    "me" - the player.
    "here" - the current location.

    At this point the parser has identified the verb string, and the direct and
    indirect objects. It looks for a matching verb on the four following
    objects (in order or precedence):

    1. The player.
    2. The room the player is in.
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

