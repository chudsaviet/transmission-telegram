import os.path
import logging


class Persistence:

    def __init__(self, persistence_file):
        self.authorized_chats = list()
        self.persistence_file = persistence_file

        if persistence_file and os.path.isfile(persistence_file):
            logging.info('Loading authorized chats from %s' % persistence_file)

            i = 0
            file = open(persistence_file)
            for line in file:
                stripped_line = line.strip('\n\r')
                # skip empty lines
                if stripped_line:
                    self.authorized_chats.append(int(stripped_line))
                    i += 1
            file.close()
            logging.info('Loaded %d authorized chats' % i)

    def check_chat_id(self, chat_id):
        return chat_id in self.authorized_chats

    def add_chat_id(self, chat_id):
        if not self.check_chat_id(chat_id):
            file = open(self.persistence_file, mode='a')
            file.write(str(chat_id))
            file.write('\n')
            file.close()
            self.authorized_chats.append(chat_id)

    def save_state(self):
        file = open(self.persistence_file, mode='w')
        for chat_id in self.authorized_chats:
            file.write(chat_id)
            file.write('\n')
        file.close()
