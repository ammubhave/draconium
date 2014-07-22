def render(attrs, stack, body):
    if stack.get_parent_tag().name != 'head':
        raise Exception('Parent tag must be head')
    return '<title>%s</title>' % body
