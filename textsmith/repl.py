#!/usr/bin/env python3
"""
txtsmith REPL for testing purposes.
"""
from script import __version__ as version
from script.interpreter import run


def quit():
    """
    Called when exiting the REPL.
    """
    print("\nBye!")


print(f"TextSmithScript version {version}")
print("(c) 2019 Nicholas H.Tollervey")
print('Type "(help)" for more information. CTRL-C or "(exit)" to exit.')
context = {}
while True:
    try:
        code = input(">>> ").strip()
        if code.replace(' ', '') == "(exit)":
            quit()
            break
        if code:
            result = run(code, context)
            if result is not None:
                print(result)
    except KeyboardInterrupt:
        quit()
        break
    except KeyError as ex:
        print(f"Unknown symbol {ex}.")
    except Exception as ex:
        print(repr(ex))
