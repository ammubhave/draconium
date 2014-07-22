def render(attrs, stack, body):
    if stack.get_parent_tag().name != 'html':
        raise Exception('Parent tag must be html')
    return """<body role="document">%s<!-- Bootstrap core JavaScript
    ================================================== -->
    <!-- Placed at the end of the document so the pages load faster -->
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script></body>""" % body
