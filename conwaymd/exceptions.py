"""
# Conway-Markdown: exceptions.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Exception classes.
"""


class CommittedMutateException(Exception):
    pass


class MissingAttributeException(Exception):
    _missing_attribute: str

    def __init__(self, missing_attribute: str):
        self._missing_attribute = missing_attribute

    @property
    def missing_attribute(self) -> str:
        return self._missing_attribute


class UncommittedApplyException(Exception):
    pass


class UnrecognisedLabelException(Exception):
    pass
