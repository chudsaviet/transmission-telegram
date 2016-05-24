class Credentials:
    def __init__(self, address, port, user, password):
        self.address = address
        self.port = int(port)
        self.user = user
        self.password = password

    def __str__(self):
        return 'Address = %s\nPort = %d\nUser = %s\nPassword = %s\n' \
               % (self.address, self.port, self.user, self.password)