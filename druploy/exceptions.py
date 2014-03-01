
class AgileProjectError(Exception):
    pass


class CreateError(AgileProjectError):
    pass


class AlreadyExistsError(CreateError):
    pass


class ValidationError(AgileProjectError):
    pass


