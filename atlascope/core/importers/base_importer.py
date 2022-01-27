from inspect import signature, Parameter
from rest_framework.exceptions import APIException


class AtlascopeImporter:
    def __init__(self):
        self.content = None
        self.metadata = None

    @classmethod
    def get_schema(self):
        return [
            {
                "name": name,
                "class": param.annotation.__name__,
                "required": param.default == Parameter.empty,
            }
            for name, param in signature(self.perform_import).parameters.items()
            if name != 'self'
        ]

    @classmethod
    def get_parameters(self, required=False):
        return [param['name'] for param in self.get_schema() if not required or param['required']]

    def raise_schema_exception(self):
        raise APIException(
            f"This importer function accepts the following arguments: {self.get_schema()}"
        )

    def perform_import(self, **kwargs):
        pass

    def run(self, **kwargs):
        if any(kwarg not in self.get_parameters() for kwarg in kwargs) or any(
            required not in kwargs for required in self.get_parameters(required=True)
        ):
            self.raise_schema_exception()

        # TODO: This can be made asynchronous later
        # Since param checking is done before this,
        #  the user will be warned synchronously if a param is missing.
        self.perform_import(**kwargs)
        if not self.content:
            raise APIException(f'{self.__class__.__name__} has failed.')
