from .OpenStackKeywords import OpenStackKeywords
from .version import VERSION

_version_ = VERSION


class OpenStackLibrary(OpenStackKeywords):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'