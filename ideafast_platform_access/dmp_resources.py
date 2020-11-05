
import importlib.resources


def read_text_resource(name) -> str:
    """
    Returns the text content of a resource file located in the
    'ideafast_platform_access.resources' package
    """
    return importlib.resources.read_text('ideafast_platform_access.resources', name)
