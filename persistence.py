import os.path
import logging


class Persistence:

    def __init__(self, persistence_file):
        self.authorized_chats = list()
        self.persistence_file = persistence_file

        if persistence_file and os.path.isfile(persistence_file):
            logging.info('Loading authorized chats from %s' % persistence_file)

            i = 0
            with open(persistence_file) as f:
                for line in f:
                    stripped_line = line.strip('\n\r')
                    # skip empty lines
                    if stripped_line:
                        self.authorized_chats.append(int(stripped_line))
                        i += 1
            logging.info('Loaded %d authorized chats' % i)

    def check_chat_id(self, chat_id):
        return chat_id in self.authorized_chats

    def add_chat_id(self, chat_id):
        if not self.check_chat_id(chat_id):
            with open(self.persistence_file, mode='a') as f:
                f.write(str(chat_id))
                f.write('\n')
            self.authorized_chats.append(chat_id)

    def save_state(self):
        with open(self.persistence_file, mode='w') as f:
            for chat_id in self.authorized_chats:
                f.write(chat_id)
                f.write('\n')
