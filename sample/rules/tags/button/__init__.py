def render(attrs, stack, body):
    btn_type = attrs.get('type', 'default')
    if btn_type not in ['default', 'primary']:
        raise Exception('invalid button type')
    return '<button type="button" class="btn btn-%s">%s</button>' \
        % (btn_type, body)
