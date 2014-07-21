class config:
    rules = None

    SOURCES_DIRS = [
        'sample/templates',
    ]

    SOURCES_FILES = [
    ]

    entityref_allowed = ['amp', 'nbsp', 'lt', 'gt']

    @staticmethod
    def import_rules():
        import importlib
        config.rules = importlib.import_module('rules')
