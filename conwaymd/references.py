"""
# Conway-Markdown: references.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

References for links and images.
"""

from typing import NamedTuple, Optional

from conwaymd.exceptions import UnrecognisedLabelException


class Reference:
    """
    A reference to be used by links and images.

    For a given «label» (normalised to lower case), a reference consists of
    - «attribute specifications»
    - «uri»
    - «title»
    where «uri» is `href` for links and `src` for images.
    """
    _attribute_specifications: Optional[str]
    _uri: str
    _title: str

    def __init__(self, attribute_specifications: Optional[str], uri: str, title: str):
        self._attribute_specifications = attribute_specifications
        self._uri = uri
        self._title = title

    @property
    def attribute_specifications(self) -> Optional[str]:
        return self._attribute_specifications

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def title(self) -> str:
        return self._title


class ReferenceMaster:
    """
    Object storing references to be used by links and images.
    """
    _reference_from_label: dict[str, 'Reference']

    def __init__(self):
        self._reference_from_label = {}

    def store_definition(self, label: str, attribute_specifications: Optional[str], uri: str, title: str):
        label = ReferenceMaster.normalise_label(label)
        self._reference_from_label[label] = Reference(attribute_specifications, uri, title)

    def load_definition(self, label: str) -> 'ReferenceDefinition':
        label = ReferenceMaster.normalise_label(label)

        try:
            reference = self._reference_from_label[label]
        except KeyError:
            raise UnrecognisedLabelException

        attribute_specifications = reference.attribute_specifications
        uri = reference.uri
        title = reference.title

        return ReferenceDefinition(attribute_specifications, uri, title)

    @staticmethod
    def normalise_label(label: str) -> str:
        return label.lower()


class ReferenceDefinition(NamedTuple):
    attribute_specifications: Optional[str]
    uri: str
    title: str
