from .templates.base import base


def render(attrs, stack, body):
    return base(searchList={
        'content': body,
    }).respond()
