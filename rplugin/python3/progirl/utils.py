from typing import Callable, Any


class AttrDict(dict):
    def __getattribute__(self, name):
        try:
            attrib = super().__getattribute__(name)
        except AttributeError:
            attrib = super().__getitem__(name)
        return attrib

    def __setattr__(self, name, value):
        try:
            super().__getattribute__(name)
        except AttributeError:
            super().__setitem__(name, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
            super().__delitem__(name)


def unpack_args(base_func: Callable) -> Callable:

    def args_accessor(
            *args,
            **kwargs,
    ) -> Any:
        pass  # TODO

    return args_accessor


def neget(obj, default_obj=None, nobj=""):
    """Not Equal get (for default: Not empty string get)

    :return: obj if obj != nobj else default_obj
    """
    return obj if obj != nobj else default_obj


def niget(obj, default_obj=None, nobj=None):
    """Not Is get (for default: Not is None get)

    :return: `obj` if it is not `nobj` else `default_obj`
    """
    return obj if obj is not nobj else default_obj
