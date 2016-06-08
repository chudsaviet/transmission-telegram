import configparser


class BotConfig:
    def __init__(self, path):

        parser = configparser.ConfigParser()

        # open the file implicitly because parser.read() will not fail if file is not readable
        file = open(path)
        parser.read_file(file)
        file.close()

        if 'Bot' not in parser.sections():
            raise Exception('All parameters must reside in section ''Bot''')

        bot_section = parser['Bot']

        self.address = bot_section.get('address', 'localhost')

        port_string = bot_section.get('port', '9091')
        try:
            self.port = int(port_string)
        except ValueError:
            raise ValueError('Port ''%s'' is invalid' % port_string)

        try:
            self.user = bot_section.get('user')
        except KeyError:
            self.user = None

        try:
            self.password = bot_section.get('password')
        except KeyError:
            self.password = None

        if self.password and not self.user:
            raise Exception('Password with no user name is meaningless')

        self.token = bot_section.get('token', '')
        if not self.token:
            raise Exception('Telegram token is required')

        self.secret = bot_section.get('secret', '')
        if not self.secret:
            raise Exception('Secret is required')

        try:
            self.persistence_file = bot_section.get('persistence_file')
        except KeyError:
            self.persistence_file = None

    def __str__(self):
        result = '{address:<%s> ' \
                 'port:<%d> ' % (self.address, self.port)

        if not self.user:
            result += 'user:None '
        else:
            result += 'user:<%s> ' % self.user

        if not self.password:
            result += 'password:None'
        else:
            result += 'password:present '

        result += 'token:present '
        result += 'secret:present '
        result += 'persistence_file:<%s>}' % self.persistence_file

        return result

    def __repr__(self):
        return '{address:''%s'' port:%d user:''%s'' password:''%s'' ' \
               'token:''%s'' secret:''%s'' persistence_file:''%s''}' \
               % (self.address, self.port, self.user, self.password,
                  self.token, self.secret, self.persistence_file)
