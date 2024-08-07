class ErrArgException(Exception):
    def __init__(self, message="Некорректный аргумент парсинга"):
        self.message = message
        super().__init__(self.message)
